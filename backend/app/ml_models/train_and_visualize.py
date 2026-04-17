"""
train_and_visualize.py
Trains the DisruptionSeverityModel with Excel data and generates comprehensive visualizations
for accuracy prediction and model performance analysis.
Also demonstrates model persistence (save/load).
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (
    confusion_matrix,
    classification_report,
    roc_curve,
    auc,
)
from sklearn.preprocessing import label_binarize
from sklearn.model_selection import train_test_split

from app.ml_models.payoutmodel import (
    DisruptionSeverityModel,
    DisruptionFeatures,
    DISRUPTION_FEATURES,
)

# Excel file path
EXCEL_FILE = r"C:\Users\RAMNARREN GOWTHAM\Downloads\synthetic_disruption_data.xlsx"

# ── Setup ──────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create output directory for models and plots
MODEL_DIR = Path(__file__).parent / "saved_models"
PLOT_DIR = Path(__file__).parent / "plots"
MODEL_DIR.mkdir(exist_ok=True)
PLOT_DIR.mkdir(exist_ok=True)

# Set style for plots
sns.set_style("whitegrid")
plt.rcParams["figure.figsize"] = (14, 10)   


# ── Training ───────────────────────────────────────────────────────────────────

def train_and_evaluate():
    """Train model with Excel data and return metrics + test data for visualization."""
    logger.info("=" * 80)
    logger.info("TRAINING DisruptionSeverityModel WITH EXCEL DATA")
    logger.info("=" * 80)
    
    # Load Excel data
    logger.info(f"\nLoading Excel data from: {EXCEL_FILE}")
    df = pd.read_excel(EXCEL_FILE)
    logger.info(f"✓ Loaded {len(df)} rows, {len(df.columns)} columns")
    
    # Extract features and labels
    X = df[DISRUPTION_FEATURES]
    y = df['severity_label']  # 0=low, 1=medium, 2=high
    
    logger.info(f"✓ Label distribution:\n{y.value_counts().sort_index()}")
    
    # Initialize and train
    model = DisruptionSeverityModel(random_state=42)
    logger.info("\nTraining model...")
    metrics = model.train(X, y)
    
    logger.info(f"\n✓ Model Accuracy: {metrics['accuracy']:.4f}")
    logger.info(f"Classification Report:\n{pd.DataFrame(metrics['classification_report']).T}")
    
    # Get test set for visualization
    X_train, X_test, y_train, y_test = train_test_split(
        X[DISRUPTION_FEATURES], y,
        test_size=0.20, random_state=42, stratify=y
    )
    
    return model, X_test, y_test, metrics


# ── Visualization Functions ────────────────────────────────────────────────────

def plot_confusion_matrix(model, X_test, y_test):
    """Plot confusion matrix heatmap."""
    logger.info("Generating confusion matrix visualization...")
    
    y_pred = model.model.predict(X_test)
    cm = confusion_matrix(y_test, y_pred)
    
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(
        cm, annot=True, fmt='d', cmap='Blues', ax=ax,
        xticklabels=['low', 'medium', 'high'],
        yticklabels=['low', 'medium', 'high']
    )
    ax.set_xlabel('Predicted Severity', fontsize=12)
    ax.set_ylabel('True Severity', fontsize=12)
    ax.set_title('Confusion Matrix - Model Predictions', fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    filepath = PLOT_DIR / "confusion_matrix.png"
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    logger.info(f"✓ Saved: {filepath}")
    plt.close()


def plot_classification_metrics(metrics):
    """Plot precision, recall, f1-score for each class."""
    logger.info("Generating classification metrics visualization...")
    
    report = metrics["classification_report"]
    classes = ['low', 'medium', 'high']
    
    precision = [report[cls]['precision'] for cls in classes]
    recall = [report[cls]['recall'] for cls in classes]
    f1_score = [report[cls]['f1-score'] for cls in classes]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    x = np.arange(len(classes))
    width = 0.25
    
    ax.bar(x - width, precision, width, label='Precision', alpha=0.8)
    ax.bar(x, recall, width, label='Recall', alpha=0.8)
    ax.bar(x + width, f1_score, width, label='F1-Score', alpha=0.8)
    
    ax.set_xlabel('Severity Class', fontsize=12)
    ax.set_ylabel('Score', fontsize=12)
    ax.set_title('Classification Metrics by Severity Class', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(classes)
    ax.legend()
    ax.set_ylim([0, 1.1])
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    filepath = PLOT_DIR / "classification_metrics.png"
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    logger.info(f"✓ Saved: {filepath}")
    plt.close()


def plot_confidence_distribution(model, X_test, y_test):
    """Plot distribution of model confidence scores."""
    logger.info("Generating confidence distribution visualization...")
    
    proba = model.model.predict_proba(X_test)
    max_confidence = np.max(proba, axis=1)
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # Overall confidence distribution
    axes[0].hist(max_confidence, bins=30, color='skyblue', edgecolor='black', alpha=0.7)
    axes[0].axvline(max_confidence.mean(), color='red', linestyle='--', linewidth=2, label=f'Mean: {max_confidence.mean():.3f}')
    axes[0].set_xlabel('Max Confidence Score', fontsize=11)
    axes[0].set_ylabel('Frequency', fontsize=11)
    axes[0].set_title('Distribution of Model Confidence', fontsize=12, fontweight='bold')
    axes[0].legend()
    axes[0].grid(alpha=0.3)
    
    # Confidence by prediction correctness
    y_pred = model.model.predict(X_test)
    correct = max_confidence[y_pred == y_test]
    incorrect = max_confidence[y_pred != y_test]
    
    axes[1].hist([correct, incorrect], bins=25, label=['Correct', 'Incorrect'], 
                 color=['green', 'red'], alpha=0.6, edgecolor='black')
    axes[1].set_xlabel('Max Confidence Score', fontsize=11)
    axes[1].set_ylabel('Frequency', fontsize=11)
    axes[1].set_title('Confidence: Correct vs. Incorrect Predictions', fontsize=12, fontweight='bold')
    axes[1].legend()
    axes[1].grid(alpha=0.3)
    
    plt.tight_layout()
    filepath = PLOT_DIR / "confidence_distribution.png"
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    logger.info(f"✓ Saved: {filepath}")
    plt.close()


def plot_accuracy_summary(model, X_test, y_test, metrics):
    """Plot overall accuracy metrics and summary."""
    logger.info("Generating accuracy summary visualization...")
    
    y_pred = model.model.predict(X_test)
    accuracy = (y_pred == y_test).mean()
    
    classes = ['low', 'medium', 'high']
    report = metrics['classification_report']
    
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    
    # Overall Accuracy
    ax = axes[0, 0]
    ax.barh(['Model Accuracy'], [accuracy], color='#2ecc71', alpha=0.8)
    ax.set_xlim([0, 1])
    ax.set_title('Overall Accuracy', fontsize=12, fontweight='bold')
    ax.text(accuracy/2, 0, f'{accuracy:.4f}', ha='center', va='center', fontsize=14, fontweight='bold', color='white')
    
    # Per-class Accuracy
    ax = axes[0, 1]
    class_acc = [report[cls]['f1-score'] for cls in classes]
    colors = ['#3498db', '#f39c12', '#e74c3c']
    ax.barh(classes, class_acc, color=colors, alpha=0.8)
    ax.set_xlim([0, 1])
    ax.set_title('Per-Class F1-Score', fontsize=12, fontweight='bold')
    for i, v in enumerate(class_acc):
        ax.text(v/2, i, f'{v:.3f}', ha='center', va='center', fontsize=11, fontweight='bold', color='white')
    
    # Support per class
    ax = axes[1, 0]
    support = [int(report[cls]['support']) for cls in classes]
    ax.bar(classes, support, color=colors, alpha=0.8)
    ax.set_title('Test Set Distribution (Support)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Number of Samples')
    for i, v in enumerate(support):
        ax.text(i, v + 10, str(v), ha='center', fontsize=10, fontweight='bold')
    
    # Model Info
    ax = axes[1, 1]
    ax.axis('off')
    info_text = f"""
    MODEL PERFORMANCE SUMMARY
    {'='*50}
    
    Overall Accuracy:        {accuracy:.4f}
    Macro-Avg F1:            {report['macro avg']['f1-score']:.4f}
    Weighted Avg F1:         {report['weighted avg']['f1-score']:.4f}
    
    Test Set Size:           {len(y_test)} samples
    Model Version:           v2.1.0
    Calibration:             Isotonic Regression
    Base Estimator:          XGBClassifier
    
    Best Class:              {max([(c, report[c]['f1-score']) for c in classes], key=lambda x: x[1])[0]}
    Worst Class:             {min([(c, report[c]['f1-score']) for c in classes], key=lambda x: x[1])[0]}
    """
    ax.text(0.1, 0.5, info_text, fontsize=10, family='monospace',
            verticalalignment='center', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    filepath = PLOT_DIR / "accuracy_summary.png"
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    logger.info(f"✓ Saved: {filepath}")
    plt.close()


def plot_roc_curves(model, X_test, y_test):
    """Plot ROC curves for multi-class classification."""
    logger.info("Generating ROC curves visualization...")
    
    # Binarize output for ROC curve
    y_bin = label_binarize(y_test, classes=[0, 1, 2])
    proba = model.model.predict_proba(X_test)
    
    fig, ax = plt.subplots(figsize=(10, 8))
    
    colors = ['#3498db', '#f39c12', '#e74c3c']
    class_names = ['low', 'medium', 'high']
    
    for i, (color, cls_name) in enumerate(zip(colors, class_names)):
        fpr, tpr, _ = roc_curve(y_bin[:, i], proba[:, i])
        roc_auc = auc(fpr, tpr)
        ax.plot(fpr, tpr, color=color, lw=2.5, label=f'{cls_name} (AUC = {roc_auc:.3f})')
    
    # Diagonal line (random classifier)
    ax.plot([0, 1], [0, 1], 'k--', lw=1.5, label='Random Classifier')
    
    ax.set_xlabel('False Positive Rate', fontsize=12)
    ax.set_ylabel('True Positive Rate', fontsize=12)
    ax.set_title('ROC Curves - Multi-Class Classification', fontsize=14, fontweight='bold')
    ax.legend(loc='lower right', fontsize=10)
    ax.grid(alpha=0.3)
    
    plt.tight_layout()
    filepath = PLOT_DIR / "roc_curves.png"
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    logger.info(f"✓ Saved: {filepath}")
    plt.close()


# ── Model Persistence Demo ─────────────────────────────────────────────────────

def demonstrate_model_persistence(model):
    """Show save/load functionality."""
    logger.info("\n" + "=" * 80)
    logger.info("DEMONSTRATING MODEL PERSISTENCE")
    logger.info("=" * 80)
    
    model_path_joblib = MODEL_DIR / "disruption_model_joblib.pkl"
    model_path_pickle = MODEL_DIR / "disruption_model_pickle.pkl"
    
    # Save with joblib
    logger.info(f"Saving model (joblib format) to: {model_path_joblib}")
    model.save(model_path_joblib, format="joblib")
    logger.info(f"✓ File size: {model_path_joblib.stat().st_size / 1024:.2f} KB")
    
    # Save with pickle
    logger.info(f"Saving model (pickle format) to: {model_path_pickle}")
    model.save(model_path_pickle, format="pickle")
    logger.info(f"✓ File size: {model_path_pickle.stat().st_size / 1024:.2f} KB")
    
    # Load from joblib
    logger.info(f"\nLoading model from: {model_path_joblib}")
    loaded_model = DisruptionSeverityModel()
    loaded_model.load(model_path_joblib, format="joblib")
    logger.info("✓ Model loaded successfully (joblib)")
    
    # Test loaded model with sample data
    sample_features = DisruptionFeatures(
        zone_id="ZONE_TEST_001",
        rainfall_mm=85.5,
        temperature_celsius=38.2,
        aqi_index=220,
        wind_speed_kmh=45.3,
        flood_alert_flag=1,
        active_claims_zone=95,
        baseline_claims_zone=45,
        time_of_day_encoded=2,
        api_outage_flag=0,
        disruption_type="weather"
    )
    
    result = loaded_model.predict(sample_features)
    logger.info(f"\n✓ Loaded model prediction test:")
    logger.info(f"  - Predicted Severity: {result.predicted_severity}")
    logger.info(f"  - Confidence: {result.confidence_map[result.predicted_severity]:.4f}")
    logger.info(f"  - Auto-Claim Triggered: {result.trigger_auto_claim}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    """Run full training and visualization pipeline."""
    
    # Train model
    model, X_test, y_test, metrics = train_and_evaluate()
    
    # Generate visualizations
    logger.info("\n" + "=" * 80)
    logger.info("GENERATING VISUALIZATIONS")
    logger.info("=" * 80)
    
    plot_confusion_matrix(model, X_test, y_test)
    plot_classification_metrics(metrics)
    plot_confidence_distribution(model, X_test, y_test)
    plot_accuracy_summary(model, X_test, y_test, metrics)
    plot_roc_curves(model, X_test, y_test)
    
    # Demonstrate model persistence
    demonstrate_model_persistence(model)
    
    logger.info("\n" + "=" * 80)
    logger.info("✓ ALL VISUALIZATIONS COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Plots saved to: {PLOT_DIR}")
    logger.info(f"Models saved to: {MODEL_DIR}")


if __name__ == "__main__":
    main()
