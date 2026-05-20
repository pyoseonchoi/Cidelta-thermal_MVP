from src.thermal.risk_score import risk_score

def test_risk_score_foundation_criticality():
    # Create two cells with the exact same high thermal anomaly and seepage probability
    # Cell 0 is near the top (Z = 20 to 21)
    # Cell 1 is near the bottom/foundation (Z = 0 to 1)
    cells_data = {
        "metadata": {
            "dam_parameters": {
                "height_z_m": 25.0
            }
        },
        "cells": [
            {
                "cell_id": "S00_X00_Z04", # Top cell (iz=4 -> Z=20 to 21)
                "z_range_m": [20.0, 21.0],
                "thermal_anomaly_score": 0.8,
                "seepage_probability": 0.8
            },
            {
                "cell_id": "S00_X00_Z24", # Bottom cell (iz=24 -> Z=0 to 1)
                "z_range_m": [0.0, 1.0],
                "thermal_anomaly_score": 0.8,
                "seepage_probability": 0.8
            }
        ]
    }
    
    results = risk_score(cells_data)
    
    top_cell = results["cells"][0]
    bottom_cell = results["cells"][1]
    
    # Bottom cell must have a higher calculated risk score than the top cell
    assert bottom_cell["thermal_risk_score"] > top_cell["thermal_risk_score"]
    assert bottom_cell["thermal_risk_level"] >= top_cell["thermal_risk_level"]
