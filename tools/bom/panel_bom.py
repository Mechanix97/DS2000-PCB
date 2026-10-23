"""Expands the single board's JLC BOM to the references of our own panel.

KiKit renames each copy's references to <ref>_<n> (C1 -> C1_1 ... C1_4), so JLC's BOM for the
panel must list those. This takes the single board's BOM (economic variant) and the panel's
placement file, and writes the panel BOM: same lines, each designator replaced by its copies found
in the placement file. Every placed part must come from a BOM line, and every BOM part must be placed.

    python tools/bom/panel_bom.py board_bom_jlc.csv panel_cpl_jlc.csv panel_bom_jlc.csv
"""
import csv, re, sys
from collections import defaultdict

bom_in, cpl_in, bom_out = sys.argv[1:4]

copies = defaultdict(list)
with open(cpl_in, newline="", encoding="utf8") as f:
    for row in csv.DictReader(f):
        m = re.fullmatch(r"(.+)_(\d+)", row["Designator"])
        assert m, f"panel reference without a copy number: {row['Designator']}"
        copies[m.group(1)].append(row["Designator"])

used = set()
with open(bom_in, newline="", encoding="utf8") as f, open(bom_out, "w", newline="", encoding="utf8") as g:
    rd = csv.DictReader(f)
    wr = csv.DictWriter(g, rd.fieldnames, quoting=csv.QUOTE_ALL)
    wr.writeheader()
    for row in rd:
        refs = [r.strip() for r in row["Designator"].split(",")]
        missing = [r for r in refs if r not in copies]
        assert not missing, f"BOM parts not on the panel: {missing}"
        row["Designator"] = ",".join(c for r in refs for c in sorted(copies[r], key=lambda s: int(s.rsplit("_", 1)[1])))
        used.update(refs)
        wr.writerow(row)

extra = sorted(set(copies) - used)
assert not extra, f"placed on the panel but not in the BOM: {extra}"
n = {len(v) for v in copies.values()}
print(f"panel BOM: {len(used)} parts x {n} copies -> {bom_out}")
