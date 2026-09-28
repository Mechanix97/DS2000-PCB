"""Finishes the board's visible face. Safe to run repeatedly on the hand-edited board.

- GND pour on F.Cu (the other planes come from gen_pcb.py)
- the Mechardo Labs mark (DS2000.pretty/Logo_Mechardo_6mm, ENIG gold) with "DS2000",
  "mechardo labs" and "rev A" in the back-left corner, the one area of the face with no top copper
- every reference designator shown, each moved to the first spot beside its part that clears pads,
  holes, vias, other text and the board edge; any that cannot be placed stays hidden and is listed
- mechardo3d.xyz typography: Sora for the name and wordmark, IBM Plex Mono for everything technical.
  The fonts live in fonts/ (OFL); the board is flagged to embed them the next time KiCad saves it
- the USB-C footprint's silkscreen, which falls past the board edge, moves to the fab layer

KiCad 10's Python bindings hand back untyped proxies once anything has been removed from the
board, so reads and changes come first and removals last. Fonts cannot be set through the
bindings either, so they are written into the saved file.

Run with KiCad's python:  python.exe branding.py board.kicad_pcb
"""
import os, re, sys, time
import pcbnew
T0 = time.time()
def tick(msg):
    print(f"[{time.time() - T0:5.1f}s] {msg}", flush=True)

PCB = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
LIB = os.path.join(ROOT, "DS2000.pretty")
sys.path.insert(0, HERE)
from kisexp import parse, dump, find, first, Sym

tick("loading")
b = pcbnew.LoadBoard(PCB)
tick("loaded")
mm, tomm = pcbnew.FromMM, pcbnew.ToMM

BX, LOGO_Y = 75.5, 79.2
OURS = {"DS2000", "DS-2000", "rev A", "mechardo labs"}
REF_SIZE = 0.8                                  # cap height; Plex Mono Bold stems are ~0.16 mm here, above JLC's 0.153 mm
MONO_ADVANCE = 0.6 / 0.7                        # Plex Mono: 600/1000 em per char; KiCad sizes TrueType by cap height (~0.7 em)
FONTS = {                                       # text -> (face, bold)
    "DS2000": ("Sora", True), "mechardo labs": ("Sora SemiBold", False), "rev A": ("IBM Plex Mono", True),
    "MUTE": ("IBM Plex Mono SemiBold", False), "DEAFEN": ("IBM Plex Mono SemiBold", False),
    "DISCONNECT": ("IBM Plex Mono SemiBold", False),
}
TECH_FACE = ("IBM Plex Mono", True)             # Bold: debug labels and references; lighter weights print too thin at 0.8 mm
HIDDEN_REFS = ("TP", "JP", "LOGO")              # these carry a functional label instead

# ---------------------------------------------------------------- board-level
edge = b.GetBoardEdgesBoundingBox()
EX0, EY0, EX1, EY1 = tomm(edge.GetX()), tomm(edge.GetY()), tomm(edge.GetRight()), tomm(edge.GetBottom())

# KiCad judges TrueType stroke weight from text size alone and flags anything under ~1.1 mm against
# 0.08 mm. The real stems of IBM Plex Mono Bold at 0.8 mm cap height are ~0.16 mm, so the heuristic
# is relaxed rather than the text enlarged (which would leave a dozen references with no room).
b.GetDesignSettings().m_MinSilkTextThickness = mm(0.06)

if not any(z.GetLayer() == pcbnew.F_Cu and z.GetNetname() == "GND" for z in b.Zones()):
    z = pcbnew.ZONE(b); z.SetLayer(pcbnew.F_Cu); z.SetNet(b.FindNet("GND"))
    ol = z.Outline(); ol.NewOutline()
    for x, y in [(EX0, EY0), (EX1, EY0), (EX1, EY1), (EX0, EY1)]:
        ol.Append(mm(x), mm(y))
    z.SetLocalClearance(mm(0.25)); z.SetMinThickness(mm(0.25))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    b.Add(z)

stale = []
for fp in list(b.GetFootprints()):
    if str(fp.GetFPID().GetLibItemName()) == "Logo_Mechardo_6mm":
        stale.append(fp)
    elif fp.GetReference() == "J1":
        for item in fp.GraphicalItems():
            if item.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS):
                item.SetLayer(pcbnew.B_Fab)
stale += [d for d in b.GetDrawings() if isinstance(d, pcbnew.PCB_TEXT) and d.GetText() in OURS]

def text(s, x, y, size):
    t = pcbnew.PCB_TEXT(b); t.SetText(s); t.SetLayer(pcbnew.F_SilkS)
    t.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
    t.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size))); t.SetTextThickness(mm(size * 0.15))
    b.Add(t)

logo = pcbnew.FootprintLoad(LIB, "Logo_Mechardo_6mm")
logo.SetFPID(pcbnew.LIB_ID("DS2000", "Logo_Mechardo_6mm"))
logo.SetReference("LOGO1")
logo.GetField(pcbnew.FIELD_T_REFERENCE).SetVisible(False)
logo.SetPosition(pcbnew.VECTOR2I(mm(BX), mm(LOGO_Y)))
b.Add(logo)
text("DS2000", BX, LOGO_Y + 5.3, 1.6)
text("mechardo labs", BX, LOGO_Y + 7.4, 1.0)
text("rev A", BX, LOGO_Y + 9.3, 1.0)

# ---------------------------------------------------------------- reference placement
def rect(bb):
    return (tomm(bb.GetX()), tomm(bb.GetY()), tomm(bb.GetRight()), tomm(bb.GetBottom()))

obst = {pcbnew.F_SilkS: [], pcbnew.B_SilkS: []}
def add_obst(side, r, pad=0.0):
    obst[side].append((r[0] - pad, r[1] - pad, r[2] + pad, r[3] + pad))
for fp in b.GetFootprints():
    for p in fp.Pads():
        r = rect(p.GetBoundingBox())
        through = p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH)
        if through or p.IsOnLayer(pcbnew.F_Cu):
            add_obst(pcbnew.F_SilkS, r, 0.15)
        if through or p.IsOnLayer(pcbnew.B_Cu):
            add_obst(pcbnew.B_SilkS, r, 0.15)
    for g in fp.GraphicalItems():
        if g.GetLayer() in obst:
            add_obst(g.GetLayer(), rect(g.GetBoundingBox()), 0.1)
for t in b.GetTracks():
    if isinstance(t, pcbnew.PCB_VIA):
        add_obst(pcbnew.F_SilkS, rect(t.GetBoundingBox()), 0.1); add_obst(pcbnew.B_SilkS, rect(t.GetBoundingBox()), 0.1)
for d in list(b.GetDrawings()):
    if isinstance(d, pcbnew.PCB_TEXT) and d.GetLayer() in obst and d.GetText() not in OURS:
        add_obst(d.GetLayer(), rect(d.GetBoundingBox()), 0.2)
# the branding block and the logo
add_obst(pcbnew.F_SilkS, (BX - 5.2, LOGO_Y - 3.6, BX + 5.2, LOGO_Y + 9.8))

def fits(side, r):
    if r[0] < EX0 + 0.6 or r[1] < EY0 + 0.6 or r[2] > EX1 - 0.6 or r[3] > EY1 - 0.6:
        return False
    for cx, cy in [(EX0 + 3, EY0 + 3), (EX1 - 3, EY0 + 3), (EX0 + 3, EY1 - 3), (EX1 - 3, EY1 - 3)]:
        for px, py in [(r[0], r[1]), (r[2], r[1]), (r[0], r[3]), (r[2], r[3])]:
            if abs(px - cx) < 3 and abs(py - cy) < 3 and (px - cx) * (cx - (EX0 + EX1) / 2) > 0 \
                    and (py - cy) * (cy - (EY0 + EY1) / 2) > 0 and ((px - cx) ** 2 + (py - cy) ** 2) ** 0.5 > 2.4:
                return False
    return all(o[2] < r[0] or o[0] > r[2] or o[3] < r[1] or o[1] > r[3] for o in obst[side])

def fits_body(side, r, fp):
    """On a part's own body only its pads matter; its outline and courtyard are expected underneath."""
    own = [rect(p.GetBoundingBox()) for p in fp.Pads()]
    return all(o[2] < r[0] or o[0] > r[2] or o[3] < r[1] or o[1] > r[3] for o in own)

placed, hidden = 0, []
# ICs choose first; then everything else, smallest first
fps = sorted((fp for fp in b.GetFootprints() if not fp.GetReference().startswith(HIDDEN_REFS)),
             key=lambda f: (not f.GetReference().startswith("U"),
                            (lambda r: (r[2] - r[0]) * (r[3] - r[1]))(rect(f.GetBoundingBox(False)))))
for fp in fps:
    ref = fp.GetReference()
    side = pcbnew.B_SilkS if fp.IsFlipped() else pcbnew.F_SilkS
    cy_ = fp.GetCourtyard(pcbnew.B_CrtYd if fp.IsFlipped() else pcbnew.F_CrtYd)
    x0, y0, x1, y1 = rect(cy_.BBox()) if cy_.OutlineCount() else rect(fp.GetBoundingBox(False))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    # TrueType boxes include the line gap: allow for it so neighbours never touch
    w, h = len(ref) * MONO_ADVANCE * REF_SIZE + 0.3, REF_SIZE / 0.7 + 0.2
    g = 0.15
    cands = [(cx, y0 - g - h / 2, 0), (cx, y1 + g + h / 2, 0), (x0 - g - w / 2, cy, 0), (x1 + g + w / 2, cy, 0),
             (x0 - g - h / 2, cy, 90), (x1 + g + h / 2, cy, 90)]
    for step in (0.0, 0.6, 1.2, 1.8, 2.4):       # rings further out when the first one is full
        for dx in (-1.0, 1.0, -2.0, 2.0, -3.0, 3.0, -4.0, 4.0):
            cands += [(cx + dx, y0 - g - h / 2 - step, 0), (cx + dx, y1 + g + h / 2 + step, 0)]
        for dy in (-1.0, 1.0, -2.0, 2.0):
            cands += [(x0 - g - h / 2 - step, cy + dy, 90), (x1 + g + h / 2 + step, cy + dy, 90)]
            cands += [(x0 - g - w / 2 - step, cy + dy, 0), (x1 + g + w / 2 + step, cy + dy, 0)]
    for sx in (-1, 1):                           # diagonal corners, for parts boxed in on every side
        for sy in (-1, 1):
            cands.append((cx + sx * ((x1 - x0) / 2 + g + w / 2), cy + sy * ((y1 - y0) / 2 + g + h / 2), 0))
    if ref.startswith(("U", "SW")):
        cands.append((cx, cy, 0))                # ICs and switches: on the body, as usual
    field = fp.GetField(pcbnew.FIELD_T_REFERENCE)
    for tx, ty, ang in cands:
        tw, th = (w, h) if ang == 0 else (h, w)
        r = (tx - tw / 2, ty - th / 2, tx + tw / 2, ty + th / 2)
        on_body = (tx, ty) == (cx, cy)
        if fits(side, r) or (on_body and fits_body(side, r, fp)):
            field.SetVisible(True); field.SetLayer(side)
            field.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER); field.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
            field.SetKeepUpright(True)
            field.SetTextSize(pcbnew.VECTOR2I(mm(REF_SIZE), mm(REF_SIZE))); field.SetTextThickness(mm(0.12))
            field.SetPosition(pcbnew.VECTOR2I(mm(tx), mm(ty)))
            field.SetTextAngle(pcbnew.EDA_ANGLE(ang, pcbnew.DEGREES_T))
            add_obst(side, r, 0.1); placed += 1
            break
    else:
        field.SetVisible(False); hidden.append(ref)
for fp in b.GetFootprints():
    if fp.GetReference().startswith(HIDDEN_REFS):
        fp.GetField(pcbnew.FIELD_T_REFERENCE).SetVisible(False)

for item in stale:
    b.Remove(item)
tick("saving")
pcbnew.SaveBoard(PCB, b)
tick("fonts")

# ---------------------------------------------------------------- fonts, written into the file
root = parse(open(PCB, encoding="utf8").read())
def set_face(node, face, bold=False):
    eff = first(node, "effects")
    if eff is None:
        return
    font = first(eff, "font")
    font[:] = [x for x in font if not (isinstance(x, list) and x[0] in ("face", "bold"))]
    font.insert(1, ["face", face])
    if bold:
        font.append(["bold", Sym("yes")])
for node in root:
    if isinstance(node, list) and node and node[0] == "gr_text":
        face, bold = FONTS.get(node[1], TECH_FACE)
        set_face(node, face, bold)
    elif isinstance(node, list) and node and node[0] == "footprint":
        for prop in find(node, "property"):
            if prop[1] == "Reference":
                set_face(prop, *TECH_FACE)
    elif isinstance(node, list) and node and node[0] == "embedded_fonts":
        node[1] = Sym("yes")
# drop previously embedded files so KiCad re-embeds only the fonts still in use
root[:] = [n for n in root if not (isinstance(n, list) and n and n[0] == "embedded_files")]
open(PCB, "w", encoding="utf8", newline="\n").write(dump(root) + "\n")
tick("re-loading")
b = pcbnew.LoadBoard(PCB)                        # round-trip through KiCad to normalise the file and embed fonts
pcbnew.SaveBoard(PCB, b)
tick("done")

print(f"branding applied: {placed} references placed, {len(hidden)} hidden ({' '.join(hidden)})")
