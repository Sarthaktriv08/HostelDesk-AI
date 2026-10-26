from datetime import datetime, timedelta, timezone
from typing import Optional
import os, uuid
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from sqlalchemy import create_engine, String, Text, DateTime, ForeignKey, select, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session
from jose import jwt, JWTError
from passlib.context import CryptContext

class Settings(BaseSettings):
    secret_key: str = "CHANGE_ME_BEFORE_DEPLOYMENT"
    database_url: str = "sqlite:///./hostel_desk.db"
    frontend_origin: str = "http://localhost:5500"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    class Config:
        env_file = ".env"
        extra = "ignore"
settings=Settings()
connect_args={"check_same_thread":False} if settings.database_url.startswith("sqlite") else {}
engine=create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal=sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
class Base(DeclarativeBase): pass
class User(Base):
    __tablename__="users"
    id: Mapped[int]=mapped_column(primary_key=True)
    name: Mapped[str]=mapped_column(String(120))
    email: Mapped[str]=mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str]=mapped_column(String(255))
    role: Mapped[str]=mapped_column(String(20), default="student")
    hostel: Mapped[str]=mapped_column(String(100), default="")
class Complaint(Base):
    __tablename__="complaints"
    id: Mapped[int]=mapped_column(primary_key=True)
    ticket_id: Mapped[str]=mapped_column(String(30), unique=True, index=True)
    title: Mapped[str]=mapped_column(String(200))
    description: Mapped[str]=mapped_column(Text)
    category: Mapped[str]=mapped_column(String(80), default="Other")
    priority: Mapped[str]=mapped_column(String(20), default="medium")
    status: Mapped[str]=mapped_column(String(30), default="submitted")
    hostel: Mapped[str]=mapped_column(String(100), default="")
    room: Mapped[str]=mapped_column(String(50), default="")
    student_id: Mapped[int]=mapped_column(ForeignKey("users.id"))
    assigned_to: Mapped[Optional[str]]=mapped_column(String(120), nullable=True)
    warden_remark: Mapped[Optional[str]]=mapped_column(Text, nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)
Base.metadata.create_all(engine)
pwd=CryptContext(schemes=["argon2"], deprecated="auto")
oauth=OAuth2PasswordBearer(tokenUrl="/api/auth/token")
app=FastAPI(title=settings.app_name if hasattr(settings,"app_name") else "Hostel Desk API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://hosteldesk-ai-frontend.onrender.com",
        "http://localhost:3000",
        "http://127.0.0.1:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
def get_db():
    db=SessionLocal()
    try: yield db
    finally: db.close()
def token_for(u):
    return jwt.encode({"sub":str(u.id),"role":u.role,"exp":datetime.now(timezone.utc)+timedelta(hours=12)},settings.secret_key,algorithm="HS256")
def current_user(token:str=Depends(oauth), db:Session=Depends(get_db)):
    try: uid=int(jwt.decode(token,settings.secret_key,algorithms=["HS256"])["sub"])
    except (JWTError,ValueError): raise HTTPException(401,"Invalid or expired token")
    u=db.get(User,uid)
    if not u: raise HTTPException(401,"User not found")
    return u
def warden(u=Depends(current_user)):
    if u.role not in ("warden","admin"): raise HTTPException(403,"Warden access required")
    return u
class Register(BaseModel):
    name:str=Field(min_length=2,max_length=120)
    email:str
    password:str=Field(min_length=8)
    role:str="student"
    hostel:str=""
class ComplaintIn(BaseModel):
    title:str=Field(min_length=3,max_length=200)
    description:str=Field(min_length=10,max_length=10000)
    category:str="Other"
    priority:str="medium"
    hostel:str=""
    room:str=""
class UpdateComplaint(BaseModel):
    status:Optional[str]=None
    priority:Optional[str]=None
    assigned_to:Optional[str]=None
    warden_remark:Optional[str]=None
def serialize(c):
    return {"id":c.id,"ticket_id":c.ticket_id,"title":c.title,"description":c.description,"category":c.category,"priority":c.priority,"status":c.status,"hostel":c.hostel,"room":c.room,"student_id":c.student_id,"assigned_to":c.assigned_to,"warden_remark":c.warden_remark,"created_at":c.created_at.isoformat()}
@app.get("/api/health")
def health(): return {"ok":True,"service":"Hostel Desk API","ai_configured":bool(settings.gemini_api_key)}
@app.post("/api/auth/register",status_code=201)
def register(data:Register,db:Session=Depends(get_db)):
    email=data.email.strip().lower()
    if db.scalar(select(User).where(User.email==email)): raise HTTPException(409,"Email already registered")
    # Public registration cannot grant privileged roles.
    u=User(name=data.name.strip(),email=email,password_hash=pwd.hash(data.password),role="student",hostel=data.hostel)
    db.add(u);db.commit();db.refresh(u)
    return {"access_token":token_for(u),"token_type":"bearer","user":{"id":u.id,"name":u.name,"email":u.email,"role":u.role,"hostel":u.hostel}}
@app.post("/api/auth/token")
def login(form:OAuth2PasswordRequestForm=Depends(),db:Session=Depends(get_db)):
    u=db.scalar(select(User).where(User.email==form.username.lower().strip()))
    if not u or not pwd.verify(form.password,u.password_hash): raise HTTPException(401,"Incorrect email or password")
    return {"access_token":token_for(u),"token_type":"bearer"}
@app.get("/api/users/me")
def me(u=Depends(current_user)): return {"id":u.id,"name":u.name,"email":u.email,"role":u.role,"hostel":u.hostel}
@app.post("/api/complaints",status_code=201)
def create_complaint(data:ComplaintIn,u=Depends(current_user),db:Session=Depends(get_db)):
    text=(data.title+" "+data.description+" "+data.category).lower()
    urgent=any(k in text for k in ["fire","smoke","sparking","electric shock","emergency","gas leak"])
    priority="high" if urgent else data.priority.lower()
    if priority not in ("low","medium","high"): priority="medium"
    category = data.category
    # If no category was selected (or the generic default was used), ask the local trained model.
    if not category or category.strip().lower() == "other":
        try:
            from ml.predict import predict_category
            category = predict_category(data.title + ". " + data.description)["category"]
        except (FileNotFoundError, ValueError):
            category = data.category or "Other"
    ticket="HD-"+uuid.uuid4().hex[:8].upper()
    c=Complaint(ticket_id=ticket,title=data.title,description=data.description,category=category,priority=priority,hostel=data.hostel or u.hostel,room=data.room,student_id=u.id)
    db.add(c);db.commit();db.refresh(c);return serialize(c)
@app.get("/api/complaints")
def list_complaints(u=Depends(current_user),db:Session=Depends(get_db)):
    q=select(Complaint).order_by(Complaint.created_at.desc())
    if u.role=="student": q=q.where(Complaint.student_id==u.id)
    return [serialize(c) for c in db.scalars(q).all()]
@app.get("/api/complaints/{ticket_id}/track")
def track(ticket_id:str,u=Depends(current_user),db:Session=Depends(get_db)):
    c=db.scalar(select(Complaint).where(Complaint.ticket_id==ticket_id))
    if not c or (u.role=="student" and c.student_id!=u.id): raise HTTPException(404,"Complaint not found")
    return serialize(c)
@app.patch("/api/complaints/{ticket_id}")
def update(ticket_id:str,data:UpdateComplaint,u=Depends(warden),db:Session=Depends(get_db)):
    c=db.scalar(select(Complaint).where(Complaint.ticket_id==ticket_id))
    if not c: raise HTTPException(404,"Complaint not found")
    if data.status is not None:
        if data.status not in ("submitted","analysis","assigned","in_progress","resolved","rejected","cancelled"): raise HTTPException(422,"Invalid status")
        c.status=data.status
    if data.priority is not None:
        if data.priority not in ("low","medium","high"): raise HTTPException(422,"Invalid priority")
        c.priority=data.priority
    if data.assigned_to is not None:c.assigned_to=data.assigned_to
    if data.warden_remark is not None:c.warden_remark=data.warden_remark
    db.commit();db.refresh(c);return serialize(c)
@app.get("/api/dashboard/stats")
def stats(u=Depends(current_user),db:Session=Depends(get_db)):
    q=select(Complaint)
    if u.role=="student":q=q.where(Complaint.student_id==u.id)
    rows=db.scalars(q).all()
    return {"total":len(rows),"pending":sum(c.status not in ("resolved","rejected","cancelled") for c in rows),"resolved":sum(c.status=="resolved" for c in rows),"high_priority":sum(c.priority=="high" and c.status!="resolved" for c in rows)}
class MLClassifyIn(BaseModel):
    complaint_text: str = Field(min_length=5, max_length=10000)

@app.post("/api/ml/classify")
def classify_with_trained_model(data: MLClassifyIn, u=Depends(current_user)):
    """Classify complaint category using the locally trained scikit-learn model."""
    try:
        from predict import predict_category
        result = predict_category(data.complaint_text)
        return {"source": "local_trained_model", **result}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

@app.get("/api/ml/info")
def trained_model_info(u=Depends(current_user)):
    """Return training metadata for the local complaint classifier."""
    from pathlib import Path
    import json
    metadata_path = Path(__file__).resolve().parent / "model_metadata.json"
    if not metadata_path.exists():
        raise HTTPException(status_code=503, detail="Model metadata not found. Train the model first.")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    # Keep this response compact; detailed per-class metrics remain in the metadata file.
    return {
        "model_name": metadata.get("model_name"),
        "algorithm": metadata.get("algorithm"),
        "training_examples": metadata.get("training_examples"),
        "test_examples": metadata.get("test_examples"),
        "categories": metadata.get("categories"),
        "test_accuracy": metadata.get("test_accuracy"),
        "macro_f1": metadata.get("macro_f1"),
        "data_source": metadata.get("data_source"),
        "evaluation_note": metadata.get("evaluation_note"),
    }

class AnalyzeIn(BaseModel):
    description:str=Field(min_length=5,max_length=10000)
    category:str="Other"
@app.post("/api/ai/analyze")
def analyze(data:AnalyzeIn,u=Depends(current_user)):
    text=data.description
    if settings.gemini_api_key:
        try:
            from google import genai
            client=genai.Client(api_key=settings.gemini_api_key)
            response=client.models.generate_content(model=settings.gemini_model,contents=f"Classify this hostel complaint. Return concise JSON with category, priority (low/medium/high), and suggested_action. Never downplay danger. Complaint: {text}")
            return {"source":"gemini","analysis":response.text}
        except Exception:
            pass
    t=text.lower()
    pairs=[(["wire","electric","fan","light","socket","power"],"Electrical"),(["water","tap","pipe","leak","toilet","plumbing"],"Water & plumbing"),(["wifi","internet","network"],"Wi-Fi & internet"),(["clean","garbage","dust"],"Cleanliness"),(["food","mess","meal"],"Mess & food"),(["security","threat","theft"],"Security")]
    cat=next((name for keys,name in pairs if any(k in t for k in keys)),data.category or "Other")
    priority="high" if any(k in t for k in ["fire","smoke","sparking","shock","gas leak","emergency"]) else ("medium" if any(k in t for k in ["broken","leak","not working","blocked"]) else "low")
    return {"source":"rules_fallback","category":cat,"priority":priority,"suggested_action":"Contact the hostel warden immediately for any safety emergency." if priority=="high" else "Review and assign to the appropriate hostel maintenance team."}
