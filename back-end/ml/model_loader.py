import pickle
import os
import sys

def load_model():
    """
    Load the trained ML model from disk.
    
    Returns:
        The loaded model object, or None if loading fails.
    """
    # Get the directory where this script is located
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Path to the model file
    model_path = os.path.join(current_dir, 'trained_model', 'dumped_clf.pkl')
    
    # Check if a model exists directly in ml/
    if not os.path.exists(model_path):
        model_path = os.path.join(current_dir, 'dumped_clf.pkl')
        
    if not os.path.exists(model_path):
        print(f"⚠ Model file not found at: {model_path}")
        return None
        
    try:
        print(f"⏳ Loading ML model from {model_path}...")
        with open(model_path, 'rb') as f:
            model = pickle.load(f)
        print("✓ Model loaded successfully!")
        return model
    except Exception as e:
        print(f"✗ Failed to load model: {e}")
        return None
