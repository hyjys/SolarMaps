"""조립 가이드용 그림 렌더 (Blender 5.x, build_stand.py 실행 후).

결과: modeling/stand_guide/_img/*.png (투명 배경, Workbench) + anchors.json (설명선 끝점의 화면 좌표).
build_pdf.py 가 PDF 로 묶는다.
"""
import math
import os

import json

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else \
    r"C:\Users\이민기\Desktop\개발\EURIF\SolarMaps\modeling\stand_guide"
IMG_DIR = os.path.join(HERE, "_img")
STAND_PY = os.path.join(os.path.dirname(HERE), "build_stand.py")

# build_stand.py 상단 상수만 가져온다
C = {}
exec(open(STAND_PY, encoding="utf-8").read().split("FONT_PATHS")[0], C)
FX, FY, HALF = C["FX"], C["FY"], C["HALF"]
HZ, KN_Y, AX_Z, GAP = C["HZ"], C["KN_Y"], C["AX_Z"], C["GAP"]
LEG_A, LEG_B, LEG_T, EAR_T = C["LEG_A"], C["LEG_B"], C["LEG_T"], C["EAR_T"]
KEY_U, KEY_L, KEY_Z = C["KEY_U"], C["KEY_L"], C["KEY_Z"]
RAIL_T, RIM_W, PANEL_CLR = C["RAIL_T"], C["RIM_W"], C["PANEL_CLR"]
CLIP_L, CLIP_GAP, WEDGE_W, WEDGE_L = C["CLIP_L"], C["CLIP_GAP"], C["WEDGE_W"], C["WEDGE_L"]
WEDGE_MIN, WEDGE_MAX, WEDGE_TOOTH = C["WEDGE_MIN"], C["WEDGE_MAX"], C["WEDGE_TOOTH"]
PANEL_T = C["PANEL_T_SHOW"]

T = Matrix.Translation
R = Matrix.Rotation
O = bpy.data.objects
SC = bpy.data.scenes["SolarMaps_Stand"]
(bpy.context.window or bpy.context.window_manager.windows[0]).scene = SC

# ---- 렌더 설정 ----
try:
    SC.render.engine = "BLENDER_WORKBENCH"
except TypeError:
    pass
SC.render.film_transparent = True
SC.render.image_settings.file_format = "PNG"
SC.render.image_settings.color_mode = "RGBA"
sh = SC.display.shading
sh.light = "STUDIO"
sh.color_type = "MATERIAL"
sh.show_object_outline = True
sh.object_outline_color = (0, 0, 0)
sh.show_cavity = True
sh.cavity_type = "BOTH"
SC.display.render_aa = "16"
SC.view_settings.view_transform = "Standard"

GUIDE = bpy.data.collections.get("SolarMaps_Stand_Guide") or bpy.data.collections.new("SolarMaps_Stand_Guide")
if GUIDE.name not in SC.collection.children:
    SC.collection.children.link(GUIDE)
for c in ("SolarMaps_Stand", "SolarMaps_Stand_Ref", "SolarMaps_Stand_Plates", "SolarMaps_Stand_Guide"):
    bpy.data.collections[c].hide_render = False
    bpy.data.collections[c].hide_viewport = False


cam_data = bpy.data.cameras.get("GuideCam") or bpy.data.cameras.new("GuideCam")
cam = O.get("GuideCam") or bpy.data.objects.new("GuideCam", cam_data)
if cam.name not in GUIDE.objects:
    GUIDE.objects.link(cam)
cam_data.clip_start, cam_data.clip_end = 1, 10000
SC.camera = cam


def clear_guide():
    for ob in list(GUIDE.objects):
        if ob is not cam:
            data = ob.data
            bpy.data.objects.remove(ob, do_unlink=True)
            if isinstance(data, bpy.types.Curve):
                bpy.data.curves.remove(data)


def inst(src, m):
    ob = bpy.data.objects.new(src.name + "_g", src.data)
    GUIDE.objects.link(ob)
    ob.matrix_world = m
    return ob


def set_cam(loc, target, lens=50.0, ortho=None):
    cam.location = loc
    d = Vector(target) - Vector(loc)
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    if ortho:
        cam_data.type = "ORTHO"
        cam_data.ortho_scale = ortho
    else:
        cam_data.type = "PERSP"
        cam_data.lens = lens
    bpy.context.view_layer.update()


ANCHORS = {}
CUR = []


def callout(key, loc):
    """설명선이 가리킬 점 — 화면 정규화 좌표 (0~1, 좌하단 원점) 로 기록."""
    CUR.append((key, Vector(loc)))       # 투영은 render() 에서 해상도(화면비)를 정한 뒤에


def show_only(objs):
    keep = set(objs) | {cam} | set(GUIDE.objects)
    for ob in SC.objects:
        ob.hide_render = ob not in keep


def render(name, res=(1800, 1200)):
    SC.render.resolution_x, SC.render.resolution_y = res
    SC.render.resolution_percentage = 100
    pts = []
    for key, co in CUR:
        u, v, _ = world_to_camera_view(SC, cam, co)
        pts.append((key, round(u, 4), round(v, 4)))
    ANCHORS[name] = {"res": list(res), "points": pts}
    CUR.clear()
    SC.render.filepath = os.path.join(IMG_DIR, name + ".png")
    bpy.ops.render.render(write_still=True)


def foot_d(deg):
    th = math.radians(deg)
    return LEG_A * math.cos(th) + math.sqrt(LEG_B ** 2 - (LEG_A * math.sin(th) + C["FOOT_DZ"]) ** 2)


def m_frame(deg):
    return T((0, 0, HZ)) @ R(math.radians(deg), 4, "X") @ T((0, -KN_Y, -AX_Z))


def m_leg(deg, x):
    th = math.radians(deg)
    p = (LEG_A * math.cos(th), HZ + LEG_A * math.sin(th))
    f = (foot_d(deg), HZ - C["FOOT_DZ"])
    L = math.hypot(f[0] - p[0], f[1] - p[1])
    uy, uz = (f[0] - p[0]) / L, (f[1] - p[1]) / L
    return Matrix(((0, 0, 1, x), (uy, -uz, 0, p[0]), (uz, uy, 0, p[1]), (0, 0, 0, 1)))


def mat_cols(cx, cy, cz, t):
    return Matrix(((cx[0], cy[0], cz[0], t[0]), (cx[1], cy[1], cz[1], t[1]),
                   (cx[2], cy[2], cz[2], t[2]), (0, 0, 0, 1)))


os.makedirs(IMG_DIR, exist_ok=True)
ASSEMBLED = [ob for ob in bpy.data.collections["SolarMaps_Stand"].objects if not ob.hide_viewport]
PANEL = O["REF_Panel_482x185"]
SHOW = C["SHOW_ANGLE"]
MF = m_frame(SHOW)

# 1. 완성 모습 (앞 / 뒤 아래쪽에서 — 뒷면 口자 개방부)
clear_guide()
show_only(ASSEMBLED + [PANEL])
set_cam((720, -520, 420), (246, 95, 45), lens=42)
callout("frame", MF @ Vector((HALF - 60, FY, RAIL_T + 3)))
callout("base", (FX + 4, 150, 8))
callout("leg", m_leg(SHOW, FX + GAP) @ Vector((55, 0, LEG_T)))
callout("clip", MF @ Vector((C["CLIP_X"][3], -1, 30)))
callout("wedge", MF @ Vector((C["CLIP_X"][2] + 20, RIM_W + PANEL_CLR + 4, RAIL_T + PANEL_T + 5)))
render("01_overview_front")
show_only(ASSEMBLED + [PANEL])
set_cam((560, 640, -30), (246, 95, 50), lens=40)
callout("opening", MF @ Vector((HALF + 90, FY / 2, 0)))
callout("key", MF @ Vector((HALF, KEY_U[0] + 3, 0)))
render("02_overview_back")

# 2. 출력판
clear_guide()
p1, p2 = O["Plate1_L"], O["Plate2_R"]
p1.location, p2.location = (0, 0, 0), (270, 0, 0)
show_only([p1, p2])
set_cam((258, 108, 800), (258, 108, 0), ortho=530)
render("03_plates", (1800, 800))
p2.location = (0, 0, 0)

# 3. 프레임 이음 — 뒷면이 위로 오게 뒤집은 상태, 연결키는 위에서, 핀은 바깥에서
clear_guide()
G = R(math.pi, 4, "X")
inst(O["Stand_FrameHalf_L"], G)
inst(O["Stand_FrameHalf_R"], G)
key_m = G @ T((HALF, KEY_U[0], -35))
inst(O["Stand_Key"], key_m)
inst(O["Stand_Key"], G @ T((HALF, FY - KEY_U[1], -35)))
for x in (HALF - KEY_L / 2, HALF + KEY_L / 2):
    inst(O["Stand_Pin_Joint"], G @ T((x, -30, KEY_Z / 2)) @ R(math.pi / 2, 4, "Z"))
    inst(O["Stand_Pin_Joint"], G @ T((x, FY + 30, KEY_Z / 2)) @ R(-math.pi / 2, 4, "Z"))
show_only([])
set_cam((360, 200, 160), (246.5, -5, 0), lens=40)
callout("key", key_m @ Vector((KEY_L * 0.6, 3.5, KEY_Z)))
callout("slot", G @ Vector((HALF - 12, KEY_U[0] + 3.5, 0)))
callout("jpin", G @ Vector((HALF + KEY_L / 2, -22, KEY_Z / 2)))
callout("half_l", G @ Vector((HALF - 60, 7, 0)))
callout("half_r", G @ Vector((HALF + 50, 7, 0)))
render("04_joint")

# 4. 힌지 — 프레임 반쪽 L + 받침대 L, 힌지 핀을 바깥에서
clear_guide()
inst(O["Stand_FrameHalf_L"], MF)
inst(O["Stand_Base_L"], Matrix())
inst(O["Stand_Pin_Hinge"], T((-GAP - EAR_T - 45, 0, HZ)))
show_only([])
set_cam((-210, -190, 140), (10, 20, 25), lens=50)
callout("hpin", (-GAP - EAR_T - 45 + 12, 0, HZ + 3))
callout("knuckle", MF @ Vector((7, KN_Y, RAIL_T)))
callout("ear", (-GAP - EAR_T / 2, -6, 6))
render("05_hinge")

# 5. 다리 — 다리를 레일 바깥에, 다리 핀으로
clear_guide()
inst(O["Stand_FrameHalf_L"], MF)
inst(O["Stand_Base_L"], Matrix())
inst(O["Stand_Pin_Hinge"], T((-GAP - EAR_T, 0, HZ)))
leg_m = T((-80, 0, 0)) @ m_leg(SHOW, -GAP - LEG_T)
inst(O["Stand_Leg"], leg_m)
pin_m = T((-150, 0, 0)) @ MF @ T((-GAP - LEG_T, KN_Y + LEG_A, AX_Z))
inst(O["Stand_Pin_Leg"], pin_m)
show_only([])
set_cam((-330, -300, 250), (-60, 90, 45), lens=45)
callout("lpin", pin_m @ Vector((8, 0, 3)))
callout("leg", leg_m @ Vector((55, 0, LEG_T)))
callout("lhole", MF @ Vector((0, KN_Y + LEG_A, AX_Z)))
callout("notch", (-GAP - LEG_T / 2, foot_d(SHOW), HZ))
render("06_leg")

# 6. 각도 — 옆(-X)에서 본 최저 / 표시(최적) / 최고 각도
for deg in (min(C["ANGLES"]), SHOW, max(C["ANGLES"])):
    clear_guide()
    mf = m_frame(deg)
    for ob, m in ((O["Stand_FrameHalf_L"], mf), (O["Stand_Base_L"], Matrix()),
                  (O["Stand_Leg"], m_leg(deg, -GAP - LEG_T)),
                  (O["Stand_Pin_Hinge"], T((-GAP - EAR_T, 0, HZ))),
                  (O["Stand_Pin_Leg"], mf @ T((-GAP - LEG_T, KN_Y + LEG_A, AX_Z))), (PANEL, mf)):
        inst(ob, m)
    show_only([])
    set_cam((-600, 95, 95), (0, 95, 95), ortho=250)
    render(f"07_angle_{deg}", (1200, 1200))

# 7. 클립 + 쐐기 — 평평한 프레임 위 (분해 / 쐐기 대기 / 완료)
x0 = 70.0
s_mid = (CLIP_GAP - PANEL_T - WEDGE_TOOTH - WEDGE_MIN) / (WEDGE_MAX - WEDGE_MIN) * WEDGE_L
wz = RAIL_T + PANEL_T
m_clip = mat_cols((0, 1, 0), (0, 0, 1), (1, 0, 0), (x0 - CLIP_L / 2, 0, 0))
m_wedge = mat_cols((1, 0, 0), (0, 0, 1), (0, -1, 0), (x0 - s_mid, RIM_W + PANEL_CLR + WEDGE_W, wz))
for name, dy, dx in (("08_clip_step1", -45, 75), ("09_clip_step2", 0, 75), ("10_clip_done", 0, 0)):
    clear_guide()
    inst(O["Stand_FrameHalf_L"], Matrix())
    inst(PANEL, Matrix())
    inst(O["Stand_Clip"], T((0, dy, 0)) @ m_clip)
    inst(O["Stand_Wedge"], T((dx, 0, 0)) @ m_wedge)
    show_only([])
    set_cam((-20, -190, 140), (100, 10, 18), lens=55)
    callout("clip", T((0, dy, 0)) @ m_clip @ Vector((-2.6, 20, CLIP_L / 2)))
    callout("wedge", T((dx, 0, 0)) @ m_wedge @ Vector((45, 8, WEDGE_W / 2)))
    callout("panel", (x0 + 40, 60, RAIL_T + PANEL_T))
    render(name, (1500, 1000))

clear_guide()
show_only(ASSEMBLED + [PANEL])
bpy.data.collections["SolarMaps_Stand_Plates"].hide_viewport = True
with open(os.path.join(IMG_DIR, "anchors.json"), "w", encoding="utf-8") as fh:
    json.dump(ANCHORS, fh, ensure_ascii=False, indent=1)
print("rendered", sorted(os.listdir(IMG_DIR)))
