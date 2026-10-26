# Hostel Desk Backend

## Setup (Windows / VS Code)
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
```
If activation is blocked, run `py -m pip install -r requirements.txt` and `py ml/train_model.py` without activating.

## Train the local ML model
From this `backend` directory:
```powershell
py ml/train_model.py
py ml/predict.py
```
The model is saved to `ml/hostel_complaint_model.joblib`. The model is a local TF-IDF + Logistic Regression classifier and does not require Gemini to classify a complaint.

## Start API
```powershell
uvicorn app.main:app --reload --port 8000
```
Open `http://127.0.0.1:8000/docs`.

## ML endpoints
- `POST /api/ml/classify` — requires a bearer token; body example: `{{"complaint_text":"The fan in my room has stopped working"}}`.
- `GET /api/ml/info` — requires a bearer token; displays training/evaluation metadata.
- When creating a complaint with category `Other`, the backend attempts local model classification.

## Dataset transparency
`data/hostel_survey_cleaned.csv` contains 10,000 survey rows with direct identifiers removed. The uploaded workbook's Read Me sheet states these are simulated responses, not actual student survey results. `data/complaint_text_training.csv` is a separate synthetic text dataset created for the complaint classifier because the workbook does not provide matching free-text complaint labels for each respondent. Read `data/DATASET_README.md` before presenting the model results.

## Notes
The frontend is preserved from the previous package. Its existing UI has not been rewritten to consume all API routes automatically; use `/docs` to test the backend endpoints.
