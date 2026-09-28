"""Generates the DS-2000 rev A schematic (RP2350A) as a KiCad 10 .kicad_sch.

Every pin is connected through a short wire stub ending in a net label or power symbol, so the
schematic's connectivity is exactly the NETS below and nothing is implied by wire geometry.
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
    return str(_uuid.uuid5(_uuid.NAMESPACE_URL, f"ds2000/rev-a/{_n}"))

POWER = {"GND": "power:GND", "+3V3": "power:+3V3", "+1V1": "power:+1V1",
         "+5V": "power:+5V", "VBUS": "power:VBUS"}
STUB = 2.54

# --------------------------------------------------------------------------------------------
# Parts: ref, lib_id, value, footprint, (x, y), {pin: net}, extra fields
# A pin mapped to None is an intentional no-connect. Every pin must be listed.
# --------------------------------------------------------------------------------------------
R0402 = "Resistor_SMD:R_0402_1005Metric"
C0402 = "Capacitor_SMD:C_0402_1005Metric"
C0805 = "Capacitor_SMD:C_0805_2012Metric"
PARTS = []
def snap(v): return round(round(v / 2.54) * 2.54, 2)
def part(ref, lib, value, fp, at, conn, **fields):
    at = (snap(at[0]), snap(at[1]))
    PARTS.append(dict(ref=ref, lib=lib, value=value, fp=fp, at=at, conn=conn, fields=fields))
def R(ref, value, a, b, at, **f): part(ref, "Device:R_Small", value, R0402, at, {"1": a, "2": b}, **f)
def C(ref, value, a, b, at, fp=C0402, **f): part(ref, "Device:C_Small", value, fp, at, {"1": a, "2": b}, **f)

TEXTS = []
def note(x, y, s, size=2.54): TEXTS.append((x, y, s, size))

# ---- USB input -----------------------------------------------------------------------------
note(20, 22, "USB-C input, protection, 3.3 V LDO")
part("J1", "Connector:USB_C_Receptacle_USB2.0_16P", "USB-C", "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12",
     (45.72, 63.5), {"A1": "GND", "A12": "GND", "B1": "GND", "B12": "GND", "SH": "GND",
                     "A4": "VBUS", "A9": "VBUS", "B4": "VBUS", "B9": "VBUS",
                     "A5": "CC1", "B5": "CC2", "A6": "USB_CONN_DP", "B6": "USB_CONN_DP",
                     "A7": "USB_CONN_DM", "B7": "USB_CONN_DM", "A8": None, "B8": None},
     MPN="TYPE-C-31-M-12", Manufacturer="Korean Hroparts Elec")
R("R1", "5.1k", "CC1", "GND", (76.2, 88.9))
R("R2", "5.1k", "CC2", "GND", (86.36, 88.9))
part("F1", "Device:Polyfuse_Small", "500mA hold", "Fuse:Fuse_1206_3216Metric", (88.9, 45.72),
     {"1": "VBUS", "2": "+5V"}, MPN="1206L050YR", Manufacturer="Littelfuse")
part("U1", "Power_Protection:USBLC6-2SC6", "USBLC6-2SC6", "Package_TO_SOT_SMD:SOT-23-6", (104.14, 71.12),
     {"1": "USB_CONN_DP", "6": "USB_CONN_DP", "3": "USB_CONN_DM", "4": "USB_CONN_DM",
      "2": "GND", "5": "+5V"}, MPN="USBLC6-2SC6", Manufacturer="STMicroelectronics")
R("R3", "27", "USB_CONN_DP", "USB_DP", (124.46, 68.58), Note="Place close to U3")
R("R4", "27", "USB_CONN_DM", "USB_DM", (134.62, 68.58), Note="Place close to U3")
part("U2", "Regulator_Linear:AP2112K-3.3", "AP2112K-3.3", "Package_TO_SOT_SMD:SOT-23-5", (129.54, 40.64),
     {"1": "+5V", "3": "+5V", "2": "GND", "4": None, "5": "+3V3"},
     MPN="AP2112K-3.3TRG1", Manufacturer="Diodes Inc")
C("C1", "10u", "+5V", "GND", (106.68, 40.64), fp=C0805)
C("C2", "10u", "+3V3", "GND", (147.32, 40.64), fp=C0805)

# ---- MCU -----------------------------------------------------------------------------------
note(170, 22, "RP2350A, core regulator, crystal, flash")
MCU = {"1": "+3V3", "11": "+3V3", "20": "+3V3", "30": "+3V3", "38": "+3V3", "45": "+3V3",
       "6": "+1V1", "23": "+1V1", "39": "+1V1", "50": "+1V1",
       "44": "+3V3", "53": "+3V3", "54": "+3V3", "49": "+3V3",
       "46": "VREG_AVDD", "48": "VREG_LX", "47": "GND", "61": "GND",
       "21": "XIN", "22": "XOUT", "24": "SWCLK", "25": "SWDIO", "26": "RUN",
       "51": "USB_DM", "52": "USB_DP",
       "60": "QSPI_SS", "56": "QSPI_SCLK", "57": "QSPI_SD0", "59": "QSPI_SD1",
       "58": "QSPI_SD2", "55": "QSPI_SD3",
       # Pinout owned by DS-2000-Firmware/include/pins.h
       "2": "KEY_MUTE", "3": "KEY_DEAFEN", "4": "KEY_DISCONNECT", "8": "LED_DIN_3V3"}
for p in pins("MCU_RaspberryPi:RP2350A"):
    MCU.setdefault(p[0], None)
part("U3", "MCU_RaspberryPi:RP2350A", "RP2350A", "Package_DFN_QFN:QFN-60-1EP_7x7mm_P0.4mm_EP3.4x3.4mm_ThermalVias",
     (228.6, 124.46), MCU, MPN="RP2350A", Manufacturer="Raspberry Pi")

# Core switching regulator, per "Hardware design with RP2350" (Minimal design)
L = (180, 45.72)
part("L1", "Device:L_Small", "3.3u", "Inductor_SMD:L_Murata_DFE201610P", L, {"1": "VREG_LX", "2": "+1V1"},
     MPN="AOTA-B201610S3R3-101-T", Manufacturer="Abracon",
     Note="Polarity-marked inductor; orientation matters. Verify pads against Abracon datasheet")
C("C3", "4.7u", "+1V1", "GND", (190.5, 45.72), Note="VREG output cap, layout per RP2350 guide")
C("C4", "4.7u", "+3V3", "GND", (200.66, 45.72), Note="VREG_VIN")
R("R5", "33", "+3V3", "VREG_AVDD", (210.82, 45.72), Note="VREG_AVDD RC filter")
C("C5", "4.7u", "VREG_AVDD", "GND", (220.98, 45.72), Note="VREG_AVDD RC filter")

# Decoupling: one 100 nF per IOVDD, per DVDD, ADC_AVDD, and one shared by USB_OTP_VDD/QSPI_IOVDD
x0 = 170
for i, net in enumerate(["+3V3"] * 6 + ["+1V1"] * 3 + ["+3V3", "+3V3"]):
    C(f"C{6 + i}", "100n", net, "GND", (x0 + i * 10.16, 200.66))
note(170, 188, "Decoupling at the pins: C6-C11 IOVDD, C12-C14 DVDD, C15 ADC_AVDD, C16 USB_OTP_VDD+QSPI_IOVDD", 1.524)

# Crystal
part("Y1", "Device:Crystal_GND24_Small", "12MHz", "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm", (160.02, 139.7),
     {"1": "XIN", "3": "XTAL_OUT", "2": "GND", "4": "GND"}, MPN="ABM8-272-T3", Manufacturer="Abracon")
R("R6", "1k", "XOUT", "XTAL_OUT", (175.26, 147.32))
C("C17", "15p", "XIN", "GND", (149.86, 149.86))
C("C18", "15p", "XTAL_OUT", "GND", (165.1, 157.48))

# Flash + BOOTSEL
part("U4", "Memory_Flash:W25Q32JVSS", "W25Q32JVSS", "Package_SO:SOIC-8_5.3x5.3mm_P1.27mm", (152.4, 101.6),
     {"1": "QSPI_SS", "6": "QSPI_SCLK", "5": "QSPI_SD0", "2": "QSPI_SD1", "3": "QSPI_SD2",
      "7": "QSPI_SD3", "8": "+3V3", "4": "GND"}, MPN="W25Q32JVSSIQ", Manufacturer="Winbond")
C("C19", "100n", "+3V3", "GND", (116.84, 81.28))
R("R7", "10k", "+3V3", "QSPI_SS", (116.84, 104.14), DNP=True, Note="DNF: only needed with other flash parts")
R("R8", "1k", "QSPI_SS", "BOOTSEL", (116.84, 124.46))
part("SW4", "Switch:SW_Push", "BOOTSEL", "Button_Switch_SMD:SW_Push_1P1T_XKB_TS-1187A", (116.84, 142.24),
     {"1": "BOOTSEL", "2": "GND"}, MPN="TS-1187A-B-A-B", Manufacturer="XKB")

# Reset + SWD
note(20, 180, "Reset, SWD, mounting")
R("R9", "10k", "+3V3", "RUN", (38.1, 200.66))
part("SW5", "Switch:SW_Push", "RESET", "Button_Switch_SMD:SW_Push_1P1T_XKB_TS-1187A", (55.88, 210.82),
     {"1": "RUN", "2": "GND"}, MPN="TS-1187A-B-A-B", Manufacturer="XKB")
part("J2", "Connector_Generic:Conn_01x03", "SWD", "Connector_JST:JST_SH_SM03B-SRSS-TB_1x03-1MP_P1.00mm_Horizontal",
     (91.44, 205.74), {"1": "SWCLK", "2": "GND", "3": "SWDIO"},
     MPN="SM03B-SRSS-TB", Manufacturer="JST", Note="Raspberry Pi Debug Probe pinout")
for i in range(4):
    part(f"H{i + 1}", "Mechanical:MountingHole_Pad", "M2", "MountingHole:MountingHole_2.2mm_M2_Pad_Via",
         (38.1 + i * 12.7, 238.76), {"1": "GND"})

# ---- Keys and LEDs -------------------------------------------------------------------------
note(290, 22, "Keys (GP0-GP2, internal pull-ups) and per-key SK6812MINI-E")
for i, (net, name) in enumerate([("KEY_MUTE", "MUTE"), ("KEY_DEAFEN", "DEAFEN"), ("KEY_DISCONNECT", "DISCONNECT")]):
    part(f"SW{i + 1}", "Switch:SW_Push", name, "Button_Switch_Keyboard:SW_Cherry_MX_1.00u_PCB",
         (304.8, 45.72 + i * 15.24), {"1": net, "2": "GND"})
part("U5", "74xGxx:74AHCT1G125", "74AHCT1G125", "Package_TO_SOT_SMD:SOT-353_SC-70-5", (309.88, 109.22),
     {"1": "GND", "2": "LED_DIN_3V3", "3": "GND", "4": "LED_DIN_5V", "5": "+5V"},
     MPN="74AHCT1G125GW", Manufacturer="Nexperia", Note="3.3 V -> 5 V level shift for the LED data line")
C("C20", "100n", "+5V", "GND", (330.2, 91.44))
R("R10", "100", "LED_DIN_5V", "LED_DIN", (355.6, 109.22), Note="Damping, place near D1")
chain = ["LED_DIN", "LED_D1_D2", "LED_D2_D3", None]
for i, name in enumerate(["MUTE", "DEAFEN", "DISCONNECT"]):
    x = 294.64 + i * 45.72
    part(f"D{i + 1}", "LED:SK6812MINI-E", "SK6812MINI-E", "LED_SMD:LED_SK6812MINI-E_3.2x2.8mm_P1.5mm_ReverseMount",
         (x, 147.32), {"3": "+5V", "1": "GND", "2": chain[i], "4": chain[i + 1]},
         MPN="SK6812MINI-E", Manufacturer="Opsco", Note=f"Under the {name} key")
    C(f"C{21 + i}", "100n", "+5V", "GND", (x + 15.24, 147.32))

# ---- Power flags ---------------------------------------------------------------------------
FLAGS = [("VBUS", (99.06, 238.76)), ("GND", (124.46, 238.76)), ("+5V", (149.86, 238.76)), ("+1V1", (175.26, 238.76)), ("VREG_AVDD", (200.66, 238.76))]

# --------------------------------------------------------------------------------------------
items, lib_nodes, used_libs = [], {}, set()
pwr_n = [0]

def use(lib_id):
    if lib_id not in lib_nodes:
        lib_nodes[lib_id] = lib_symbol(lib_id)

def prop(name, value, x, y, hide=False, angle=0, justify=None):
    eff = ["effects", ["font", ["size", Sym("1.27"), Sym("1.27")]]]
    if justify: eff.append(["justify", Sym(justify)])
    if hide: eff.append(["hide", Sym("yes")])
    return ["property", name, value, ["at", Sym(f"{x:g}"), Sym(f"{y:g}"), Sym(str(angle))], eff]

def lib_prop_pos(lib_id, name):
    for p in find(lib_nodes[lib_id], "property"):
        if p[1] == name:
            at = first(p, "at")
            hidden = any(isinstance(e, list) and e[0] == "hide" and e[1] == "yes" for e in (first(p, "effects") or []))
            hidden = hidden or any(isinstance(e, list) and e[0] == "hide" for e in p)
            return float(at[1]), float(at[2]), int(float(at[3])), hidden
    return 0.0, 0.0, 0, True

def place(ref, lib_id, value, x, y, fields=None, in_bom=True, dnp=False, pin_numbers=()):
    use(lib_id)
    node = ["symbol", ["lib_id", lib_id], ["at", Sym(f"{x:g}"), Sym(f"{y:g}"), Sym("0")], ["unit", Sym("1")],
            ["exclude_from_sim", Sym("no")], ["in_bom", Sym("yes" if in_bom else "no")],
            ["on_board", Sym("yes")], ["dnp", Sym("yes" if dnp else "no")], ["uuid", uid()]]
    for name, val in [("Reference", ref), ("Value", value)] + list((fields or {}).items()):
        px, py, ang, hidden = lib_prop_pos(lib_id, name) if name in ("Reference", "Value", "Footprint", "Datasheet", "Description") else (0, 0, 0, True)
        node.append(prop(name, val, x + px, y - py, hide=hidden, angle=ang))
    for num in pin_numbers:
        node.append(["pin", num, ["uuid", uid()]])
    node.append(["instances", ["project", PROJECT, ["path", "/" + ROOT, ["reference", ref], ["unit", Sym("1")]]]])
    items.append(node)

DIRS = {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}
LABEL = {(1, 0): (0, "left"), (-1, 0): (180, "right"), (0, -1): (90, "left"), (0, 1): (270, "right")}
# rotation that points a power symbol's body away from the pin, for stub direction d
PWR_ROT_GND = {(0, 1): 0, (0, -1): 180, (1, 0): 90, (-1, 0): 270}
PWR_ROT_RAIL = {(0, -1): 0, (0, 1): 180, (1, 0): 270, (-1, 0): 90}

def power(net, x, y, rot):
    pwr_n[0] += 1
    lib_id = POWER[net]; use(lib_id)
    ref = f"#PWR{pwr_n[0]:03d}"
    node = ["symbol", ["lib_id", lib_id], ["at", Sym(f"{x:g}"), Sym(f"{y:g}"), Sym(str(rot))], ["unit", Sym("1")],
            ["exclude_from_sim", Sym("no")], ["in_bom", Sym("no")], ["on_board", Sym("yes")], ["dnp", Sym("no")],
            ["uuid", uid()], prop("Reference", ref, x, y + 5, hide=True), prop("Value", net, x, y + (3.5 if net == "GND" else -3.5)),
            prop("Footprint", "", x, y, hide=True), prop("Datasheet", "", x, y, hide=True),
            ["pin", "1", ["uuid", uid()]],
            ["instances", ["project", PROJECT, ["path", "/" + ROOT, ["reference", ref], ["unit", Sym("1")]]]]]
    items.append(node)

def wire(x1, y1, x2, y2):
    items.append(["wire", ["pts", ["xy", Sym(f"{x1:g}"), Sym(f"{y1:g}")], ["xy", Sym(f"{x2:g}"), Sym(f"{y2:g}")]],
                  ["stroke", ["width", Sym("0")], ["type", Sym("default")]], ["uuid", uid()]])

def label(net, x, y, d):
    ang, just = LABEL[d]
    items.append(["label", net, ["at", Sym(f"{x:g}"), Sym(f"{y:g}"), Sym(str(ang))],
                  ["effects", ["font", ["size", Sym("1.27"), Sym("1.27")]], ["justify", Sym(just), Sym("bottom")]],
                  ["uuid", uid()]])

def attach(net, x, y, d):
    ex, ey = x + d[0] * STUB, y + d[1] * STUB
    wire(x, y, ex, ey)
    if net in POWER:
        power(net, ex, ey, (PWR_ROT_GND if net == "GND" else PWR_ROT_RAIL)[d])
    else:
        label(net, ex, ey, d)

errors = []
for p in PARTS:
    lib_id = p["lib"]
    fp_lib, fp_name = p["fp"].split(":")
    if not os.path.exists(f"{FPDIR}/{fp_lib}.pretty/{fp_name}.kicad_mod"):
        errors.append(f"{p['ref']}: footprint {p['fp']} not found")
    plist = pins(lib_id)
    nums = {q[0] for q in plist}
    if set(p["conn"]) != nums:
        errors.append(f"{p['ref']}: unmapped {sorted(nums - set(p['conn']))} unknown {sorted(set(p['conn']) - nums)}")
    fields = {"Footprint": p["fp"], "Datasheet": "", **{k: v for k, v in p["fields"].items() if k != "DNP"}}
    place(p["ref"], lib_id, p["value"], *p["at"], fields=fields, dnp=p["fields"].get("DNP", False),
          pin_numbers=sorted(nums, key=lambda s: (len(s), s)))
    sx, sy = p["at"]
    done = set()
    for num, name, ptype, px, py, ang in plist:
        net = p["conn"].get(num)
        x, y = sx + px, sy - py
        key = (round(x, 3), round(y, 3))
        if key in done:          # stacked pins share one connection point
            continue
        done.add(key)
        if net is None:
            items.append(["no_connect", ["at", Sym(f"{x:g}"), Sym(f"{y:g}")], ["uuid", uid()]])
        else:
            attach(net, x, y, DIRS[ang])

# stacked pins must agree on their net
for p in PARTS:
    seen = {}
    for num, *_rest in pins(p["lib"]):
        px, py = _rest[2], _rest[3]
        seen.setdefault((px, py), set()).add(p["conn"].get(num))
    for k, v in seen.items():
        if len(v) > 1:
            errors.append(f"{p['ref']}: stacked pins at {k} disagree {v}")

for net, (x, y) in FLAGS:
    x, y = snap(x), snap(y)
    use("power:PWR_FLAG")
    pwr_n[0] += 1
    ref = f"#FLG{pwr_n[0]:03d}"
    items.append(["symbol", ["lib_id", "power:PWR_FLAG"], ["at", Sym(f"{x:g}"), Sym(f"{y:g}"), Sym("0")], ["unit", Sym("1")],
                  ["exclude_from_sim", Sym("no")], ["in_bom", Sym("no")], ["on_board", Sym("yes")], ["dnp", Sym("no")],
                  ["uuid", uid()], prop("Reference", ref, x, y - 5, hide=True), prop("Value", "PWR_FLAG", x, y - 3.8, hide=True),
                  prop("Footprint", "", x, y, hide=True), prop("Datasheet", "", x, y, hide=True),
                  ["pin", "1", ["uuid", uid()]],
                  ["instances", ["project", PROJECT, ["path", "/" + ROOT, ["reference", ref], ["unit", Sym("1")]]]]])
    attach(net, x, y, (0, 1))

for x, y, s, size in TEXTS:
    items.append(["text", s, ["exclude_from_sim", Sym("no")], ["at", Sym(f"{x:g}"), Sym(f"{y:g}"), Sym("0")],
                  ["effects", ["font", ["size", Sym(f"{size:g}"), Sym(f"{size:g}")], ["thickness", Sym("0.3")] if size > 2 else ["bold", Sym("no")]],
                   ["justify", Sym("left"), Sym("bottom")]], ["uuid", uid()]])

if errors:
    sys.exit("\n".join(errors))

sch = ["kicad_sch", ["version", Sym("20260306")], ["generator", "eeschema"], ["generator_version", "10.0"],
       ["uuid", ROOT], ["paper", "A3"],
       ["title_block", ["title", "DS-2000"], ["date", "2026-09-28"], ["rev", "A"], ["company", "Mechardo Labs"],
        ["comment", Sym("1"), "RP2350A, 3x MX keys, SK6812MINI-E per key, USB-C"],
        ["comment", Sym("2"), "Pinout follows DS-2000-Firmware/include/pins.h"]],
       ["lib_symbols"] + list(lib_nodes.values())] + items + \
      [["sheet_instances", ["path", "/", ["page", "1"]]], ["embedded_fonts", Sym("no")]]
with open(OUT, "w", encoding="utf8", newline="\n") as f:
    f.write(dump(sch) + "\n")
print(f"wrote {OUT}: {len(PARTS)} parts, {len(items)} items")
