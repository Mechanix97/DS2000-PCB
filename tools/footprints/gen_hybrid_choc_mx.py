"""Writes DS2000.pretty/SW_Hybrid_Choc_V1_MX_1.00u.kicad_mod.

The Choc V1 footprint of gen_choc_v1.py plus the holes of a 3-pin (plate-mount) MX switch on the
same centre, so either switch can be soldered: Choc V1 for the product, MX for prototypes.

- Choc V1: pins at (0, -5.9) and (5, -3.8), 1.9 mm posts at +-5.5 mm, as in gen_choc_v1.py.
- MX: pins at (2.54, -5.08) and (-3.81, -2.54), 1.5 mm drill, as KiCad's SW_Cherry_MX_1.00u_PCB
  moved to its centre post. Both switches have their pins north of the centre and their LED window
  south of it (Choc 4.7 mm, MX 5.08 mm), so the LED under the key serves both.
- One centre hole of 4 mm for the MX post; the 3.45 mm Choc post sits in it and its side posts
  locate it.
- Pads with the same number are the same contact: MX pin 1 (pad 2 mm, to keep 0.55 mm from both
  Choc pins) joins Choc pin 1 with a short track on the board; MX pin 2 is the other contact.

Every hole stays under the 13.8 mm Choc housing and the 14 mm MX housing, so nothing extra shows on
the face. The courtyard is the Choc one, which also covers the MX housing.
"""
import os, uuid

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "DS2000.pretty",
                   "SW_Hybrid_Choc_V1_MX_1.00u.kicad_mod")

def u():
    return f'(uuid "{uuid.uuid4()}")'

def rect(x0, y0, x1, y1, layer, w):
    return (f'\t(fp_rect (start {x0} {y0}) (end {x1} {y1}) (stroke (width {w}) (type solid)) (fill no) '
            f'(layer "{layer}") {u()})\n')

def pad(num, kind, x, y, size, drill, layers):
    return (f'\t(pad "{num}" {kind} circle (at {x} {y}) (size {size} {size}) (drill {drill}) '
            f'(layers {layers}) {u()})\n')

CU = '"*.Cu" "*.Mask"'
body = (
    rect(-7.5, -7.5, 7.5, 7.5, "F.Fab", 0.1)
    + rect(-7.0, -7.0, 7.0, 7.0, "F.Fab", 0.1)                 # MX lower housing
    + rect(-7.25, -7.25, 7.25, 7.25, "F.SilkS", 0.12)
    + rect(-7.15, -7.15, 7.15, 7.15, "F.CrtYd", 0.05)
    + rect(-8.75, -8.25, 8.75, 8.25, "Dwgs.User", 0.1)          # MBK keycap
    + rect(-2.5, 4.7 - 1.575, 2.5, 4.7 + 1.575, "Dwgs.User", 0.1)  # Choc LED window
    # Choc V1
    + pad("1", "thru_hole", 0, -5.9, 2.2, 1.2, CU)
    + pad("2", "thru_hole", 5, -3.8, 2.2, 1.2, CU)
    + pad("", "np_thru_hole", -5.5, 0, 1.9, 1.9, CU)
    + pad("", "np_thru_hole", 5.5, 0, 1.9, 1.9, CU)
    # MX, 3-pin
    + pad("1", "thru_hole", 2.54, -5.08, 2.0, 1.5, CU)
    + pad("2", "thru_hole", -3.81, -2.54, 2.2, 1.5, CU)
    # shared centre post
    + pad("", "np_thru_hole", 0, 0, 4.0, 4.0, CU)
)
out = f'''(footprint "SW_Hybrid_Choc_V1_MX_1.00u"
\t(version 20250114)
\t(generator "gen_hybrid_choc_mx.py")
\t(layer "F.Cu")
\t(descr "Kailh Choc V1 (CPG1350) or 3-pin MX keyswitch, 1u, soldered. Choc geometry per Kailh CPG135001D02, MX per KiCad SW_Cherry_MX_1.00u_PCB; shared 4 mm centre hole. LED window south of centre for both")
\t(tags "Kailh Choc V1 CPG1350 Cherry MX hybrid keyswitch")
\t(property "Reference" "REF**" (at 0 -9 0) (layer "F.SilkS") {u()} (effects (font (size 1 1) (thickness 0.15))))
\t(property "Value" "SW_Hybrid_Choc_V1_MX_1.00u" (at 0 9.5 0) (layer "F.Fab") {u()} (effects (font (size 1 1) (thickness 0.15))))
\t(attr through_hole)
{body}\t(model "${{KIPRJMOD}}/3dmodels/DS2000.3dshapes/SW_Kailh_Choc_V1.step" (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))
)
'''
open(OUT, "w", encoding="utf8", newline="\n").write(out)
print("wrote", os.path.normpath(OUT))
