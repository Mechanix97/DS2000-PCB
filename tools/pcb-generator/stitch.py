"""Stitches the GND pours on F.Cu and B.Cu to the In1 plane with a grid of vias.

Without stitching, parts of the top and bottom pours reach ground only through whatever pad they
happen to touch. A via goes on each grid point that clears pads, tracks, other vias, holes, the
board edge and every courtyard (parts and logos) by a margin; existing stitching is replaced, so
the script is safe to re-run after the layout changes.

Run with KiCad's python:  python.exe stitch.py board.kicad_pcb [pitch_mm]
"""
import math, sys
import pcbnew

PCB = sys.argv[1]
PITCH = float(sys.argv[2]) if len(sys.argv) > 2 else 3.5
VIA_D, VIA_DRILL = 0.5, 0.25
CLEAR, EDGE = 0.3, 1.2
b = pcbnew.LoadBoard(PCB)
mm, tomm = pcbnew.FromMM, pcbnew.ToMM
gnd = b.FindNet("GND")
edge = b.GetBoardEdgesBoundingBox()
EX0, EY0, EX1, EY1 = tomm(edge.GetX()), tomm(edge.GetY()), tomm(edge.GetRight()), tomm(edge.GetBottom())

def rect(bb):
    return (tomm(bb.GetX()), tomm(bb.GetY()), tomm(bb.GetRight()), tomm(bb.GetBottom()))

def rect_dist(px, py, r):
    return math.hypot(max(r[0] - px, 0, px - r[2]), max(r[1] - py, 0, py - r[3]))

def seg_dist(a, c, p):
    dx, dy = c[0] - a[0], c[1] - a[1]
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L))
    return math.hypot(a[0] + t * dx - p[0], a[1] + t * dy - p[1])

# previous stitching: GND vias with no track ending on them
ends = set()
for t in b.GetTracks():
    if not isinstance(t, pcbnew.PCB_VIA):
        for p in (t.GetStart(), t.GetEnd()):
            ends.add((round(tomm(p.x), 3), round(tomm(p.y), 3)))
old = [t for t in b.GetTracks() if isinstance(t, pcbnew.PCB_VIA) and t.GetNetname() == "GND"
       and t.IsLocked() and (round(tomm(t.GetPosition().x), 3), round(tomm(t.GetPosition().y), 3)) not in ends]

rects, holes, segs, vias = [], [], [], []
for fp in b.GetFootprints():
    for side in (pcbnew.F_CrtYd, pcbnew.B_CrtYd):
        cy = fp.GetCourtyard(side)
        if cy.OutlineCount():
            rects.append(rect(cy.BBox()))
    for p in fp.Pads():
        rects.append(rect(p.GetBoundingBox()))
        if p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH):
            c = p.GetPosition(); holes.append((tomm(c.x), tomm(c.y), tomm(max(p.GetDrillSize().x, p.GetDrillSize().y)) / 2))
    for g in fp.GraphicalItems():                     # the LED light cut-outs
        if g.GetLayer() == pcbnew.Edge_Cuts:
            rects.append(rect(g.GetBoundingBox()))
for t in b.GetTracks():
    if isinstance(t, pcbnew.PCB_VIA):
        if any(t.m_Uuid.AsString() == v.m_Uuid.AsString() for v in old):
            continue
        c = t.GetPosition(); vias.append((tomm(c.x), tomm(c.y), tomm(t.GetWidth(pcbnew.F_Cu)) / 2))
    else:
        s, e = t.GetStart(), t.GetEnd()
        segs.append(((tomm(s.x), tomm(s.y)), (tomm(e.x), tomm(e.y)), tomm(t.GetWidth()) / 2, t.GetNetname()))

def free(x, y):
    r = VIA_D / 2
    if not (EX0 + EDGE <= x <= EX1 - EDGE and EY0 + EDGE <= y <= EY1 - EDGE):
        return False
    for cx, cy in [(EX0 + 3, EY0 + 3), (EX1 - 3, EY0 + 3), (EX0 + 3, EY1 - 3), (EX1 - 3, EY1 - 3)]:
        if abs(x - cx) < 3 and abs(y - cy) < 3 and (x - cx) * (cx - (EX0 + EX1) / 2) > 0 \
                and (y - cy) * (cy - (EY0 + EY1) / 2) > 0 and math.hypot(x - cx, y - cy) > 3 - EDGE:
            return False
    if any(rect_dist(x, y, q) < r + CLEAR for q in rects):
        return False
    if any(math.hypot(x - hx, y - hy) < hr + r + CLEAR for hx, hy, hr in holes + vias):
        return False
    return all(seg_dist(a, c, (x, y)) >= w + r + CLEAR for a, c, w, _n in segs)

placed = 0
y = EY0 + EDGE
while y <= EY1 - EDGE:
    x = EX0 + EDGE
    while x <= EX1 - EDGE:
        if free(x, y):
            v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
            v.SetWidth(mm(VIA_D)); v.SetDrill(mm(VIA_DRILL)); v.SetNet(gnd); v.SetLocked(True)
            b.Add(v); vias.append((x, y, VIA_D / 2)); placed += 1
        x += PITCH
    y += PITCH

for v in old:
    b.Remove(v)
pcbnew.SaveBoard(PCB, b)
print(f"stitching: {placed} GND vias ({len(old)} previous replaced)")
