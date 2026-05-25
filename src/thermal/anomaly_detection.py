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

    # Establish the 2D baseline template image using spatial filtering
    # (keeps local spatial context and prevents horizontal background false positives)
    if kernel_size % 2 == 0:
        kernel_size += 1
    local_mean = cv2.GaussianBlur(temp_map, (kernel_size, kernel_size), 0)
    
    # Delta T: Positive = warmer than surroundings, Negative = cooler than surroundings
    delta_t = temp_map - local_mean
    
    # Run the physical simulation to calculate the expected physical temperature drop (thermal signature)
    # due to seepage under the current physical boundary conditions.
    physical_drop = 2.5  # Fallback seepage cooling signature (Celsius)
    try:
        from src.thermal.ogs_integration import OgsIntegration
        sim = OgsIntegration(config_path, dam_type)
        
        # Run wet (with seepage anomaly at the toe) and dry simulations
        anomalies = [{'y': [sim.base_width - 15.0, sim.base_width], 'z': [0.0, 5.0], 'k': sim.k_anomaly}]
        results_wet = sim.run_simulation(seepage_anomalies=anomalies)
        results_dry = sim.run_simulation(seepage_anomalies=None)
        
        t_dry = np.array(results_dry["slope_temperatures"])
        t_wet = np.array(results_wet["slope_temperatures"])
        
        # Calculate maximum temperature drop on the slope
        temp_drop = np.maximum(0.0, t_dry - t_wet)
        max_physical_drop = float(np.max(temp_drop))
        
        if max_physical_drop > 0.3:
            physical_drop = max_physical_drop
            print(f"      [+] Calibrated physical seepage cooling signature: {physical_drop:.2f}°C")
    except Exception as e:
        print(f"[!] Warning: Physics-based threshold calibration failed: {e}. Using default {physical_drop}°C signature.")

    # Dynamically scale thresholds based on the physical temperature drop signature
    max_cooling_threshold = physical_drop
    t_medium = 0.3 * physical_drop
    t_high = 0.6 * physical_drop
    seepage_center_temp = 0.45 * physical_drop
    
    print(f"      [+] Dynamic physical thresholds -> High Risk: >={t_high:.2f}°C, Medium Risk: >={t_medium:.2f}°C")
    
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
