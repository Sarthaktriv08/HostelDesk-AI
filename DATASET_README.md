# Hostel Desk training data

## Source workbook
`chandigarh-university-hostel-survey-10000-students-final(2).xlsx` was supplied for this task. Its Read Me sheet explicitly describes the 10,000 rows as a **synthetic, illustrative dataset**, not real data collected from actual Chandigarh University students.

## Files
- `hostel_survey_cleaned.csv`: all 10,000 survey rows with direct identifiers (`S.No`, `Student Name`, `Roll Number`) removed. This is for survey analysis and category distribution, not direct text-model training.
- `survey_problem_category_summary.csv`: category counts and percentages from the cleaned survey.
- `complaint_text_training.csv`: 640 synthetic complaint-text examples across 8 issue categories, built for training a text classifier. Each row includes a `template_id` so test data can be split by base template.
- `../ml/hostel_complaint_model.joblib`: fitted model created by running the training script.
- `../ml/model_metadata.json`: evaluation metrics and training provenance.

## Important distinction
The workbook has a `Most Frequent Problem Faced` category but it does not contain a matched, labeled free-text complaint for every respondent. Therefore it would be misleading to pretend its survey rows directly train a complaint-text classifier. The text examples in `complaint_text_training.csv` are synthetic and use the issue-category names from the workbook as a taxonomy. The model is trained on those examples, while the cleaned 10,000-row survey is included for project analytics and to guide category choices.

## Privacy and authenticity
Direct identifiers were removed from the cleaned survey export. The source workbook itself says all names, roll numbers, and responses are simulated. Do not describe this as a real survey of 10,000 students. Replace/augment it with consented, genuine, labeled complaints when available.

## Training command
From the `backend` directory:
```powershell
py -m pip install -r requirements.txt
py ml/train_model.py
```
