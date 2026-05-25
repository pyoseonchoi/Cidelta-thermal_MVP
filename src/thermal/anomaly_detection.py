import os
import yaml
import cv2
import numpy as np

def anomaly_detection(temp_map, config_path=None, dam_type="concrete"):
    """
    Detects temperature anomalies (specifically localized cool spots indicating moisture/seepage)
    by comparing pixel values with a spatial baseline (local mean).
    
    Args:
        temp_map (numpy.ndarray): Temperature map in Celsius.
        config_path (str, optional): Path to configuration YAML.
        dam_type (str): Type of dam material ('concrete', 'earthfill').
        
    Returns:
        dict: A dictionary containing:
            - 'delta_t': Temperature deviation from local average (ndarray).
            - 'anomaly_score': Normalized anomaly index [0, 1] (ndarray).
            - 'seepage_probability': Seepage likelihood [0, 1] (ndarray).
            - 'moisture_level': Gridded categories ('low', 'medium', 'high') (ndarray).
    """
    if temp_map is None:
        raise ValueError("Temperature map cannot be None")
        
    # Default values (fallback to concrete if config file not found/loaded)
    kernel_size = 101
    max_cooling_threshold = 3.5
    seepage_center_temp = 1.2
    t_medium = 0.8
    t_high = 2.0
    
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                dam_configs = config.get("dam_types", {})
                dam_cfg = dam_configs.get(dam_type, {})
                if dam_cfg:
                    kernel_size = dam_cfg.get("gaussian_kernel_size", kernel_size)
                    max_cooling_threshold = dam_cfg.get("max_cooling_threshold", max_cooling_threshold)
                    seepage_center_temp = dam_cfg.get("seepage_center_temp", seepage_center_temp)
                    risk_thresholds = dam_cfg.get("risk_thresholds", {})
                    t_medium = risk_thresholds.get("medium", t_medium)
                    t_high = risk_thresholds.get("high", t_high)
        except Exception as e:
            print(f"[!] Error loading config in anomaly_detection: {e}")

    # Ensure kernel size is odd and valid
    if kernel_size % 2 == 0:
        kernel_size += 1
        
    # Calculate local baseline temperature using a large Gaussian blur kernel
    local_mean = cv2.GaussianBlur(temp_map, (kernel_size, kernel_size), 0)
    
    # Delta T: Positive = warmer than surroundings, Negative = cooler than surroundings
    delta_t = temp_map - local_mean
    
    # Cooling magnitude (evaporative cooling from seepage)
    cooling = np.maximum(0.0, -delta_t)
    
    # Anomaly score: normalized magnitude of cooling
    anomaly_score = np.clip(cooling / max_cooling_threshold, 0.0, 1.0)
    
    # Seepage probability modeled via Sigmoid function
    seepage_probability = np.zeros_like(cooling, dtype=np.float32)
    mask = cooling > 0.1
    seepage_probability[mask] = 1.0 / (1.0 + np.exp(-3.0 * (cooling[mask] - seepage_center_temp)))
    
    # Moisture level classification based on temperature deviation thresholds
    moisture_level = np.full(temp_map.shape, "low", dtype=object)
    moisture_level[cooling >= t_medium] = "medium"
    moisture_level[cooling >= t_high] = "high"
    
    return {
        "delta_t": delta_t,
        "anomaly_score": anomaly_score,
        "seepage_probability": seepage_probability,
        "moisture_level": moisture_level
    }
