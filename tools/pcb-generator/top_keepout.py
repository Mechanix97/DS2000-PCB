"""Keeps the autorouter's tracks off the visible top face.

The board is the product's top face, so F.Cu tracks are only welcome in the component strip around
the RP2350A, where the parts already are. Before autorouting, "add" puts a track keepout on F.Cu
over the rest of the face (the keys, the logos, the sides); vias, pads and pours stay allowed, so
everything else routes on B.Cu underneath. "remove" takes it out again after routing.

Run with KiCad's python:  python.exe top_keepout.py board.kicad_pcb add|remove
"""
import sys
import pcbnew

PCB, MODE = sys.argv[1], sys.argv[2]
NAME = "top face keepout"
# F.Cu tracks allowed only inside this box: the strip from the flash and J3's resistors (left) to the
# 3.3 V regulator (right), from the back edge down to the crystal, clear of the switch courtyards
STRIP = (80.5, 71.0, 119.0, 93.6)

b = pcbnew.LoadBoard(PCB)
mm, tomm = pcbnew.FromMM, pcbnew.ToMM
for z in list(b.Zones()):
    if z.GetIsRuleArea() and z.GetZoneName().startswith(NAME):
        b.Remove(z)
if MODE == "add":
    e = b.GetBoardEdgesBoundingBox()
    x0, y0, x1, y1 = tomm(e.GetX()) - 1, tomm(e.GetY()) - 1, tomm(e.GetRight()) + 1, tomm(e.GetBottom()) + 1
    sx0, sy0, sx1, sy1 = STRIP
    # four rectangles around the strip
    for i, (a, c, d, f) in enumerate([(x0, y0, sx0, y1), (sx1, y0, x1, y1), (sx0, y0, sx1, sy0), (sx0, sy1, sx1, y1)]):
        if c >= f or a >= d:
            continue
        z = pcbnew.ZONE(b); z.SetIsRuleArea(True); z.SetLayer(pcbnew.F_Cu); z.SetZoneName(f"{NAME} {i}")
        z.SetDoNotAllowTracks(True); z.SetDoNotAllowVias(False); z.SetDoNotAllowPads(False)
        z.SetDoNotAllowZoneFills(False); z.SetDoNotAllowFootprints(False)
        ol = z.Outline(); ol.NewOutline()
        for px, py in [(a, c), (d, c), (d, f), (a, f)]:
            ol.Append(mm(px), mm(py))
        b.Add(z)
    print(f"top keepout: F.Cu tracks limited to x {sx0}..{sx1}, y {sy0}..{sy1}")
else:
    print("top keepout removed")
pcbnew.SaveBoard(PCB, b)
