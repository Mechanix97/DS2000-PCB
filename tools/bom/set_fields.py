"""Writes the BOM fields (MPN, Manufacturer, LCSC) into DS2000.kicad_sch.

PARTS below is the parts list for JLCPCB assembly. Every LCSC number was checked against its LCSC /
JLCPCB product page on 2026-09-28, or comes from Raspberry Pi's RP2350A minimal design BOM (R4-S1),
whose parts rev A copies around the core regulator. On 2026-10-08 the parts that have a JLC basic
equivalent (no extended-part fee) or a cheaper drop-in were swapped (DS2000-PCB cost-down PR). Parts without an LCSC number (switches, test and
jumper pads, holes, J3's wire holes) are fitted by hand or are bare copper, and stay out of the JLC
BOM and placement files.

Basic or extended: JLC's BOM upload shows it per line; the generic passives here are the common
Samsung / UNI-ROYAL / FH parts of its library.

Run with any python:  python tools/bom/set_fields.py
"""
import os, re

SCH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "DS2000.kicad_sch")

C100N = ("CL05B104KO5NNNC", "Samsung Electro-Mechanics", "C1525")
PARTS = {
    # capacitors
    **{r: ("CL21A106KAYNNNE", "Samsung Electro-Mechanics", "C15850") for r in ("C1", "C2")},        # 10u 25V X5R 0805
    **{r: ("CL05A475MP5NRNC", "Samsung Electro-Mechanics", "C23733") for r in ("C3", "C4", "C5")},  # 4.7u 10V X5R, basic
    **{f"C{i}": C100N for i in list(range(6, 17)) + [19, 20, 21, 22]},                               # 100n 16V X7R 0402
    **{r: ("0402CG330J500NT", "FH", "C1562") for r in ("C17", "C18")},                             # 33p 50V C0G 0402, for Y1's 20 pF load
    # resistors
    **{r: ("RC0402FR-0727RL", "Yageo", "C138021") for r in ("R3", "R4")},                          # 27R 1%, as the reference
    "R5": ("0402WGF330JTCE", "UNI-ROYAL", "C25105"),                                              # 33R, basic (AVDD filter, tolerance irrelevant)
    **{r: ("0402WGF1001TCE", "UNI-ROYAL", "C11702") for r in ("R6", "R8")},                        # 1k 1%
    **{r: ("0402WGF1002TCE", "UNI-ROYAL", "C25744") for r in ("R7", "R9")},                        # 10k 1% (R7 is DNP)
    "R10": ("0402WGF1000TCE", "UNI-ROYAL", "C25076"),                                             # 100R 1%
    # the rest
    "U1": ("USBLC6-2SC6", "UMW", "C2687116"),                                                     # same part, second source, 1/4 the price
    "U2": ("XC6206P332MR-G", "Torex", "C5446"),                                                   # 200 mA LDO, basic
    "U3": ("RP2350A", "Raspberry Pi", "C42411118"),
    "U4": ("W25Q16JVSSIQ", "Winbond", "C82317"),                                                  # 2 MB, same 208 mil footprint
    "U5": ("74AHCT1G125GW,125", "Nexperia", "C12495"),
    "Y1": ("X322512MSB4SI", "YXC", "C9002"),                                                      # 12 MHz, 20 pF, 80 ohm ESR, basic
    "L1": ("AOTA-B201610S3R3-101-T", "Abracon", "C42411119"),
    **{r: ("WS2812B-2020-V6", "Worldsemi", "C52917434") for r in ("D1", "D2")},                 # top side, in the Choc LED window
}

def prop(name, value, at):
    return (f'\t\t(property "{name}" "{value}"\n\t\t\t{at}\n\t\t\t(hide yes)\n\t\t\t(show_name no)\n'
            f'\t\t\t(do_not_autoplace no)\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n'
            f'\t\t\t\t)\n\t\t\t)\n\t\t)\n')

s = open(SCH, encoding="utf8").read()
done = set()
for ref, (mpn, mfr, lcsc) in PARTS.items():
    i = s.find(f'(property "Reference" "{ref}"')
    assert i >= 0, ref
    st = s.rfind("\n\t(symbol\n", 0, i) + 1
    en = s.index("\n\t)\n", i) + 3
    blk = s[st:en]
    for name in ("MPN", "Manufacturer", "LCSC"):            # drop old values, rewrite all three
        blk = re.sub(r'\t\t\(property "%s" "[^"]*"\n(?:\t\t\t.*\n)*?\t\t\)\n' % name, "", blk)
    at = re.search(r'\(property "Reference" "[^"]*"\n\t\t\t(\(at [^)]*\))', blk).group(1)
    k = blk.index("\t\t(pin ")
    blk = blk[:k] + prop("MPN", mpn, at) + prop("Manufacturer", mfr, at) + prop("LCSC", lcsc, at) + blk[k:]
    s = s[:st] + blk + s[en:]
    done.add(ref)
open(SCH, "w", encoding="utf8", newline="\n").write(s)

# the board's footprints carry the same fields, so the schematic parity check stays clean
import uuid
PCB = os.path.join(os.path.dirname(SCH), "DS2000.kicad_pcb")
def fprop(name, value, fab):
    return (f'\t\t(property "{name}" "{value}"\n\t\t\t(at 0 0 0)\n\t\t\t(layer "{fab}")\n\t\t\t(hide yes)\n'
            f'\t\t\t(uuid "{uuid.uuid4()}")\n\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n'
            f'\t\t\t\t\t(thickness 0.15)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n')
p = open(PCB, encoding="utf8").read()
for ref, (mpn, mfr, lcsc) in PARTS.items():
    i = p.find(f'\t\t(property "Reference" "{ref}"\n')
    assert i >= 0, ref
    st = p.rfind("\n\t(footprint ", 0, i) + 1
    en = p.index("\n\t)\n", i) + 3
    blk = p[st:en]
    for name in ("MPN", "Manufacturer", "LCSC"):
        blk = re.sub(r'\t\t\(property "%s" "[^"]*"\n(?:\t\t\t.*\n)*?\t\t\)\n' % name, "", blk)
    fab = "B.Fab" if '\t\t(layer "B.Cu")' in blk[:400] else "F.Fab"
    k = blk.index('\t\t(property "Value"')
    k = blk.index("\n\t\t)\n", k) + 5                      # after the Value property
    blk = blk[:k] + fprop("MPN", mpn, fab) + fprop("Manufacturer", mfr, fab) + fprop("LCSC", lcsc, fab) + blk[k:]
    p = p[:st] + blk + p[en:]
open(PCB, "w", encoding="utf8", newline="\n").write(p)
print(f"BOM fields written for {len(done)} parts, in the schematic and on the board")
