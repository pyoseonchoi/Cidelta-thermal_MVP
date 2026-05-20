import bpy
import json
import os

def make_thermal_material(name, color, alpha=1.0):
    """
    Creates or retrieves a material with custom base color and transparency.
    """
    mat = bpy.data.materials.get(name)
    if not mat:
        mat = bpy.data.materials.new(name)
    
    mat.use_nodes = True
    # Clear node tree
    mat.node_tree.nodes.clear()
    
    # Create Principled BSDF and Output nodes
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    node_bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    
    # Set properties
    if "Base Color" in node_bsdf.inputs:
        node_bsdf.inputs["Base Color"].default_value = color
    if "Alpha" in node_bsdf.inputs:
        node_bsdf.inputs["Alpha"].default_value = alpha
    if "Roughness" in node_bsdf.inputs:
        node_bsdf.inputs["Roughness"].default_value = 0.5
        
    # Link nodes
    links.new(node_bsdf.outputs["BSDF"], node_output.inputs["Surface"])
    
    # Set diffuse color for viewport display
    mat.diffuse_color = color
    
    # Set transparency settings for EEVEE/Viewport rendering
    if alpha < 1.0:
        if hasattr(mat, "blend_method"):
            mat.blend_method = 'BLEND'
        if hasattr(mat, "surface_render_method"):
            mat.surface_render_method = 'BLENDED'
        if hasattr(mat, "use_transparency_overlap"):
            mat.use_transparency_overlap = True
            
    return mat

def apply_thermal():
    print("=========================================================")
    print(" [*] Applying Dam Thermal Analysis Results in Blender")
    print("=========================================================")
    
    # List of possible paths to find the thermal result JSON
    blend_dir = os.path.dirname(bpy.data.filepath) if bpy.data.filepath else ""
    candidate_paths = [
        os.path.join(blend_dir, "..", "outputs", "thermal_json", "thermal_result.json"),
        os.path.join(blend_dir, "outputs", "thermal_json", "thermal_result.json"),
        os.path.join(os.getcwd(), "outputs", "thermal_json", "thermal_result.json"),
        "C:\\Users\\user\\Desktop\\Cidelta-thermal_MVP\\outputs\\thermal_json\\thermal_result.json"
    ]
    
    json_path = None
    for path in candidate_paths:
        if path and os.path.exists(path):
            json_path = os.path.abspath(path)
            break
            
    if not json_path:
        print("[!] Error: thermal_result.json not found in candidate paths:")
        for path in candidate_paths:
            if path:
                print(f"  - {path}")
        return
        
    print(f"[*] Loading results from: {json_path}")
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"[!] Error parsing JSON: {e}")
        return
        
    # Create materials for each risk level
    # Format: (R, G, B, A)
    mats = {
        0: make_thermal_material("Thermal_Risk_0_Stable", (0.15, 0.75, 0.35, 0.40), 0.40),  # Soft Transparent Green
        1: make_thermal_material("Thermal_Risk_1_Low", (0.90, 0.85, 0.15, 0.75), 0.75),     # Translucent Yellow
        2: make_thermal_material("Thermal_Risk_2_Medium", (0.95, 0.45, 0.05, 0.95), 0.95),   # Opaque Orange
        3: make_thermal_material("Thermal_Risk_3_High", (0.90, 0.05, 0.05, 1.00), 1.00)     # Opaque Red
    }
    
    cells = data.get("cells", [])
    updated_count = 0
    missing_count = 0
    
    for cell in cells:
        cell_id = cell.get("cell_id")
        risk_lvl = cell.get("thermal_risk_level", 0)
        
        # Select appropriate material
        target_mat = mats.get(risk_lvl, mats[0])
        
        # Find object in Blender scene
        obj_name = f"Cell_{cell_id}"
        obj = bpy.data.objects.get(obj_name)
        
        if obj:
            # Update the first material (the face material)
            if len(obj.data.materials) > 0:
                obj.data.materials[0] = target_mat
            else:
                obj.data.materials.append(target_mat)
                
            # Assign metadata custom properties to the Blender object for interactivity
            obj["thermal_mean_temp_c"] = cell.get("thermal_mean_temp_c", 0.0)
            obj["thermal_delta_t_c"] = cell.get("thermal_delta_t_c", 0.0)
            obj["thermal_anomaly_score"] = cell.get("thermal_anomaly_score", 0.0)
            obj["seepage_probability"] = cell.get("seepage_probability", 0.0)
            obj["moisture_level"] = cell.get("moisture_level", "low")
            obj["thermal_risk_level"] = risk_lvl
            
            updated_count += 1
        else:
            missing_count += 1
            
    print("---------------------------------------------------------")
    print(f" [+] Result mapping complete!")
    print(f"      Mapped cell objects:  {updated_count}")
    if missing_count > 0:
        print(f"      Unmatched cell names: {missing_count} (ignored)")
    print("=========================================================")

if __name__ == "__main__":
    apply_thermal()
