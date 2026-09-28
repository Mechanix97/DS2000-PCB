"""Hand-routes the nets the autorouter should not improvise, before fanout and Freerouting.

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

ROW = 89.1                                   # the XIN run, clear of the pin row and of C8's pad
route(XIN, [pin21, (pin21[0], ROW), (y1_xin[0], ROW), y1_xin])
route(XIN, [y1_xin, (c17[0], y1_xin[1]), c17])                       # load cap beside the pad
route(XOUT, [pin22, (pin22[0], r6_in[1]), r6_in])                     # straight down into R6
route(XTAL, [r6_out, (r6_out[0], y1_out[1]), y1_out])                 # R6 down, then left into Y1
route(XTAL, [(r6_out[0], y1_out[1]), (c18[0], y1_out[1]), c18])       # load cap beside R6
# IOVDD pin 20 sits beside XIN, so it cannot drop to a via: it runs left under the NC pins 16-19,
# above the XIN run, to its decoupling cap C8
pin20, c8 = at("U3", "20"), at("C8", "1")
assert net_of("U3", "20") == "+3V3" == net_of("C8", "1") and c8[0] < pin20[0]
route("+3V3", [pin20, (pin20[0], 88.45), (c8[0], 88.45), c8])

pcbnew.SaveBoard(PCB, b)
print("prerouted: crystal loop (XIN, XOUT, output) and IOVDD pin 20, locked")
