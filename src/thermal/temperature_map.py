import os
import yaml
import numpy as np

def temperature_map(image, config_path=None):
    """
    Converts a grayscale intensity image to a physical temperature map in Celsius.
    
    Args:
        image (numpy.ndarray): Preprocessed grayscale thermal image.
        config_path (str, optional): Path to configuration YAML.
        
    Returns:
        numpy.ndarray: Temperature map in Celsius.
    """
    if image is None:
        raise ValueError("Input image cannot be None")
        
    # Default temperature range for concrete dam surface (in Celsius)
    min_temp = 18.0
    max_temp = 38.0
    
    # Try to load custom temperature range from config
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                analysis_cfg = config.get("thermal_analysis", {})
                min_temp = analysis_cfg.get("min_temp", min_temp)
                max_temp = analysis_cfg.get("max_temp", max_temp)
        except Exception:
            pass
            
    # Map pixel values linearly from [0, 255] to [min_temp, max_temp]
    normalized = image.astype(np.float32) / 255.0
    temp_map = min_temp + normalized * (max_temp - min_temp)
    
    return temp_map
