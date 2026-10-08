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

# ---------------------------------------------------------------- Kailh Choc V1 (CPG1350), soldered
# Footprint origin is the switch centre. Heights from the CPG1350 datasheet: 2.2 mm lower housing
# (plate side), 15 x 15 flange, housing top at 5.0 mm, stem to 8.0 mm, 3 mm travel. Pins at
# footprint (0, -5.9) and (5, -3.8) = model (0, 5.9) and (5, 3.8); LED window 4.7 mm south = model -y.
def choc_v1():
    lower = colored(Pos(0, 0, 1.1) * Box(13.8, 13.8, 2.2), BLACK)
    flange = colored(Pos(0, 0, 2.6) * Box(15.0, 15.0, 0.8), BLACK)
    upper = loft([Plane.XY.offset(3.0) * Rectangle(14.5, 14.5), Plane.XY.offset(5.0) * Rectangle(12.0, 12.0)])
    upper = upper - Pos(0, -4.7, 4.0) * Box(5.0, 3.15, 2.2)            # LED window
    upper = colored(upper, GREY)
    stem = colored(Pos(-2.85, 0, 6.5) * Box(1.2, 3.0, 3.0) + Pos(2.85, 0, 6.5) * Box(1.2, 3.0, 3.0), RED)
    posts = [colored(Pos(x, 0, -1.2) * Cylinder(0.9, 2.4), BLACK) for x in (-5.5, 5.5)]
    posts.append(colored(Pos(0, 0, -1.4) * Cylinder(1.6, 2.8), BLACK))
    pins = [colored(Pos(x, y, -1.5) * Cylinder(0.5, 3.0), SILVER) for x, y in [(0, 5.9), (5, 3.8)]]
    return Compound(children=[lower, flange, upper, stem] + posts + pins)

def keycap_mbk():
    """MBK-style low-profile cap: 17.5 x 16.5 mm, 2.2 mm thick with a shallow spherical dish,
    sitting on the stem (underside at 6.5 mm, top ~8.7 mm above the board)."""
    z0, hgt = 6.5, 2.2
    cap = loft([Plane.XY.offset(z0) * RectangleRounded(17.5, 16.5, 1.2),
                Plane.XY.offset(z0 + hgt) * RectangleRounded(16.7, 15.7, 1.6)])
    from build123d import Sphere
    cap = cap - Pos(0, 0, z0 + hgt + 60.0 - 0.35) * Sphere(60.0)
    return Compound(children=[colored(cap, KEYCAP)])

# ---------------------------------------------------------------- WS2812B-2020 (KiCad has no model)
def ws2812b_2020():
    # Worldsemi WS2812B-2020-V6: 2.2 x 2.0 mm base 0.28 mm thick, lens to 0.84 mm, pads at the corners
    base = colored(Pos(0, 0, 0.14) * Box(2.2, 2.0, 0.28), WHITE)
    lens = colored(Pos(0, 0, 0.28 + 0.28) * Box(1.5, 2.0, 0.56), (0.97, 0.97, 0.92))
    parts = [base, lens]
    for x in (-0.915, 0.915):
        for y in (-0.55, 0.55):
            parts.append(colored(Pos(x, y, 0.05) * Box(0.4, 0.5, 0.1), SILVER))
    # pin 1 (DOUT) is footprint (-0.915, -0.55): model (-x, +y)
    parts.append(colored(Pos(-0.45, 0.6, 0.84) * Box(0.3, 0.3, 0.02), GREY))
    return Compound(children=parts)

if __name__ == "__main__":
    for name, fn in [("QFN-60-1EP_7x7mm_P0.4mm", qfn60), ("USB_C_Receptacle_HRO_TYPE-C-31-M-12", usb_c),
                     ("SW_Cherry_MX_1.00u_PCB", mx_switch), ("Keycap_1u_MX", keycap),
                     ("SW_Kailh_Choc_V1", choc_v1), ("Keycap_1u_MBK", keycap_mbk),
                     ("LED_WS2812B-2020", ws2812b_2020)]:
        shape = fn()
        bb = shape.bounding_box()
        export_step(shape, f"{OUT}/{name}.step")
        print(f"{name}: x {bb.min.X:.2f}..{bb.max.X:.2f} y {bb.min.Y:.2f}..{bb.max.Y:.2f} z {bb.min.Z:.2f}..{bb.max.Z:.2f}")
