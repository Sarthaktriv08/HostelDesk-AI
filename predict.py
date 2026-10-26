```python
"""Load the saved model once and classify a hostel complaint."""
from pathlib import Path
import joblib

MODEL_PATH = Path(__file__).resolve().parent / "hostel_complaint_model.joblib"
_MODEL = None


def _load_model():
    global _MODEL

    if _MODEL is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Model file not found at {MODEL_PATH}. "
                "Ensure hostel_complaint_model.joblib is present in the repository."
            )

        _MODEL = joblib.load(MODEL_PATH)

    return _MODEL


def predict_category(complaint_text: str) -> dict:
    text = complaint_text.strip()

    if len(text) < 5:
        raise ValueError(
            "Please provide a complaint description of at least 5 characters."
        )

    model = _load_model()
    probabilities = model.predict_proba([text])[0]
    index = int(probabilities.argmax())

    return {
        "category": str(model.classes_[index]),
        "confidence": round(float(probabilities[index]), 4),
        "model": "TF-IDF + calibrated LinearSVC",
        "note": (
            "Confidence is a model score, not a guarantee of correctness. "
            "The model was trained on synthetic examples."
        ),
    }


if __name__ == "__main__":
    while True:
        complaint = input("Enter complaint (or 'exit'): ").strip()

        if complaint.lower() == "exit":
            break

        if complaint:
            print(predict_category(complaint))
```
