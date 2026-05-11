import bpy
import math
import json
import os
from mathutils import Vector

# =========================================================
# 1. 기본 설정
# =========================================================

DAM_LENGTH_X = 70.0
BASE_WIDTH_Y = 70.0
HEIGHT_Z = 25.0

UPSTREAM_ANGLE_DEG = 60

SLICE_INTERVAL = 5.0

CELL_X = 1.0
CELL_LEG_Y = 1.0
CELL_LEG_Z = 1.0

DOWNSTREAM_ANGLE_DEG = math.degrees(math.atan(CELL_LEG_Z / CELL_LEG_Y))

# 변위를 실제 형상에 얼마나 반영할지
# 0.0이면 완전히 붙은 정규 셀
# 0.15~0.25면 울퉁불퉁함이 보임
DISPLACEMENT_VISUAL_SCALE = 0.20

WIRE_THICKNESS = 0.014
SHOW_CELL_WIREFRAME = True

BOUNDARY_LINE_THICKNESS = 0.045

# =========================================================
# 2. 초기화
# =========================================================

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

bpy.context.scene.unit_settings.system = 'METRIC'
bpy.context.scene.unit_settings.scale_length = 1.0

# 이전 실행에서 남은 선택 핸들러 제거
for h in bpy.app.handlers.depsgraph_update_post[:]:
    if getattr(h, "__name__", "") == "sync_slice_selection":
        bpy.app.handlers.depsgraph_update_post.remove(h)

# =========================================================
# 3. 재질 생성
# =========================================================

def make_mat(name, color, alpha=1.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = color

    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        if "Base Color" in bsdf.inputs:
            bsdf.inputs["Base Color"].default_value = color
        if "Alpha" in bsdf.inputs:
            bsdf.inputs["Alpha"].default_value = alpha
        if "Roughness" in bsdf.inputs:
            bsdf.inputs["Roughness"].default_value = 0.65

    if alpha < 1.0:
        if hasattr(mat, "blend_method"):
            mat.blend_method = 'BLEND'
        if hasattr(mat, "surface_render_method"):
            mat.surface_render_method = 'BLENDED'
        if hasattr(mat, "use_transparency_overlap"):
            mat.use_transparency_overlap = True

    return mat

mat_body = make_mat("Continuous_Dam_Body_Context", (0.62, 0.52, 0.40, 0.30), 0.30)
mat_water = make_mat("Water", (0.15, 0.42, 0.95, 0.35), 0.35)

mat_selector = make_mat("Slice_Selector_Transparent", (1.0, 1.0, 1.0, 0.06), 0.06)
mat_boundary = make_mat("5m_Boundary_Black", (0.0, 0.0, 0.0, 1.0))

mat_stable = make_mat("Stable_Green", (0.25, 0.80, 0.25, 1.0))

# 바깥으로 튀어나온 경우
mat_out_low  = make_mat("Outward_Low_Yellow", (0.95, 0.88, 0.20, 1.0))
mat_out_mid  = make_mat("Outward_Mid_Orange", (1.00, 0.52, 0.10, 1.0))
mat_out_high = make_mat("Outward_High_Red", (0.90, 0.08, 0.08, 1.0))

# 안쪽으로 들어간 경우
mat_in_low  = make_mat("Inward_Low_SkyBlue", (0.45, 0.80, 1.00, 1.0))
mat_in_mid  = make_mat("Inward_Mid_Blue", (0.15, 0.40, 0.95, 1.0))
mat_in_high = make_mat("Inward_High_Purple", (0.62, 0.25, 0.90, 1.0))

mat_wire = make_mat("Black_Cell_Edges", (0.02, 0.02, 0.02, 1.0))

# =========================================================
# 4. 댐 단면 계산
# =========================================================

theta_up = math.radians(UPSTREAM_ANGLE_DEG)

run_up = HEIGHT_Z / math.tan(theta_up)

# 외부 사면은 1m, 1m, sqrt(2) 직각삼각형 셀 기준
downstream_run = HEIGHT_Z * (CELL_LEG_Y / CELL_LEG_Z)

top_width = BASE_WIDTH_Y - run_up - downstream_run

if top_width <= 0:
    raise ValueError("상부 폭이 0 이하입니다. BASE_WIDTH_Y를 키우거나 HEIGHT_Z를 낮추세요.")

# 측면 단면 좌표: (Y, Z)
A = (0.0, 0.0)
B = (run_up, HEIGHT_Z)
C = (run_up + top_width, HEIGHT_Z)
D = (BASE_WIDTH_Y, 0.0)

profile = [A, B, C, D]

cell_hypotenuse = math.sqrt(CELL_LEG_Y ** 2 + CELL_LEG_Z ** 2)

# 외부 사면 바깥쪽 법선
normal_y = CELL_LEG_Z / cell_hypotenuse
normal_z = CELL_LEG_Y / cell_hypotenuse

num_slices = int(DAM_LENGTH_X / SLICE_INTERVAL)

print("===== Dam Info =====")
print(f"Height: {HEIGHT_Z} m")
print(f"Base width: {BASE_WIDTH_Y} m")
print(f"Top width: {top_width:.3f} m")
print(f"Upstream angle: {UPSTREAM_ANGLE_DEG} deg")
print(f"Downstream angle: {DOWNSTREAM_ANGLE_DEG:.2f} deg")
print(f"Cell side triangle: {CELL_LEG_Y}m, {CELL_LEG_Z}m, {cell_hypotenuse:.3f}m")
print(f"Number of slices: {num_slices}")

# =========================================================
# 5. 가상 변위 함수
# =========================================================

def gaussian(x, s, cx, cs, sx, ss):
    return math.exp(-0.5 * (((x - cx) / sx) ** 2 + ((s - cs) / ss) ** 2))

def displacement_components(x, s):
    # 바깥으로 불룩 튀어나옴
    bulge_outward = 1.40 * gaussian(x, s, 16, 18, 7, 5)

    # 안쪽으로 움푹 들어감
    sink_inward = -1.15 * gaussian(x, s, 39, 31, 6, 6)

    # 하단부 밀림
    lower_slide = 0.75 * gaussian(x, s, 55, 32, 10, 8) * (s / HEIGHT_Z)

    # 대각선 침하/균열 밴드
    diagonal_line = 0.45 * x + 5
    distance_to_line = s - diagonal_line
    crack_band = -0.65 * math.exp(-0.5 * (distance_to_line / 1.3) ** 2) * math.exp(
        -0.5 * ((x - 48) / 20) ** 2
    )

    return {
        "bulge_outward": bulge_outward,
        "sink_inward": sink_inward,
        "lower_slide": lower_slide,
        "crack_band": crack_band,
    }

def total_displacement(x, s):
    comps = displacement_components(x, s)
    total = sum(comps.values())
    dominant = max(comps, key=lambda k: abs(comps[k]))
    return total, dominant

def displacement_class(displacement):
    a = abs(displacement)

    if a < 0.20:
        return "stable", 0, "neutral"

    if displacement > 0:
        if a < 0.60:
            return "out_low", 1, "outward"
        elif a < 1.00:
            return "out_mid", 2, "outward"
        else:
            return "out_high", 3, "outward"

    else:
        if a < 0.60:
            return "in_low", 1, "inward"
        elif a < 1.00:
            return "in_mid", 2, "inward"
        else:
            return "in_high", 3, "inward"

def get_material_for_displacement(displacement):
    color_name, magnitude_level, direction = displacement_class(displacement)

    if color_name == "stable":
        return mat_stable, color_name, magnitude_level, direction
    if color_name == "out_low":
        return mat_out_low, color_name, magnitude_level, direction
    if color_name == "out_mid":
        return mat_out_mid, color_name, magnitude_level, direction
    if color_name == "out_high":
        return mat_out_high, color_name, magnitude_level, direction
    if color_name == "in_low":
        return mat_in_low, color_name, magnitude_level, direction
    if color_name == "in_mid":
        return mat_in_mid, color_name, magnitude_level, direction
    if color_name == "in_high":
        return mat_in_high, color_name, magnitude_level, direction

    return mat_stable, "stable", 0, "neutral"

# =========================================================
# 6. 컬렉션
# =========================================================

main_collection = bpy.data.collections.new(
    "01_Attached_Dam_With_5m_Slices_And_Individual_Cells"
)
bpy.context.scene.collection.children.link(main_collection)

cell_root_collection = bpy.data.collections.new("02_Individual_Outer_Prism_Cells_By_Slice")
main_collection.children.link(cell_root_collection)

selector_collection = bpy.data.collections.new("03_5m_Slice_Selectors")
main_collection.children.link(selector_collection)

boundary_collection = bpy.data.collections.new("04_Visible_5m_Boundary_Lines")
main_collection.children.link(boundary_collection)

context_collection = bpy.data.collections.new("05_Water_And_Context")
main_collection.children.link(context_collection)

# =========================================================
# 7. 연속된 통짜 댐 몸체 생성
# =========================================================

def create_continuous_dam_body(collection):
    verts = []

    for x in [0.0, DAM_LENGTH_X]:
        for y, z in profile:
            verts.append((x, y, z))

    faces = [
        (0, 4, 5, 1),   # 물 쪽 사면
        (1, 5, 6, 2),   # 상단
        # 외부 사면은 셀들이 담당하므로 제외
        # (2, 6, 7, 3),
        (3, 7, 4, 0),   # 바닥
        (0, 1, 2, 3),   # 시작 단면
        (4, 7, 6, 5),   # 끝 단면
    ]

    mesh = bpy.data.meshes.new("Continuous_Dam_Body_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()

    obj = bpy.data.objects.new("Continuous_Dam_Body_Attached", mesh)
    collection.objects.link(obj)
    obj.data.materials.append(mat_body)

    return obj

# =========================================================
# 8. 5m 선택용 Selector 생성
# =========================================================

def create_slice_selector(x0, x1, slice_id, collection):
    """
    실제 댐을 자르지는 않고, 5m 구간 선택용 투명 박스만 생성.
    이 Selector를 선택하면 해당 슬라이스의 작은 셀들이 같이 선택됨.
    """

    verts = []

    for y, z in profile:
        verts.append((x0, y, z))

    for y, z in profile:
        verts.append((x1, y, z))

    faces = [
        (0, 4, 5, 1),
        (1, 5, 6, 2),
        (2, 6, 7, 3),
        (3, 7, 4, 0),
        (0, 1, 2, 3),
        (4, 7, 6, 5),
    ]

    mesh = bpy.data.meshes.new(f"Slice_{slice_id:02d}_Selector_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()

    obj = bpy.data.objects.new(
        f"Slice_{slice_id:02d}_Selector_{int(x0)}m_{int(x1)}m",
        mesh
    )
    collection.objects.link(obj)
    obj.data.materials.append(mat_selector)

    obj.display_type = 'WIRE'
    obj.show_in_front = True
    obj.hide_render = True

    obj["slice_id"] = slice_id
    obj["is_slice_selector"] = True

    return obj

# =========================================================
# 9. 5m 경계선 생성
# =========================================================

def create_curve_line(name, points, mat, collection, thickness):
    curve = bpy.data.curves.new(name, type='CURVE')
    curve.dimensions = '3D'
    curve.resolution_u = 1
    curve.bevel_depth = thickness
    curve.bevel_resolution = 2

    spline = curve.splines.new(type='POLY')
    spline.points.add(len(points) - 1)

    for p, co in zip(spline.points, points):
        p.co = (co[0], co[1], co[2], 1.0)

    obj = bpy.data.objects.new(name, curve)
    collection.objects.link(obj)
    obj.data.materials.append(mat)

    return obj

def create_5m_boundary_lines(collection):
    for k in range(num_slices + 1):
        x = k * SLICE_INTERVAL

        # 외부 사면 쪽 경계선
        outer_points = []

        z_count = int(round(HEIGHT_Z / CELL_LEG_Z))

        for iz in range(z_count + 1):
            z = HEIGHT_Z - iz * CELL_LEG_Z
            y = C[0] + iz * CELL_LEG_Y
            outer_points.append((x, y, z))

        create_curve_line(
            f"Boundary_Outer_Slope_{k:02d}_{int(x)}m",
            outer_points,
            mat_boundary,
            collection,
            BOUNDARY_LINE_THICKNESS
        )

        # 상단 경계선
        create_curve_line(
            f"Boundary_Top_{k:02d}_{int(x)}m",
            [(x, B[0], B[1]), (x, C[0], C[1])],
            mat_boundary,
            collection,
            BOUNDARY_LINE_THICKNESS * 0.75
        )

# =========================================================
# 10. 외부 셀 점 계산
# =========================================================

def shifted_outer_point(x, y, z, s):
    """
    외부 사면 위의 점을 변위값에 따라 바깥/안쪽으로 이동.
    같은 좌표는 같은 변위로 계산되므로 슬라이스 사이 틈이 줄어듦.
    """

    disp, dominant = total_displacement(x, s)

    shift_y = disp * DISPLACEMENT_VISUAL_SCALE * normal_y
    shift_z = disp * DISPLACEMENT_VISUAL_SCALE * normal_z

    return (x, y + shift_y, z + shift_z), disp, dominant

# =========================================================
# 11. 작은 직각삼각기둥 셀 생성
# =========================================================

def create_single_prism_cell(
    cell_id,
    slice_id,
    xa,
    xb,
    iz,
    collection
):
    z_top = HEIGHT_Z - iz * CELL_LEG_Z
    z_bottom = HEIGHT_Z - (iz + 1) * CELL_LEG_Z

    y_top = C[0] + iz * CELL_LEG_Y
    y_bottom = C[0] + (iz + 1) * CELL_LEG_Y

    s_top = iz * cell_hypotenuse
    s_bottom = (iz + 1) * cell_hypotenuse
    s_mid = (iz + 0.5) * cell_hypotenuse

    # 외부 사면 위의 두 점은 vertex-based displacement 사용
    p0, _, _ = shifted_outer_point(xa, y_top, z_top, s_top)
    p1, _, _ = shifted_outer_point(xa, y_bottom, z_bottom, s_bottom)
    p3, _, _ = shifted_outer_point(xb, y_top, z_top, s_top)
    p4, _, _ = shifted_outer_point(xb, y_bottom, z_bottom, s_bottom)

    # 내부 직각 꼭짓점은 기본 위치 유지
    # 겉 한 겹 셀의 두께 기준점 역할
    p2 = (xa, y_top, z_bottom)
    p5 = (xb, y_top, z_bottom)

    x_mid = (xa + xb) / 2.0
    disp_mid, dominant = total_displacement(x_mid, s_mid)

    verts = [p0, p1, p2, p3, p4, p5]

    faces = [
        (0, 2, 1),     # 왼쪽 삼각형 면
        (3, 4, 5),     # 오른쪽 삼각형 면
        (0, 1, 4, 3),  # 외부 빗변 사각형 면
        (0, 3, 5, 2),  # 내부 세로 사각형 면
        (2, 5, 4, 1),  # 내부 아래 사각형 면
    ]

    mesh = bpy.data.meshes.new(f"Cell_{cell_id}_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()

    obj = bpy.data.objects.new(f"Cell_{cell_id}", mesh)
    collection.objects.link(obj)

    mat_disp, color_name, magnitude_level, direction = get_material_for_displacement(disp_mid)

    obj.data.materials.append(mat_disp)
    obj.data.materials.append(mat_wire)

    for poly in obj.data.polygons:
        poly.material_index = 0

    if SHOW_CELL_WIREFRAME:
        wire_mod = obj.modifiers.new("Visible_Cell_Edges", 'WIREFRAME')
        wire_mod.thickness = WIRE_THICKNESS
        wire_mod.use_replace = False
        wire_mod.use_even_offset = True
        wire_mod.use_boundary = True

        if hasattr(wire_mod, "material_offset"):
            wire_mod.material_offset = 1

    obj.show_in_front = True

    obj["slice_id"] = slice_id
    obj["is_slice_cell"] = True
    obj["cell_id"] = cell_id
    obj["displacement_m"] = round(disp_mid, 4)
    obj["dominant_virtual_case"] = dominant
    obj["direction"] = direction
    obj["magnitude_level"] = magnitude_level
    obj["color_class"] = color_name

    record = {
        "cell_id": cell_id,
        "object_name": obj.name,
        "slice_id": slice_id,
        "x_range_m": [round(xa, 4), round(xb, 4)],
        "z_range_m": [round(z_bottom, 4), round(z_top, 4)],
        "cell_type": "right_triangular_prism_outer_shell",
        "side_triangle_m": {
            "horizontal_leg_y": CELL_LEG_Y,
            "vertical_leg_z": CELL_LEG_Z,
            "hypotenuse": round(cell_hypotenuse, 4)
        },
        "outer_face_size_m": {
            "width_x": CELL_X,
            "height_along_slope": round(cell_hypotenuse, 4)
        },
        "vertices": {
            "p0": [round(v, 4) for v in p0],
            "p1": [round(v, 4) for v in p1],
            "p2": [round(v, 4) for v in p2],
            "p3": [round(v, 4) for v in p3],
            "p4": [round(v, 4) for v in p4],
            "p5": [round(v, 4) for v in p5],
        },
        "displacement_m": round(disp_mid, 4),
        "abs_displacement_m": round(abs(disp_mid), 4),
        "dominant_virtual_case": dominant,
        "direction": direction,
        "magnitude_level": magnitude_level,
        "color_class": color_name
    }

    return obj, record

# =========================================================
# 12. 슬라이스별 셀 생성
# =========================================================

def create_cells_for_slice(x0, x1, slice_id, root_collection, json_records):
    slice_collection = bpy.data.collections.new(
        f"Slice_{slice_id:02d}_Cells_{int(x0)}m_{int(x1)}m"
    )
    root_collection.children.link(slice_collection)

    x_count = int(round((x1 - x0) / CELL_X))
    z_count = int(round(HEIGHT_Z / CELL_LEG_Z))

    for ix in range(x_count):
        xa = x0 + ix * CELL_X
        xb = xa + CELL_X

        for iz in range(z_count):
            cell_id = f"S{slice_id:02d}_X{ix:02d}_Z{iz:02d}"

            _, record = create_single_prism_cell(
                cell_id=cell_id,
                slice_id=slice_id,
                xa=xa,
                xb=xb,
                iz=iz,
                collection=slice_collection
            )

            record["slice_range_m"] = [round(x0, 4), round(x1, 4)]
            json_records.append(record)

# =========================================================
# 13. 물 생성
# =========================================================

def create_box(name, minx, maxx, miny, maxy, minz, maxz, mat, collection):
    verts = [
        (minx, miny, minz),
        (maxx, miny, minz),
        (maxx, maxy, minz),
        (minx, maxy, minz),
        (minx, miny, maxz),
        (maxx, miny, maxz),
        (maxx, maxy, maxz),
        (minx, maxy, maxz),
    ]

    faces = [
        (0, 1, 2, 3),
        (4, 7, 6, 5),
        (0, 4, 5, 1),
        (1, 5, 6, 2),
        (2, 6, 7, 3),
        (3, 7, 4, 0),
    ]

    mesh = bpy.data.meshes.new(name + "_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()

    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.data.materials.append(mat)

    return obj

# =========================================================
# 14. Selector 선택 시 해당 슬라이스 셀 같이 선택
# =========================================================

_SELECTION_SYNC_GUARD = False

def sync_slice_selection(scene, depsgraph):
    global _SELECTION_SYNC_GUARD

    if _SELECTION_SYNC_GUARD:
        return

    selected = bpy.context.selected_objects
    if not selected:
        return

    target_slice_ids = set()

    for obj in selected:
        if obj.get("is_slice_selector"):
            sid = obj.get("slice_id")
            if sid is not None:
                target_slice_ids.add(int(sid))

    if not target_slice_ids:
        return

    try:
        _SELECTION_SYNC_GUARD = True

        for sid in target_slice_ids:
            for obj in bpy.data.objects:
                if obj.get("slice_id") == sid:
                    obj.select_set(True)

    finally:
        _SELECTION_SYNC_GUARD = False

bpy.app.handlers.depsgraph_update_post.append(sync_slice_selection)

# =========================================================
# 15. 실제 생성
# =========================================================

all_cell_records = []

# 통짜 댐 몸체
create_continuous_dam_body(context_collection)

# 5m 경계선
create_5m_boundary_lines(boundary_collection)

# 5m Selector와 셀 생성
for k in range(num_slices):
    x0 = k * SLICE_INTERVAL
    x1 = (k + 1) * SLICE_INTERVAL

    create_slice_selector(x0, x1, k, selector_collection)
    create_cells_for_slice(x0, x1, k, cell_root_collection, all_cell_records)

# 물
create_box(
    "Water_Block",
    0.0,
    DAM_LENGTH_X,
    -16.0,
    1.2,
    0.0,
    HEIGHT_Z * 0.85,
    mat_water,
    context_collection
)

# =========================================================
# 16. JSON 저장
# =========================================================

metadata = {
    "description": "Continuous attached dam body with 5m slice boundaries. Only downstream exterior outer layer is divided into individual right triangular prism cells.",
    "important_note": "Synthetic MVP geometry for visualization and data-pipeline testing, not real structural analysis.",
    "coordinate_system": {
        "X": "dam longitudinal direction",
        "Y": "from water side toward downstream exterior side",
        "Z": "height"
    },
    "dam_parameters": {
        "length_x_m": DAM_LENGTH_X,
        "base_width_y_m": BASE_WIDTH_Y,
        "height_z_m": HEIGHT_Z,
        "upstream_angle_deg": UPSTREAM_ANGLE_DEG,
        "downstream_angle_deg": round(DOWNSTREAM_ANGLE_DEG, 4),
        "top_width_m": round(top_width, 4),
        "slice_interval_m": SLICE_INTERVAL,
        "number_of_slices": num_slices
    },
    "cell_definition": {
        "cell_type": "right_triangular_prism",
        "individual_cell_objects": True,
        "x_width_m": CELL_X,
        "side_triangle_horizontal_leg_y_m": CELL_LEG_Y,
        "side_triangle_vertical_leg_z_m": CELL_LEG_Z,
        "side_triangle_hypotenuse_m": round(cell_hypotenuse, 4),
        "outer_face_shape": "rectangle",
        "outer_face_width_x_m": CELL_X,
        "outer_face_height_along_slope_m": round(cell_hypotenuse, 4),
        "scope": "only one outer shell layer on downstream exterior side"
    },
    "color_mapping": {
        "stable": "green",
        "out_low": "yellow",
        "out_mid": "orange",
        "out_high": "red",
        "in_low": "skyblue",
        "in_mid": "blue",
        "in_high": "purple"
    }
}

output = {
    "metadata": metadata,
    "cells": all_cell_records
}

base_dir = os.path.dirname(bpy.data.filepath) if bpy.data.filepath else os.path.join(os.path.expanduser("~"), "Desktop")

if not os.path.isdir(base_dir):
    base_dir = os.path.expanduser("~")

json_path = os.path.join(base_dir, "dam_attached_body_outer_cells_directional_risk.json")

with open(json_path, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print("===== JSON Export Complete =====")
print(f"Exported cells: {len(all_cell_records)}")
print(f"Saved to: {json_path}")

# =========================================================
# 17. 조명 / 카메라
# =========================================================

bpy.ops.object.light_add(type='AREA', location=(35, -60, 70))
light = bpy.context.object
light.name = "Area Light"
light.data.energy = 1200
light.data.size = 15

bpy.ops.object.camera_add(location=(100, -120, 55))
cam = bpy.context.object
cam.name = "Camera"

target = Vector((DAM_LENGTH_X / 2, BASE_WIDTH_Y / 2, HEIGHT_Z / 2))
direction = target - cam.location
cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

bpy.context.scene.camera = cam

for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        for space in area.spaces:
            if space.type == 'VIEW_3D':
                space.clip_end = 1000

print("===== Finished =====")
print("Continuous dam body is attached.")
print("5m slices are shown by boundary lines and selector boxes.")
print("Outer prism cells are individual selectable objects.")
print("Click Slice_XX_Selector, then press '/' to view that 5m slice and its cells.")