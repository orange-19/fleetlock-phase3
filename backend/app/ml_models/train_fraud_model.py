"""
Train and Test Fraud Detection Model using Telematics Data
===========================================================

This script:
1. Uses TelematicsClient to generate fraud and genuine trip data
2. Trains the GPS fraud detection model
3. Generates graphs for: accuracy, confusion matrix, feature importance
"""

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    confusion_matrix, classification_report, accuracy_score,
    precision_score, recall_score, f1_score
)
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.ml_models.fraud_detection import GPSFraudModel, FEATURE_COLUMNS
from app.integrations.telematics_client import TelematicsClient

# Configure plotting
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")


def generate_dataset(n_genuine=500, n_fraud=500):
    """Generate fraud and genuine samples using TelematicsClient"""
    
    print(f"\n→ Generating {n_genuine} genuine samples...")
    
    telematics = TelematicsClient()
    model = GPSFraudModel()
    
    X_data = []
    y_data = []
    
    # Generate genuine samples
    for i in range(n_genuine):
        telematics_features = telematics.generate_fraud_detection_features(
            zone_id="ZONE_CHENNAI_N",
            fraud_type="genuine"
        )
        gps_trace = telematics.generate_gps_trace(num_points=15, stationary=False)
        claimed_loc = (13.0827, 80.2707)
        actual_loc = (13.0835, 80.2715)
        
        features = model.build_features(telematics_features, gps_trace, claimed_loc, actual_loc)
        feature_row = [features[col] for col in FEATURE_COLUMNS]
        X_data.append(feature_row)
        y_data.append(0)  # 0 = genuine
    
    print(f"→ Generating {n_fraud} fraud samples...")
    
    # Generate fraud samples
    fraud_types = ["location_mismatch", "route_fraud", "device_fraud"]
    for i in range(n_fraud):
        fraud_type = fraud_types[i % len(fraud_types)]
        telematics_features = telematics.generate_fraud_detection_features(
            zone_id="ZONE_CHENNAI_N",
            fraud_type=fraud_type
        )
        gps_trace = telematics.generate_gps_trace(num_points=15, stationary=i % 5 == 0)
        claimed_loc = (13.0827, 80.2707)
        actual_loc = (13.15, 80.35)  # Far away for fraud
        
        features = model.build_features(telematics_features, gps_trace, claimed_loc, actual_loc)
        feature_row = [features[col] for col in FEATURE_COLUMNS]
        X_data.append(feature_row)
        y_data.append(1)  # 1 = fraud
    
    return np.array(X_data), np.array(y_data)


def plot_accuracy_scores(y_true, y_pred, y_pred_proba=None):
    """Generate accuracy metrics visualization"""
    
    accuracy = accuracy_score(y_true, y_pred)
    precision = precision_score(y_true, y_pred)
    recall = recall_score(y_true, y_pred)
    f1 = f1_score(y_true, y_pred)
    
    metrics = ['Accuracy', 'Precision', 'Recall', 'F1-Score']
    scores = [accuracy, precision, recall, f1]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(metrics, scores, color=['#2ecc71', '#3498db', '#e74c3c', '#f39c12'], alpha=0.8, edgecolor='black')
    
    ax.set_ylabel('Score', fontsize=12, fontweight='bold')
    ax.set_title('Fraud Detection Model - Accuracy Metrics', fontsize=14, fontweight='bold')
    ax.set_ylim(0, 1.1)
    
    # Add value labels on bars
    for bar, score in zip(bars, scores):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{score:.4f}',
                ha='center', va='bottom', fontweight='bold', fontsize=11)
    
    ax.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig('saved_models/fraud_accuracy_metrics.png', dpi=300, bbox_inches='tight')
    print("✓ Saved: fraud_accuracy_metrics.png")
    plt.close()
    
    return {'accuracy': accuracy, 'precision': precision, 'recall': recall, 'f1': f1}


def plot_confusion_matrix(y_true, y_pred):
    """Generate confusion matrix visualization"""
    
    cm = confusion_matrix(y_true, y_pred)
    
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', cbar=True, ax=ax,
                xticklabels=['Genuine', 'Fraud'],
                yticklabels=['Genuine', 'Fraud'],
                annot_kws={'size': 14, 'fontweight': 'bold'})
    
    ax.set_ylabel('True Label', fontsize=12, fontweight='bold')
    ax.set_xlabel('Predicted Label', fontsize=12, fontweight='bold')
    ax.set_title('Fraud Detection Model - Confusion Matrix', fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('saved_models/fraud_confusion_matrix.png', dpi=300, bbox_inches='tight')
    print("✓ Saved: fraud_confusion_matrix.png")
    plt.close()


def plot_feature_importance(model):
    """Generate feature importance (helpful features) visualization"""
    
    importances = model.model.feature_importances_
    indices = np.argsort(importances)[::-1]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    colors = plt.cm.viridis(np.linspace(0, 1, len(FEATURE_COLUMNS)))
    bars = ax.barh(range(len(FEATURE_COLUMNS)), importances[indices], color=colors, edgecolor='black')
    
    ax.set_yticks(range(len(FEATURE_COLUMNS)))
    ax.set_yticklabels([FEATURE_COLUMNS[i] for i in indices])
    ax.set_xlabel('Importance Score', fontsize=12, fontweight='bold')
    ax.set_title('Fraud Detection Model - Feature Importance', fontsize=14, fontweight='bold')
    
    # Add value labels
    for i, (bar, importance) in enumerate(zip(bars, importances[indices])):
        ax.text(importance, bar.get_y() + bar.get_height()/2.,
                f' {importance:.4f}',
                va='center', fontweight='bold', fontsize=10)
    
    ax.grid(axis='x', alpha=0.3)
    plt.tight_layout()
    plt.savefig('saved_models/fraud_feature_importance.png', dpi=300, bbox_inches='tight')
    print("✓ Saved: fraud_feature_importance.png")
    plt.close()


def main():
    print("\n" + "="*70)
    print("  FRAUD DETECTION MODEL - TRAIN AND TEST")
    print("="*70)
    
    # Create saved_models directory
    os.makedirs('saved_models', exist_ok=True)
    
    # Generate dataset
    print("\n[1/4] Generating dataset from TelematicsClient...")
    X, y = generate_dataset(n_genuine=500, n_fraud=500)
    print(f"✓ Dataset shape: {X.shape}, Labels: {np.bincount(y)}")
    
    # Split data
    print("\n[2/4] Splitting into train (80%) and test (20%) sets...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"✓ Train: {X_train.shape[0]}, Test: {X_test.shape[0]}")
    
    # Train model
    print("\n[3/4] Training fraud detection model...")
    model = GPSFraudModel()
    model.train(X_train, y_train)
    print("✓ Model trained successfully")
    
    # Evaluate
    print("\n[4/4] Evaluating and generating visualizations...")
    y_pred = model.model.predict(X_test)
    y_pred_proba = model.model.predict_proba(X_test)
    
    # Generate graphs
    metrics = plot_accuracy_scores(y_test, y_pred, y_pred_proba)
    plot_confusion_matrix(y_test, y_pred)
    plot_feature_importance(model)
    
    # Save model
    model_info = model.save('saved_models/fraud_model.joblib')
    print(f"✓ Model saved: {model_info['file_size_mb']:.2f} MB")
    
    # Print summary
    print("\n" + "="*70)
    print("  RESULTS SUMMARY")
    print("="*70)
    print(f"\nAccuracy:  {metrics['accuracy']:.4f}")
    print(f"Precision: {metrics['precision']:.4f}")
    print(f"Recall:    {metrics['recall']:.4f}")
    print(f"F1-Score:  {metrics['f1']:.4f}")
    print(f"\nTop 3 Helpful Features:")
    
    importances = model.model.feature_importances_
    top_indices = np.argsort(importances)[::-1][:3]
    for rank, idx in enumerate(top_indices, 1):
        print(f"  {rank}. {FEATURE_COLUMNS[idx]}: {importances[idx]:.4f}")
    
    print("\n✓ Graphs saved to saved_models/")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
