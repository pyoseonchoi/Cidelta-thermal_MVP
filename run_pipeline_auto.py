import os
import sys
import subprocess
import argparse
import glob

def find_blender():
    """
    Finds the Blender executable on the system.
    First checks the system PATH, then checks common install directories on Windows.
    """
    # 1. Check if 'blender' is in the system PATH
    try:
        # On Windows, 'where' is used; on Unix/macOS, 'which' is used.
        cmd = "where" if os.name == "nt" else "which"
        result = subprocess.run([cmd, "blender"], capture_output=True, text=True, check=True)
        path = result.stdout.strip().split("\n")[0]
        if os.path.exists(path):
            return path
    except Exception:
        pass

    # 2. Check default Windows installation paths
    if os.name == "nt":
        program_files = os.environ.get("ProgramFiles", "C:\\Program Files")
        blender_dir = os.path.join(program_files, "Blender Foundation")
        if os.path.exists(blender_dir):
            # Recursively search for blender.exe
            matches = glob.glob(os.path.join(blender_dir, "**", "blender.exe"), recursive=True)
            if matches:
                # Return the match (typically sorted, so newer versions may be grouped)
                # Let's sort by version folder names by sorting descending
                matches.sort(reverse=True)
                return matches[0]

    return None

def run_command(cmd, desc):
    """
    Runs a shell command and streams output to terminal.
    """
    print("\n" + "=" * 60)
    print(f" [>] Executing: {desc}")
    print("=" * 60)
    print(f"Running command: {' '.join(cmd)}\n")
    
    try:
        # Set environment variable to force UTF-8 output from Python subprocesses
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        # Run subprocess and stream output
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            bufsize=1
        )
        
        # Read stdout line by line
        for line in process.stdout:
            print(line, end="")
            
        process.wait()
        
        if process.returncode != 0:
            print(f"\n[!] Error: Command failed with return code {process.returncode}")
            sys.exit(process.returncode)
            
    except Exception as e:
        print(f"\n[!] Exception occurred while running command: {e}")
        sys.exit(1)

def find_python(project_root):
    """
    Finds the Python executable to run the analysis script.
    Checks if a local virtual environment (.venv) exists first.
    """
    venv_python = os.path.join(project_root, ".venv", "Scripts", "python.exe")
    if os.path.exists(venv_python):
        return venv_python
    return sys.executable

def main():
    parser = argparse.ArgumentParser(description="Dam Thermal Analysis MVP - Fully Automated Workflow")
    parser.add_argument(
        "--image",
        type=str,
        default="data/sample_thermal/thermal_sample_01.png",
        help="Path to thermal image for analysis (default: data/sample_thermal/thermal_sample_01.png)"
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Open the final analyzed scene in Blender GUI after workflow completes"
    )
    parser.add_argument(
        "--blender-path",
        type=str,
        help="Explicit path to blender.exe (skips auto-detection)"
    )
    
    args = parser.parse_args()
    
    # Get project root directory
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # 1. Locate Blender
    blender_path = args.blender_path or find_blender()
    if not blender_path:
        print("[!] Error: Blender executable not found automatically.")
        print("    Please provide it using the --blender-path argument.")
        print("    Example: python run_pipeline_auto.py --blender-path \"C:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe\"")
        sys.exit(1)
        
    print(f"[*] Blender path located: {blender_path}")
    print(f"[*] Analyzing image:      {args.image}")
    
    # Locate Python
    python_path = find_python(project_root)
    print(f"[*] Python path located:  {python_path}")
    
    # Ensure outputs directories exist
    os.makedirs(os.path.join(project_root, "outputs", "blender_json"), exist_ok=True)
    os.makedirs(os.path.join(project_root, "outputs", "thermal_json"), exist_ok=True)
    os.makedirs(os.path.join(project_root, "outputs", "blender_renders"), exist_ok=True)
    os.makedirs(os.path.join(project_root, "blender", "scenes"), exist_ok=True)
    
    # Define script paths
    script_create_cells = os.path.join(project_root, "blender", "scripts", "01_create_dam_cells.py")
    script_apply_thermal = os.path.join(project_root, "blender", "scripts", "02_apply_thermal_result.py")
    script_export_view = os.path.join(project_root, "blender", "scripts", "03_export_blender_view.py")
    
    blend_scene = os.path.join(project_root, "blender", "scenes", "dam_scene.blend")
    blend_scene_analyzed = os.path.join(project_root, "blender", "scenes", "dam_scene_analyzed.blend")
    
    # STEP 1: Run Blender in background mode to create cells and save base blend file
    cmd_step1 = [
        blender_path,
        "--background",
        "--python", script_create_cells
    ]
    run_command(cmd_step1, "Step 1: Blender Cell & Scene Generation (Headless)")
    
    # STEP 2: Run Python main thermal analysis pipeline
    cmd_step2 = [
        python_path,
        "-m", "src.thermal.run_pipeline",
        "--image", args.image
    ]
    run_command(cmd_step2, "Step 2: Python Thermal Analysis Pipeline")
    
    # STEP 3: Run Blender in background to load scene, apply results, save, and render view
    cmd_step3 = [
        blender_path,
        blend_scene,
        "--background",
        "--python", script_apply_thermal,
        "--python", script_export_view
    ]
    run_command(cmd_step3, "Step 3: Apply Results and Render View (Headless)")
    
    print("\n" + "=" * 60)
    print(" [+] Automated Workflow Finished Successfully!")
    print("=" * 60)
    print(f" [*] Created cell geometry JSON:   outputs/blender_json/dam_attached_body_outer_cells_directional_risk.json")
    print(f" [*] Created thermal result JSON:  outputs/thermal_json/thermal_result.json")
    print(f" [*] Generated 3D Render Image:    outputs/blender_renders/dam_thermal_3d_render.png")
    print(f" [*] Saved Base Blend File:        blender/scenes/dam_scene.blend")
    print(f" [*] Saved Analyzed Blend File:    blender/scenes/dam_scene_analyzed.blend")
    print("=" * 60)
    
    # STEP 4 (Optional): Open GUI to let the user interact with the final result
    if args.gui:
        print("\n[*] Opening final analyzed scene in Blender GUI...")
        cmd_gui = [blender_path, blend_scene_analyzed]
        subprocess.Popen(cmd_gui)

if __name__ == "__main__":
    main()
