"""거치대 조립 가이드 PDF (A4 인쇄용) 생성.

필요: pip install reportlab pillow
순서: Blender 에서 build_stand.py → stand_guide/render_views.py 실행 후 이 스크립트 실행.
결과: modeling/solarmaps_stand_assembly_guide.pdf
"""
import math
import os
import sys

from reportlab.lib.colors import black, white
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

HERE = os.path.dirname(os.path.abspath(__file__))
MODELING = os.path.dirname(HERE)
sys.path.insert(0, MODELING)
from guide_pdf import (ACCENT, GREY, MARGIN, PH, PW, blender_constants, bullets,  # noqa: E402
                       draw_image, header, note_box, paragraph, setup, table)

OUT = os.environ.get("GUIDE_OUT") or os.path.join(MODELING, "solarmaps_stand_assembly_guide.pdf")
C = blender_constants(os.path.join(MODELING, "build_stand.py"))
setup(os.path.join(HERE, "_img"), "SolarMaps 태양광 패널 거치대 · 조립 가이드")
A4 = (PW, PH)


# ---------------------------------------------------------------------
# 치수 계산 (본문에 쓰는 값)
# ---------------------------------------------------------------------
def foot_d(deg):
    th = math.radians(deg)
    return C["LEG_A"] * math.cos(th) + math.sqrt(
        C["LEG_B"] ** 2 - (C["LEG_A"] * math.sin(th) + C["FOOT_DZ"]) ** 2)


def pin_len(grip):
    return C["PIN_HEAD_T"] + grip + C["PIN_BARB"]


HINGE_LEN = pin_len(C["EAR_T"] + C["GAP"] + C["RAIL_W"] + C["GAP"] + C["EAR_T"] + 0.2)
LEG_PIN_LEN = pin_len(C["LEG_T"] + C["GAP"] + C["RAIL_W"] + 0.2)
JOINT_LEN = pin_len(C["RAIL_W"] + 0.2)


# =====================================================================
# 페이지
# =====================================================================
c = canvas.Canvas(OUT, pagesize=A4)
c.setTitle("SolarMaps 태양광 패널 거치대 조립 가이드")
c.setAuthor("HAFS EURIF SolarMaps")
TW = PW - 2 * MARGIN
page = 1

# ---- 1. 표지 + 부품 목록 ----
c.setFillColor(ACCENT)
c.rect(0, PH - 48 * mm, PW, 48 * mm, stroke=0, fill=1)
c.setFillColor(white)
c.setFont("KRB", 24)
c.drawString(MARGIN, PH - 24 * mm, "태양광 패널 거치대 조립 가이드")
c.setFont("KR", 11.5)
c.drawString(MARGIN, PH - 33 * mm, "HAFS EURIF · SolarMaps 노드용 접이식 패널 (482 × 185 mm)")
c.drawString(MARGIN, PH - 40 * mm, "각도 20° ~ 70° (10° 간격) · 출력 2판 · 볼트 없이 프린트 핀으로 조립")

draw_image(c, "01_overview_front", MARGIN, PH - 150 * mm, w=TW, h=96 * mm, callouts=(
    ("frame", "프레임 (L/R 반쪽)", -40, 42),
    ("clip", "클립", -52, -20),
    ("wedge", "쐐기", 30, 38),
    ("leg", "다리", 58, 18),
    ("base", "받침대", 50, -24),
))

y = PH - 158 * mm
c.setFont("KRB", 13)
c.setFillColor(ACCENT)
c.drawString(MARGIN, y, "부품 목록")
y -= 6
rows = [
    ["프레임 반쪽 L / R", "각 1", "파랑", "口자 프레임. 가운데에서 연결"],
    ["받침대 L / R", "각 1", "회색", "힌지 + 각도 노치 (각도 숫자 음각)"],
    ["다리", "2", "주황", "프레임과 받침대 노치 사이 버팀"],
    ["연결키", "2", "빨강", "프레임 두 반쪽을 잇는 블록"],
    [f"힌지 핀 (Ø6, 약 {HINGE_LEN:.0f}mm)", "2", "분홍", "가장 긴 핀. 프레임 ↔ 받침대"],
    [f"다리 핀 (Ø6, 약 {LEG_PIN_LEN:.0f}mm)", "2", "분홍", "중간 길이. 다리 ↔ 프레임"],
    [f"이음 핀 (Ø5, 약 {JOINT_LEN:.0f}mm)", "6", "분홍", "가장 짧은 핀. 4개 사용 + 예비 2"],
    ["클립", "8", "노랑", "패널 가장자리를 누름 (긴 변마다 4)"],
    ["쐐기", "8", "초록", "클립 아래로 밀어 넣어 두께 맞춤"],
]
y = table(c, MARGIN, y, [("부품", 62 * mm), ("수량", 16 * mm), ("그림 색", 20 * mm), ("역할", TW - 98 * mm)],
          rows, size=9)
y -= 8
paragraph(c, "※ 모든 부품이 출력판 2장(plate1_L, plate2_R)에 들어 있습니다. 필요한 도구는 없습니다. "
             "핀을 뺄 때만 롱노즈 펜치가 있으면 편합니다. 그림 색은 구분용이며 실제 필라멘트 색과는 관계없습니다.",
          MARGIN, y, TW, size=9, color=GREY)
c.setFillColor(GREY)
c.setFont("KR", 8)
c.drawCentredString(PW / 2, 9 * mm, f"- {page} -")
c.showPage()
page += 1

# ---- 2. 출력 ----
header(c, "0", "출력 (Bambu Lab A1, 2판)", page)
y = PH - 30 * mm
_, h = draw_image(c, "03_plates", MARGIN, y - 80 * mm, w=TW, h=80 * mm)
c.setFont("KRB", 10)
c.setFillColor(black)
c.drawCentredString(MARGIN + TW * 0.25, y - 84 * mm, "판 1 — solarmaps_stand_plate1_L.stl")
c.drawCentredString(MARGIN + TW * 0.75, y - 84 * mm, "판 2 — solarmaps_stand_plate2_R.stl")
y -= 94 * mm
y = bullets(c, [
    "① 두 STL 을 각각 한 판씩 출력합니다 (판 크기 246.5 × 216 mm, 높이 24 mm). "
    "받침대·다리·핀·클립·쐐기가 프레임 반쪽 안쪽 빈 공간에 미리 배치되어 있습니다.",
    "② 슬라이서에서 '자동 정렬(Arrange)'을 누르지 마세요. 그대로 판 가운데에 두면 됩니다. "
    "한 덩어리로 읽히는 것이 정상입니다.",
    "③ 서포트는 필요 없습니다. 가로 구멍은 물방울 모양이라 서포트 없이 뽑히고, 핀은 밑면이 평평하게 깎여 있습니다.",
    "④ 권장 설정: PLA, 0.4 노즐, 레이어 0.2 mm, 벽 4줄, 내부 채움 25% 이상. "
    "핀 강도는 벽 줄 수에 가장 크게 좌우됩니다.",
    "⑤ 출력 후 작은 부품을 떼어 내고 핀 끝 두 갈래 사이의 실(스트링)을 정리하세요.",
], MARGIN, y, TW)
y -= 6
note_box(c, MARGIN, y, TW, "핀 사용법 (모든 단계 공통)", [
    "핀은 머리 반대쪽 끝이 두 갈래로 갈라져 있고, 끝에 걸림턱이 있습니다.",
    "머리가 바깥쪽에 오도록 구멍에 대고 '딸깍' 소리가 날 때까지 끝까지 밀어 넣습니다.",
    "뺄 때: 반대편으로 튀어나온 두 갈래를 손가락이나 롱노즈로 모아 쥔 채 머리 쪽으로 밀어냅니다.",
    "구멍이 빡빡하면 구멍 안의 거스러미를 먼저 정리하세요. 힘으로 억지로 넣으면 갈래가 부러질 수 있습니다 (예비 이음 핀 2개 포함).",
])
c.showPage()
page += 1

# ---- 3. 1단계: 프레임 연결 ----
header(c, "1", "프레임 두 반쪽 연결", page)
y = PH - 30 * mm
draw_image(c, "04_joint", MARGIN, y - 120 * mm, w=TW, h=120 * mm, callouts=(
    ("key", "① 연결키", 60, 30),
    ("slot", "연결키 홈", -70, 25),
    ("jpin", "② 이음 핀 (가장 짧은 핀)", 90, -20),
    ("half_l", "반쪽 L", -30, -35),
    ("half_r", "반쪽 R", 20, 40),
))
y -= 128 * mm
y = bullets(c, [
    "① 프레임 반쪽 L 과 R 을 뒷면(평평하고 홈이 파인 면)이 위로 오게 뒤집어 가운데 끝면끼리 맞댑니다.",
    "② 아래 레일과 위 레일의 이음부 홈에 연결키를 하나씩 눌러 끼웁니다. "
    "연결키 구멍의 뾰족한 쪽이 레일 구멍의 뾰족한 쪽과 같은 방향(아래 = 패널 쪽)을 향해야 구멍이 맞습니다.",
    "③ 레일 바깥쪽에서 이음 핀을 넣습니다. 레일 → 연결키 → 레일을 지나 프레임 안쪽으로 걸림턱이 나오면 됩니다. "
    "레일 하나에 2개씩, 모두 4개입니다.",
    "④ 프레임을 다시 뒤집어 이음부가 평평하게 맞는지 확인합니다.",
], MARGIN, y, TW)
c.showPage()
page += 1

# ---- 4. 2~3단계: 받침대, 다리 ----
header(c, "2", "받침대 연결  ·  3  다리 연결", page)
y = PH - 30 * mm
half = (TW - 6 * mm) / 2
c.setFont("KRB", 12)
c.setFillColor(ACCENT)
c.drawString(MARGIN, y - 4, "2단계 — 받침대 (힌지)")
draw_image(c, "05_hinge", MARGIN, y - 100 * mm, w=TW, h=90 * mm, callouts=(
    ("hpin", "힌지 핀 (가장 긴 핀)", -95, 12),
    ("knuckle", "프레임 너클", 45, 45),
    ("ear", "받침대 귀", 70, -30),
))
y -= 104 * mm
y = bullets(c, [
    "① 프레임 짧은 변 아래쪽의 둥근 돌기(너클)를 받침대 앞쪽 두 귀 사이에 넣습니다. "
    "받침대 L 은 L 쪽, R 은 R 쪽입니다. 노치 줄이 프레임 바깥쪽에 오면 맞게 놓인 것입니다.",
    "② 바깥 귀 쪽에서 힌지 핀을 귀 → 너클 → 귀 순서로 밀어 넣습니다. 반대쪽도 같습니다.",
], MARGIN, y, TW, size=9.5)
y -= 10
c.setFont("KRB", 12)
c.setFillColor(ACCENT)
c.drawString(MARGIN, y - 4, "3단계 — 다리")
draw_image(c, "06_leg", MARGIN, y - 92 * mm, w=TW, h=84 * mm, callouts=(
    ("lpin", "다리 핀 (중간 길이)", -40, 30),
    ("leg", "다리", -40, -30),
    ("lhole", "피벗 구멍", 55, 25),
    ("notch", "각도 노치", 60, -25),
))
y -= 96 * mm
bullets(c, [
    "① 다리의 큰 구멍 쪽을 프레임 짧은 변 바깥면의 피벗 구멍에 맞춥니다. 다리는 프레임 바깥쪽(받침대 노치 줄 위)에 옵니다.",
    "② 다리 바깥에서 다리 핀을 다리 → 레일 순서로 넣습니다. 걸림턱은 프레임 안쪽으로 나옵니다. 반대쪽도 같습니다.",
], MARGIN, y, TW, size=9.5)
c.showPage()
page += 1

# ---- 5. 4단계: 각도 ----
header(c, "4", "각도 맞추기", page)
y = PH - 30 * mm
w3 = (TW - 8 * mm) / 3
for i, deg in enumerate((20, 40, 70)):
    x = MARGIN + i * (w3 + 4 * mm)
    draw_image(c, f"07_angle_{deg}", x, y - 62 * mm, w=w3, h=58 * mm)
    c.setFont("KRB", 13)
    c.setFillColor(black)
    c.drawCentredString(x + w3 / 2, y - 68 * mm, f"{deg}°")
y -= 78 * mm
y = bullets(c, [
    "① 프레임 윗부분을 잡고 조금 들어 올린 뒤, 다리 발끝을 원하는 각도의 노치에 내려놓습니다.",
    "② 노치 옆 받침대 윗면에 각도 숫자가 새겨져 있습니다. 힌지 쪽(앞)에서 뒤로 갈수록 각도가 낮아집니다.",
    "③ 양쪽 다리를 반드시 같은 숫자에 놓으세요. 다르면 프레임이 비틀립니다.",
    "④ 발끝이 노치 바닥까지 내려앉았는지 확인합니다. 노치 뒤쪽 벽이 다리를 받쳐 줍니다.",
], MARGIN, y, TW)
y -= 6
c.setFont("KRB", 11)
c.setFillColor(ACCENT)
c.drawString(MARGIN, y - 4, "노치 위치 (힌지 축에서 발끝 중심까지)")
y -= 10
rows = [[f"{deg}°", f"{foot_d(deg):.0f} mm", tip] for deg, tip in (
    (70, "겨울철 해가 낮을 때"), (60, ""), (50, ""), (40, ""),
    (30, "연평균 발전량 권장 (서울 위도 37.5°)"), (20, "여름철"))]
y = table(c, MARGIN, y, [("각도", 25 * mm), ("거리", 30 * mm), ("참고", TW - 55 * mm)], rows, size=9.5)
y -= 8
paragraph(c, "※ 우리나라 고정 설치 최적 경사는 보통 30~35° 입니다. 계절마다 바꿀 수 있다면 여름 20°, 봄·가을 40°, 겨울 60~70° 가 유리합니다. "
             "패널 정면이 남쪽을 향하게 두세요.", MARGIN, y, TW, size=9, color=GREY)
c.showPage()
page += 1

# ---- 6. 5단계: 패널 + 클립 ----
header(c, "5", "패널 올리고 클립·쐐기로 고정", page)
y = PH - 28 * mm
w2 = (TW - 6 * mm) / 2
CLIP_SHOTS = (
    ("08_clip_step1", "① 클립을 바깥에서 끼우기",
     (("clip", "클립", 55, -30), ("wedge", "쐐기", 30, 35), ("panel", "패널", -40, 30))),
    ("09_clip_step2", "② 쐐기를 얇은 쪽부터 밀어 넣기",
     (("wedge", "← 이 방향으로 밀기", 0, 35), ("clip", "클립", 55, -30))),
    ("10_clip_done", "③ 더 안 들어갈 때까지 밀면 완료",
     (("wedge", "쐐기", 45, 35), ("clip", "클립", 55, -30))),
)
for i, (name, cap, co) in enumerate(CLIP_SHOTS):
    x = MARGIN + (i % 2) * (w2 + 6 * mm)
    top = y - (i // 2) * 76 * mm
    draw_image(c, name, x, top - 66 * mm, w=w2, h=64 * mm, callouts=co)
    c.setFont("KRB", 10.5)
    c.setFillColor(black)
    c.drawCentredString(x + w2 / 2, top - 72 * mm, cap)
# 오른쪽 아래 칸: 요점
note_box(c, MARGIN + w2 + 6 * mm, y - 78 * mm, w2, "요점", [
    "클립은 긴 변마다 4개, 이음 핀 머리를 피해 끼웁니다.",
    f"쐐기로 패널 두께 약 {C['PANEL_T_RANGE'][0]:.0f}~{C['PANEL_T_RANGE'][1]:.0f} mm 에 맞춥니다.",
    "톱니가 걸쇠에 걸려 거꾸로 빠지지 않습니다.",
], size=9.5)
y -= 156 * mm
bullets(c, [
    "① 패널을 앞면(셀)이 위로 오게 프레임 턱 위에 올립니다. 뒷면의 USB 포트 주머니는 가운데 뚫린 口자 공간으로 들어가고, "
    "USB 케이블도 이 공간으로 빼냅니다 (다음 쪽 그림).",
    "② 긴 변마다 클립 4개를 프레임 바깥쪽에서 안쪽으로 밀어 끼웁니다. 클립 아래쪽 갈고리가 레일 안쪽 모서리에 '딸깍' 걸리면 됩니다.",
    "③ 쐐기를 얇은 쪽부터 클립 윗날과 패널 사이로 밀어 넣습니다. 손으로 더 이상 들어가지 않을 때까지 밀면 패널이 눌립니다.",
    "④ 뺄 때는 쐐기 두꺼운 쪽을 살짝 들어 톱니를 풀고 당깁니다.",
], MARGIN, y, TW, size=9.5)
c.showPage()
page += 1

# ---- 7. 완성 (뒷면) + 설치·점검 ----
header(c, "", "완성 모습 · 설치와 점검", page)
y = PH - 30 * mm
draw_image(c, "02_overview_back", MARGIN, y - 110 * mm, w=TW, h=108 * mm, callouts=(
    ("opening", "口자 개방부 — USB 주머니·케이블 자리", 30, 60),
    ("key", "연결키 + 이음 핀", 60, -30),
))
c.setFont("KR", 9)
c.setFillColor(GREY)
c.drawCentredString(PW / 2, y - 116 * mm, "뒤쪽 아래에서 본 모습. 패널은 가장자리 턱으로만 받쳐지고 가운데는 비어 있습니다.")
y -= 124 * mm
note_box(c, MARGIN, y, TW, "설치 · 점검", [
    "평평하고 바람이 덜 부는 곳에 두고, 패널 정면이 남쪽을 향하게 합니다. 받침대의 작은 구멍으로 끈을 묶어 고정할 수 있습니다.",
    "각도를 바꾼 뒤나 강풍이 분 뒤에는 핀이 빠지지 않았는지, 쐐기가 헐거워지지 않았는지 확인합니다.",
    "각도를 바꿀 때는 프레임 윗부분을 받친 채 다리를 옮기세요. 다리를 먼저 빼면 프레임이 앞으로 넘어집니다.",
    "PLA 는 한여름 직사광선 아래에서 물러질 수 있습니다. 휘어지면 PETG 로 다시 출력하는 것이 좋습니다.",
    "부품이 부러지면 modeling/stand_parts/ 의 부품별 STL 로 그 부품만 다시 출력합니다.",
])
c.showPage()
c.save()
print("saved", OUT)
