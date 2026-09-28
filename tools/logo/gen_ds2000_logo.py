"""Turns the DS2000 product logo (mechardo3d.xyz, static/images/DS2000/logo/ds2000-logo.webp) into a
KiCad footprint.

The logo has two colours and the board has three finishes, so:
  white "DS 2000" lettering  -> white silkscreen
  blue arcs                  -> ENIG gold (copper with a solder-mask opening)
Each colour is thresholded, traced with potrace, resolved with an even-odd fill so the counters of
D and 0 become holes, and each hole is joined to its outline with a zero-width keyhole cut, because
footprint polygons cannot carry holes.

Usage: python gen_ds2000_logo.py ds2000-logo.webp out.kicad_mod [height_mm]
Needs: pillow, numpy, potracer, pyclipper
"""
import math, sys, uuid
import numpy as np
import potrace, pyclipper
from PIL import Image

SRC, OUT = sys.argv[1], sys.argv[2]
HEIGHT = float(sys.argv[3]) if len(sys.argv) > 3 else 8.6
img = np.asarray(Image.open(SRC).convert("RGB")).astype(int)
H_PX, W_PX = img.shape[:2]
S = HEIGHT / H_PX
r, g, b = img[..., 0], img[..., 1], img[..., 2]
MASKS = {
    "white": (r > 150) & (g > 150) & (b > 140) & (abs(r - b) < 60),
    "blue": (b > 120) & (r < 110) & (b - r > 60),
}

def pt(p):
    return (p.x, p.y) if hasattr(p, "x") else (p[0], p[1])

def trace(mask):
    """Closed polylines, in pixels, from potrace's corner and Bezier segments."""
    out = []
    # potracer traces the False pixels, so hand it the complement
    for curve in potrace.Bitmap(~mask).trace(turdsize=20, alphamax=1.0, opticurve=True, opttolerance=0.2):
        pts, cur = [], pt(curve.start_point)
        pts.append(cur)
        for seg in curve.segments:
            if seg.is_corner:
                pts += [pt(seg.c), pt(seg.end_point)]
            else:
                c1, c2, e = pt(seg.c1), pt(seg.c2), pt(seg.end_point)
                for k in range(1, 9):
                    t = k / 8
                    pts.append(tuple((1 - t) ** 3 * cur[i] + 3 * (1 - t) ** 2 * t * c1[i]
                                     + 3 * (1 - t) * t ** 2 * c2[i] + t ** 3 * e[i] for i in range(2)))
            cur = pt(seg.end_point)
        out.append(pts)
    return out

def shapes(contours):
    """Even-odd resolve into [(outer, [holes...])]."""
    k = 100
    pc = pyclipper.Pyclipper()
    for c in contours:
        pc.AddPath([(round(x * k), round(y * k)) for x, y in c], pyclipper.PT_SUBJECT, True)
    tree = pc.Execute2(pyclipper.CT_UNION, pyclipper.PFT_EVENODD, pyclipper.PFT_EVENODD)
    res = []
    def walk(node):
        for child in node.Childs:
            if not child.IsHole:
                res.append(([(x / k, y / k) for x, y in child.Contour],
                            [[(x / k, y / k) for x, y in h.Contour] for h in child.Childs]))
                for h in child.Childs:
                    walk(h)                                  # islands inside holes
    walk(tree)
    return res

def area(p):
    return sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p))) / 2

def keyhole(outer, holes):
    """One polygon: each hole joined to the outline by a vertical cut from its topmost point."""
    poly = list(outer)
    if area(poly) < 0:
        poly.reverse()
    for hole in sorted(holes, key=lambda h: min(y for _x, y in h)):
        hole = list(hole)
        if area(hole) > 0:
            hole.reverse()
        hi = min(range(len(hole)), key=lambda i: hole[i][1])
        hx, hy = hole[hi]
        best = None                                          # nearest edge of poly straight above
        for i in range(len(poly)):
            (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % len(poly)]
            if (x1 - hx) * (x2 - hx) <= 0 and x1 != x2:
                y = y1 + (hx - x1) * (y2 - y1) / (x2 - x1)
                if y < hy and (best is None or y > best[0]):
                    best = (y, i)
        y, i = best
        bridge = (hx, y)
        ring = hole[hi:] + hole[:hi]
        poly = poly[:i + 1] + [bridge] + ring + [ring[0], bridge] + poly[i + 1:]
    return poly

def fp_poly(points, layer):
    body = " ".join(f"(xy {round((x - W_PX / 2) * S, 4)} {round((y - H_PX / 2) * S, 4)})" for x, y in points)
    return (f'\t(fp_poly\n\t\t(pts {body})\n\t\t(stroke (width 0) (type solid))\n\t\t(fill yes)\n'
            f'\t\t(layer "{layer}")\n\t\t(uuid "{uuid.uuid4()}")\n\t)\n')

polys, stats = "", {}
for colour, layers in [("white", ["F.SilkS"]), ("blue", ["F.Cu", "F.Mask"])]:
    items = shapes(trace(MASKS[colour]))
    stats[colour] = (len(items), sum(len(h) for _o, h in items))
    for outer, holes in items:
        p = keyhole(outer, holes)
        for layer in layers:
            polys += fp_poly(p, layer)

w_mm, h_mm = W_PX * S / 2 + 0.25, H_PX * S / 2 + 0.25
name = f"Logo_DS2000_{HEIGHT:g}mm"
out = f'''(footprint "{name}"
\t(version 20250114)
\t(generator "gen_ds2000_logo.py")
\t(layer "F.Cu")
\t(descr "DS2000 product logo from mechardo3d.xyz: white lettering in silkscreen, the blue arcs in ENIG copper")
\t(tags "logo DS2000")
\t(property "Reference" "LOGO2" (at 0 {h_mm + 1} 0) (layer "F.Fab") (hide yes) (uuid "{uuid.uuid4()}") (effects (font (size 1 1) (thickness 0.15))))
\t(property "Value" "{name}" (at 0 {h_mm + 2} 0) (layer "F.Fab") (hide yes) (uuid "{uuid.uuid4()}") (effects (font (size 1 1) (thickness 0.15))))
\t(attr board_only exclude_from_pos_files exclude_from_bom)
{polys}\t(fp_rect (start {-w_mm} {-h_mm}) (end {w_mm} {h_mm}) (stroke (width 0.05) (type solid)) (fill no) (layer "F.CrtYd") (uuid "{uuid.uuid4()}"))
)
'''
open(OUT, "w", encoding="utf8", newline="\n").write(out)
print(f"wrote {OUT}: {W_PX * S:.2f} x {HEIGHT} mm; white {stats['white'][0]} shapes / {stats['white'][1]} holes, "
      f"blue {stats['blue'][0]} shapes / {stats['blue'][1]} holes")
