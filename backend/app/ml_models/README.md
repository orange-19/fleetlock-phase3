# DisruptionSeverityModel - Training & Visualization Guide

## Overview
This package contains:
- **payoutmodel.py**: Main model class with persistence methods (save/load)
- **train_and_visualize.py**: Training script with comprehensive visualizations
- **requirements.txt**: Dependencies

## What's New

### ✅ Model Persistence Features Added
The model now has `save()` and `load()` methods supporting:
- **joblib** format (default, fastest)
- **pickle** format (compatible)
- Automatic directory creation

### ✅ Visualizations Generated
Running the script generates 5 comprehensive graphs:

1. **confusion_matrix.png** - Shows prediction accuracy matrix
2. **classification_metrics.png** - Precision, Recall, F1-Score per class
3. **confidence_distribution.png** - Model confidence score distribution
4. **accuracy_summary.png** - Overall performance dashboard
5. **roc_curves.png** - ROC curves for multi-class classification

## Installation

```bash
cd ml_models
pip install -r requirements.txt
```

## Quick Start

### 1. Train Model & Generate Visualizations
```bash
python train_and_visualize.py
```

This will:
- Train the model on synthetic data
- Generate 5 visualization PNG files in `./plots/`
- Save trained model to `./saved_models/`
- Display accuracy metrics in console

### 2. Use Model Persistence

#### Save a trained model:
```python
from payoutmodel import DisruptionSeverityModel

model = DisruptionSeverityModel()
model.train()  # or load from data

# Save with joblib (recommended - fastest)
model.save("my_model.pkl", format="joblib")

# Or with pickle
model.save("my_model.pkl", format="pickle")
```

#### Load a saved model:
```python
model = DisruptionSeverityModel()
model.load("my_model.pkl", format="joblib")

# Model is ready to use
result = model.predict(features)
```

## Model Performance Indicators

The visualization script shows:

| Metric | What It Shows |
|--------|---------------|
| **Overall Accuracy** | Percentage of correct predictions |
| **Confusion Matrix** | How predictions map to actual classes |
| **F1-Score** | Balance between precision & recall per class |
| **Confidence Distribution** | Model certainty levels |
| **ROC Curves** | True positive vs false positive rate |

## Output Files Structure

```
ml_models/
├── payoutmodel.py
├── train_and_visualize.py
├── requirements.txt
├── saved_models/
│   ├── disruption_model_joblib.pkl    (trained model - joblib)
│   └── disruption_model_pickle.pkl    (trained model - pickle)
└── plots/
    ├── confusion_matrix.png
    ├── classification_metrics.png
    ├── confidence_distribution.png
    ├── accuracy_summary.png
    └── roc_curves.png
```

## Sample Code - Custom Training

```python
from payoutmodel import DisruptionSeverityModel
import pandas as pd

# Create and train model
model = DisruptionSeverityModel()

# Option 1: Use synthetic data (default)
metrics = model.train()
print(f"Accuracy: {metrics['accuracy']:.4f}")

# Option 2: Use your own data
# X: DataFrame with features, y: Series with labels (0=low, 1=medium, 2=high)
metrics = model.train(X=your_features, y=your_labels)

# Save model
model.save("production_model.pkl", format="joblib")

# Later: Load and predict
model = DisruptionSeverityModel()
model.load("production_model.pkl")
result = model.predict(features)
```

## Model Information

- **Model Type**: XGBClassifier + Isotonic Calibration
- **Classes**: low (0.50 payout), medium (0.75 payout), high (1.00 payout)
- **Features**: 11 environmental & operational signals
- **Auto-Trigger**: Parametric thresholds for emergency claims
- **Fallback**: Rule-based logic if model unavailable

## Troubleshooting

### "Model must be trained before saving"
Train the model first:
```python
model.train()
model.save("model.pkl")
```

### Plots not displaying on Windows
Ensure matplotlib backend works:
```python
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
```

### Memory issues with large datasets
Use smaller `n_samples` in `generate_synthetic_data()`:
```python
X, y = model.generate_synthetic_data(n_samples=1000)  # Instead of 5000
```

## Next Steps

1. ✅ Run `python train_and_visualize.py` to see the graphs
2. ✅ Review the accuracy metrics in `plots/accuracy_summary.png`
3. ✅ Check for saved models in `saved_models/`
4. ✅ Integrate model persistence into production code
5. ✅ Use ROC curves to tune decision thresholds as needed
