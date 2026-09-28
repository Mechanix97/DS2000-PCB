"""Minimal S-expression reader/writer and KiCad symbol-library helpers."""
import re

LIBDIR = "C:/Program Files/KiCad/10.0/share/kicad/symbols"

class Sym(str):
    """An unquoted atom."""

def parse(text):
    tokens = re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+', text)
    stack, cur = [], []
    for t in tokens:
        if t == "(":
            stack.append(cur); cur = []
        elif t == ")":
            done = cur; cur = stack.pop(); cur.append(done)
        elif t.startswith('"'):
            cur.append(t[1:-1].replace('\\"', '"').replace("\\\\", "\\"))
        else:
            cur.append(Sym(t))
    return cur[0]

def dump(node, indent=0):
    tab = "\t" * indent
    if isinstance(node, list) and node and not isinstance(node[0], list):
        node = [Sym(node[0])] + node[1:]   # the head of a list is always a keyword
    if not isinstance(node, list):
        if isinstance(node, Sym):
            return node
        return '"' + str(node).replace("\\", "\\\\").replace('"', '\\"') + '"'
    if all(not isinstance(x, list) for x in node):
        return tab + "(" + " ".join(dump(x) for x in node) + ")"
    head = [x for x in node if not isinstance(x, list)]
    out = tab + "(" + " ".join(dump(x) for x in head)
    for x in node:
        if isinstance(x, list):
            out += "\n" + dump(x, indent + 1)
    return out + "\n" + tab + ")"

def find(node, key):
    return [x for x in node if isinstance(x, list) and x and x[0] == key]

def first(node, key):
    r = find(node, key)
    return r[0] if r else None

_libcache = {}
def library(lib):
    if lib not in _libcache:
        with open(f"{LIBDIR}/{lib}.kicad_sym", encoding="utf8") as f:
            _libcache[lib] = parse(f.read())
    return _libcache[lib]

def lib_symbol(lib_id):
    """Returns the flattened symbol node named `lib_id` ready for a schematic's lib_symbols."""
    lib, name = lib_id.split(":")
    syms = {s[1]: s for s in find(library(lib), "symbol")}
    node = syms[name]
    ext = first(node, "extends")
    if ext:
        parent = lib_symbol(f"{lib}:{ext[1]}")
        pname = ext[1]
        body = [x for x in parent[2:] if not (isinstance(x, list) and x[0] in ("property", "symbol"))]
        props = find(node, "property")
        units = []
        for u in find(parent, "symbol"):
            u = list(u); u[1] = u[1].replace(pname.split(":")[-1], name, 1); units.append(u)
        own = [x for x in node[2:] if isinstance(x, list) and x[0] not in ("property", "extends", "symbol")]
        # child-level flags override parent ones
        keys = {x[0] for x in own}
        body = [x for x in body if x[0] not in keys] + own
        node = ["symbol", name] + body + props + units
    node = list(node)
    node[1] = lib_id if ":" not in node[1] else node[1]
    return node

def pins(lib_id, unit=1):
    """[(number, name, type, x, y, angle)] for the given unit (plus the common unit 0)."""
    node = lib_symbol(lib_id)
    name = lib_id.split(":")[1]
    out = []
    for u in find(node, "symbol"):
        m = re.match(re.escape(name) + r"_(\d+)_(\d+)$", u[1])
        if not m or int(m.group(1)) not in (0, unit) or int(m.group(2)) not in (0, 1):
            continue
        for p in find(u, "pin"):
            at = first(p, "at")
            out.append((first(p, "number")[1], first(p, "name")[1], str(p[1]),
                        float(at[1]), float(at[2]), int(float(at[3]))))
    return out

if __name__ == "__main__":
    import sys
    for lid in sys.argv[1:]:
        print("==", lid)
        for p in sorted(pins(lid), key=lambda p: (len(p[0]), p[0])):
            print("  ", p)
