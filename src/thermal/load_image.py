import os
import cv2
import json

def load_image(path):
    """
    Loads a thermal image and its metadata from disk if available.
    
    Args:
        path (str): Path to the thermal image file.
        
    Returns:
        tuple: (numpy.ndarray, dict) containing the image array and metadata.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Image not found at path: {path}")
        
    image = cv2.imread(path)
    if image is None:
        raise ValueError(f"Failed to load image at: {path}")
        
    # Try to load companion metadata file
    metadata = {}
    for ext in ['.png', '.jpg', '.jpeg']:
        if path.lower().endswith(ext):
            meta_path = path[:-len(ext)] + "_meta.json"
            if os.path.exists(meta_path):
                try:
                    with open(meta_path, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                except Exception:
                    pass
            break
            
    return image, metadata
