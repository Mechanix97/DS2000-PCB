"""Generates the DS-2000 rev A schematic (RP2350A) as a KiCad 10 .kicad_sch.

Each circuit stage sits in its own titled box and is wired internally. Signals that travel between
stages use a net label, and supplies use power symbols. Every part lists its intended connectivity
in `conn`; after drawing, any pin left untouched is finished automatically (power symbol, label or
no-connect), and the exported netlist is checked against `conn` by check_netlist.py.
"""
import os, sys, uuid as _uuid
from kisexp import lib_symbol, pins, dump, find, first, Sym

OUT = sys.argv[1]
PROJECT = "DS2000"
FPDIR = "C:/Program Files/KiCad/10.0/share/kicad/footprints"
ROOT = str(_uuid.uuid5(_uuid.NAMESPACE_URL, "ds2000/rev-a/root"))
_n = 0
def uid():
    global _n; _n += 1
    return str(_uuid.uuid5(_uuid.NAMESPACE_URL, f"ds2000/rev-a2/{_n}"))

POWER = {"GND": "power:GND", "+3V3": "power:+3V3", "+1V1": "power:+1V1", "+5V": "power:+5V", "VBUS": "power:VBUS"}
G = 2.54
def f(v): return Sym(f"{round(v, 4):g}")
def xy(x, y): return ["xy", f(x), f(y)]
def at(x, y, a=0): return ["at", f(x), f(y), Sym(str(a))]
def font(size=1.27): return ["font", ["size", f(size), f(size)]]

def xf(dx, dy, rot, mirror):
    dx, dy = {0: (dx, dy), 90: (dy, -dx), 180: (-dx, -dy), 270: (-dy, dx)}[rot]
    if mirror == "x": dy = -dy
    if mirror == "y": dx = -dx
    return dx, dy

items, lib_nodes, wires, points_used, texts = [], {}, [], set(), []
pwr_count = [0]
def use(lib_id):
    if lib_id not in lib_nodes: lib_nodes[lib_id] = lib_symbol(lib_id)

# ------------------------------------------------------------------------------------ parts
R0402, C0402, C0805 = "Resistor_SMD:R_0402_1005Metric", "Capacitor_SMD:C_0402_1005Metric", "Capacitor_SMD:C_0805_2012Metric"
PARTS = {}

class Part:
    def __init__(self, ref, lib, value, fp, pos, conn, rot=0, mirror=None, fields=None, dnp=False, text=None, props=None, bom=True):
        self.ref, self.lib, self.value, self.fp, self.rot, self.mirror = ref, lib, value, fp, rot, mirror
        self.x, self.y = pos
        self.conn, self.fields, self.dnp, self.text, self.props = conn, fields or {}, dnp, text, props or {}
        self.bom = bom
        self.pins = {}
        for num, name, ptype, px, py, ang in pins(lib):
            dx, dy = xf(px, -py, rot, mirror)
            import math
            bx, by = round(math.cos(math.radians(ang))), round(-math.sin(math.radians(ang)))
            bx, by = xf(bx, by, rot, mirror)
            self.pins.setdefault(num, (round(self.x + dx, 3), round(self.y + dy, 3), (-bx, -by)))
        PARTS[ref] = self
    def p(self, num): return self.pins[num][:2]
    def out(self, num): return self.pins[num][2]

def part(ref, lib, value, fp, pos, conn, **kw): return Part(ref, lib, value, fp, pos, conn, **kw)
def R(ref, value, a, b, pos, rot=0, **kw): return Part(ref, "Device:R_Small", value, R0402, pos, {"1": a, "2": b}, rot=rot, **kw)
def C(ref, value, a, b, pos, fp=C0402, rot=0, **kw): return Part(ref, "Device:C_Small", value, fp, pos, {"1": a, "2": b}, rot=rot, **kw)

# ------------------------------------------------------------------------------------ drawing
def W(*pts):
    for a, b in zip(pts, pts[1:]):
        assert a[0] == b[0] or a[1] == b[1], ("non-orthogonal wire", a, b)
        wires.append((tuple(map(lambda v: round(v, 3), a)), tuple(map(lambda v: round(v, 3), b))))

GND_ROT = {(0, 1): 0, (0, -1): 180, (1, 0): 90, (-1, 0): 270}
RAIL_ROT = {(0, -1): 0, (0, 1): 180, (1, 0): 270, (-1, 0): 90}
def PWR(net, pt, d=None):
    """Power symbol whose pin sits at pt, glyph pointing along d (default: GND down, rails up)."""
    use(POWER[net]); pwr_count[0] += 1
    d = d or ((0, 1) if net == "GND" else (0, -1))
    rot = (GND_ROT if net == "GND" else RAIL_ROT)[d]
    ref = f"#PWR{pwr_count[0]:03d}"
    x, y = pt
    vx, vy = d
    tx, ty = x + vx * (4.2 if net == "GND" else 3.6), y + vy * (4.2 if net == "GND" else 3.6)
    items.append(["symbol", ["lib_id", POWER[net]], at(x, y, rot), ["unit", Sym("1")], ["exclude_from_sim", Sym("no")],
                  ["in_bom", Sym("no")], ["on_board", Sym("yes")], ["dnp", Sym("no")], ["uuid", uid()],
                  ["property", "Reference", ref, at(x, y), ["hide", Sym("yes")], ["effects", font()]],
                  ["property", "Value", net, at(tx, ty)] + ([["hide", Sym("yes")]] if vx and net == "GND" else []) + [["effects", font()]],
                  ["property", "Footprint", "", at(x, y), ["hide", Sym("yes")], ["effects", font()]],
                  ["property", "Datasheet", "", at(x, y), ["hide", Sym("yes")], ["effects", font()]],
                  ["pin", "1", ["uuid", uid()]],
                  ["instances", ["project", PROJECT, ["path", "/" + ROOT, ["reference", ref], ["unit", Sym("1")]]]]])
    points_used.add((round(x, 3), round(y, 3)))

def FLAG(pt):
    use("power:PWR_FLAG"); pwr_count[0] += 1
    ref = f"#FLG{pwr_count[0]:03d}"
    x, y = pt
    points_used.add((round(x, 3), round(y, 3)))
    items.append(["symbol", ["lib_id", "power:PWR_FLAG"], at(x, y), ["unit", Sym("1")], ["exclude_from_sim", Sym("no")],
                  ["in_bom", Sym("no")], ["on_board", Sym("yes")], ["dnp", Sym("no")], ["uuid", uid()],
                  ["property", "Reference", ref, at(x, y - 5), ["hide", Sym("yes")], ["effects", font()]],
                  ["property", "Value", "PWR_FLAG", at(x, y - 4), ["hide", Sym("yes")], ["effects", font()]],
                  ["property", "Footprint", "", at(x, y), ["hide", Sym("yes")], ["effects", font()]],
                  ["property", "Datasheet", "", at(x, y), ["hide", Sym("yes")], ["effects", font()]],
                  ["pin", "1", ["uuid", uid()]],
                  ["instances", ["project", PROJECT, ["path", "/" + ROOT, ["reference", ref], ["unit", Sym("1")]]]]])

LABEL_ANG = {(1, 0): (0, "left"), (-1, 0): (180, "right"), (0, -1): (90, "left"), (0, 1): (270, "right")}
def LBL(net, pt, d):
    ang, just = LABEL_ANG[d]
    items.append(["label", net, at(pt[0], pt[1], ang), ["effects", font(), ["justify", Sym(just), Sym("bottom")]], ["uuid", uid()]])
    points_used.add((round(pt[0], 3), round(pt[1], 3)))

def NC(pt):
    items.append(["no_connect", at(*pt)[:3], ["uuid", uid()]])
    points_used.add((round(pt[0], 3), round(pt[1], 3)))

def stub(part_, num, net=None, length=G):
    """Short wire out of a pin, ending in a power symbol or a label."""
    net = net or part_.conn[num]
    x, y = part_.p(num); d = part_.out(num)
    e = (x + d[0] * length, y + d[1] * length)
    W((x, y), e)
    if net in POWER: PWR(net, e, d if net == "GND" or d != (0, 1) else d)
    else: LBL(net, e, d)

boxes = []
def BOX(x1, y1, x2, y2, title, title_at="top"):
    boxes.append(([(x1, y1), (x2, y1), (x2, y2), (x1, y2)], title, title_at))
def BOXPOLY(pts, title, title_at="top"):
    boxes.append((pts, title, title_at))

def TEXT(pt, s, size=1.27):
    texts.append((pt, s, size))

# ====================================================================================
# A. USB-C input, fuse and ESD
# ====================================================================================
BOX(15.24, 30.48, 157.48, 111.76, "USB-C input, fuse, ESD and wire pads")
J1 = part("J1", "Connector:USB_C_Receptacle_USB2.0_16P", "USB-C", "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12",
          (40.64, 76.2), {"A1": "GND", "A12": "GND", "B1": "GND", "B12": "GND", "SH": "GND",
                          "A4": "VBUS", "A9": "VBUS", "B4": "VBUS", "B9": "VBUS",
                          "A5": "CC1", "B5": "CC2", "A6": "USB_CONN_DP", "B6": "USB_CONN_DP",
                          "A7": "USB_CONN_DM", "B7": "USB_CONN_DM", "A8": None, "B8": None},
          fields={"MPN": "TYPE-C-31-M-12", "Manufacturer": "Korean Hroparts Elec"})
F1 = part("F1", "Device:Polyfuse_Small", "500mA hold", "Fuse:Fuse_1206_3216Metric", (71.12, 50.8),
          {"1": "VBUS", "2": "+5V"}, rot=90, fields={"MPN": "1206L050YR", "Manufacturer": "Littelfuse"})
W(J1.p("A4"), (60.96, 60.96), (60.96, 50.8), F1.p("1"))
FLAG((63.5, 50.8)); PWR("VBUS", (60.96, 50.8))
W(F1.p("2"), (86.36, 50.8)); FLAG((81.28, 50.8)); PWR("+5V", (86.36, 50.8))
R1 = R("R1", "5.1k", "GND", "CC1", (66.04, 63.5))
R2 = R("R2", "5.1k", "GND", "CC2", (76.2, 66.04))
W(J1.p("A5"), R1.p("2")); W(J1.p("B5"), R2.p("2"))
W(R1.p("1"), (66.04, 58.42)); PWR("GND", (66.04, 58.42), (0, -1))
W(R2.p("1"), (76.2, 60.96)); PWR("GND", (76.2, 60.96), (0, -1))
W(J1.p("A1"), (40.64, 101.6)); PWR("GND", (40.64, 101.6)); W(J1.p("SH"), J1.p("A1"))
U1 = part("U1", "Power_Protection:USBLC6-2SC6", "USBLC6-2SC6", "Package_TO_SOT_SMD:SOT-23-6", (99.06, 76.2),
          {"1": "USB_CONN_DM", "6": "USB_CONN_DM", "3": "USB_CONN_DP", "4": "USB_CONN_DP", "2": "GND", "5": "+5V"},
          fields={"MPN": "USBLC6-2SC6", "Manufacturer": "STMicroelectronics"},
          props={"Reference": (99.06, 88.9), "Value": (99.06, 91.44)})
W(J1.p("A7"), J1.p("B7")); W(J1.p("A6"), J1.p("B6"))
W(J1.p("A7"), (88.9, 73.66), (88.9, 76.2), U1.p("1"))
W(J1.p("B6"), (86.36, 81.28), (86.36, 78.74), U1.p("3"))
R4 = R("R4", "27", "USB_CONN_DM", "USB_DM", (127.0, 76.2), rot=90, fields={"Note": "Place close to U3"})
R3 = R("R3", "27", "USB_CONN_DP", "USB_DP", (137.16, 78.74), rot=90, fields={"Note": "Place close to U3"})
W(U1.p("6"), R4.p("1")); W(U1.p("4"), R3.p("1"))
# USBLC6 pins 1/6 and 3/4 are one line through the part: the two sides share a name
LBL("USB_CONN_DM", (63.5, 73.66), (1, 0)); LBL("USB_CONN_DP", (63.5, 81.28), (1, 0))
LBL("USB_CONN_DM", (106.68, 76.2), (1, 0)); LBL("USB_CONN_DP", (109.22, 78.74), (1, 0))
# Solder holes for a hard-wired USB cable, used instead of J1. Upstream of the fuse and the ESD
# so a soldered cable gets the same protection as the receptacle.
part("J3", "Connector_Generic:Conn_01x04", "USB wire", "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
     (127.0, 96.52), {"1": "VBUS", "2": "USB_CONN_DM", "3": "USB_CONN_DP", "4": "GND"}, bom=False,
     fields={"Note": "Bare holes: solder a USB cable here instead of fitting J1 (red, white, green, black)"},
     props={"Reference": (129.54, 95.25), "Value": (129.54, 97.79)})
TEXT((20.32, 110.49), "CC 5.1k: USB device (UFP). U1 at the connector, R3/R4 next to the RP2350. J3: optional soldered cable.")

# ====================================================================================
# B. 3.3 V regulator
# ====================================================================================
BOX(162.56, 30.48, 233.68, 88.9, "3.3 V regulator")
U2 = part("U2", "Regulator_Linear:AP2112K-3.3", "AP2112K-3.3", "Package_TO_SOT_SMD:SOT-23-5", (205.74, 58.42),
          {"1": "+5V", "3": "+5V", "2": "GND", "4": None, "5": "+3V3"},
          fields={"MPN": "AP2112K-3.3TRG1", "Manufacturer": "Diodes Inc"})
C1 = C("C1", "10u", "+5V", "GND", (187.96, 58.42), fp=C0805)
C2 = C("C2", "10u", "+3V3", "GND", (223.52, 58.42), fp=C0805)
W(U2.p("3"), U2.p("1")); W(U2.p("1"), (182.88, 55.88)); PWR("+5V", (182.88, 55.88))
W(U2.p("5"), (228.6, 55.88)); PWR("+3V3", (228.6, 55.88))
TEXT((165.1, 86.36), "EN tied to VIN: always on. 250 mV dropout.")

# ====================================================================================
# G. Reset
# ====================================================================================
BOX(238.76, 30.48, 287.02, 88.9, "Reset")
R9 = R("R9", "10k", "+3V3", "RUN", (264.16, 53.34))
SW5 = part("JP2", "Jumper:SolderJumper_2_Open", "RESET", "Jumper:SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm", (264.16, 60.96),
           {"1": "RUN", "2": "GND"}, rot=270, bom=False,
           fields={"Note": "Bridge briefly to reset"},
           props={"Reference": (267.97, 60.96), "Value": (267.97, 63.5)})
TEXT((241.3, 86.36), "JP2: bridge briefly to reset. R9 keeps RUN high.")
W((256.54, 55.88), R9.p("2")); LBL("RUN", (256.54, 55.88), (-1, 0))

# ====================================================================================
# J. Mounting holes
# ====================================================================================
BOX(292.1, 30.48, 368.3, 88.9, "Mounting holes (PCB corners, to GND)")
for i in range(4):
    part(f"H{i + 1}", "Mechanical:MountingHole_Pad", "M2", "MountingHole:MountingHole_2.2mm_M2_Pad_Via",
         (304.8 + i * 15.24, 53.34), {"1": "GND"})
FLAG((360.68, 55.88)); W((360.68, 55.88), (360.68, 58.42)); PWR("GND", (360.68, 58.42))

# ====================================================================================
# C. RP2350A supplies (wired straight into the MCU's top pins)
# ====================================================================================
BOX(147.32, 116.84, 210.82, 147.32, "RP2350A supplies")
MCU_CONN = {"1": "+3V3", "11": "+3V3", "20": "+3V3", "30": "+3V3", "38": "+3V3", "45": "+3V3",
            "6": "+1V1", "23": "+1V1", "39": "+1V1", "50": "+1V1",
            "44": "+3V3", "53": "+3V3", "54": "+3V3", "49": "+3V3",
            "46": "VREG_AVDD", "48": "VREG_LX", "47": "GND", "61": "GND",
            "21": "XIN", "22": "XOUT", "24": "SWCLK", "25": "SWDIO", "26": "RUN",
            "51": "USB_DM", "52": "USB_DP",
            "60": "QSPI_SS", "56": "QSPI_SCLK", "57": "QSPI_SD0", "59": "QSPI_SD1", "58": "QSPI_SD2", "55": "QSPI_SD3",
            "2": "KEY_MUTE", "3": "KEY_DEAFEN", "4": "KEY_DISCONNECT", "8": "LED_DIN_3V3"}
for p_ in pins("MCU_RaspberryPi:RP2350A"): MCU_CONN.setdefault(p_[0], None)
U3 = part("U3", "MCU_RaspberryPi:RP2350A", "RP2350A", "Package_DFN_QFN:QFN-60-1EP_7x7mm_P0.4mm_EP3.4x3.4mm_ThermalVias",
          (182.88, 195.58), MCU_CONN, fields={"MPN": "RP2350A", "Manufacturer": "Raspberry Pi"},
          props={"Reference": (201.93, 243.84), "Value": (201.93, 246.38)})
for n in ["53", "44", "54", "1", "49"]:
    W(U3.p(n), (U3.p(n)[0], 144.78))
W((U3.p("53")[0], 144.78), (U3.p("49")[0], 144.78)); PWR("+3V3", (175.26, 144.78))
L1 = part("L1", "Device:L_Small", "3.3u", "Inductor_SMD:L_Murata_DFE201610P", (190.5, 134.62),
          {"1": "VREG_LX", "2": "+1V1"}, rot=90,
          fields={"MPN": "AOTA-B201610S3R3-101-T", "Manufacturer": "Abracon",
                  "Note": "Polarity-marked; orientation and layout per RP2350 guide. Verify pads"})
W(U3.p("48"), L1.p("1"))
C3 = C("C3", "4.7u", "+1V1", "GND", (203.2, 142.24), fields={"Note": "VREG output cap"})
W(U3.p("50"), (U3.p("50")[0], 139.7)); W(U3.p("6"), (U3.p("6")[0], 139.7))
W((U3.p("50")[0], 139.7), C3.p("1"))
W(L1.p("2"), (193.04, 139.7)); W(L1.p("2"), (193.04, 129.54)); PWR("+1V1", (193.04, 129.54))
FLAG((200.66, 139.7))
R5 = R("R5", "33", "+3V3", "VREG_AVDD", (160.02, 129.54), rot=90)
C5 = C("C5", "4.7u", "VREG_AVDD", "GND", (170.18, 132.08))
W(U3.p("46"), (165.1, 129.54)); W(R5.p("2"), (165.1, 129.54), C5.p("1"))
W(R5.p("1"), (154.94, 129.54)); PWR("+3V3", (154.94, 129.54))
FLAG((167.64, 129.54))
W(U3.p("47"), (U3.p("47")[0], 243.84)); W(U3.p("61"), (U3.p("61")[0], 243.84))
W((U3.p("47")[0], 243.84), (U3.p("61")[0], 243.84)); PWR("GND", (U3.p("61")[0], 243.84))
TEXT((148.59, 121.92), "Core regulator: layout exactly as the RP2350 guide")

# ====================================================================================
# D. MCU
# ====================================================================================
BOX(152.4, 149.86, 210.82, 251.46, "RP2350A", title_at="bottom")

# ====================================================================================
# F. QSPI flash and BOOTSEL (flash mirrored so the six QSPI lines run straight)
# ====================================================================================
BOXPOLY([(66.04, 165.1), (149.86, 165.1), (149.86, 205.74), (107.95, 205.74), (107.95, 220.98), (66.04, 220.98)],
        "QSPI flash and BOOTSEL")
U4 = part("U4", "Memory_Flash:W25Q32JVSS", "W25Q32JVSS", "Package_SO:SOIC-8_5.3x5.3mm_P1.27mm", (99.06, 198.12),
          {"1": "QSPI_SS", "6": "QSPI_SCLK", "5": "QSPI_SD0", "2": "QSPI_SD1", "3": "QSPI_SD2", "7": "QSPI_SD3",
           "8": "+3V3", "4": "GND"}, mirror="y", fields={"MPN": "W25Q32JVSSIQ", "Manufacturer": "Winbond"},
          props={"Reference": (86.36, 208.28), "Value": (86.36, 210.82)})
for fp_, mp in [("1", "60"), ("6", "56"), ("5", "57"), ("2", "59"), ("3", "58"), ("7", "55")]:
    W(U4.p(fp_), U3.p(mp))
R7 = R("R7", "10k", "+3V3", "QSPI_SS", (132.08, 187.96), dnp=True, fields={"Note": "DNF, only for other flash parts"})
R8 = R("R8", "1k", "BOOTSEL", "QSPI_SS", (121.92, 187.96))
SW4 = part("JP1", "Jumper:SolderJumper_2_Open", "BOOTSEL", "Jumper:SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm", (114.3, 177.8),
           {"1": "GND", "2": "BOOTSEL"}, bom=False,
           fields={"Note": "Bridge with tweezers while plugging in USB (or pressing RESET) to enter USB boot"})
W(R8.p("1"), (121.92, 177.8), SW4.p("2"))
W(SW4.p("1"), (106.68, 177.8), (106.68, 180.34)); PWR("GND", (106.68, 180.34))
C19 = C("C19", "100n", "+3V3", "GND", (76.2, 195.58))
TEXT((68.58, 170.18), "JP1: bridge the pads while plugging in USB to enter USB boot.")

# ====================================================================================
# E. Crystal and SWD
# ====================================================================================
BOX(110.49, 209.55, 149.86, 241.3, "12 MHz crystal, SWD", title_at="bottom")
C17 = C("C17", "15p", "XIN", "GND", (114.3, 213.36))
Y1 = part("Y1", "Device:Crystal_GND24_Small", "12MHz", "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm", (124.46, 213.36),
          {"1": "XIN", "3": "XTAL_OUT", "2": "GND", "4": "GND"}, rot=270,
          fields={"MPN": "ABM8-272-T3", "Manufacturer": "Abracon"},
          props={"Reference": (127.0, 214.63), "Value": (127.0, 217.17)})
W(U3.p("21"), C17.p("1"))
W(Y1.p("2"), (119.38, 213.36), (119.38, 215.9)); PWR("GND", (119.38, 215.9))
R6 = R("R6", "1k", "XTAL_OUT", "XOUT", (147.32, 220.98), rot=90)
C18 = C("C18", "15p", "XTAL_OUT", "GND", (132.08, 223.52))
W(U3.p("22"), R6.p("2")); W(R6.p("1"), (124.46, 220.98), Y1.p("3"))
J2 = part("J2", "Connector_Generic:Conn_01x03", "SWD", "Connector_JST:JST_SH_SM03B-SRSS-TB_1x03-1MP_P1.00mm_Horizontal",
          (139.7, 228.6), {"1": "SWCLK", "2": "GND", "3": "SWDIO"}, mirror="y",
          fields={"MPN": "SM03B-SRSS-TB", "Manufacturer": "JST", "Note": "Raspberry Pi Debug Probe pinout"},
          props={"Reference": (137.16, 234.95), "Value": (137.16, 237.49)})
W(U3.p("24"), (154.94, 228.6), (154.94, 226.06), J2.p("1"))
W(U3.p("25"), J2.p("3"))
W(J2.p("2"), (147.32, 228.6)); PWR("GND", (147.32, 228.6), (1, 0))

# ====================================================================================
# H. Keys
# ====================================================================================
BOX(226.06, 114.3, 259.08, 151.13, "Keys")
rows = [124.46, 132.08, 139.7]
for i, (gp, net, name, turn) in enumerate([("2", "KEY_MUTE", "MUTE", 213.36), ("3", "KEY_DEAFEN", "DEAFEN", 218.44),
                                           ("4", "KEY_DISCONNECT", "DISCONNECT", 223.52)]):
    sw = part(f"SW{i + 1}", "Switch:SW_Push", name, "Button_Switch_Keyboard:SW_Cherry_MX_1.00u_PCB",
              (238.76, rows[i]), {"1": net, "2": "GND"})
    W(U3.p(gp), (turn, U3.p(gp)[1]), (turn, rows[i]), sw.p("1"))
    W(sw.p("2"), (248.92, rows[i]))
W((248.92, rows[0]), (248.92, rows[2] + G)); PWR("GND", (248.92, rows[2] + G))
TEXT((227.33, 149.86), "GP0-GP2, internal pull-ups")

# ====================================================================================
# I. Key LEDs
# ====================================================================================
BOX(213.36, 167.64, 322.58, 228.6, "Key LEDs: 3.3 V -> 5 V level shift, SK6812MINI-E")
U5 = part("U5", "74xGxx:74AHCT1G125", "74AHCT1G125", "Package_TO_SOT_SMD:SOT-353_SC-70-5", (238.76, 190.5),
          {"1": "GND", "2": "LED_DIN_3V3", "3": "GND", "4": "LED_DIN_5V", "5": "+5V"},
          fields={"MPN": "74AHCT1G125GW", "Manufacturer": "Nexperia"},
          props={"Reference": (243.84, 198.12), "Value": (243.84, 203.2)})
W(U3.p("8"), (210.82, U3.p("8")[1]), (210.82, 190.5), U5.p("2"))
W(U5.p("1"), (238.76, 177.8)); PWR("GND", (238.76, 177.8), (0, -1))
W(U5.p("5"), (233.68, 177.8), (228.6, 177.8)); PWR("+5V", (228.6, 177.8))
R10 = R("R10", "100", "LED_DIN_5V", "LED_DIN", (259.08, 190.5), rot=90, fields={"Note": "Damping, near D1"})
W(U5.p("4"), R10.p("1"))
C("C20", "100n", "+5V", "GND", (223.52, 215.9))
chain = ["LED_DIN", "LED_D1_D2", None]
leds = []
for i, name in enumerate(["MUTE", "DEAFEN"]):
    d = part(f"D{i + 1}", "LED:SK6812MINI-E", "SK6812MINI-E", "LED_SMD:LED_SK6812MINI-E_3.2x2.8mm_P1.5mm_ReverseMount",
             (276.86 + i * 27.94, 190.5), {"3": "+5V", "1": "GND", "2": chain[i], "4": chain[i + 1]},
             fields={"MPN": "SK6812MINI-E", "Manufacturer": "Opsco", "Note": f"Under the {name} key"})
    leds.append(d)
    C(f"C{21 + i}", "100n", "+5V", "GND", (276.86 + i * 27.94, 215.9))
W(R10.p("2"), leds[0].p("2")); W(leds[0].p("4"), leds[1].p("2"))
TEXT((214.63, 227.33), "D1 under mute, D2 under deafen (reverse-mounted). Disconnect key has no LED. One 100n per LED.")

# ====================================================================================
# Decoupling row
# ====================================================================================
BOX(66.04, 256.54, 299.72, 284.48, "Decoupling, placed at the pins")
dec = [("C4", "4.7u", "+3V3", "VREG_VIN")] + [(f"C{6 + i}", "100n", "+3V3", "IOVDD") for i in range(6)] + \
      [(f"C{12 + i}", "100n", "+1V1", "DVDD") for i in range(3)] + [("C15", "100n", "+3V3", "ADC_AVDD"),
                                                                    ("C16", "100n", "+3V3", "USB_OTP+QSPI_IOVDD")]
for i, (ref, val, net, what) in enumerate(dec):
    C(ref, val, net, "GND", (78.74 + i * 17.78, 270.51), fields={"Note": what})
TEXT((68.58, 283.21), "C4 VREG_VIN · C6-C11 IOVDD x6 · C12-C14 DVDD x3 · C15 ADC_AVDD · C16 USB_OTP_VDD + QSPI_IOVDD (shared, as in the reference)")

# ------------------------------------------------------------------------------------ finish
def on_segment(p, a, b):
    (x, y), (x1, y1), (x2, y2) = p, a, b
    if x1 == x2 == x: return min(y1, y2) - 1e-6 <= y <= max(y1, y2) + 1e-6
    if y1 == y2 == y: return min(x1, x2) - 1e-6 <= x <= max(x1, x2) + 1e-6
    return False

errors = []
for part_ in PARTS.values():
    fl, fn = part_.fp.split(":")
    if not os.path.exists(f"{FPDIR}/{fl}.pretty/{fn}.kicad_mod"): errors.append(f"{part_.ref}: footprint missing")
    if set(part_.conn) != set(part_.pins): errors.append(f"{part_.ref}: conn/pins mismatch {set(part_.pins) ^ set(part_.conn)}")
    for num, (x, y, d) in part_.pins.items():
        touched = any(on_segment((x, y), a, b) for a, b in wires) or (x, y) in points_used
        if touched:
            if part_.conn[num] is None: errors.append(f"{part_.ref}.{num} is NC but wired")
            continue
        if part_.conn[num] is None: NC((x, y))
        else: stub(part_, num)

for part_ in PARTS.values():
    use(part_.lib)
    node = ["symbol", ["lib_id", part_.lib], at(part_.x, part_.y, part_.rot)]
    if part_.mirror: node.append(["mirror", Sym(part_.mirror)])
    node += [["unit", Sym("1")], ["exclude_from_sim", Sym("no")], ["in_bom", Sym("yes" if part_.bom else "no")], ["on_board", Sym("yes")],
             ["dnp", Sym("yes" if part_.dnp else "no")], ["uuid", uid()]]
    small = part_.lib in ("Device:R_Small", "Device:C_Small", "Device:L_Small", "Device:Polyfuse_Small")
    fields = {"Footprint": part_.fp, "Datasheet": "", **part_.fields}
    for name, val in [("Reference", part_.ref), ("Value", part_.value)] + list(fields.items()):
        hide = name not in ("Reference", "Value")
        if small:
            if part_.rot in (90, 270):
                ox, oy = 0, (-2.03 if name == "Reference" else 2.54 + 0.5)
                eff = ["effects", font()]
            else:
                ox, oy = 1.52, (-0.64 if name == "Reference" else 1.27)
                eff = ["effects", font(), ["justify", Sym("left")]]
            node.append(["property", name, val, at(part_.x + ox, part_.y + oy)] + ([["hide", Sym("yes")]] if hide else []) + [eff])
        elif name in part_.props:
            px_, py_ = part_.props[name]
            node.append(["property", name, val, at(px_, py_), ["effects", font(), ["justify", Sym("left")]]])
        else:
            lp = next((p for p in find(lib_nodes[part_.lib], "property") if p[1] == name), None)
            if lp is not None and not hide:
                a_ = first(lp, "at"); ox, oy = xf(float(a_[1]), -float(a_[2]), part_.rot, part_.mirror)
                eff = ["effects", font()]
            else:
                ox = oy = 0; eff = ["effects", font()]
            node.append(["property", name, val, at(part_.x + ox, part_.y + oy)] + ([["hide", Sym("yes")]] if hide else []) + [eff])
    for num in sorted(part_.pins, key=lambda s: (len(s), s)):
        node.append(["pin", num, ["uuid", uid()]])
    node.append(["instances", ["project", PROJECT, ["path", "/" + ROOT, ["reference", part_.ref], ["unit", Sym("1")]]]])
    items.append(node)

# wires, split where another wire's endpoint or a pin lands on them, plus junction dots
endpoints = [p for w in wires for p in w]
pinpts = [(x, y) for pt in PARTS.values() for (x, y, _d) in pt.pins.values()]
counts = {}
for p in endpoints + [q for q in pinpts if any(on_segment(q, a, b) for a, b in wires)] + list(points_used):
    counts[p] = counts.get(p, 0) + 1
for p in set(endpoints) | set(points_used):
    through = sum(1 for a, b in wires if on_segment(p, a, b) and p not in (a, b))
    if counts.get(p, 0) + 2 * through >= 3:
        items.append(["junction", at(*p)[:3], ["diameter", Sym("0")], ["color", Sym("0"), Sym("0"), Sym("0"), Sym("0")], ["uuid", uid()]])
def split(ws, cuts):
    out = []
    for a, b in ws:
        inner = sorted({c for c in cuts if on_segment(c, a, b) and c not in (a, b)},
                       key=lambda c: abs(c[0] - a[0]) + abs(c[1] - a[1]))
        pts = [a] + inner + [b]
        out += list(zip(pts, pts[1:]))
    return out
wires[:] = split(wires, set(endpoints) | set(pinpts) | set(points_used))
for a, b in wires:
    items.append(["wire", ["pts", xy(*a), xy(*b)], ["stroke", ["width", Sym("0")], ["type", Sym("default")]], ["uuid", uid()]])

for pts, title, title_at in boxes:
    x1, y1 = pts[0]
    y2 = max(p[1] for p in pts)
    items.append(["polyline", ["pts"] + [xy(*p) for p in pts + [pts[0]]],
                  ["stroke", ["width", Sym("0.254")], ["type", Sym("dash")], ["color", Sym("72"), Sym("72"), Sym("160"), Sym("1")]],
                  ["fill", ["type", Sym("none")]], ["uuid", uid()]])
    ty = y1 - 1.27 if title_at == "top" else y2 - 1.27
    items.append(["text", title, ["exclude_from_sim", Sym("no")], at(x1 + 1.27, ty),
                  ["effects", ["font", ["size", f(2), f(2)], ["thickness", f(0.3)], ["bold", Sym("yes")], ["color", Sym("72"), Sym("72"), Sym("160"), Sym("1")]],
                   ["justify", Sym("left"), Sym("bottom")]], ["uuid", uid()]])
for (x, y), s, size in texts:
    items.append(["text", s, ["exclude_from_sim", Sym("no")], at(x, y), ["effects", ["font", ["size", f(size), f(size)], ["italic", Sym("yes")]],
                  ["justify", Sym("left"), Sym("bottom")]], ["uuid", uid()]])

if errors: sys.exit("\n".join(errors))
sch = ["kicad_sch", ["version", Sym("20260306")], ["generator", "eeschema"], ["generator_version", "10.0"],
       ["uuid", ROOT], ["paper", "A3"],
       ["title_block", ["title", "DS-2000"], ["date", "2026-09-28"], ["rev", "A"], ["company", "Mechardo Labs"],
        ["comment", Sym("1"), "RP2350A, 3x MX keys, SK6812MINI-E per key, USB-C"],
        ["comment", Sym("2"), "Pinout follows DS-2000-Firmware/include/pins.h"]],
       ["lib_symbols"] + list(lib_nodes.values())] + items + \
      [["sheet_instances", ["path", "/", ["page", "1"]]], ["embedded_fonts", Sym("no")]]
with open(OUT, "w", encoding="utf8", newline="\n") as fh:
    fh.write(dump(sch) + "\n")

# the intended netlist, for check_netlist.py
import json
json.dump({p.ref: p.conn for p in PARTS.values()}, open(OUT + ".conn.json", "w"), indent=0)
print(f"wrote {OUT}: {len(PARTS)} parts, {len(wires)} wires")
