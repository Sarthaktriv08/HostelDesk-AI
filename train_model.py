"""Train the Hostel Desk complaint-text classifier.

The survey workbook contains 10,000 synthetic survey responses, but no free-text
complaint label for each row. Therefore this text model uses a separate,
explicitly synthetic complaint-example dataset whose category names come from
the survey's 'Most Frequent Problem Faced' field. Test data is split by base
template, so paraphrases of a training template do not leak into test data.
"""
from pathlib import Path
import json
import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import FeatureUnion
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.pipeline import Pipeline
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

ROOT = Path(__file__).resolve().parent
DATA = ROOT.parent / "data" / "complaint_text_training.csv"
MODEL = ROOT / "hostel_complaint_model.joblib"
METADATA = ROOT / "model_metadata.json"

def main():
    df = pd.read_csv(DATA).dropna(subset=["complaint_text", "category", "template_id"])
    df["complaint_text"] = df["complaint_text"].astype(str).str.strip()
    df["category"] = df["category"].astype(str).str.strip()
    df = df[(df.complaint_text != "") & (df.category != "")]
    splitter = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=42)
    train_idx, test_idx = next(splitter.split(df, df["category"], groups=df["template_id"]))
    train_df, test_df = df.iloc[train_idx], df.iloc[test_idx]
    model = Pipeline([
        ("features", FeatureUnion([
            ("word", TfidfVectorizer(ngram_range=(1, 2), lowercase=True, strip_accents="unicode", sublinear_tf=True)),
            ("character", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), lowercase=True, sublinear_tf=True)),
        ])),
        ("classifier", CalibratedClassifierCV(
            estimator=LinearSVC(C=1.0, class_weight="balanced", random_state=42),
            cv=3,
        )),
    ])
    model.fit(train_df["complaint_text"], train_df["category"])
    pred = model.predict(test_df["complaint_text"])
    labels = sorted(df["category"].unique().tolist())
    accuracy = float(accuracy_score(test_df["category"], pred))
    report = classification_report(test_df["category"], pred, labels=labels, output_dict=True, zero_division=0)
    cm = confusion_matrix(test_df["category"], pred, labels=labels)
    joblib.dump(model, MODEL)
    metadata = {
        "model_name": "Hostel Desk Complaint Category Classifier",
        "algorithm": "TF-IDF word + character n-grams + calibrated LinearSVC",
        "training_examples": int(len(train_df)),
        "test_examples": int(len(test_df)),
        "unique_templates": int(df["template_id"].nunique()),
        "train_templates": int(train_df["template_id"].nunique()),
        "test_templates": int(test_df["template_id"].nunique()),
        "categories": labels,
        "test_accuracy": round(accuracy, 4),
        "macro_precision": round(float(report["macro avg"]["precision"]), 4),
        "macro_recall": round(float(report["macro avg"]["recall"]), 4),
        "macro_f1": round(float(report["macro avg"]["f1-score"]), 4),
        "classification_report": report,
        "confusion_matrix": {"labels": labels, "matrix": cm.tolist()},
        "data_source": "Synthetic complaint examples. Category taxonomy informed by the uploaded survey's problem categories. The survey workbook itself is marked as simulated and is not real student data.",
        "evaluation_note": "Scores measure performance on held-out synthetic templates only. They do not establish accuracy on real student complaints; collect and label real complaints for a reliable estimate.",
        "random_state": 42,
    }
    METADATA.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print("Training complete.")
    print(f"Saved model: {MODEL}")
    print(f"Training examples: {len(train_df)}; test examples: {len(test_df)}")
    print(f"Categories: {', '.join(labels)}")
    print(f"Held-out synthetic-template accuracy: {accuracy:.3f}")
    print(f"Macro F1: {report['macro avg']['f1-score']:.3f}")
    print("Important: this is a synthetic-data benchmark, not verified real-world accuracy.")

if __name__ == "__main__":
    main()
