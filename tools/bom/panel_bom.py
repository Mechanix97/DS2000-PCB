"""JLC BOM and placement file for our own panel, with one designator per copy.

KiKit keeps each copy's references as on the single board (C1 four times), so the silkscreen on
the visible face reads as designed. JLC needs a unique designator per placed part, so this numbers
the copies in the panel's placement file (C1 -> C1_1 ... C1_4, by position: rows top to bottom, then
left to right) and writes the matching BOM from the single board's (economic variant). Every placed
part must come from a BOM line, and every BOM part must be placed on each copy.

    python tools/bom/panel_bom.py board_bom_jlc.csv panel_cpl_jlc.csv out_bom_jlc.csv out_cpl_jlc.csv
"""
import csv, sys
from collections import defaultdict

bom_in, cpl_in, bom_out, cpl_out = sys.argv[1:5]

with open(cpl_in, newline="", encoding="utf8") as f:
    rd = csv.DictReader(f)
    fields, rows = rd.fieldnames, list(rd)

by_ref = defaultdict(list)
for r in rows:
    by_ref[r["Designator"]].append(r)
copies = {}
for ref, rs in by_ref.items():
    # JLC's Y is negative downwards: higher Y is nearer the top of the panel
    rs.sort(key=lambda r: (-round(float(r["Mid Y"]), 1), round(float(r["Mid X"]), 1)))
    copies[ref] = []
    for n, r in enumerate(rs, 1):
        r["Designator"] = f"{ref}_{n}"
        copies[ref].append(r["Designator"])
count = {len(v) for v in copies.values()}
assert len(count) == 1, f"not every part is on every copy: {count}"

with open(cpl_out, "w", newline="", encoding="utf8") as g:
    wr = csv.DictWriter(g, fields)
    wr.writeheader()
    wr.writerows(rows)

used = set()
with open(bom_in, newline="", encoding="utf8") as f, open(bom_out, "w", newline="", encoding="utf8") as g:
    rd = csv.DictReader(f)
    wr = csv.DictWriter(g, rd.fieldnames, quoting=csv.QUOTE_ALL)
    wr.writeheader()
    for row in rd:
        refs = [r.strip() for r in row["Designator"].split(",")]
        missing = [r for r in refs if r not in copies]
        assert not missing, f"BOM parts not on the panel: {missing}"
        row["Designator"] = ",".join(c for r in refs for c in copies[r])
        used.update(refs)
        wr.writerow(row)

extra = sorted(set(copies) - used)
assert not extra, f"placed on the panel but not in the BOM: {extra}"
print(f"panel: {len(used)} parts x {count.pop()} copies -> {bom_out}, {cpl_out}")
