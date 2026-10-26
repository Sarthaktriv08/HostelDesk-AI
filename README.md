# Hostel Desk — Full Project + Trained ML Classifier

This package contains the existing frontend, FastAPI backend, SQLite-backed complaint APIs, and a trained local complaint-text classifier.

## Quick start
1. Extract the ZIP.
2. Open the `backend` folder in VS Code.
3. In Terminal, run:
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   py -m pip install -r requirements.txt
   py ml/train_model.py
   uvicorn app.main:app --reload --port 8000
   ```
4. Open `http://127.0.0.1:8000/docs`.

See `backend/README.md` for details.

**Data/accuracy disclaimer:** The source workbook explicitly says its 10,000 survey responses are simulated. The complaint-text training examples are also synthetic. The included evaluation score is measured on held-out synthetic templates, not real hostel complaints. Collect and label genuine complaints to evaluate real-world accuracy.
