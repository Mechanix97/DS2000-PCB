"""Turns a logo footprint's exposed copper into a pad, so the board can tie it to GND.

The board is the product's top face and the logos' ENIG copper is touchable. As plain footprint
graphics it has no net and floats; as pad "1" (custom shape, copper only, the mask openings stay the
footprint's own F.Mask polygons) the board gives it GND and the F.Cu pour joins it solidly. The pad's
anchor sits at the point of the shape farthest from its edges, so it adds no copper of its own.

Used by gen_logo.py and gen_ds2000_logo.py, and runnable on a footprint file (it is idempotent):
    python tools/logo/copper_pad.py DS2000.pretty/Logo_Mechardo_5mm.kicad_mod ...
"""
import re, sys, uuid

POLY = re.compile(r'\t\(fp_poly\n\t\t\(pts ([^\n]*)\)\n\t\t\(stroke [^\n]*\n\t\t\(fill yes\)\n'
                  r'\t\t\(layer "F\.Cu"\)\n\t\t\(uuid "[^"]*"\)\n\t\)\n')


def inside(x, y, pts):
    c = False
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            c = not c
    return c


def edge_dist(x, y, pts):
    best = 1e9
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        dx, dy = x2 - x1, y2 - y1
        t = max(0, min(1, ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy or 1)))
        best = min(best, ((x - x1 - t * dx) ** 2 + (y - y1 - t * dy) ** 2) ** 0.5)
    return best


def anchor(pts):
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    best = None
    n = 60
    for i in range(1, n):
        for j in range(1, n):
            x = min(xs) + (max(xs) - min(xs)) * i / n
            y = min(ys) + (max(ys) - min(ys)) * j / n
            if inside(x, y, pts):
                d = edge_dist(x, y, pts)
                if best is None or d > best[0]:
                    best = (d, round(x, 4), round(y, 4))
    assert best and best[0] > 0.1, "no room for the pad anchor"
    return best[1], best[2]


def pad(m):
    pts = [(float(a), float(b)) for a, b in re.findall(r'\(xy ([-\d.]+) ([-\d.]+)\)', m.group(1))]
    ax, ay = anchor(pts)
    rel = " ".join(f"(xy {round(x - ax, 4)} {round(y - ay, 4)})" for x, y in pts)
    return (f'\t(pad "1" smd custom\n\t\t(at {ax} {ay})\n\t\t(size 0.2 0.2)\n\t\t(layers "F.Cu")\n'
            f'\t\t(zone_connect 2)\n\t\t(options\n\t\t\t(clearance outline)\n\t\t\t(anchor circle)\n\t\t)\n'
            f'\t\t(primitives\n\t\t\t(gr_poly\n\t\t\t\t(pts {rel})\n\t\t\t\t(width 0)\n\t\t\t\t(fill yes)\n\t\t\t)\n\t\t)\n'
            f'\t\t(uuid "{uuid.uuid4()}")\n\t)\n')


def copper_as_pad(text):
    return POLY.sub(pad, text)


if __name__ == "__main__":
    for f in sys.argv[1:]:
        s = open(f, encoding="utf8").read()
        t = copper_as_pad(s)
        open(f, "w", encoding="utf8", newline="\n").write(t)
        print(f, "->", t.count('(pad "1"'), "copper pad(s)")
