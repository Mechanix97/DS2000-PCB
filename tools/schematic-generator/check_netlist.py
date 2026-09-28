"""Compares a KiCad netlist export with the intended connectivity written by gen_sch2.py."""
import json, re, sys
net_file, conn_file = sys.argv[1], sys.argv[2]
s = open(net_file, encoding="utf8").read()
got = {}
for blk in re.split(r"\(net\s+\(code", s[s.find("(nets"):])[1:]:
    name = re.search(r'\(name "([^"]*)"', blk).group(1)
    nodes = frozenset(re.findall(r'\(node\s+\(ref "([^"]+)"\)\s*\(pin "([^"]+)"\)', blk))
    got[nodes] = name
conn = json.load(open(conn_file))
want = {}
for ref, m in conn.items():
    for pin, net in m.items():
        if net is not None:
            want.setdefault(net, set()).add((ref, pin))
ok = True
got_sets = set(got)
for net, nodes in want.items():
    if frozenset(nodes) not in got_sets:
        ok = False
        # find where these pins ended up
        where = {got[g] for g in got for n in nodes if n in g}
        print(f"MISMATCH {net}: intended {sorted(nodes)}\n   found in nets {where}")
# pins that should be unconnected must be alone
for ref, m in conn.items():
    for pin, net in m.items():
        if net is None:
            for g in got:
                if (ref, pin) in g and len(g) > 1:
                    ok = False; print(f"NC pin {ref}.{pin} is connected to {got[g]}")
extra = [got[g] for g in got if not any(frozenset(n) == g for n in want.values()) and len(g) > 1]
if extra: ok = False; print("unexpected nets:", extra)
print("NETLIST OK" if ok else "NETLIST DIFFERS")
sys.exit(0 if ok else 1)
