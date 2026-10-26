# Hostel Desk complaint classifier

- Algorithm: TF-IDF word + character n-grams + calibrated LinearSVC.
- Training examples: 480.
- Held-out test examples: 160.
- Held-out synthetic-template accuracy: 66.2%.
- Held-out macro F1: 0.632.

The held-out split groups all variations of each base template together, which reduces direct template leakage. Nevertheless, both train and test data are synthetic; the metrics are only a prototype benchmark and should not be claimed as real-world accuracy.

## Retrain
From `backend/`:
```powershell
py -m pip install -r requirements.txt
py ml/train_model.py
```

## Try predictions
```powershell
py ml/predict.py
```

## API
- `POST /api/ml/classify` — authenticated endpoint; JSON body: `{"complaint_text":"The fan in my room has stopped working"}`.
- `GET /api/ml/info` — authenticated model metadata endpoint.
- Complaint creation uses the trained model when category is blank or `Other`.

This model predicts one of 8 categories: Electrical, Wi-Fi & internet, Cleanliness, Water & plumbing, Mess & food, Furniture, Security, Medical.
