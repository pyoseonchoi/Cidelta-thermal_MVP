import os
import yaml
import numpy as np

def risk_score(cells_data, config_path=None, weights_path=None, dam_type="concrete"):
    """
    Calculates the combined risk score and categorical risk level for each dam grid cell.
    Amplifies thermal seepage risk if it occurs near the dam foundation.
    
    Args:
        cells_data (dict): Dictionary containing cell records and metadata.
        config_path (str, optional): Path to thermal configuration.
        weights_path (str, optional): Path to risk weights YAML.
        dam_type (str): Type of dam material ('concrete', 'earthfill').
        
    Returns:
        dict: The cells_data dictionary updated with risk scores and risk levels.
    """
    # Default weights
    w_temp = 0.4
    w_seepage = 0.3
    w_loc = 0.3
    
    # Try to load weights from config
    if weights_path and os.path.exists(weights_path):
        try:
            with open(weights_path, 'r', encoding='utf-8') as f:
                weight_cfg = yaml.safe_load(f)
                rw_all = weight_cfg.get("risk_weights", {})
                # If weights are partitioned by dam_type, load the specific partition
                if dam_type in rw_all:
                    rw = rw_all.get(dam_type, {})
                else:
                    rw = rw_all
                w_temp = rw.get("temperature_deviation", w_temp)
                w_seepage = rw.get("anomaly_size", w_seepage) # mapped to anomaly_size in config
                w_loc = rw.get("location_criticality", w_loc)
        except Exception as e:
            print(f"[!] Error loading risk weights: {e}")
            
    cells = cells_data.get("cells", [])
    meta = cells_data.get("metadata", {})
    dam_params = meta.get("dam_parameters", {})
    height_z_m = float(dam_params.get("height_z_m", 25.0))
    
    updated_cells = []
    
    for cell in cells:
        s_temp = cell.get("thermal_anomaly_score", 0.0)
        s_seepage = cell.get("seepage_probability", 0.0)
        z_range = cell.get("z_range_m", [0.0, 1.0])
        z_bottom = z_range[0]
        
        # Location criticality: higher risk closer to the base (Z=0)
        # s_loc ranges from 1.0 (bottom) to 0.0 (top)
        s_loc = 1.0 - (z_bottom / height_z_m)
        
        # Combine thermal indicators
        total_w_thermal = w_temp + w_seepage
        if total_w_thermal > 0:
            thermal_base = (w_temp * s_temp + w_seepage * s_seepage) / total_w_thermal
        else:
            thermal_base = 0.0
            
        # Amplification factor based on location criticality
        # At the bottom, the risk is multiplied by (1.0 + w_loc)
        location_multiplier = 1.0 + (s_loc * w_loc)
        
        # Final combined risk score [0.0, 1.0]
        final_score = float(np.clip(thermal_base * location_multiplier, 0.0, 1.0))
        
        # Map score to risk level (0: Stable, 1: Low, 2: Medium, 3: High)
        if final_score < 0.20:
            risk_lvl = 0
        elif final_score < 0.45:
            risk_lvl = 1
        elif final_score < 0.70:
            risk_lvl = 2
        else:
            risk_lvl = 3
            
        cell["thermal_risk_score"] = round(final_score, 2)
        cell["thermal_risk_level"] = risk_lvl
        
        updated_cells.append(cell)
        
    cells_data["cells"] = updated_cells
    return cells_data
