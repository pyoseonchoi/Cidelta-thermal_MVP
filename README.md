# 🌊 Dam Thermal MVP

This project is a Minimum Viable Product (MVP) for analyzing thermal images of dams to detect anomalies and assess risks. It integrates thermal image processing with 3D visualization using Blender.

## 🚀 MVP Execution Flow

1. **Step 1: Blender Geometry Setup**
   - Run `blender/scripts/01_create_dam_cells.py` in Blender.
   - ➜ This generates the dam cells and initial geometry.

2. **Step 2: Thermal Analysis Pipeline**
   - Run the thermal pipeline in a standard Python environment.
   - ➜ This processes the thermal image and generates `thermal_result.json`.

3. **Step 3: Visualization Update**
   - Run `blender/scripts/02_apply_thermal_result.py` in Blender.
   - ➜ This applies the calculated thermal risk levels as colors to the 3D cells.

---

## 🛠 Execution Command (Bash)

To run the thermal analysis pipeline manually:

```bash
python -m src.thermal.run_pipeline \
  --image data/sample_thermal/thermal_sample_01.png \
  --cell-json outputs/blender_json/dam_attached_body_outer_cells_directional_risk.json \
  --output outputs/thermal_json/thermal_result.json
```

---

## 📊 Data Format (JSON Unification)

The output JSON follows this unified structure for seamless integration between the analysis pipeline and Blender visualization:

```json
{
  "metadata": {
    "source": "thermal_sample_01.png",
    "analysis_type": "thermal_moisture_risk",
    "note": "Dummy thermal MVP result"
  },
  "cells": [
    {
      "cell_id": "S03_X02_Z14",
      "slice_id": 3,
      "thermal_mean_temp_c": 22.8,
      "thermal_delta_t_c": -1.6,
      "thermal_anomaly_score": 0.73,
      "seepage_probability": 0.81,
      "moisture_level": "high",
      "thermal_risk_level": 3,
      "thermal_confidence": 0.84
    }
  ]
}
```

---

## 📂 Project Structure

- `blender/`: Scripts and scenes for 3D visualization.
- `src/`: Core logic for thermal analysis and fusion.
- `data/`: Sample images and metadata.
- `configs/`: Configuration files for analysis and risk weighting.
- `outputs/`: Generated JSON results, screenshots, and reports.
