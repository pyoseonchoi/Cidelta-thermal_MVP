import json
import os
import numpy as np

def _generate_fallback_cells(length_x=70.0, height_z=25.0, slice_interval=5.0, cell_x=1.0, cell_leg_z=1.0):
    num_slices = int(length_x / slice_interval)
    cells = []
    for s_id in range(num_slices):
        x0 = s_id * slice_interval
        x1 = x0 + slice_interval
        x_count = int((x1 - x0) / cell_x)
        z_count = int(height_z / cell_leg_z)
        for ix in range(x_count):
            xa = x0 + ix * cell_x
            xb = xa + cell_x
            for iz in range(z_count):
                cell_id = f"S{s_id:02d}_X{ix:02d}_Z{iz:02d}"
                z_top = height_z - iz * cell_leg_z
                z_bottom = height_z - (iz + 1) * cell_leg_z
                cells.append({
                    "cell_id": cell_id,
                    "slice_id": s_id,
                    "x_range_m": [xa, xb],
                    "z_range_m": [z_bottom, z_top]
                })
    return {
        "metadata": {
            "description": "Fallback auto-generated cell layout for Cidelta-thermal MVP.",
            "dam_parameters": {
                "length_x_m": length_x,
                "height_z_m": height_z,
                "slice_interval_m": slice_interval
            }
        },
        "cells": cells
    }

def cell_mapping(temp_map, anomaly_results, cell_json_path):
    """
    Maps 3D grid cells to 2D image coordinates and aggregates thermal parameters per cell.
    
    Args:
        temp_map (numpy.ndarray): 2D array of temperatures in Celsius.
        anomaly_results (dict): Dictionary of 2D anomaly arrays from anomaly_detection.
        cell_json_path (str): Path to the Blender cell geometry JSON.
        
    Returns:
        dict: The loaded JSON with updated thermal analysis results per cell.
    """
    if not os.path.exists(cell_json_path):
        print(f"[*] Cell geometry file not found. Generating fallback geometry at: {cell_json_path}")
        parent_dir = os.path.dirname(cell_json_path)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)
        fallback_data = _generate_fallback_cells()
        with open(cell_json_path, 'w', encoding='utf-8') as f:
            json.dump(fallback_data, f, ensure_ascii=False, indent=2)
        
    with open(cell_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    cells = data.get("cells", [])
    meta = data.get("metadata", {})
    dam_params = meta.get("dam_parameters", {})
    
    # Get dam dimensions (fallback to defaults if metadata is missing)
    length_x_m = float(dam_params.get("length_x_m", 70.0))
    height_z_m = float(dam_params.get("height_z_m", 25.0))
    
    H, W = temp_map.shape[:2]
    
    updated_cells = []
    
    for cell in cells:
        cell_id = cell.get("cell_id")
        x_range = cell.get("x_range_m", [0.0, 1.0])
        z_range = cell.get("z_range_m", [0.0, 1.0])
        
        # Linear projection of X-coordinate to horizontal image pixels (u)
        u_start = int(np.clip((x_range[0] / length_x_m) * W, 0, W))
        u_end = int(np.clip((x_range[1] / length_x_m) * W, 0, W))
        
        # Linear projection of Z-coordinate to vertical image pixels (v)
        # Z=25 is the top of the dam (row 0), Z=0 is the bottom (row H)
        v_start = int(np.clip((1.0 - z_range[1] / height_z_m) * H, 0, H))
        v_end = int(np.clip((1.0 - z_range[0] / height_z_m) * H, 0, H))
        
        # Ensure slice is valid
        if u_end <= u_start:
            u_end = min(u_start + 1, W)
        if v_end <= v_start:
            v_end = min(v_start + 1, H)
            
        # Crop the cell region from the anomaly maps
        temp_crop = temp_map[v_start:v_end, u_start:u_end]
        delta_t_crop = anomaly_results["delta_t"][v_start:v_end, u_start:u_end]
        anomaly_crop = anomaly_results["anomaly_score"][v_start:v_end, u_start:u_end]
        seepage_crop = anomaly_results["seepage_probability"][v_start:v_end, u_start:u_end]
        
        # Aggregate statistics
        mean_temp = float(np.mean(temp_crop))
        mean_delta_t = float(np.mean(delta_t_crop))
        mean_anomaly = float(np.mean(anomaly_crop))
        mean_seepage = float(np.mean(seepage_crop))
        
        # Determine moisture level
        cooling = -mean_delta_t
        if cooling >= 2.0:
            moisture_lvl = "high"
        elif cooling >= 0.8:
            moisture_lvl = "medium"
        else:
            moisture_lvl = "low"
            
        # Confidence score based on temperature uniformity (more uniform = higher confidence)
        std_temp = np.std(temp_crop)
        confidence = float(np.clip(1.0 - (std_temp / 5.0), 0.5, 0.95))
        
        # Update cell record
        cell["thermal_mean_temp_c"] = round(mean_temp, 2)
        cell["thermal_delta_t_c"] = round(mean_delta_t, 2)
        cell["thermal_anomaly_score"] = round(mean_anomaly, 2)
        cell["seepage_probability"] = round(mean_seepage, 2)
        cell["moisture_level"] = moisture_lvl
        cell["thermal_confidence"] = round(confidence, 2)
        
        updated_cells.append(cell)
        
    data["cells"] = updated_cells
    return data
