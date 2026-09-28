"""Builds the DS-2000 rev A board skeleton with KiCad's pcbnew API.

Footprints, values, nets and the symbol links come from the schematic's netlist export, so the board
is in parity with the schematic. Mechanical parts (outline, holes, keys, LEDs, USB-C) are placed
exactly; the rest get a starting position in the component strip behind the keys, grouped by
function. Routing is left to the designer.

Run with KiCad's python:  python.exe gen_pcb.py <netlist.net> <out.kicad_pcb>
"""
import math, re, sys
import pcbnew

NET, OUT = sys.argv[1], sys.argv[2]
FPDIR = "C:/Program Files/KiCad/10.0/share/kicad/footprints"
mm = pcbnew.FromMM

# ---------------------------------------------------------------- netlist
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
from kisexp import parse, find, first
root = parse(open(NET, encoding="utf8").read())
comps = {}
for c in find(first(root, "components"), "comp"):
    props = {first(p, "name")[1]: (first(p, "value") or [None, ""])[1] for p in find(c, "property")}
    comps[first(c, "ref")[1]] = dict(
        value=first(c, "value")[1], fp=first(c, "footprint")[1], uuid=first(c, "tstamps")[1],
        sheet=props.get("Sheetname", ""), dnp="dnp" in props, nobom="exclude_from_bom" in props,
        fields={first(f_, "name")[1]: next((x for x in f_[1:] if not isinstance(x, list)), "")
                for f_ in find(first(c, "fields") or [], "field")
                if first(f_, "name")[1] not in ("Footprint", "Datasheet", "Description")})
pad_net = {}
netnames = []
for n in find(first(root, "nets"), "net"):
    name = first(n, "name")[1]
    netnames.append(name)
    for node in find(n, "node"):
        pad_net[(first(node, "ref")[1], first(node, "pin")[1])] = name

# ---------------------------------------------------------------- geometry
# Board: x 64..136, y 67..117 (y grows towards the user). Keys centred on y = 100.
X0, X1, Y0, Y1, RAD = 64.0, 136.0, 67.0, 117.0, 3.0
KEY_Y, PITCH = 100.0, 19.05
KEYS = {"SW1": 100 - PITCH, "SW2": 100.0, "SW3": 100 + PITCH}
LED_UNDER = {"D1": "SW1", "D2": "SW2"}
MX_CENTER_FROM_ORIGIN = (-2.54, 5.08)     # SW_Cherry_MX_1.00u_PCB: origin is pin 1
LED_FROM_CENTER = (0.0, 5.08)             # MX LED window, opposite the switch pins
HOLE = 4.0                                # hole centre from each edge

# ref: (x, y, rotation_deg, side)   side "F" or "B"
P = {
    # mechanical
    "H1": (X0 + HOLE, Y0 + HOLE, 0, "F"), "H2": (X1 - HOLE, Y0 + HOLE, 0, "F"),
    "H3": (X0 + HOLE, Y1 - HOLE, 0, "F"), "H4": (X1 - HOLE, Y1 - HOLE, 0, "F"),
    "J1": (100.0, Y0 + 3.65, 180, "B"),          # underneath: plug and cable sit low, face flush with the back edge
    "J3": (76.0, 70.0, 90, "F"),                 # USB wire holes, along the back edge
    "J2": (124.0, 70.5, 180, "F"),               # SWD, back edge, right
    # USB input
    "F1": (89.5, 70.5, 0, "F"), "R1": (93.5, 73.5, 90, "F"), "R2": (106.5, 73.5, 90, "F"),
    "U1": (100.0, 77.8, 0, "F"), "R4": (97.3, 77.8, 90, "F"), "R3": (102.7, 77.8, 90, "F"),
    # 3.3 V regulator
    "C1": (109.5, 73.5, 90, "F"), "U2": (113.0, 73.5, 0, "F"), "C2": (116.5, 73.5, 90, "F"),
    # RP2350A and its core regulator (to be laid out as in the RP2350 guide)
    "U3": (100.0, 84.0, 0, "F"),
    "L1": (107.0, 78.2, 0, "F"), "C3": (110.0, 78.2, 90, "F"), "C4": (107.0, 75.9, 0, "F"),
    "R5": (112.5, 78.2, 90, "F"), "C5": (114.0, 78.2, 90, "F"),
    "C6": (94.3, 81.7, 90, "F"), "C12": (94.3, 83.7, 90, "F"), "C7": (94.3, 85.7, 90, "F"),
    "C11": (105.7, 81.2, 90, "F"), "C14": (105.7, 83.6, 90, "F"), "C10": (107.4, 84.0, 90, "F"),
    "C15": (107.4, 81.4, 90, "F"), "C16": (95.6, 78.6, 90, "F"),
    "C8": (98.6, 89.7, 0, "F"), "C13": (100.6, 89.7, 0, "F"), "C9": (103.3, 89.7, 0, "F"),
    # flash and BOOTSEL
    "U4": (84.0, 79.0, 0, "F"), "C19": (84.0, 74.5, 0, "F"), "JP1": (80.0, 74.5, 0, "F"),
    "R7": (90.5, 77.0, 90, "F"), "R8": (90.5, 79.8, 90, "F"),
    # crystal
    "Y1": (95.0, 91.5, 0, "F"), "R6": (98.8, 92.2, 0, "F"), "C17": (91.8, 90.7, 90, "F"), "C18": (91.8, 93.2, 90, "F"),
    # reset
    "R9": (106.5, 89.7, 0, "F"), "JP2": (110.0, 90.0, 0, "F"),
    # LED data
    "U5": (90.5, 86.5, 0, "F"), "C20": (90.5, 83.3, 0, "F"), "R10": (87.5, 86.5, 90, "F"),
}
for ref, cx in KEYS.items():
    P[ref] = (cx - MX_CENTER_FROM_ORIGIN[0], KEY_Y - MX_CENTER_FROM_ORIGIN[1], 0, "F")
for led, sw in LED_UNDER.items():
    cx = KEYS[sw]
    P[led] = (cx + LED_FROM_CENTER[0], KEY_Y + LED_FROM_CENTER[1], 0, "B")
    P["C21" if led == "D1" else "C22"] = (cx, KEY_Y + 8.2, 0, "B")

missing = set(comps) - set(P)
extra = set(P) - set(comps)
if missing or extra:
    sys.exit(f"placement table mismatch: missing {sorted(missing)} extra {sorted(extra)}")

# ---------------------------------------------------------------- board
print("creating board", flush=True)
board = pcbnew.NewBoard(OUT)
print("board ok", flush=True)
board.SetCopperLayerCount(4)
ds = board.GetDesignSettings()
ds.SetBoardThickness(mm(1.6))
# JLCPCB 4-layer capabilities, with some margin
ds.m_MinClearance = mm(0.1)
ds.m_TrackMinWidth = mm(0.1)
ds.m_ViasMinSize = mm(0.4)
ds.m_MinThroughDrill = mm(0.2)
ds.m_HoleClearance = mm(0.2)
ds.m_HoleToHoleMin = mm(0.25)
ds.m_CopperEdgeClearance = mm(0.3)   # the reverse-mount LED cut-out sits close to its pads
ns = ds.m_NetSettings
dflt = ns.GetDefaultNetclass()
dflt.SetTrackWidth(mm(0.2)); dflt.SetClearance(mm(0.15)); dflt.SetViaDiameter(mm(0.5)); dflt.SetViaDrill(mm(0.25))
for cname, width, pattern in [("Power", 0.4, ["GND", "+5V", "+3V3", "+1V1", "VBUS", "VREG_LX"]),
                              ("USB", 0.2, ["USB_*"])]:
    nc = pcbnew.NETCLASS(cname)
    nc.SetTrackWidth(mm(width)); nc.SetClearance(mm(0.15)); nc.SetViaDiameter(mm(0.6)); nc.SetViaDrill(mm(0.3))
    if cname == "USB":
        nc.SetDiffPairWidth(mm(0.2)); nc.SetDiffPairGap(mm(0.2))
    ns.SetNetclass(cname, nc)
    for pat in pattern:
        ns.SetNetclassPatternAssignment(pat, cname)

nets = {}
for name in netnames:
    ni = pcbnew.NETINFO_ITEM(board, name)
    board.Add(ni)
    nets[name] = ni

print("nets ok", flush=True)
for ref, c in comps.items():
    lib, name = c["fp"].split(":")
    fp = pcbnew.FootprintLoad(f"{FPDIR}/{lib}.pretty", name)
    if fp is None:
        sys.exit(f"cannot load {c['fp']}")
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    fp.SetReference(ref)
    fp.SetValue(c["value"])
    fp.SetPath(pcbnew.KIID_PATH("/" + c["uuid"]))
    fp.SetSheetname("/")
    fp.SetSheetfile("DS2000.kicad_sch")
    if c["dnp"]:
        fp.SetDNP(True)
    if c["nobom"]:
        fp.SetExcludedFromBOM(True)
    for fname, fval in c["fields"].items():
        fp.SetField(fname, fval)
        fld = fp.GetField(fname)
        fld.SetText(fval); fld.SetVisible(False)
    if ref == "J3":
        fp.Models().clear()          # bare holes: no header is fitted
    # KiCad's library has no STEP for these three; use the project's own simplified models
    own = {"J1": ["USB_C_Receptacle_HRO_TYPE-C-31-M-12"], "U3": ["QFN-60-1EP_7x7mm_P0.4mm"],
           "SW1": ["SW_Cherry_MX_1.00u_PCB", "Keycap_1u_MX"], "SW2": ["SW_Cherry_MX_1.00u_PCB", "Keycap_1u_MX"],
           "SW3": ["SW_Cherry_MX_1.00u_PCB", "Keycap_1u_MX"]}
    if ref in own:
        fp.Models().clear()
        for mname in own[ref]:
            m = pcbnew.FP_3DMODEL()
            m.m_Filename = "${KIPRJMOD}/3dmodels/DS2000.3dshapes/" + mname + ".step"
            m.m_Show = True
            fp.Models().push_back(m)
    if ref == "J1":
        # its GND pins are too narrow and close together for thermal spokes: join them solidly
        fp.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
    board.Add(fp)
    x, y, rot, side = P[ref]
    fp.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
    fp.SetOrientationDegrees(rot)
    if side == "B":
        fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    for pad in fp.Pads():
        net = pad_net.get((ref, pad.GetNumber()))
        if net:
            pad.SetNet(nets[net])

print("footprints ok", flush=True)
# ---------------------------------------------------------------- outline
def seg(a, b):
    sh = pcbnew.PCB_SHAPE(board); sh.SetShape(pcbnew.SHAPE_T_SEGMENT)
    sh.SetStart(pcbnew.VECTOR2I(mm(a[0]), mm(a[1]))); sh.SetEnd(pcbnew.VECTOR2I(mm(b[0]), mm(b[1])))
    sh.SetLayer(pcbnew.Edge_Cuts); sh.SetWidth(mm(0.1)); board.Add(sh)
def arc(center, start, angle):
    sh = pcbnew.PCB_SHAPE(board); sh.SetShape(pcbnew.SHAPE_T_ARC)
    sh.SetCenter(pcbnew.VECTOR2I(mm(center[0]), mm(center[1])))
    sh.SetStart(pcbnew.VECTOR2I(mm(start[0]), mm(start[1])))
    sh.SetArcAngleAndEnd(pcbnew.EDA_ANGLE(angle, pcbnew.DEGREES_T))
    sh.SetLayer(pcbnew.Edge_Cuts); sh.SetWidth(mm(0.1)); board.Add(sh)
seg((X0 + RAD, Y0), (X1 - RAD, Y0)); seg((X1, Y0 + RAD), (X1, Y1 - RAD))
seg((X1 - RAD, Y1), (X0 + RAD, Y1)); seg((X0, Y1 - RAD), (X0, Y0 + RAD))
arc((X1 - RAD, Y0 + RAD), (X1 - RAD, Y0), 90)
arc((X1 - RAD, Y1 - RAD), (X1, Y1 - RAD), 90)
arc((X0 + RAD, Y1 - RAD), (X0 + RAD, Y1), 90)
arc((X0 + RAD, Y0 + RAD), (X0, Y0 + RAD), 90)

# ---------------------------------------------------------------- planes
def zone(layer, netname, prio=0):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNet(nets[netname])
    z.SetAssignedPriority(prio)
    ol = z.Outline()
    ol.NewOutline()
    inset, r = 0.5, RAD - 0.5
    for cx, cy, a0 in [(X1 - RAD, Y0 + RAD, -90), (X1 - RAD, Y1 - RAD, 0), (X0 + RAD, Y1 - RAD, 90), (X0 + RAD, Y0 + RAD, 180)]:
        for k in range(7):
            a = math.radians(a0 + k * 15)
            ol.Append(mm(cx + r * math.cos(a)), mm(cy + r * math.sin(a)))
    z.SetLocalClearance(mm(0.3))
    z.SetMinThickness(mm(0.2))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    board.Add(z)
zone(pcbnew.In1_Cu, "GND")
zone(pcbnew.In2_Cu, "+3V3")
zone(pcbnew.B_Cu, "GND")

# ---------------------------------------------------------------- key legends (silkscreen)
def text(s_, x, y, size=1.2, layer=pcbnew.F_SilkS):
    t = pcbnew.PCB_TEXT(board); t.SetText(s_); t.SetLayer(layer)
    t.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
    t.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size))); t.SetTextThickness(mm(size * 0.15))
    board.Add(t)
for ref, label in [("SW1", "MUTE"), ("SW2", "DEAFEN"), ("SW3", "DISCONNECT")]:
    text(label, KEYS[ref], Y1 - 3.0)
text("DS-2000", 121.0, 84.0, 1.5)
text("rev A", 121.0, 86.5, 1.0)

print("filling", flush=True)
# Zones are left unfilled: press B in KiCad, or run DRC with --refill-zones.
pcbnew.SaveBoard(OUT, board)
print(f"saved {OUT}: {len(comps)} footprints, {len(netnames)} nets")

# Stackup: JLCPCB JLC04161H-7628 (4 layers, 1.6 mm), black mask, white silk, ENIG. The pcbnew
# Python API does not expose the stackup list, so it is written into the saved file.
STACKUP = '''
		(stackup
			(layer "F.SilkS" (type "Top Silk Screen") (color "White"))
			(layer "F.Paste" (type "Top Solder Paste"))
			(layer "F.Mask" (type "Top Solder Mask") (color "Black") (thickness 0.01))
			(layer "F.Cu" (type "copper") (thickness 0.035))
			(layer "dielectric 1" (type "prepreg") (thickness 0.2104) (material "7628") (epsilon_r 4.4) (loss_tangent 0.02))
			(layer "In1.Cu" (type "copper") (thickness 0.0152))
			(layer "dielectric 2" (type "core") (thickness 1.065) (material "FR4") (epsilon_r 4.6) (loss_tangent 0.02))
			(layer "In2.Cu" (type "copper") (thickness 0.0152))
			(layer "dielectric 3" (type "prepreg") (thickness 0.2104) (material "7628") (epsilon_r 4.4) (loss_tangent 0.02))
			(layer "B.Cu" (type "copper") (thickness 0.035))
			(layer "B.Mask" (type "Bottom Solder Mask") (color "Black") (thickness 0.01))
			(layer "B.Paste" (type "Bottom Solder Paste"))
			(layer "B.SilkS" (type "Bottom Silk Screen") (color "White"))
			(copper_finish "ENIG")
			(dielectric_constraints no)
		)'''
txt = open(OUT, encoding="utf8").read()
assert "(stackup" not in txt and "\t(setup" in txt
txt = txt.replace("\t(setup", "\t(setup" + STACKUP, 1)
open(OUT, "w", encoding="utf8", newline="\n").write(txt)
print("stackup written")
