import cv2
import numpy as np

def anomaly_detection(temp_map):
    """
    Detects temperature anomalies (specifically localized cool spots indicating moisture/seepage)
    by comparing pixel values with a spatial baseline (local mean).
    
    Args:
        temp_map (numpy.ndarray): Temperature map in Celsius.
        
    Returns:
        dict: A dictionary containing:
            - 'delta_t': Temperature deviation from local average (ndarray).
            - 'anomaly_score': Normalized anomaly index [0, 1] (ndarray).
            - 'seepage_probability': Seepage likelihood [0, 1] (ndarray).
            - 'moisture_level': Gridded categories ('low', 'medium', 'high') (ndarray).
    """
    if temp_map is None:
        raise ValueError("Temperature map cannot be None")
        
    # Calculate local baseline temperature using a large Gaussian blur kernel
    # representing the expected temperature profile of dry concrete.
    kernel_size = 101
    local_mean = cv2.GaussianBlur(temp_map, (kernel_size, kernel_size), 0)
    
    # Delta T: Positive = warmer than surroundings, Negative = cooler than surroundings
    delta_t = temp_map - local_mean
    
    # Cooling magnitude (evaporative cooling from seepage)
    cooling = np.maximum(0.0, -delta_t)
    
    # Anomaly score: normalized magnitude of cooling
    # We define 3.5 degrees of cooling as maximum anomaly (1.0)
    anomaly_score = np.clip(cooling / 3.5, 0.0, 1.0)
    
    # Seepage probability modeled via Sigmoid function centered around 1.2°C cooling
    seepage_probability = np.zeros_like(cooling, dtype=np.float32)
    mask = cooling > 0.2
    seepage_probability[mask] = 1.0 / (1.0 + np.exp(-3.0 * (cooling[mask] - 1.2)))
    
    # Moisture level classification based on temperature deviation thresholds
    moisture_level = np.full(temp_map.shape, "low", dtype=object)
    moisture_level[cooling >= 0.8] = "medium"
    moisture_level[cooling >= 2.0] = "high"
    
    return {
        "delta_t": delta_t,
        "anomaly_score": anomaly_score,
        "seepage_probability": seepage_probability,
        "moisture_level": moisture_level
    }
