import cv2
import numpy as np

def preprocess(image):
    """
    Preprocesses the raw thermal image by converting it to grayscale (if needed)
    and applying a bilateral filter to denoise while preserving structural edges.
    
    Args:
        image (numpy.ndarray): Raw BGR or grayscale thermal image.
        
    Returns:
        numpy.ndarray: Denoised grayscale image.
    """
    if image is None:
        raise ValueError("Input image cannot be None")
        
    # Convert BGR/RGB to Grayscale
    if len(image.shape) == 3 and image.shape[2] >= 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
        
    # Use Bilateral Filter to reduce thermal noise while keeping sharp edges
    denoised = cv2.bilateralFilter(gray, d=9, sigmaColor=75, sigmaSpace=75)
    
    return denoised
