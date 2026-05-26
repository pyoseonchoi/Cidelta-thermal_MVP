import os
import shutil
import uuid
import asyncio
import json
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Cidelta Thermal MVP Test Server",
    description="Web interface for uploading thermal images, running analysis, and rendering 3D dam models in Blender",
    version="1.0.0"
)

# Enable CORS for local development testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SESSIONS_DIR = os.path.join(PROJECT_ROOT, "outputs", "sessions")
os.makedirs(SESSIONS_DIR, exist_ok=True)

# Concurrency lock to prevent multiple Blender renders from colliding
pipeline_lock = asyncio.Lock()

@app.post("/api/analyze")
async def analyze_image(
    file: UploadFile = File(...),
    dam_type: str = Form("concrete")
):
    if dam_type not in ["concrete", "earthfill"]:
        raise HTTPException(status_code=400, detail="Invalid dam material type. Choose 'concrete' or 'earthfill'.")
        
    session_id = uuid.uuid4().hex
    session_dir = os.path.join(SESSIONS_DIR, session_id)
    os.makedirs(session_dir, exist_ok=True)
    
    # Save original uploaded image
    file_ext = os.path.splitext(file.filename)[1]
    if not file_ext:
        file_ext = ".png" # default to png
    original_filename = f"original_thermal{file_ext}"
    original_path = os.path.join(session_dir, original_filename)
    
    try:
        with open(original_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded image: {str(e)}")
        
    # We acquire the lock to run the pipeline sequentially
    async with pipeline_lock:
        python_executable = os.path.join(PROJECT_ROOT, ".venv", "Scripts", "python.exe")
        if not os.path.exists(python_executable):
            python_executable = "python" # Fallback to system python
            
        pipeline_script = os.path.join(PROJECT_ROOT, "run_pipeline_auto.py")
        
        # Build run command
        cmd = [
            python_executable,
            pipeline_script,
            "--image", original_path,
            "--dam-type", dam_type
        ]
        
        print(f"[*] Running pipeline for session {session_id}: {' '.join(cmd)}")
        
        try:
            import subprocess
            # Run the command and capture logs via a thread-safe sync subprocess call to avoid Windows loop issues
            result = await asyncio.to_thread(
                subprocess.run,
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=PROJECT_ROOT
            )
            logs = result.stdout
            returncode = result.returncode
            
            # Save logs to session directory
            log_path = os.path.join(session_dir, "execution.log")
            with open(log_path, "w", encoding="utf-8") as lf:
                lf.write(logs)
                
            if returncode != 0:
                return JSONResponse(
                    status_code=500,
                    content={
                        "success": False,
                        "session_id": session_id,
                        "logs": logs,
                        "error": f"Pipeline failed with return code {returncode}"
                    }
                )
                
            # Copy output files to the session folder
            src_render = os.path.join(PROJECT_ROOT, "outputs", "blender_renders", "dam_thermal_3d_render.png")
            src_json = os.path.join(PROJECT_ROOT, "outputs", "thermal_json", "thermal_result.json")
            
            dest_render = os.path.join(session_dir, "dam_thermal_3d_render.png")
            dest_json = os.path.join(session_dir, "thermal_result.json")
            
            # Check if output files exist and copy them
            if os.path.exists(src_render):
                shutil.copy2(src_render, dest_render)
            else:
                logs += "\n[!] Render image not found at outputs/blender_renders/dam_thermal_3d_render.png"
                
            stats = {}
            if os.path.exists(src_json):
                shutil.copy2(src_json, dest_json)
                # Load stats from JSON
                try:
                    with open(dest_json, "r", encoding="utf-8") as jf:
                        stats = json.load(jf)
                except Exception as je:
                    logs += f"\n[!] Failed to parse thermal_result.json: {str(je)}"
            else:
                logs += "\n[!] JSON output not found at outputs/thermal_json/thermal_result.json"
                
            return {
                "success": True,
                "session_id": session_id,
                "original_image_url": f"/outputs/sessions/{session_id}/{original_filename}",
                "render_image_url": f"/outputs/sessions/{session_id}/dam_thermal_3d_render.png" if os.path.exists(dest_render) else None,
                "stats": stats,
                "logs": logs
            }
            
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "session_id": session_id,
                    "error": f"Internal server error during analysis execution: {str(e)}"
                }
            )

# Mount outputs directory to serve renders and original images
app.mount("/outputs", StaticFiles(directory=os.path.join(PROJECT_ROOT, "outputs")), name="outputs")

# Mount web frontend folder (we will create this folder next)
web_dir = os.path.join(PROJECT_ROOT, "web")
os.makedirs(web_dir, exist_ok=True)

# Helper route for serving index.html
@app.get("/")
async def read_index():
    index_path = os.path.join(web_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Welcome to Cidelta Thermal MVP! Frontend assets are missing."}

app.mount("/", StaticFiles(directory=web_dir), name="web")

if __name__ == "__main__":
    import uvicorn
    # Run server locally on port 8000
    uvicorn.run(app, host="127.0.0.1", port=8000)
