"""Removes vias listed as dangling in a KiCad DRC report.  python.exe cleanup_vias.py board drc.rpt"""
import re, sys
import pcbnew
board_path, rpt_path = sys.argv[1], sys.argv[2]
rpt = open(rpt_path, encoding="utf8").read()
pts = []
for block in re.split(r"\n(?=\[)", rpt):
    if block.startswith("[via_dangling]"):
        m = re.search(r"@\(([\d.]+) mm, ([\d.]+) mm\)", block)
        if m:
            pts.append((float(m.group(1)), float(m.group(2))))
b = pcbnew.LoadBoard(board_path)
removed = 0
for t in list(b.GetTracks()):
    if isinstance(t, pcbnew.PCB_VIA):
        x, y = pcbnew.ToMM(t.GetPosition().x), pcbnew.ToMM(t.GetPosition().y)
        if any(abs(x - a) < 0.01 and abs(y - c) < 0.01 for a, c in pts):
            b.Remove(t); removed += 1
pcbnew.SaveBoard(board_path, b)
print(f"removed {removed} dangling via(s)")
