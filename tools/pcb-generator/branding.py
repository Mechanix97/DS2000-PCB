"""Applies the visible-face silkscreen and branding to a board. Safe to run repeatedly.

- hides every reference designator (they stay in the file for assembly drawings)
- moves the USB-C footprint's silkscreen, which falls past the board edge, to the fab layer
- writes the product name, "mechardo labs" and the revision, and places the Mechardo Labs mark
  (DS2000.pretty/Logo_Mechardo_6mm, ENIG gold) in the free back-left corner

KiCad 10's Python bindings hand back untyped proxies once anything has been removed from the
board, so every read and change happens first and removals come last, just before saving.

Run with KiCad's python:  python.exe branding.py board.kicad_pcb
"""
import os, sys
import pcbnew

PCB = sys.argv[1]
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
LIB = os.path.join(ROOT, "DS2000.pretty")
b = pcbnew.LoadBoard(PCB)
mm = pcbnew.FromMM

# back left, between the H1 hole and the flash: the one corner of the face with no top copper
BX, LOGO_Y = 75.5, 79.2
OURS = {"DS2000", "DS-2000", "rev A", "mechardo labs"}

stale = []
for fp in list(b.GetFootprints()):
    if str(fp.GetFPID().GetLibItemName()) == "Logo_Mechardo_6mm":
        stale.append(fp)
        continue
    fp.GetField(pcbnew.FIELD_T_REFERENCE).SetVisible(False)
    if fp.GetReference() == "J1":
        for item in fp.GraphicalItems():
            if item.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS):
                item.SetLayer(pcbnew.B_Fab)
stale += [d for d in b.GetDrawings() if isinstance(d, pcbnew.PCB_TEXT) and d.GetText() in OURS]

def text(s, x, y, size, bold=False):
    t = pcbnew.PCB_TEXT(b); t.SetText(s); t.SetLayer(pcbnew.F_SilkS)
    t.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
    t.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
    t.SetTextThickness(mm(size * (0.2 if bold else 0.15)))
    b.Add(t)

logo = pcbnew.FootprintLoad(LIB, "Logo_Mechardo_6mm")
logo.SetFPID(pcbnew.LIB_ID("DS2000", "Logo_Mechardo_6mm"))
logo.SetReference("LOGO1")
logo.GetField(pcbnew.FIELD_T_REFERENCE).SetVisible(False)
logo.SetPosition(pcbnew.VECTOR2I(mm(BX), mm(LOGO_Y)))
b.Add(logo)
text("DS2000", BX, LOGO_Y + 5.2, 1.6, bold=True)
text("mechardo labs", BX, LOGO_Y + 7.3, 0.8)
text("rev A", BX, LOGO_Y + 8.9, 0.8)

for item in stale:
    b.Remove(item)
pcbnew.SaveBoard(PCB, b)
print(f"branding applied ({len(stale)} old items replaced)")
