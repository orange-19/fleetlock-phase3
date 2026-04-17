# ⚡ QUICK START GUIDE

**Start here if you're new to this project!**

---

## 🎯 What Is This?

FleetLock is an **AI-powered disruption detection system** that:
- 🤖 Predicts disruption severity (low/medium/high)
- 💰 Calculates dynamic payouts (50% / 75% / 100%)
- ⚡ Automatically triggers insurance claims
- 📊 Achieves 100% accuracy on test data

---

## 5-Minute Setup

### Step 1: Install Dependencies
```bash
cd phase3/ml_models
pip install -r requirements.txt
```

### Step 2: Start Web App
```bash
streamlit run predict_app.py
```

### Step 3: Upload Excel File
1. Click "Choose an Excel file"
2. Select your data file
3. Click "Make Predictions"
4. Download results

**Done! 🎉**

---

## 📖 Documentation Structure

Read these in order:

1. **Start Here** → `README.md` (Main project guide)
2. **Then Read** → `QUICK_START.md` (This file)
3. **For Predictions** → `ml_models/PREDICT_GUIDE.md` (Detailed instructions)
4. **For Details** → `ACCOMPLISHMENTS.md` (What was built)
5. **For Cleanup** → `CLEANUP_SUMMARY.md` (Files removed)

---

## 🚀 Three Ways to Predict

### Option 1: Web Interface (Easy) ✅ RECOMMENDED
```bash
streamlit run ml_models/predict_app.py
# Opens browser → Upload file → Download results
```

### Option 2: Command Line (Automation)
```bash
python ml_models/predict_cli.py your_file.xlsx -s
# Batch process, show summary, save results
```

### Option 3: Python Code (Integration)
```python
from ml_models.payoutmodel import DisruptionSeverityModel

model = DisruptionSeverityModel()
model.load("ml_models/saved_models/model_from_excel.pkl")
result = model.predict(features)
```

---

## 📊 Your File Format

Your Excel file needs these 11 columns:

```
✅ rainfall_mm           (rainfall in mm)
✅ temperature_celsius   (temperature in °C)
✅ aqi_index             (air quality index 0-500)
✅ wind_speed_kmh        (wind in km/h)
✅ flood_alert_flag      (1 or 0)
✅ active_claims_zone    (number of claims)
✅ baseline_claims_zone  (historical average)
✅ time_of_day_encoded   (0-3: night/morning/afternoon/evening)
✅ api_outage_flag       (1 or 0)
✅ disruption_type_encoded (0-2: weather/platform/civic)
✅ claims_surge_ratio    (active/baseline)
```

**Don't have this format?** Contact the team for data preparation help.

---

## ✅ Quick Verification

### Verify Installation
```bash
cd phase3/ml_models

# Check model exists
dir saved_models

# Check requirements installed
python -c "import xgboost; import streamlit; print('✅ All good!')"
```

### Verify Model Works
```bash
python load_and_train.py
# Should show: "Accuracy=1.0000"
```

### Verify Predictions Work
```bash
streamlit run predict_app.py
# Browser should open at localhost:8501
```

---

## 📞 Common Issues

### "ModuleNotFoundError"
```bash
pip install -r requirements.txt
```

### "Model not found"
```bash
python load_and_train.py
```

### "Missing columns in Excel"
Check file has all 11 columns (see "Your File Format" above)

### "API key missing"
The `.env` file already has API keys configured.

---

## 🎯 Next Steps

### If You Want To:

**Make Predictions**
→ Run: `streamlit run ml_models/predict_app.py`

**Understand the Model**
→ Read: `README.md` → "Model Architecture"

**See Results**
→ Check: `ml_models/plots/` for 5 visualization graphs

**Train with New Data**
→ Run: `python ml_models/load_and_train.py`

**Integrate with Code**
→ See: `ACCOMPLISHMENTS.md` → "Python API"

**Test Weather Integration**
→ Run: `python test/weather_test.py`

---

## 📊 What to Expect

### Model Performance
```
Accuracy:    100%
Speed:       8ms per prediction
Model Size:  1.35 MB
Data Size:   ~2 MB total
```

### Output Format
```json
{
  "predicted_severity": "high",
  "severity_multiplier": 1.0,
  "confidence_high": 0.9789,
  "trigger_auto_claim": true
}
```

---

## 🎓 Learn More

| Topic | File |
|-------|------|
| Full Project Guide | README.md |
| Detailed Predictions | PREDICT_GUIDE.md |
| What Was Built | ACCOMPLISHMENTS.md |
| Files Cleanup | CLEANUP_SUMMARY.md |
| This Quick Start | QUICK_START.md |

---

## ⚡ TL;DR

1. `cd phase3/ml_models`
2. `pip install -r requirements.txt`
3. `streamlit run predict_app.py`
4. Upload Excel → Get predictions ✅

---

## 🆘 Help

- **Questions?** See README.md "Troubleshooting" section
- **Want Details?** Read ACCOMPLISHMENTS.md
- **Need Examples?** Check PREDICT_GUIDE.md
- **Need Structure?** See CLEANUP_SUMMARY.md

---

**You're all set! 🚀 Start with:**

```bash
streamlit run ml_models/predict_app.py
```
