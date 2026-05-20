import argparse
import sys
import os
import numpy as np

from src.thermal.load_image import load_image
from src.thermal.preprocess import preprocess
from src.thermal.temperature_map import temperature_map
from src.thermal.anomaly_detection import anomaly_detection
from src.thermal.cell_mapping import cell_mapping
from src.thermal.risk_score import risk_score
from src.thermal.export_json import export_json

def main():
    parser = argparse.ArgumentParser(description="Dam Thermal Analysis MVP Pipeline")
    parser.add_argument(
        "--image",
        type=str,
        default="data/sample_thermal/thermal_sample_01.png",
        help="Path to thermal image"
    )
    parser.add_argument(
        "--cell-json",
        type=str,
        default="outputs/blender_json/dam_attached_body_outer_cells_directional_risk.json",
        help="Path to cell geometry JSON"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="outputs/thermal_json/thermal_result.json",
        help="Path to save thermal analysis result JSON"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="configs/thermal_config.yaml",
        help="Path to thermal config yaml"
    )
    parser.add_argument(
        "--weights",
        type=str,
        default="configs/risk_weights.yaml",
        help="Path to risk weights yaml"
    )
    
    args = parser.parse_args()
    
    print("=========================================================")
    print(" [~] Cidelta Dam Thermal Analysis Pipeline - Starting")
    print("=========================================================")
    print(f"[*] Input Image:  {args.image}")
    print(f"[*] Cell JSON:    {args.cell_json}")
    print(f"[*] Output Path:  {args.output}")
    print(f"[*] Config file:  {args.config}")
    print(f"[*] Weights file: {args.weights}")
    print("---------------------------------------------------------")
    
    try:
        # 1. Load image and metadata
        print("[1/6] Loading image...")
        img, metadata = load_image(args.image)
        print(f"      Image loaded successfully. Shape: {img.shape}")
        if metadata:
            ambient_t = metadata.get('ambient_temperature') or metadata.get('ambient_temp')
            emissivity = metadata.get('emissivity')
            print(f"      Metadata found: Ambient Temp={ambient_t}°C, Emissivity={emissivity}")
            
        # 2. Preprocess image (Grayscale conversion + Denoise)
        print("[2/6] Preprocessing image...")
        preprocessed = preprocess(img)
        print("      Image denoising complete.")
        
        # 3. Create temperature map
        print("[3/6] Mapping pixels to temperature (Celsius)...")
        temp_map = temperature_map(preprocessed, args.config)
        print(f"      Mapped temp range: Min={temp_map.min():.2f}°C, Max={temp_map.max():.2f}°C, Mean={temp_map.mean():.2f}°C")
        
        # 4. Detect anomalies (moisture/seepage)
        print("[4/6] Running anomaly and seepage detection...")
        anomalies = anomaly_detection(temp_map)
        
        # Statistics on anomalies
        prob = anomalies["seepage_probability"]
        high_prob_count = int(np.sum(prob > 0.7))
        med_prob_count = int(np.sum((prob >= 0.3) & (prob <= 0.7)))
        print(f"      Detection completed. Seepage suspect pixels: High={high_prob_count}, Medium={med_prob_count}")
        
        # 5. Map 2D results to 3D Cell grid
        print("[5/6] Mapping 2D analysis to 3D cell geometry...")
        mapped_data = cell_mapping(temp_map, anomalies, args.cell_json)
        
        # 6. Calculate structural risk scores
        print("[6/6] Computing location-critical risk scores...")
        final_data = risk_score(mapped_data, args.config, args.weights)
        
        # Summary calculations
        cells = final_data.get("cells", [])
        risk_counts = {0: 0, 1: 0, 2: 0, 3: 0}
        moisture_counts = {"low": 0, "medium": 0, "high": 0}
        for cell in cells:
            r_lvl = cell.get("thermal_risk_level", 0)
            m_lvl = cell.get("moisture_level", "low")
            risk_counts[r_lvl] = risk_counts.get(r_lvl, 0) + 1
            moisture_counts[m_lvl] = moisture_counts.get(m_lvl, 0) + 1
            
        # Update export metadata
        if "metadata" not in final_data:
            final_data["metadata"] = {}
        final_data["metadata"]["analysis_summary"] = {
            "source_image": args.image,
            "total_cells": len(cells),
            "risk_levels": risk_counts,
            "moisture_levels": moisture_counts
        }
        
        # Save output JSON
        export_json(final_data, args.output)
        
        print("---------------------------------------------------------")
        print(" [+] Pipeline Execution Successful!")
        print(f"      Total cells processed: {len(cells)}")
        print(f"      Risk Level 0 (Stable): {risk_counts[0]}")
        print(f"      Risk Level 1 (Low):    {risk_counts[1]}")
        print(f"      Risk Level 2 (Medium): {risk_counts[2]}")
        print(f"      Risk Level 3 (High):   {risk_counts[3]}")
        print(f"      Moisture: High={moisture_counts['high']}, Medium={moisture_counts['medium']}, Low={moisture_counts['low']}")
        print(f"      Saved final results to: {args.output}")
        print("=========================================================")
        
    except Exception as e:
        print(f"\n[!] Pipeline failed with error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
