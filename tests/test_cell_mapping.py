import os
import json
import numpy as np
from src.thermal.cell_mapping import cell_mapping

def test_cell_mapping_projection(tmp_path):
    # Setup dummy temp map and anomaly detection output
    temp_map = np.full((100, 100), 25.0, dtype=np.float32)
    
    anomaly_results = {
        "delta_t": np.zeros((100, 100), dtype=np.float32),
        "anomaly_score": np.zeros((100, 100), dtype=np.float32),
        "seepage_probability": np.zeros((100, 100), dtype=np.float32)
    }
    
    # Save a temporary cell geometry JSON
    cell_json_path = os.path.join(tmp_path, "dummy_cells.json")
    cell_data = {
        "metadata": {
            "dam_parameters": {
                "length_x_m": 70.0,
                "height_z_m": 25.0
            }
        },
        "cells": [
            {
                "cell_id": "S00_X00_Z00",
                "x_range_m": [0.0, 10.0],
                "z_range_m": [20.0, 25.0]
            }
        ]
    }
    
    with open(cell_json_path, 'w', encoding='utf-8') as f:
        json.dump(cell_data, f, indent=2)
        
    mapped = cell_mapping(temp_map, anomaly_results, cell_json_path)
    
    assert len(mapped["cells"]) == 1
    cell = mapped["cells"][0]
    assert "thermal_mean_temp_c" in cell
    assert cell["thermal_mean_temp_c"] == 25.0
    assert "moisture_level" in cell
    assert cell["moisture_level"] == "low"
