"""Simplified, dimensionally faithful STEP models for footprints KiCad ships without one.

KiCad model space: X right, Y towards the top of the 2D view (i.e. footprint -y), Z up from the
board surface, origin at the footprint origin. Colours are carried in the STEP.
"""
import sys
from build123d import (Box, Compound, Color, Cylinder, Location, Pos, Rot, export_step, loft,
                       Rectangle, RectangleRounded, Plane, extrude, SlotOverall, Align, Sketch)

OUT = sys.argv[1] if len(sys.argv) > 1 else "."

def colored(shape, rgb):
    shape.color = Color(*rgb)
    return shape

BLACK, GREY, SILVER, WHITE, RED, KEYCAP = (0.08, 0.08, 0.09), (0.35, 0.35, 0.37), (0.78, 0.78, 0.80), \
    (0.95, 0.95, 0.95), (0.80, 0.10, 0.10), (0.93, 0.93, 0.91)

# ---------------------------------------------------------------- QFN-60 7x7 (RP2350A)
def qfn60():
    body_h, n, pitch = 0.85, 15, 0.4
    body = colored(Pos(0, 0, body_h / 2) * Box(7.0, 7.0, body_h), BLACK)
    parts = [body]
    start = -(n - 1) / 2 * pitch
    for i in range(n):
        o = start + i * pitch
        for x, y, w, l in [(o, 3.5 - 0.2, 0.2, 0.4), (o, -3.5 + 0.2, 0.2, 0.4),
                           (3.5 - 0.2, o, 0.4, 0.2), (-3.5 + 0.2, o, 0.4, 0.2)]:
            parts.append(colored(Pos(x, y, 0.1) * Box(w + 0.02, l + 0.02, 0.2), SILVER))
    # pin 1 is top-left in the footprint: model (-x, +y)
    parts.append(colored(Pos(-2.8, 2.8, body_h) * Cylinder(0.3, 0.04), GREY))
    return Compound(children=parts)

# ---------------------------------------------------------------- USB-C, HRO TYPE-C-31-M-12
def usb_c():
    w, h, depth = 8.94, 3.26, 7.30
    front_y = -3.65                       # the opening is on footprint +y, model -y
    outer = Plane.XZ.offset(-front_y) * SlotOverall(w, h)
    shell = extrude(outer, amount=depth)  # XZ normal is -Y: extrude towards -y... fix below
    shell = Pos(0, 0, h / 2) * shell
    bb = shell.bounding_box()
    shell = Pos(0, front_y - bb.min.Y, 0) * shell
    inner = Plane.XZ.offset(-front_y) * SlotOverall(w - 0.6, h - 0.6)
    cavity = Pos(0, 0, h / 2) * extrude(inner, amount=6.4)
    cb = cavity.bounding_box()
    cavity = Pos(0, front_y - cb.min.Y - 0.01, 0) * cavity
    shell = colored(shell - cavity, SILVER)
    tongue = colored(Pos(0, front_y + 0.6 + 3.0, h / 2) * Box(6.6, 6.0, 0.7), BLACK)
    return Compound(children=[shell, tongue])

# ---------------------------------------------------------------- Cherry MX switch (PCB mount)
# Footprint origin is pin 1; the switch centre is at footprint (-2.54, +5.08) = model (-2.54, -5.08).
MX_C = (-2.54, -5.08)
def mx_switch():
    cx, cy = MX_C
    bottom = colored(Pos(cx, cy, 2.5) * Box(14.0, 14.0, 5.0), BLACK)
    lower = Pos(cx, cy, 5.0) * Rectangle(15.6, 15.6)
    upper = Pos(cx, cy, 11.6) * Rectangle(11.4, 11.4)
    top = colored(loft([Plane.XY.offset(5.0) * Pos(cx, cy) * Rectangle(15.6, 15.6),
                        Plane.XY.offset(11.6) * Pos(cx, cy) * Rectangle(11.4, 11.4)]), GREY)
    stem = colored(Pos(cx, cy, 13.4) * (Box(4.1, 1.17, 3.6) + Box(1.17, 4.1, 3.6)), RED)
    pins = [colored(Pos(x, y, -1.7) * Cylinder(0.75, 3.4), SILVER) for x, y in [(0, 0), (-6.35, -2.54)]]
    return Compound(children=[bottom, top, stem] + pins)

def keycap():
    cx, cy = MX_C
    z0, hgt = 12.2, 7.5
    cap = loft([Plane.XY.offset(z0) * Pos(cx, cy) * RectangleRounded(18.2, 18.2, 1.0),
                Plane.XY.offset(z0 + hgt) * Pos(cx, cy) * RectangleRounded(12.7, 12.7, 1.5)])
    dish = Pos(cx, cy, z0 + hgt + 14.2) * Cylinder(15.0, 30.0, rotation=(0, 0, 0))
    from build123d import Sphere
    cap = cap - (Pos(cx, cy, z0 + hgt + 20.0 - 0.6) * Sphere(20.0))
    return Compound(children=[colored(cap, KEYCAP)])

if __name__ == "__main__":
    for name, fn in [("QFN-60-1EP_7x7mm_P0.4mm", qfn60), ("USB_C_Receptacle_HRO_TYPE-C-31-M-12", usb_c),
                     ("SW_Cherry_MX_1.00u_PCB", mx_switch), ("Keycap_1u_MX", keycap)]:
        shape = fn()
        bb = shape.bounding_box()
        export_step(shape, f"{OUT}/{name}.step")
        print(f"{name}: x {bb.min.X:.2f}..{bb.max.X:.2f} y {bb.min.Y:.2f}..{bb.max.Y:.2f} z {bb.min.Z:.2f}..{bb.max.Z:.2f}")
