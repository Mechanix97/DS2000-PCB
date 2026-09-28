"""Turns the Mechardo Labs mark (mechardo3d.xyz favicon.svg) into a KiCad footprint.

The board face shows it in ENIG gold: a rounded square of copper whose solder-mask opening leaves
the "m" covered, so the letter reads black on gold. The mask opening is one polygon with a keyhole
cut, because footprint polygons cannot carry holes.

Usage: python gen_logo.py favicon.svg out.kicad_mod [size_mm]
"""
import math, re, sys, uuid

SVG, OUT = sys.argv[1], sys.argv[2]
SIZE = float(sys.argv[3]) if len(sys.argv) > 3 else 6.0
src = open(SVG, encoding="utf8").read()
VIEW = 512.0
S = SIZE / VIEW
RX = float(re.search(r'<rect[^>]*rx="([\d.]+)"', src).group(1))
D = re.search(r'<path[^>]*d="([^"]+)"', src).group(1)

def parse_path(d):
    """M, H, V, L, Q, Z (absolute), which is all the mark uses. Quadratic curves are flattened."""
    toks = re.findall(r"[MHVLQZ]|-?\d+(?:\.\d+)?", d)
    pts, cur, i, cmd = [], (0.0, 0.0), 0, None
    while i < len(toks):
        t = toks[i]
        if t in "MHVLQZ":
            cmd = t; i += 1
            if cmd == "Z":
                continue
        if cmd == "M" or cmd == "L":
            cur = (float(toks[i]), float(toks[i + 1])); i += 2; pts.append(cur)
        elif cmd == "H":
            cur = (float(toks[i]), cur[1]); i += 1; pts.append(cur)
        elif cmd == "V":
            cur = (cur[0], float(toks[i])); i += 1; pts.append(cur)
        elif cmd == "Q":
            c = (float(toks[i]), float(toks[i + 1])); e = (float(toks[i + 2]), float(toks[i + 3])); i += 4
            for k in range(1, 9):
                t_ = k / 8
                pts.append(((1 - t_) ** 2 * cur[0] + 2 * (1 - t_) * t_ * c[0] + t_ ** 2 * e[0],
                            (1 - t_) ** 2 * cur[1] + 2 * (1 - t_) * t_ * c[1] + t_ ** 2 * e[1]))
            cur = e
    return pts

def rounded_square(size, r, seg=8):
    pts = []
    for cx, cy, a0 in [(size - r, r, -90), (size - r, size - r, 0), (r, size - r, 90), (r, r, 180)]:
        for k in range(seg + 1):
            a = math.radians(a0 + 90 * k / seg)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts

def area(p):
    return sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p))) / 2

outer = rounded_square(VIEW, RX)
# The glyph is one contour whose humps overlap; browsers fill it with the nonzero rule. A polygon
# taken as-is renders the overlaps as holes, so resolve it to its nonzero union first.
import pyclipper
SCALE = 1000
pc = pyclipper.Pyclipper()
pc.AddPath([(round(x * SCALE), round(y * SCALE)) for x, y in parse_path(D)], pyclipper.PT_SUBJECT, True)
union = pc.Execute(pyclipper.CT_UNION, pyclipper.PFT_NONZERO, pyclipper.PFT_NONZERO)
assert len(union) == 1, f"expected one outline for the m, got {len(union)}"
letter = [(x / SCALE, y / SCALE) for x, y in union[0]]
if area(outer) * area(letter) > 0:          # the hole must wind the other way
    letter = letter[::-1]
# keyhole: bridge from the outer ring's lowest point to the letter's lowest point
oi = max(range(len(outer)), key=lambda k: (outer[k][1], -abs(outer[k][0] - VIEW / 2)))
li = max(range(len(letter)), key=lambda k: (letter[k][1], -abs(letter[k][0] - VIEW / 2)))
outer_r = outer[oi:] + outer[:oi]
letter_r = letter[li:] + letter[:li]
mask = outer_r + [outer_r[0]] + letter_r + [letter_r[0]]

def xy(p):
    # centre the mark on the footprint origin, in mm
    return f"(xy {round((p[0] - VIEW / 2) * S, 4)} {round((p[1] - VIEW / 2) * S, 4)})"

def poly(points, layer):
    body = " ".join(xy(p) for p in points)
    return (f'\t(fp_poly\n\t\t(pts {body})\n\t\t(stroke (width 0) (type solid))\n\t\t(fill yes)\n'
            f'\t\t(layer "{layer}")\n\t\t(uuid "{uuid.uuid4()}")\n\t)\n')

h = SIZE / 2 + 0.25
name = f"Logo_Mechardo_{SIZE:g}mm"
out = f'''(footprint "{name}"
\t(version 20250114)
\t(generator "gen_logo.py")
\t(layer "F.Cu")
\t(descr "Mechardo Labs mark from mechardo3d.xyz, ENIG copper with the m left under solder mask")
\t(tags "logo mechardo")
\t(property "Reference" "LOGO1" (at 0 {h + 1} 0) (layer "F.Fab") (hide yes) (uuid "{uuid.uuid4()}") (effects (font (size 1 1) (thickness 0.15))))
\t(property "Value" "{name}" (at 0 {h + 2} 0) (layer "F.Fab") (hide yes) (uuid "{uuid.uuid4()}") (effects (font (size 1 1) (thickness 0.15))))
\t(attr board_only exclude_from_pos_files exclude_from_bom)
{poly(outer, "F.Cu")}{poly(mask, "F.Mask")}\t(fp_rect (start {-h} {-h}) (end {h} {h}) (stroke (width 0.05) (type solid)) (fill no) (layer "F.CrtYd") (uuid "{uuid.uuid4()}"))
)
'''
open(OUT, "w", encoding="utf8", newline="\n").write(out)
print(f"wrote {OUT}: {len(outer)} outer, {len(letter)} letter points, {SIZE} mm")
