"""Writes DS2000.pretty/SW_Kailh_Choc_V1_1.00u.kicad_mod.

Geometry from Kailh's CPG1350 datasheet (CPG135001D02, "PCB hole drawing", seen from the copper
side) and identical to kiswitch's footprint of the same name (github.com/kiswitch/kiswitch, MIT):
3.4 mm centre hole, 1.9 mm posts at +-5.5 mm, pins at (0, -5.9) and (5, -3.8). In KiCad's top view
the LED window (5 x 3.15 mm) sits 4.7 mm south of the centre, opposite the pins; that is where
gen_pcb.py puts the SK6812MINI-E.

The courtyard follows the 13.8 mm lower housing, which is all that touches the board: the 15 mm
flange sits 2.2 mm up, so low parts (0402, the 0.8 mm crystal) may tuck under its edge.

The keycap outline (MBK, 17.5 x 16.5 mm) is drawn on Dwgs.User for spacing checks.
"""
import os, uuid

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "DS2000.pretty",
                   "SW_Kailh_Choc_V1_1.00u.kicad_mod")

def u():
    return f'(uuid "{uuid.uuid4()}")'

def rect(x0, y0, x1, y1, layer, w):
    return (f'\t(fp_rect (start {x0} {y0}) (end {x1} {y1}) (stroke (width {w}) (type solid)) (fill no) '
            f'(layer "{layer}") {u()})\n')

def pad(num, kind, x, y, size, drill, layers):
    return (f'\t(pad "{num}" {kind} circle (at {x} {y}) (size {size} {size}) (drill {drill}) '
            f'(layers {layers}) {u()})\n')

body = (
    rect(-7.5, -7.5, 7.5, 7.5, "F.Fab", 0.1)
    + rect(-7.6, -7.6, 7.6, 7.6, "F.SilkS", 0.12)
    + rect(-7.15, -7.15, 7.15, 7.15, "F.CrtYd", 0.05)           # lower housing + 0.25: the 15 mm flange is 2.2 mm up
    + rect(-8.75, -8.25, 8.75, 8.25, "Dwgs.User", 0.1)          # MBK keycap
    + rect(-2.5, 4.7 - 1.575, 2.5, 4.7 + 1.575, "Dwgs.User", 0.1)  # LED window in the switch
    + pad("1", "thru_hole", 0, -5.9, 2.2, 1.2, '"*.Cu" "*.Mask"')
    + pad("2", "thru_hole", 5, -3.8, 2.2, 1.2, '"*.Cu" "*.Mask"')
    + pad("", "np_thru_hole", 0, 0, 3.45, 3.45, '"*.Cu" "*.Mask"')
    + pad("", "np_thru_hole", -5.5, 0, 1.9, 1.9, '"*.Cu" "*.Mask"')
    + pad("", "np_thru_hole", 5.5, 0, 1.9, 1.9, '"*.Cu" "*.Mask"')
)
out = f'''(footprint "SW_Kailh_Choc_V1_1.00u"
\t(version 20250114)
\t(generator "gen_choc_v1.py")
\t(layer "F.Cu")
\t(descr "Kailh Choc V1 (CPG1350) low-profile keyswitch, 1u, soldered. Geometry per Kailh datasheet CPG135001D02 and kiswitch (MIT). LED window 4.7 mm south of centre")
\t(tags "Kailh Choc V1 CPG1350 keyswitch low profile")
\t(property "Reference" "REF**" (at 0 -9 0) (layer "F.SilkS") {u()} (effects (font (size 1 1) (thickness 0.15))))
\t(property "Value" "SW_Kailh_Choc_V1_1.00u" (at 0 9.5 0) (layer "F.Fab") {u()} (effects (font (size 1 1) (thickness 0.15))))
\t(attr through_hole)
{body}\t(model "${{KIPRJMOD}}/3dmodels/DS2000.3dshapes/SW_Kailh_Choc_V1.step" (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))
)
'''
open(OUT, "w", encoding="utf8", newline="\n").write(out)
print("wrote", os.path.normpath(OUT))
