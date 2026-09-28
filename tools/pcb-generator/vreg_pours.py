"""Adds the core regulator's small copper pours from the RP2350A minimal design (Raspberry Pi,
RPI-RP2350A-MINIMAL R4-S1, MIT), after autorouting.

They are the reference's zones around pins 46-50, in coordinates relative to VREG_LX (pin 48), with
the same priorities relative to each other, above the board-wide F.Cu GND pour. preroute.py's tracks
already make the connections; the pours widen them the way the reference does: VREG_PGND tied solidly
to both caps' ground, a short wide VREG_LX, and the +1V1 node at L1's dot and the output cap.
The reference's pour under the package (+3V3 and +1V1 inside the pin ring) is not copied; preroute.py
runs a +3V3 track there instead.

Run with KiCad's python:  python.exe vreg_pours.py board.kicad_pcb
"""
import sys
import pcbnew

PCB = sys.argv[1]
b = pcbnew.LoadBoard(PCB)
mm, tomm = pcbnew.FromMM, pcbnew.ToMM
u3 = next(f for f in b.GetFootprints() if f.GetReference() == "U3")
lx = next(p for p in u3.Pads() if p.GetNumber() == "48")
ox, oy = tomm(lx.GetPosition().x), tomm(lx.GetPosition().y)

POURS = [   # (net, priority, min width, outline relative to pin 48)
    ("+3V3", 17, 0.15, [(-0.5, 0.4), (-0.5, -0.6), (-0.75, -0.85), (-0.75, -1.4), (-0.3, -1.4), (-0.3, 0.4)]),
    ("VREG_LX", 15, 0.15, [(-0.1, 0.3), (-0.1, -0.5), (-0.15, -0.55), (-0.15, -2.7), (0.35, -3.2), (0.35, -4.6),
                           (1.05, -4.6), (1.05, -2.9), (0.75, -2.6), (0.3, -2.6), (0.15, -2.45), (0.15, -0.55),
                           (0.1, -0.5), (0.1, 0.3)]),
    ("GND", 14, 0.15, [(0.3, 0.3), (0.3, -1.4), (0.45, -1.4), (0.45, -1.85), (0.3, -1.85), (0.3, -2.35), (1.1, -2.35),
                       (1.4, -2.05), (1.4, -1.3), (0.5, -0.4), (0.5, 0.3)]),
    ("+1V1", 16, 0.15, [(-0.35, -1.85), (-0.35, -4.6), (-1.05, -4.6), (-1.05, -2.75), (-0.75, -2.45), (-0.75, -2.3),
                        (-0.95, -2.3), (-1.3, -2.65), (-1.5, -2.65), (-1.8, -2.35), (-1.8, -1.75), (-1.5, -1.45),
                        (-1.0, -1.45), (-1.0, -1.65), (-0.45, -1.65), (-0.45, -1.85)]),
]
netname = {"VREG_LX": lx.GetNetname()}
n = 0
for net, prio, minw, pts in POURS:
    z = pcbnew.ZONE(b); z.SetLayer(pcbnew.F_Cu); z.SetNet(b.FindNet(netname.get(net, net)))
    ol = z.Outline(); ol.NewOutline()
    for dx, dy in pts:
        ol.Append(mm(ox + dx), mm(oy + dy))
    z.SetAssignedPriority(prio); z.SetLocalClearance(mm(0.15)); z.SetMinThickness(mm(minw))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL); z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    z.SetZoneName(f"VREG {net}"); b.Add(z); n += 1
pcbnew.SaveBoard(PCB, b)
print(f"vreg pours: {n} zones from the RP2350A minimal design")
