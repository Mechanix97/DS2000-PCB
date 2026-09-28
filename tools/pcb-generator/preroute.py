"""Hand-routes the nets the autorouter should not improvise, before fanout and Freerouting.

The core regulator: a copy of the RP2350A minimal design's layout (Raspberry Pi, RPI-RP2350A-MINIMAL
R4-S1, MIT), in coordinates relative to VREG_LX (pin 48). Our U3 sits the same way round as theirs,
so the offsets carry over unchanged. The copper pours of that layout are added after autorouting by
vreg_pours.py; the tracks here already make every connection on their own.

The crystal loop: XIN and XOUT leave the RP2350A's bottom edge straight down into a crystal turned
so its XIN pad is top-left and its output pad bottom-right, so the two nets never cross and neither
needs a via. Tracks are locked, which Freerouting treats as fixed.

Geometry follows gen_pcb.py's placement (U3, Y1 rot 270, R6 rot 90, C17 rot 180, C18 rot 90); the
script asserts every pad it connects is where it expects, so a placement change cannot silently
produce a wrong route.

Run with KiCad's python:  python.exe preroute.py board.kicad_pcb
"""
import sys
import pcbnew

PCB = sys.argv[1]
b = pcbnew.LoadBoard(PCB)
mm, tomm = pcbnew.FromMM, pcbnew.ToMM
pads = {(fp.GetReference(), p.GetNumber()): p for fp in b.GetFootprints() for p in fp.Pads()}

def at(ref, num):
    p = pads[(ref, num)].GetPosition()
    return (round(tomm(p.x), 3), round(tomm(p.y), 3))

def route(net, pts, width=0.2):
    n = b.FindNet(net)
    for a, c in zip(pts, pts[1:]):
        if a == c:
            continue
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(pcbnew.VECTOR2I(mm(a[0]), mm(a[1]))); t.SetEnd(pcbnew.VECTOR2I(mm(c[0]), mm(c[1])))
        t.SetWidth(mm(width)); t.SetLayer(pcbnew.F_Cu); t.SetNet(n); t.SetLocked(True)
        b.Add(t)

def net_of(ref, num):
    return pads[(ref, num)].GetNetname()

XIN, XOUT, XTAL = net_of("U3", "21"), net_of("U3", "22"), net_of("Y1", "3")
assert net_of("Y1", "1") == XIN and net_of("C17", "1") == XIN
assert net_of("R6", "2") == XOUT and net_of("R6", "1") == XTAL and net_of("C18", "1") == XTAL

pin21, pin22 = at("U3", "21"), at("U3", "22")
y1_xin, y1_out = at("Y1", "1"), at("Y1", "3")
c17, r6_in, r6_out, c18 = at("C17", "1"), at("R6", "2"), at("R6", "1"), at("C18", "1")
# the crystal must sit where this layout assumes: XIN pad up-left of its output pad, both left of XOUT
assert y1_xin[0] < y1_out[0] < pin22[0] and y1_xin[1] < y1_out[1], (y1_xin, y1_out, pin22)

ROW = 89.6                                   # the XIN run, clear of the pin row and of C8's pad
route(XIN, [pin21, (pin21[0], ROW), (y1_xin[0], ROW), y1_xin])
route(XIN, [y1_xin, (c17[0], y1_xin[1]), c17])                       # load cap beside the pad
route(XOUT, [pin22, (pin22[0], r6_in[1]), r6_in])                     # straight down into R6
route(XTAL, [r6_out, (r6_out[0], y1_out[1]), y1_out])                 # R6 down, then left into Y1
route(XTAL, [(r6_out[0], y1_out[1]), (c18[0], y1_out[1]), c18])       # load cap beside R6
# IOVDD pin 20 sits beside XIN, so it cannot drop to a via: it runs left under the NC pins 16-19,
# above the XIN run, to its decoupling cap C8
pin20, c8 = at("U3", "20"), at("C8", "1")
assert net_of("U3", "20") == "+3V3" == net_of("C8", "1") and c8[0] < pin20[0]
route("+3V3", [pin20, (pin20[0], 88.95), (c8[0], 88.95), c8])

# ---------------------------------------------------------------- core regulator (RP2350A minimal design)
O = at("U3", "48")
def rel(dx, dy):
    return (round(O[0] + dx, 3), round(O[1] + dy, 3))
def via(net, dx, dy, drill=0.3, dia=0.6):
    v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(mm(rel(dx, dy)[0]), mm(rel(dx, dy)[1])))
    v.SetDrill(mm(drill)); v.SetWidth(mm(dia)); v.SetNet(b.FindNet(net)); v.SetLocked(True); b.Add(v)
def rroute(net, pts, width):
    route(net, [rel(*p) for p in pts], width)

LX, AVDD, DM, DP = net_of("U3", "48"), net_of("U3", "46"), net_of("U3", "51"), net_of("U3", "52")
expect = {("U3", "46"): (0.8, 0), ("U3", "47"): (0.4, 0), ("U3", "49"): (-0.4, 0), ("U3", "50"): (-0.8, 0),
          ("C4", "1"): (-0.515, -1.16), ("C4", "2"): (0.515, -1.16), ("C3", "1"): (-0.515, -2.1), ("C3", "2"): (0.515, -2.1),
          ("L1", "1"): (-0.7, -3.75), ("L1", "2"): (0.7, -3.75), ("C5", "1"): (2.2, -2.08), ("C5", "2"): (2.2, -1.12),
          ("R5", "1"): (4.16, -2.08), ("R5", "2"): (3.14, -2.08), ("R4", "2"): (-2.1, -3.44), ("R3", "2"): (-3.1, -3.44),
          ("C16", "1"): (-4.1, -3.47), ("C16", "2"): (-4.1, -4.43)}
for (ref, num), (dx, dy) in expect.items():
    px, py = at(ref, num)
    assert abs(px - O[0] - dx) < 0.02 and abs(py - O[1] - dy) < 0.02, (ref, num, px - O[0], py - O[1])
assert net_of("L1", "1") == "+1V1" and net_of("L1", "2") == LX, "L1 pin 1 (polarity dot) must be +1V1"
assert net_of("C5", "1") == AVDD == net_of("R5", "2") and net_of("R5", "1") == "+3V3"

rroute(LX, [(0, 0), (0, -2.6), (0.7, -3.3), (0.7, -3.75)], 0.25)                 # between C4's and C3's pads
rroute("+1V1", [(-0.7, -3.75), (-0.7, -2.1), (-0.515, -2.1)], 0.4)                 # L1 dot -> output cap
rroute("+1V1", [(-0.515, -2.1), (-1.5, -2.1)], 0.4)
rroute("+1V1", [(-1.5, -2.35), (-1.5, -1.75)], 0.4)
via("+1V1", -1.5, -2.35); via("+1V1", -1.5, -1.75)                                # down to the DVDD pins
rroute("+1V1", [(-0.8, 0), (-0.825, -0.013), (-0.825, -0.675), (-1.075, -0.925), (-1.075, -1.675), (-0.9, -2.1)], 0.15)  # VREG_FB at the output cap
rroute("+3V3", [(-0.4, 0), (-0.4, -0.6), (-0.515, -0.85), (-0.515, -1.16)], 0.2)   # VREG_VIN -> input cap
rroute("GND", [(0.4, 0), (0.4, -0.5), (0.515, -0.7), (0.515, -1.16)], 0.2)         # VREG_PGND -> both caps' ground
rroute("GND", [(0.515, -1.16), (0.515, -2.1)], 0.3)
rroute("GND", [(0.515, -1.45), (1.1, -1.45)], 0.3); via("GND", 1.1, -1.45, 0.25)
rroute("GND", [(0.515, -2.05), (1.1, -2.05)], 0.3); via("GND", 1.1, -2.05, 0.25)
rroute(AVDD, [(0.8, 0), (0.8, -0.15), (1.64, -0.99), (1.64, -1.52), (2.2, -2.08), (3.14, -2.08)], 0.15)
rroute("GND", [(2.2, -1.12), (2.2, -0.75), (1.85, -0.4)], 0.4); via("GND", 1.85, -0.4, 0.25)
rroute("+3V3", [(4.16, -2.08), (4.8, -2.08)], 0.3); via("+3V3", 4.8, -2.08)               # R5 lies beside C5: J1's shell pin is above it
# +3V3 under the package, between the pin row and the exposed pad, joining VREG_VIN to USB_OTP_VDD
# and QSPI_IOVDD (53, 54) as the reference's pour does, with one via to the In2 plane
rroute("+3V3", [(-0.4, 0), (-0.4, 1.05)], 0.2); via("+3V3", -0.4, 1.05)
rroute("+3V3", [(-2.0, 0), (-2.0, 0.75)], 0.2); rroute("+3V3", [(-2.4, 0), (-2.4, 0.75), (-2.0, 0.75)], 0.2)
rroute("+3V3", [(-2.0, 0.75), (-2.0, 1.05), (-0.4, 1.05)], 0.2)
rroute("+3V3", [(-2.0, 0), (-2.0, -0.45), (-2.4, -0.85)], 0.15)
rroute("+3V3", [(-2.4, 0), (-2.4, -0.85), (-4.1, -2.55), (-4.1, -3.47)], 0.2)     # to C16
rroute("GND", [(-4.1, -4.43), (-4.1, -5.9)], 0.3); via("GND", -4.1, -5.9, 0.25)          # clear of J1's peg
# USB from the series resistors into pins 51/52, threading between the regulator and the QSPI fan
# (0.15 mm as in the reference: the pair squeezes past VREG_FB here for 3 mm)
rroute(DM, [(-1.2, 0), (-1.225, -0.013), (-1.225, -0.651), (-2.1, -1.526), (-2.1, -3.44)], 0.15)
rroute(DP, [(-1.6, 0), (-1.6, -0.55), (-3.1, -2.05), (-3.1, -3.44)], 0.15)

pcbnew.SaveBoard(PCB, b)
print("prerouted: core regulator (RP2350A minimal design), crystal loop (XIN, XOUT, output), IOVDD pin 20, locked")
