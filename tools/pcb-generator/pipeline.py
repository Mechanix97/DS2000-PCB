"""Rebuilds the board from the schematic into build/pcb/: placement, plane fanout, autorouting, DRC.

It never touches the repository's DS2000.kicad_pcb. Once the board has been edited by hand, that
file is the source of truth; this pipeline only reproduces how the first routed version was made,
or explores a variant, which is then compared and copied over deliberately.

Requirements:
  - KiCad 10 (kicad-cli and its bundled python)
  - Freerouting 2.4+ and a Java 25 runtime: set FREEROUTING_JAR, and JAVA if java is not on PATH

Usage (from anywhere):  python tools/pcb-generator/pipeline.py [--no-route] [--passes N]
"""
import os, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
WORK = os.path.join(ROOT, "build", "pcb")
KPY = os.environ.get("KICAD_PYTHON", "C:/Program Files/KiCad/10.0/bin/python.exe")
KCLI = os.environ.get("KICAD_CLI", "C:/Program Files/KiCad/10.0/bin/kicad-cli.exe")
JAVA = os.environ.get("JAVA", "java")
FR = os.environ.get("FREEROUTING_JAR", "")
route = "--no-route" not in sys.argv
passes = sys.argv[sys.argv.index("--passes") + 1] if "--passes" in sys.argv else "80"
if route and not os.path.exists(FR):
    sys.exit("Set FREEROUTING_JAR to the Freerouting jar (or pass --no-route)")

def script(name):
    return os.path.join(HERE, name)

def run(args, **kw):
    r = subprocess.run(args, cwd=WORK, capture_output=True, text=True, **kw)
    out = "\n".join(l for l in (r.stdout + r.stderr).splitlines() if "image handler" not in l)
    if r.returncode:
        print(out); sys.exit(f"failed: {args[:3]}")
    return out

os.makedirs(WORK, exist_ok=True)
for f in ("DS2000.kicad_pro", "DS2000.kicad_prl", "DS2000.ses"):
    if os.path.exists(os.path.join(WORK, f)):
        os.remove(os.path.join(WORK, f))
for f in ("DS2000.kicad_sch", "DS2000.kicad_dru"):
    shutil.copy(os.path.join(ROOT, f), WORK)

run([KCLI, "sch", "export", "netlist", "--format", "kicadsexpr", "-o", "net.net", "DS2000.kicad_sch"])
print(run([KPY, "-u", script("gen_pcb.py"), "net.net", "DS2000.kicad_pcb"]).splitlines()[-2])
print(run([KPY, "-u", script("fanout.py"), "DS2000.kicad_pcb"]).strip())

def import_ses():
    run([KPY, "-c", "import pcbnew; b=pcbnew.LoadBoard('DS2000.kicad_pcb'); "
                    "assert pcbnew.ImportSpecctraSES(b, 'DS2000.ses'); pcbnew.SaveBoard('DS2000.kicad_pcb', b)"])

def freeroute():
    run([KPY, "-c", "import pcbnew; b=pcbnew.LoadBoard('DS2000.kicad_pcb'); pcbnew.ExportSpecctraDSN(b, 'DS2000.dsn')"])
    if os.path.exists(os.path.join(WORK, "DS2000.ses")):
        os.remove(os.path.join(WORK, "DS2000.ses"))
    log = run([JAVA, "-jar", FR, "-de", "DS2000.dsn", "-do", "DS2000.ses", "-mp", passes, "-inc", "Plane",
               "--gui.enabled=false"], timeout=1800)
    m = re.findall(r"Auto-routing stage completed:.*", log)
    return m[-1] if m else ""

if route:
    print(freeroute()[:150])
    import_ses()
    for _ in range(2):                         # incremental passes over the routed board
        print("  incremental:", freeroute()[:130])
        import_ses()

def drc():
    run([KCLI, "pcb", "drc", "--schematic-parity", "--refill-zones", "--severity-all", "-o", "drc.rpt", "DS2000.kicad_pcb"])
    return open(os.path.join(WORK, "drc.rpt"), encoding="utf8").read()

rpt = drc()
if "[via_dangling]" in rpt:
    print(run([KPY, "-u", script("cleanup_vias.py"), "DS2000.kicad_pcb", "drc.rpt"]).strip())
    rpt = drc()
counts = {}
for k in re.findall(r"^\[([a-z_]+)\]", rpt, re.M):
    counts[k] = counts.get(k, 0) + 1
print("DRC:", ", ".join(f"{v} {k}" for k, v in sorted(counts.items(), key=lambda kv: -kv[1])) or "clean")
print(f"Board written to {os.path.join(WORK, 'DS2000.kicad_pcb')}")
