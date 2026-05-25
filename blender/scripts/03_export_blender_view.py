import bpy
import os

def export_view():
    print("=========================================================")
    print(" [*] Rendering Blender Active Camera View...")
    print("=========================================================")
    
    # Determine the project output paths
    if '__file__' in globals():
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    else:
        project_root = os.getcwd()
        
    render_dir = os.path.join(project_root, "outputs", "blender_renders")
    if not os.path.exists(render_dir):
        # Fallback to candidates if needed
        blend_dir = os.path.dirname(bpy.data.filepath) if bpy.data.filepath else ""
        candidate_dirs = [
            os.path.join(blend_dir, "..", "outputs", "blender_renders"),
            os.path.join(blend_dir, "outputs", "blender_renders"),
            os.path.join(os.getcwd(), "outputs", "blender_renders"),
            "C:\\Users\\user\\Desktop\\Cidelta-thermal_MVP\\outputs\\blender_renders"
        ]
        for d in candidate_dirs:
            if d:
                render_dir = os.path.abspath(d)
                break
                
    if render_dir and not os.path.exists(render_dir):
        os.makedirs(render_dir, exist_ok=True)
        
    output_path = os.path.join(render_dir, "dam_thermal_3d_render.png")
    
    # Configure Blender scene render settings
    scene = bpy.context.scene
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = output_path
    
    # Execute the render
    print(f"[*] Starting render. Saving to: {output_path}")
    try:
        bpy.ops.render.render(write_still=True)
        print(" [+] Rendering complete and saved successfully!")
    except Exception as e:
        print(f"[!] Error during rendering: {e}")
    print("=========================================================")

if __name__ == "__main__":
    export_view()
