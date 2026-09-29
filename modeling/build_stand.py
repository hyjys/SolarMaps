r"""SolarMaps 태양광 패널(접이식 482 x 185) 가변 각도 거치대 생성 스크립트.

Blender 5.x 에서 실행한다 (MCP 또는 Text Editor 에서 Run Script). 새 씬 "SolarMaps_Stand" 에 만든다.
1 BU = 1 mm.

제약: Bambu Lab A1 (256 x 256), 학교 공용 → 출력 횟수 최소화, 외부 부품(볼트 등) 사용 불가.
    → 전 부품을 출력 2판에 담는다: modeling/solarmaps_stand_plate1_L.stl, _plate2_R.stl
      (프레임 반쪽 + 그 안쪽 빈 공간에 받침대·다리·연결키·스냅핀·클립·쐐기)
      부품별 STL 은 modeling/stand_parts/ (재출력용).

구성 (옆에서 본 모습, 왼쪽이 앞/남쪽):

              프레임(口자, 가장자리 턱으로만 받침 → 뒷면 USB 포트 자리 개방)
             /
            /  <- 다리 피벗 (힌지에서 프레임을 따라 LEG_A)
           / \
          /   \  다리 (LEG_B)
   힌지 -> o    \
   ======[받침대]==v==v==v==v==v==v====   <- 각도 노치 70..20°

프레임 좌표 (프레임 로컬): X = 패널 긴 변, Y = 짧은 변 (Y=0 이 아래 가장자리 = 힌지 쪽),
Z = 두께 (Z=0 이 뒷면, 패널은 Z=RAIL_T 턱 위에 놓임).

프레임은 가운데(X=FX/2)에서 L/R 두 쪽. 긴 레일 이음부 홈에 연결키를 뒤에서 끼우고
가로 스냅핀으로 고정한다. 회전축(힌지·다리 피벗)도 전부 스냅핀.
패널 두께는 5~15mm 범위(실측 불가)라서, 클립은 15mm 기준으로 넉넉히 두고
톱니 쐐기를 클립 아래로 밀어 넣어 조인다.
"""
import math
import os

import bmesh
import bpy
from mathutils import Matrix

OUT_DIR = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else \
    r"C:\Users\이민기\Desktop\개발\EURIF\SolarMaps\modeling"
PARTS_DIR = os.path.join(OUT_DIR, "stand_parts")

# ---- 패널 ----
PANEL_L, PANEL_W = 482.0, 185.0
PANEL_CLR = 1.5                       # 포켓 한쪽 여유 (천 가장자리 편차)
PX, PY = PANEL_L + 2 * PANEL_CLR, PANEL_W + 2 * PANEL_CLR   # 포켓 485 x 188
PANEL_T_RANGE = (5.0, 15.0)           # 대응 두께 범위 (실측 불가 → 쐐기로 조절)
PANEL_T_SHOW = 10.0                   # 표시용

# ---- 프레임 레일 단면 ----
RIM_W = 4.0                           # 바깥 테두리 벽 폭
LEDGE = 10.0                          # 패널을 받치는 턱 폭 (이 안쪽은 전부 뚫림)
RAIL_W = RIM_W + LEDGE                # 14
RAIL_T = 18.0                         # 레일 두께 (턱 윗면 높이)
RIM_H = 6.0                           # 턱 위 테두리 (옆 밀림 방지용)
FX, FY = PX + 2 * RIM_W, PY + 2 * RIM_W                      # 프레임 외곽 493 x 196
HALF = FX / 2                         # 반쪽 길이 246.5 (A1 256 베드)

AX_Z = RAIL_T / 2                     # 힌지·피벗 축 높이 (레일 두께 중앙)
KN_R = RAIL_T / 2                     # 힌지 너클 반지름
KN_Y = -11.0                          # 힌지 축 위치 (프레임 아래 가장자리에서 11mm 아래)

# ---- 스냅핀 ----
PIN_D, PIN_HOLE = 6.0, 6.4            # 힌지·다리 피벗
JPIN_D, JPIN_HOLE = 5.0, 5.4          # 프레임 이음
PIN_HEAD_T = 2.5
PIN_BARB = 3.5                        # 걸림턱 길이
PIN_BARB_EXTRA = 0.4                  # 걸림턱 반지름 증가분
PIN_SLOT_W = 1.8
PIN_FLAT = 0.6                        # 눕혀 출력하려고 깎는 밑면

# ---- 각도 조절 ----
LEG_A = 100.0                         # 힌지 축 ~ 다리 피벗 (프레임 따라)
LEG_B = 100.0                         # 다리 피벗 ~ 발끝 중심
ANGLES = (20, 30, 40, 50, 60, 70)     # 노치 각도 (도)
SHOW_ANGLE = 30                       # 씬 표시 각도
LEG_T = 8.0                           # 다리 두께 (X)
LEG_TOP_R = 7.5
FOOT_R = 5.0
FOOT_DZ = 2.0                         # 발끝 중심을 받침대 윗면보다 이만큼 낮춤 (노치 깊이)
GAP = 0.4                             # 회전 부품 사이 틈
CUT_CLR = 0.4                         # 노치 가공 여유

# ---- 받침대 ----
PLATE_T = 4.0
HZ = PLATE_T + 2.0 + KN_R             # 힌지 축 높이 (바닥 기준) = 랙 윗면
EAR_T = 6.0
EAR_R = 8.5
BASE_X = (-14.4, 22.4)
RACK_X = (-GAP - LEG_T - 4.0, 3.6)    # 다리 홈 양옆 3.6mm 벽
RACK_Y0 = 45.0
FIX_HOLE = 4.5                        # 끈·케이블타이 고정 구멍

# ---- 프레임 이음 (연결키) ----
KEY_L = 20.0                          # 반쪽마다 들어가는 길이
KEY_U = (3.5, 10.5)                   # 키 폭 (레일 바깥 가장자리 기준)
KEY_Z = 12.0
JOINT_CLR = 0.2

# ---- 패널 고정 클립 + 쐐기 ----
CLIP_L = 15.0
CLIP_T = 2.4
CLIP_CLR = 0.25
CLIP_GAP = PANEL_T_RANGE[1] + 2.0     # 턱 윗면 ~ 클립 윗날 아랫면
CLIP_REACH = 14.0                     # 레일 바깥 가장자리에서 윗날 끝까지
HOOK_H = 0.8
CLIP_X = (70.0, HALF - 70.0, HALF + 70.0, FX - 70.0)
WEDGE_L, WEDGE_W = 60.0, 8.0
WEDGE_TOOTH, WEDGE_PITCH = 0.8, 2.5
WEDGE_MAX = CLIP_GAP - PANEL_T_RANGE[0] - WEDGE_TOOTH       # 두꺼운 끝
WEDGE_MIN = CLIP_GAP - PANEL_T_RANGE[1] - WEDGE_TOOTH       # 얇은 끝

FONT_PATHS = [r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\segoeuib.ttf"]


# =====================================================================
# 씬 / 헬퍼
# =====================================================================
def get_scene(name):
    sc = bpy.data.scenes.get(name) or bpy.data.scenes.new(name)
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 0.001
    sc.unit_settings.length_unit = "MILLIMETERS"
    win = bpy.context.window or bpy.context.window_manager.windows[0]
    win.scene = sc
    return sc


SCENE = get_scene("SolarMaps_Stand")


def get_collection(name):
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
    if coll.name not in SCENE.collection.children:
        SCENE.collection.children.link(coll)
    for ob in list(coll.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    return coll


COLL = get_collection("SolarMaps_Stand")
REF = get_collection("SolarMaps_Stand_Ref")
PLATES = get_collection("SolarMaps_Stand_Plates")


def make_obj(name, bm, coll=None):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    (coll or COLL).objects.link(ob)
    return ob


def box(name, x0, x1, y0, y1, z0, z1, bevel=0.0, coll=None):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x = x1 if v.co.x > 0 else x0
        v.co.y = y1 if v.co.y > 0 else y0
        v.co.z = z1 if v.co.z > 0 else z0
    if bevel > 0:
        vert_edges = [e for e in bm.edges
                      if abs(e.verts[0].co.x - e.verts[1].co.x) < 1e-6
                      and abs(e.verts[0].co.y - e.verts[1].co.y) < 1e-6]
        bmesh.ops.bevel(bm, geom=vert_edges, offset=bevel, segments=8,
                        profile=0.5, affect="EDGES")
    return make_obj(name, bm, coll)


def circle(cx, cy, r, n=64):
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n))
            for i in range(n)]


def hull(pts):
    """2D 볼록 껍질 (반시계)."""
    pts = sorted(set((round(x, 6), round(y, 6)) for x, y in pts))

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def teardrop(c0, c1, d):
    """출력 시 수평이 되는 구멍용 물방울 단면 (꼭짓점이 두 번째 좌표 + 방향 = 출력 위쪽)."""
    r = d / 2
    return hull(circle(c0, c1, r, 48) + [(c0, c1 + r * math.sqrt(2))])


def prism(name, pts, axis, lo, hi, coll=None):
    """2D 다각형을 축 방향으로 돌출. axis 'Z': pts=(x,y) / 'X': pts=(y,z) / 'Y': pts=(x,z)."""
    def to3(p, t):
        if axis == "Z":
            return (p[0], p[1], t)
        if axis == "X":
            return (t, p[0], p[1])
        return (p[0], t, p[1])

    bm = bmesh.new()
    lo_v = [bm.verts.new(to3(p, lo)) for p in pts]
    hi_v = [bm.verts.new(to3(p, hi)) for p in pts]
    bm.faces.new(list(reversed(lo_v)))
    bm.faces.new(hi_v)
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((lo_v[i], lo_v[j], hi_v[j], hi_v[i]))
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return make_obj(name, bm, coll)


def cone_x(name, x0, x1, r0, r1):
    """X 축 방향 원뿔대 (x0 에서 r0, x1 에서 r1)."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=48, radius1=r0, radius2=r1, depth=x1 - x0,
                          matrix=Matrix.Translation(((x0 + x1) / 2, 0, 0)) @
                          Matrix.Rotation(math.pi / 2, 4, "Y"))
    return make_obj(name, bm)


def boolean(target, cutter, op):
    mod = target.modifiers.new("bool", "BOOLEAN")
    mod.operation = op
    mod.solver = "EXACT"
    mod.object = cutter
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(target.evaluated_get(dg))
    target.modifiers.clear()
    old = target.data
    target.data = me
    bpy.data.meshes.remove(old)
    cut_me = cutter.data
    bpy.data.objects.remove(cutter, do_unlink=True)
    bpy.data.meshes.remove(cut_me)


def load_font():
    for p in FONT_PATHS:
        if os.path.exists(p):
            return bpy.data.fonts.load(p, check_existing=True)
    return None


FONT = load_font()


def text(name, body, size, cx, cy, z0, depth, rot_deg=0.0):
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = body
    cu.size = size
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    cu.extrude = depth / 2.0
    if FONT:
        cu.font = FONT
    tmp = bpy.data.objects.new(name + "_crv", cu)
    COLL.objects.link(tmp)
    tmp.location = (cx, cy, z0 + depth / 2.0)
    tmp.rotation_euler = (0, 0, math.radians(rot_deg))
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
    me.transform(tmp.matrix_world)
    bpy.data.objects.remove(tmp, do_unlink=True)
    bpy.data.curves.remove(cu)
    bm = bmesh.new()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    return make_obj(name, bm)


M_MIRROR = Matrix.Translation((FX, 0, 0)) @ Matrix.Scale(-1, 4, (1, 0, 0))   # X = FX/2 평면 대칭


def mirrored_copy(src, name):
    me = src.data.copy()
    me.name = name
    me.transform(M_MIRROR)
    me.flip_normals()
    ob = bpy.data.objects.new(name, me)
    COLL.objects.link(ob)
    return ob


def mat_cols(cx, cy, cz, t):
    """열벡터(로컬 x,y,z 축의 월드 방향)와 이동으로 4x4 행렬."""
    return Matrix(((cx[0], cy[0], cz[0], t[0]),
                   (cx[1], cy[1], cz[1], t[1]),
                   (cx[2], cy[2], cz[2], t[2]),
                   (0, 0, 0, 1)))


def foot_d(deg):
    """각도 deg 에서 힌지 축 ~ 발끝 중심 수평 거리."""
    th = math.radians(deg)
    return LEG_A * math.cos(th) + math.sqrt(LEG_B ** 2 - (LEG_A * math.sin(th) + FOOT_DZ) ** 2)


def rail_u(u, top):
    """레일 바깥 가장자리 기준 거리 u 를 프레임 Y 로 (top: 위쪽 긴 레일)."""
    return FY - u if top else u


# =====================================================================
# 프레임 반쪽 L (ㄷ자) — 출력 방향 그대로 (뒷면 Z=0 이 베드)
# =====================================================================
half_l = box("Stand_FrameHalf_L", 0.0, HALF, 0.0, FY, 0.0, RAIL_T)
boolean(half_l, box("open", RAIL_W, HALF + 1, RAIL_W, FY - RAIL_W, -1, RAIL_T + 1), "DIFFERENCE")
rim = box("rim", 0.0, HALF, 0.0, FY, RAIL_T - 0.01, RAIL_T + RIM_H)
boolean(rim, box("rim_in", RIM_W, HALF + 1, RIM_W, FY - RIM_W, RAIL_T - 1, RAIL_T + RIM_H + 1),
        "DIFFERENCE")
boolean(half_l, rim, "UNION")

# 힌지 너클 (짧은 레일 아래로 돌출) + 축 구멍, 다리 피벗 구멍
knuckle = hull(circle(KN_Y, AX_Z, KN_R) + [(0.5, 0.0), (0.5, RAIL_T)])
boolean(half_l, prism("knuckle", knuckle, "X", 0.0, RAIL_W), "UNION")
for y in (KN_Y, KN_Y + LEG_A):
    boolean(half_l, prism("hole", teardrop(y, AX_Z, PIN_HOLE), "X", -1, RAIL_W + 1), "DIFFERENCE")

# 연결키 홈 (뒷면·끝면으로 열림) + 가로 핀 구멍
for top in (False, True):
    ya, yb = sorted((rail_u(KEY_U[0] - JOINT_CLR, top), rail_u(KEY_U[1] + JOINT_CLR, top)))
    boolean(half_l, box("mortise", HALF - KEY_L - JOINT_CLR, HALF + 1, ya, yb,
                        -1, KEY_Z + JOINT_CLR), "DIFFERENCE")
    y0, y1 = sorted((rail_u(-1, top), rail_u(RAIL_W + 1, top)))
    boolean(half_l, prism("jpin", teardrop(HALF - KEY_L / 2, KEY_Z / 2, JPIN_HOLE), "Y", y0, y1),
            "DIFFERENCE")

half_r = mirrored_copy(half_l, "Stand_FrameHalf_R")

# =====================================================================
# 연결키 — 로컬: x = 레일 방향 (±KEY_L), y = 폭, z = 높이
# =====================================================================
key = box("Stand_Key", -KEY_L, KEY_L, 0.0, KEY_U[1] - KEY_U[0], 0.0, KEY_Z)
for x in (-KEY_L / 2, KEY_L / 2):
    boolean(key, prism("khole", teardrop(x, KEY_Z / 2, JPIN_HOLE), "Y", -1, KEY_U[1] - KEY_U[0] + 1),
            "DIFFERENCE")

# =====================================================================
# 다리 — 로컬: 피벗이 원점, 발끝이 +X, 두께 Z (그대로 눕혀 출력)
# =====================================================================
leg = prism("Stand_Leg", hull(circle(0, 0, LEG_TOP_R) + circle(LEG_B, 0, FOOT_R)), "Z", 0.0, LEG_T)
boolean(leg, prism("leg_hole", circle(0, 0, PIN_HOLE / 2, 48), "Z", -1, LEG_T + 1), "DIFFERENCE")

# =====================================================================
# 받침대 L — 월드 좌표 그대로 (바닥판이 베드). 힌지 축 = (Y=0, Z=HZ)
# =====================================================================
FOOTS = {deg: foot_d(deg) for deg in ANGLES}
Y_MAX = max(FOOTS.values()) + FOOT_R + 10.0
base_l = box("Stand_Base_L", BASE_X[0], BASE_X[1], -12.0, Y_MAX, 0.0, PLATE_T, bevel=3.0)
ear = hull(circle(0.0, HZ, EAR_R) + [(-11.0, 0.5), (11.0, 0.5)])
for x0, x1 in ((-GAP - EAR_T, -GAP), (RAIL_W + GAP, RAIL_W + GAP + EAR_T)):
    boolean(base_l, prism("ear", ear, "X", x0, x1), "UNION")
boolean(base_l, prism("hinge_hole", teardrop(0.0, HZ, PIN_HOLE), "X",
                      BASE_X[0] - 1, BASE_X[1] + 1), "DIFFERENCE")
boolean(base_l, box("rack", RACK_X[0], RACK_X[1], RACK_Y0, Y_MAX - 3.0, 0.5, HZ), "UNION")

# 각 각도에서의 다리 모양 그대로 파내면 노치 + 진입 경사가 동시에 생긴다
for deg, d in FOOTS.items():
    th = math.radians(deg)
    p = (LEG_A * math.cos(th), HZ + LEG_A * math.sin(th))
    shape = hull(circle(*p, LEG_TOP_R + CUT_CLR) + circle(d, HZ - FOOT_DZ, FOOT_R + CUT_CLR))
    boolean(base_l, prism("notch", shape, "X", -GAP - LEG_T - CUT_CLR, -GAP + CUT_CLR), "DIFFERENCE")

for y in (30.0, Y_MAX - 15.0):
    boolean(base_l, prism("fix", circle(17.5, y, FIX_HOLE / 2, 32), "Z", -1, PLATE_T + 1), "DIFFERENCE")

base_r = mirrored_copy(base_l, "Stand_Base_R")
for ob, lx in ((base_l, 9.0), (base_r, FX - 9.0)):
    for deg, d in FOOTS.items():
        boolean(ob, text("lbl", f"{deg}°", 5.0, lx, d, PLATE_T - 0.6, 1.6, 90.0), "DIFFERENCE")


# =====================================================================
# 스냅핀 — 로컬: 축 = X (머리 x<0, 걸림턱 x>grip), 축 중심이 원점, 밑면 평평
# 갈라진 틈이 세로라서 눕혀 출력하면 두 갈래가 수평으로 휜다 (적층 방향과 무관)
# =====================================================================
def snap_pin(name, d, grip):
    r = d / 2
    tip = grip + PIN_BARB
    ob = prism(name, circle(0, 0, r, 48), "X", -0.01, tip - 1.0)
    boolean(ob, prism("head", circle(0, 0, r + 2.5, 48), "X", -PIN_HEAD_T, 0.0), "UNION")
    boolean(ob, cone_x("barb", grip + 0.2, tip, r + PIN_BARB_EXTRA, r - 0.6), "UNION")
    boolean(ob, box("slot", tip - PIN_BARB - 5.0, tip + 1, -PIN_SLOT_W / 2, PIN_SLOT_W / 2,
                    -d, d), "DIFFERENCE")
    boolean(ob, box("flat", -PIN_HEAD_T - 1, tip + 1, -d - 3, d + 3, -d - 3, -(r - PIN_FLAT)),
            "DIFFERENCE")
    return ob


PIN_Z0 = PIN_D / 2 - PIN_FLAT         # 출력 시 들어올릴 높이
JPIN_Z0 = JPIN_D / 2 - PIN_FLAT
pin_hinge = snap_pin("Stand_Pin_Hinge", PIN_D, EAR_T + GAP + RAIL_W + GAP + EAR_T + 0.2)
pin_leg = snap_pin("Stand_Pin_Leg", PIN_D, LEG_T + GAP + RAIL_W + 0.2)
pin_joint = snap_pin("Stand_Pin_Joint", JPIN_D, RAIL_W + 0.2)

# =====================================================================
# 클립 — 로컬: x = 레일 바깥 가장자리 기준 u, y = 레일 두께 방향, z = 레일 길이 방향
# 윗날 아래 가운데 걸쇠가 쐐기 톱니에 걸려 풀리지 않는다
# =====================================================================
c, t = CLIP_CLR, CLIP_T
zt0 = RAIL_T + CLIP_GAP + c
hx = RAIL_W + c
clip_pts = [
    (-c - t, -c - t), (hx + 2.2, -c - t), (hx + 2.2, -c), (hx + 1.6, -c),
    (hx + 1.6 - HOOK_H - c, HOOK_H), (hx, HOOK_H), (hx, -c), (-c, -c),
    (-c, zt0), (CLIP_REACH, zt0), (CLIP_REACH, zt0 + t - 0.8), (CLIP_REACH - 0.8, zt0 + t),
    (-c - t, zt0 + t),
]
clip = prism("Stand_Clip", clip_pts, "Z", 0.0, CLIP_L)
pawl = [(zt0 + 0.01, CLIP_L / 2 - 0.9), (zt0 - WEDGE_TOOTH, CLIP_L / 2), (zt0 + 0.01, CLIP_L / 2 + 0.9)]
boolean(clip, prism("pawl", pawl, "X", RIM_W + PANEL_CLR, CLIP_REACH - 0.3), "UNION")


# =====================================================================
# 쐐기 — 로컬: x = 길이 (얇은 끝 0), y = 두께, z = 폭 (옆으로 눕혀 출력)
# 얇은 끝부터 클립 아래로 밀어 넣는다. 톱니는 밀어 넣는 방향으로만 넘어간다.
# =====================================================================
def wedge_h(s):
    return WEDGE_MIN + (WEDGE_MAX - WEDGE_MIN) * s / WEDGE_L


n_teeth = int(WEDGE_L / WEDGE_PITCH)
top = [(0.0, wedge_h(0.0))]
for i in range(n_teeth):
    s1 = (i + 1) * WEDGE_PITCH
    top += [(s1, wedge_h(s1) + WEDGE_TOOTH), (s1, wedge_h(s1))]
wedge = prism("Stand_Wedge", [(0.0, 0.0), (WEDGE_L, 0.0)] + list(reversed(top)), "Z", 0.0, WEDGE_W)


# =====================================================================
# 재질
# =====================================================================
def viewport_mat(name, rgba):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.diffuse_color = rgba
    return mat


COLORS = {"FrameHalf": (0.15, 0.35, 0.55, 1), "Key": (0.9, 0.3, 0.3, 1),
          "Leg": (0.9, 0.55, 0.15, 1), "Base": (0.35, 0.35, 0.38, 1),
          "Pin": (0.85, 0.2, 0.6, 1), "Clip": (0.9, 0.75, 0.2, 1), "Wedge": (0.3, 0.75, 0.35, 1)}
PARTS = (half_l, half_r, key, leg, base_l, base_r, pin_hinge, pin_leg, pin_joint, clip, wedge)
for ob in PARTS:
    kind = ob.name.split("_")[1]
    ob.data.materials.clear()
    ob.data.materials.append(viewport_mat("Stand_" + kind, COLORS[kind]))

# =====================================================================
# 출력판 2장 — 프레임 반쪽 안쪽 빈 공간(X 17~243, Y 17~179)에 나머지 부품 배치
# 판 2 는 판 1 의 거울상 (작은 부품은 모두 대칭이라 거울상 = 같은 부품)
# =====================================================================
Rz = Matrix.Rotation
T = Matrix.Translation
LAYOUT_L = [
    (half_l, Matrix()),
    (base_l, T((22 + 12, 20 - BASE_X[0] + 8, 0)) @ Rz(-math.pi / 2, 4, "Z")),
    (leg, T((22 + LEG_TOP_R, 70, 0))),
    (key, T((170, 66, 0))),
    (pin_hinge, T((25 + PIN_HEAD_T, 90, PIN_Z0))),
    (pin_leg, T((65 + PIN_HEAD_T, 90, PIN_Z0))),
] + [(pin_joint, T((100 + i * 25 + PIN_HEAD_T, 90, JPIN_Z0))) for i in range(3)] \
  + [(clip, T((25 + i * 23 + c + t, 105 + c + t, 0))) for i in range(4)] \
  + [(wedge, T((125, 102 + i * 16, 0))) for i in range(4)]

P = Matrix.Scale(-1, 4, (1, 0, 0))
LAYOUT_R = [(half_r, P @ M_MIRROR), (base_r, P @ LAYOUT_L[1][1] @ M_MIRROR)] + \
    [(ob, P @ m) for ob, m in LAYOUT_L[2:]]


def build_plate(name, layout):
    bm = bmesh.new()
    for ob, m in layout:
        tmp = bmesh.new()
        tmp.from_mesh(ob.data)
        bmesh.ops.transform(tmp, matrix=m, verts=tmp.verts)
        if m.determinant() < 0:
            bmesh.ops.reverse_faces(tmp, faces=tmp.faces)
        me = bpy.data.meshes.new("tmp")
        tmp.to_mesh(me)
        tmp.free()
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    xs = [v.co.x for v in bm.verts]
    ys = [v.co.y for v in bm.verts]
    zs = [v.co.z for v in bm.verts]
    bmesh.ops.translate(bm, verts=bm.verts, vec=(-min(xs), -min(ys), -min(zs)))
    return make_obj(name, bm, PLATES)


plate1 = build_plate("Plate1_L", LAYOUT_L)
plate2 = build_plate("Plate2_R", LAYOUT_R)
for pl in (plate1, plate2):
    pl.data.materials.append(viewport_mat("Stand_Plate", (0.6, 0.6, 0.65, 1)))


def export_stl(ob, path):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.wm.stl_export(filepath=path, export_selected_objects=True,
                          apply_modifiers=True, global_scale=1.0, use_scene_unit=False)


os.makedirs(PARTS_DIR, exist_ok=True)
bpy.context.view_layer.update()
SIZES = {}
for ob, fname in ((plate1, "solarmaps_stand_plate1_L.stl"), (plate2, "solarmaps_stand_plate2_R.stl")):
    export_stl(ob, os.path.join(OUT_DIR, fname))
    SIZES[fname] = tuple(round(v, 1) for v in ob.dimensions)
for ob in PARTS:
    export_stl(ob, os.path.join(PARTS_DIR, ob.name.lower() + ".stl"))
PLATES.hide_viewport = True

# =====================================================================
# 조립 상태로 배치 (SHOW_ANGLE)
# =====================================================================
TH = math.radians(SHOW_ANGLE)
M_FRAME = T((0, 0, HZ)) @ Rz(TH, 4, "X") @ T((0, -KN_Y, -AX_Z))


def place(ob, m, name=None):
    if name:
        ob = bpy.data.objects.new(name, ob.data)
        COLL.objects.link(ob)
    ob.matrix_world = m
    return ob


place(half_l, M_FRAME)
place(half_r, M_FRAME)
place(key, M_FRAME @ T((HALF, KEY_U[0], 0)))
place(key, M_FRAME @ T((HALF, FY - KEY_U[1], 0)), "Stand_Key_top")

p = (LEG_A * math.cos(TH), HZ + LEG_A * math.sin(TH))
f = (FOOTS[SHOW_ANGLE], HZ - FOOT_DZ)
L = math.hypot(f[0] - p[0], f[1] - p[1])
uy, uz = (f[0] - p[0]) / L, (f[1] - p[1]) / L
place(leg, mat_cols((0, uy, uz), (0, -uz, uy), (1, 0, 0), (-GAP - LEG_T, p[0], p[1])))
place(leg, mat_cols((0, uy, uz), (0, -uz, uy), (1, 0, 0), (FX + GAP, p[0], p[1])), "Stand_Leg_R")

# 핀: 머리가 바깥쪽
place(pin_hinge, T((-GAP - EAR_T, 0, HZ)))
place(pin_hinge, T((FX + GAP + EAR_T, 0, HZ)) @ Rz(math.pi, 4, "Z"), "Stand_Pin_Hinge_R")
place(pin_leg, M_FRAME @ T((-GAP - LEG_T, KN_Y + LEG_A, AX_Z)))
place(pin_leg, M_FRAME @ T((FX + GAP + LEG_T, KN_Y + LEG_A, AX_Z)) @ Rz(math.pi, 4, "Z"),
      "Stand_Pin_Leg_R")
for i, x in enumerate((HALF - KEY_L / 2, HALF + KEY_L / 2)):
    place(pin_joint, M_FRAME @ T((x, 0, KEY_Z / 2)) @ Rz(math.pi / 2, 4, "Z"),
          f"Stand_Pin_Joint_b{i}")
    place(pin_joint, M_FRAME @ T((x, FY, KEY_Z / 2)) @ Rz(-math.pi / 2, 4, "Z"),
          f"Stand_Pin_Joint_t{i}")
pin_joint.hide_viewport = True               # 원본(출력 방향)은 숨김

# 클립 + 쐐기 (표시 두께 PANEL_T_SHOW 에 맞춘 위치)
s_mid = (CLIP_GAP - PANEL_T_SHOW - WEDGE_TOOTH - WEDGE_MIN) / (WEDGE_MAX - WEDGE_MIN) * WEDGE_L
wz = RAIL_T + PANEL_T_SHOW
for i, x0 in enumerate(CLIP_X):
    place(clip, M_FRAME @ mat_cols((0, 1, 0), (0, 0, 1), (1, 0, 0), (x0 - CLIP_L / 2, 0, 0)),
          f"Stand_Clip_b{i}")
    place(clip, M_FRAME @ mat_cols((0, -1, 0), (0, 0, 1), (-1, 0, 0), (x0 + CLIP_L / 2, FY, 0)),
          f"Stand_Clip_t{i}")
    place(wedge, M_FRAME @ mat_cols((1, 0, 0), (0, 0, 1), (0, -1, 0),
                                    (x0 - s_mid, RIM_W + PANEL_CLR + WEDGE_W, wz)), f"Stand_Wedge_b{i}")
    place(wedge, M_FRAME @ mat_cols((-1, 0, 0), (0, 0, 1), (0, 1, 0),
                                    (x0 + s_mid, FY - RIM_W - PANEL_CLR - WEDGE_W, wz)),
          f"Stand_Wedge_t{i}")
for ob in (clip, wedge):
    ob.hide_viewport = True

# 참고용 패널 (출력 안 함)
panel = box("REF_Panel_482x185", RIM_W + PANEL_CLR, FX - RIM_W - PANEL_CLR,
            RIM_W + PANEL_CLR, FY - RIM_W - PANEL_CLR, RAIL_T, RAIL_T + PANEL_T_SHOW, coll=REF)
panel.matrix_world = M_FRAME
panel.data.materials.append(viewport_mat("Stand_RefPanel", (0.1, 0.15, 0.45, 0.6)))

print("PLATE_SIZES", SIZES)
print("FOOT_D", {k: round(v, 1) for k, v in FOOTS.items()})
print("WEDGE", round(WEDGE_MIN, 2), round(WEDGE_MAX, 2))
