"""Connects every GND and +3V3 SMD pad to its plane (In1 GND, In2 +3V3) before autorouting.

Order matters:
  1. RP2350A supply pins are tied with a short track straight to their decoupling capacitor, as the
     RP2350 guide asks, before anything else can occupy that space.
  2. Every other plane pad (top or bottom) gets a short track and a via, placed only where it clears
     copper of other nets on every layer, holes, other vias and the board edge.
  3. RP2350A pins that could not be tied fall back to a via.
The autorouter ignores both nets (net class "Plane").

Run with KiCad's python:  python.exe fanout.py board.kicad_pcb
"""
import math, sys
import pcbnew

PCB = sys.argv[1]
b = pcbnew.LoadBoard(PCB)
mm, tomm = pcbnew.FromMM, pcbnew.ToMM
PLANES = {"GND", "+3V3"}
MCU = "U3"
VIA_D, VIA_DRILL = 0.5, 0.25
CLEAR, HOLE_CLEAR, HOLE_TO_HOLE, EDGE_CLEAR = 0.15, 0.2, 0.25, 0.35
RAD = 3.0

edge = b.GetBoardEdgesBoundingBox()
EX0, EY0, EX1, EY1 = tomm(edge.GetX()), tomm(edge.GetY()), tomm(edge.GetRight()), tomm(edge.GetBottom())
netinfo = {n: b.FindNet(n) for n in PLANES}

def rect_dist(px, py, r):
    x0, y0, x1, y1 = r
    return math.hypot(max(x0 - px, 0, px - x1), max(y0 - py, 0, py - y1))

def seg_pt_dist(a, c, p):
    ax, ay = a; cx, cy = c; px, py = p
    dx, dy = cx - ax, cy - ay
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(ax + t * dx - px, ay + t * dy - py)

def seg_rect_dist(a, c, r, steps=16):
    return min(rect_dist(a[0] + (c[0] - a[0]) * k / steps, a[1] + (c[1] - a[1]) * k / steps, r) for k in range(steps + 1))

def inside_board(x, y, margin):
    if not (EX0 + margin <= x <= EX1 - margin and EY0 + margin <= y <= EY1 - margin):
        return False
    for cx, cy in [(EX0 + RAD, EY0 + RAD), (EX1 - RAD, EY0 + RAD), (EX0 + RAD, EY1 - RAD), (EX1 - RAD, EY1 - RAD)]:
        if abs(x - cx) <= RAD and abs(y - cy) <= RAD and (x - cx) * (cx - (EX0 + EX1) / 2) > 0 \
                and (y - cy) * (cy - (EY0 + EY1) / 2) > 0 and math.hypot(x - cx, y - cy) > RAD - margin:
            return False
    return True

# ---------------------------------------------------------------- obstacles
pads = []     # (rect, net, on_top, on_bottom, pad)
holes = []    # (x, y, radius)
for fp in b.GetFootprints():
    for pad in fp.Pads():
        c = pad.GetPosition()
        if pad.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH):
            holes.append((tomm(c.x), tomm(c.y), tomm(max(pad.GetDrillSize().x, pad.GetDrillSize().y)) / 2))
        if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
            continue
        bb = pad.GetBoundingBox()
        through = pad.GetAttribute() == pcbnew.PAD_ATTRIB_PTH
        pads.append(((tomm(bb.GetX()), tomm(bb.GetY()), tomm(bb.GetRight()), tomm(bb.GetBottom())), pad.GetNetname(),
                     through or pad.IsOnLayer(pcbnew.F_Cu), through or pad.IsOnLayer(pcbnew.B_Cu), pad))
vias = []     # (x, y, net)
tracks = []   # (a, c, width, net, layer)
for t_ in b.GetTracks():                      # tracks already on the board, e.g. from preroute.py
    if isinstance(t_, pcbnew.PCB_VIA):
        c = t_.GetPosition(); vias.append((tomm(c.x), tomm(c.y), t_.GetNetname()))
    else:
        s_, e_ = t_.GetStart(), t_.GetEnd()
        tracks.append(((tomm(s_.x), tomm(s_.y)), (tomm(e_.x), tomm(e_.y)), tomm(t_.GetWidth()), t_.GetNetname(), t_.GetLayer()))

def via_ok(x, y, net, own):
    r = VIA_D / 2
    if not inside_board(x, y, EDGE_CLEAR + r):
        return False
    for rect, onet, _t, _b, pad in pads:
        if key(pad) != key(own) and onet != net and rect_dist(x, y, rect) < r + CLEAR:
            return False
    for hx, hy, hr in holes:
        if math.hypot(x - hx, y - hy) < hr + max(VIA_DRILL / 2 + HOLE_TO_HOLE, r + HOLE_CLEAR):
            return False
    for vx, vy, vnet in vias:
        if math.hypot(x - vx, y - vy) < (VIA_DRILL + HOLE_TO_HOLE if vnet == net else VIA_D + CLEAR):
            return False
    for a, c, w, tnet, _l in tracks:
        if tnet != net and seg_pt_dist(a, c, (x, y)) < r + w / 2 + CLEAR:
            return False
    return True

def track_ok(a, c, width, net, layer, allowed=()):
    top = layer == pcbnew.F_Cu
    for rect, onet, on_t, on_b, pad in pads:
        if key(pad) in {key(p) for p in allowed} or onet == net or not (on_t if top else on_b):
            continue
        if seg_rect_dist(a, c, rect) < width / 2 + CLEAR:
            return False
    for ta, tc, w, tnet, tl in tracks:
        if tnet != net and tl == layer:
            if min(seg_pt_dist(ta, tc, (a[0] + (c[0] - a[0]) * k / 16, a[1] + (c[1] - a[1]) * k / 16))
                   for k in range(17)) < width / 2 + w / 2 + CLEAR:
                return False
    for vx, vy, vnet in vias:
        if vnet != net and seg_pt_dist(a, c, (vx, vy)) < width / 2 + VIA_D / 2 + CLEAR:
            return False
    return True

def add_track(a, c, width, net, layer):
    if math.hypot(c[0] - a[0], c[1] - a[1]) < 1e-3:
        return
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(pcbnew.VECTOR2I(mm(a[0]), mm(a[1]))); t.SetEnd(pcbnew.VECTOR2I(mm(c[0]), mm(c[1])))
    t.SetWidth(mm(width)); t.SetLayer(layer); t.SetNet(netinfo[net]); b.Add(t)
    tracks.append((a, c, width, net, layer))

def add_via(x, y, net):
    v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
    v.SetWidth(mm(VIA_D)); v.SetDrill(mm(VIA_DRILL)); v.SetNet(netinfo[net]); b.Add(v)
    vias.append((x, y, net))

def key(pad):
    return (pad.GetParentFootprint().GetReference(), pad.GetNumber()) if pad is not None else None

def pos(pad):
    c = pad.GetPosition(); return (tomm(c.x), tomm(c.y))

def try_via(fp, pad, width, layer, dists=(0.6, 0.75, 0.9, 1.05, 1.2, 1.4, 1.6, 1.8), spread=(0, 1, -1, 2, -2, 3, -3, 4)):
    net = pad.GetNetname(); px, py = pos(pad)
    fx, fy = pos(fp) if False else (tomm(fp.GetPosition().x), tomm(fp.GetPosition().y))
    base = math.atan2(py - fy, px - fx) if abs(px - fx) + abs(py - fy) > 1e-3 else 0.0
    for dist in dists:
        for k in spread:
            ang = base + k * math.pi / 4
            x, y = round(px + dist * math.cos(ang), 3), round(py + dist * math.sin(ang), 3)
            if via_ok(x, y, net, pad) and track_ok((px, py), (x, y), width, net, layer, (pad,)):
                add_via(x, y, net); add_track((px, py), (x, y), width, net, layer)
                return True
    return False

def try_tie(pad, net):
    a = pos(pad)
    targets = sorted((p for _r, n, t, _b, p in pads if n == net and t and key(p) != key(pad) and p.GetParentFootprint().GetReference() != MCU),
                     key=lambda p: math.hypot(pos(p)[0] - a[0], pos(p)[1] - a[1]))
    for tp in targets[:6]:
        c = pos(tp)
        if math.hypot(c[0] - a[0], c[1] - a[1]) > 3.5:
            break
        for path in ([a, c], [a, (c[0], a[1]), c], [a, (a[0], c[1]), c]):
            segs = list(zip(path, path[1:]))
            if all(track_ok(s, e, 0.2, net, pcbnew.F_Cu, (pad, tp)) for s, e in segs):
                for s, e in segs:
                    add_track(s, e, 0.2, net, pcbnew.F_Cu)
                return True
    return False

# ---------------------------------------------------------------- run
mcu_pads, others = [], []
for fp in b.GetFootprints():
    if fp.GetReference() == "J1":
        continue                                  # joined solidly to the B.Cu GND pour
    layer = pcbnew.B_Cu if fp.IsFlipped() else pcbnew.F_Cu
    for pad in fp.Pads():
        if pad.GetNetname() in PLANES and pad.GetAttribute() == pcbnew.PAD_ATTRIB_SMD and pad.IsOnLayer(layer):
            if fp.GetReference() == MCU:
                if pad.GetNumber() != "61":       # the exposed pad has its own thermal vias
                    mcu_pads.append((fp, pad))
            else:
                others.append((fp, pad, layer))

tied, vias_n, left = 0, 0, []
untied = []

ended = {(round(a[0], 3), round(a[1], 3)) for a, _c, _w, _n, _l in tracks} |         {(round(c[0], 3), round(c[1], 3)) for _a, c, _w, _n, _l in tracks}
def rpos(pad):
    x, y = pos(pad); return (round(x, 3), round(y, 3))

# 0. USB_OTP_VDD (53) and QSPI_IOVDD (54) are adjacent +3V3 pins hemmed in by USB (51/52) and QSPI
#    (55-60): join them and drop one via between the two escape fans, unless preroute.py already
#    wired them as in Raspberry Pi's reference
u3 = next(fp for fp in b.GetFootprints() if fp.GetReference() == MCU)
p53, p54 = (next(p for p in u3.Pads() if p.GetNumber() == n) for n in ("53", "54"))
if rpos(p53) not in ended:
    (x53, y53), (x54, y54) = pos(p53), pos(p54)
    mx, top = (x53 + x54) / 2, y53 - 0.75
    add_track((x53, y53), (mx, top), 0.2, "+3V3", pcbnew.F_Cu)
    add_track((x54, y54), (mx, top), 0.2, "+3V3", pcbnew.F_Cu)
    add_track((mx, top), (mx, top - 0.5), 0.2, "+3V3", pcbnew.F_Cu)
    add_via(mx, top - 0.5, "+3V3")
    vias_n += 1
mcu_pads = [(fp, p) for fp, p in mcu_pads if p.GetNumber() not in ("53", "54")]
# pads preroute.py already wired keep their hand routing; other pads skip their via only when
# those tracks already reach a same-net via (the core regulator), not when they just join two pads
mcu_pads = [(fp, p) for fp, p in mcu_pads if rpos(p) not in ended]
def reaches_via(pad):
    net, seen, todo = pad.GetNetname(), set(), [rpos(pad)]
    vpos = {(round(x, 3), round(y, 3)) for x, y, n in vias if n == net}
    while todo:
        q = todo.pop()
        if q in seen:
            continue
        seen.add(q)
        if q in vpos:
            return True
        for a_, c_, _w, n_, _l in tracks:
            ra, rc = (round(a_[0], 3), round(a_[1], 3)), (round(c_[0], 3), round(c_[1], 3))
            if n_ == net and q in (ra, rc):
                todo.append(rc if q == ra else ra)
    return False
others = [(fp, p, l) for fp, p, l in others if not reaches_via(p)]
for fp, pad in mcu_pads:                          # 1. RP2350A pins straight to their capacitor
    if try_tie(pad, pad.GetNetname()):
        tied += 1
    else:
        untied.append((fp, pad))
for fp, pad, layer in others:                     # 2. everything else: via
    if try_via(fp, pad, 0.3, layer):
        vias_n += 1
    else:
        left.append(f"{fp.GetReference()}.{pad.GetNumber()}")
for fp, pad in untied:                            # 3. RP2350A pins with no tie: via
    if try_via(fp, pad, 0.2, pcbnew.F_Cu, dists=(0.6, 0.75, 0.9, 1.05, 1.2, 1.4, 1.6, 1.8), spread=(0, 1, -1, 2, -2)):
        vias_n += 1
    else:
        left.append(f"{MCU}.{pad.GetNumber()}")

# 4. anything still loose: a straight or L track to the nearest same-net pad or via on its side
def tie_any(pad, layer):
    net = pad.GetNetname(); a = pos(pad)
    cands = [(pos(p), p) for _r, n, t, bo, p in pads if n == net and key(p) != key(pad) and (t if layer == pcbnew.F_Cu else bo)]
    cands += [((vx, vy), None) for vx, vy, vn in vias if vn == net]
    cands.sort(key=lambda c: math.hypot(c[0][0] - a[0], c[0][1] - a[1]))
    for c, tp in cands[:10]:
        if math.hypot(c[0] - a[0], c[1] - a[1]) > 3.5:
            break
        for path in ([a, c], [a, (c[0], a[1]), c], [a, (a[0], c[1]), c]):
            segs = list(zip(path, path[1:]))
            if all(track_ok(s_, e_, 0.2, net, layer, (pad, tp)) for s_, e_ in segs):
                for s_, e_ in segs:
                    add_track(s_, e_, 0.2, net, layer)
                return True
    return False
lookup = {f"{fp.GetReference()}.{p.GetNumber()}": (fp, p) for fp in b.GetFootprints() for p in fp.Pads()}
still = []
for item in left:
    fp, pad = lookup[item]
    if not tie_any(pad, pcbnew.B_Cu if fp.IsFlipped() else pcbnew.F_Cu):
        still.append(item)
left = still

pcbnew.SaveBoard(PCB, b)
print(f"fanout: {tied} RP2350A supply pins tied to their capacitor, {vias_n} vias, "
      f"{len(left)} left for manual routing: {' '.join(left)}")
