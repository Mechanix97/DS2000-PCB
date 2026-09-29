# DS2000 rev A — design notes

Rev A replaces the 2025 RP2040 draft (last seen at commit `7db9552`). It was drawn from scratch,
using the draft only as a reference, and fixes every defect found in it (DS2000-PCB#2-#10).

## Product decisions

| Decision | Choice | Why |
|---|---|---|
| MCU | Discrete **RP2350A** (QFN-60) | Same family as the RP2350-Zero test module the firmware runs on |
| Look | **Exposed PCB as the top face**, enclosure is a tray underneath | The board is the product's face: logo, art, legends in silkscreen |
| Top side | Switches, and **the RP2350A and its circuitry on show** in a strip behind the keys | The visible chip is part of the look |
| Bottom side | The two reverse-mount LEDs, the **USB-C receptacle** and **all debug pads** (SWD, BOOT, RST) | The plug and cable sit low, level with the tray, the top strip gains space, and debug stays off the visible face. Assembly is two-sided |
| Layers | 4 (Sig / GND / PWR / Sig), 1.6 mm | Routes mostly on inner layers so the face stays clean, solid reference for USB and the core regulator, stiff enough to hold switches without a plate |
| Finish (proposed) | Matte black soldermask, ENIG | Gold for exposed logo copper and mounting rings |
| Keys | 3× Kailh Choc V1 (low profile), **soldered, no plate**, in a row, MBK-style keycaps | Changed from Cherry MX for a lower, flatter device. Choc V1 has two locating posts, so it sits steady without a plate |
| Size | 72 × 46 mm | 3 keys at the Choc 18 mm pitch plus corner M2 holes; the extra depth is the component strip behind the keys. Kept from the MX layout so the enclosure's numbers stay put |
| Status | **SK6812MINI-E** reverse-mount under the mute and deafen keys; **disconnect has no LED** | Lights the key through the switch LED window; needs shine-through or translucent keycaps |
| Pinout | Owned by `DS2000-Firmware/include/pins.h` | See below |

## Blocks

**USB-C and power.** HRO TYPE-C-31-M-12 on the **bottom** side at the back edge, pointing backwards, so the plug and cable sit low and the top strip stays free. The tray needs a pocket of at least 4 mm under the board and a cut-out in its back wall for the plug overmould (about 12.5 × 6.5 mm). J3 is four bare 2.54 mm holes (VBUS, D-, D+, GND) to solder a USB cable instead of fitting J1; it sits upstream of the fuse and ESD, so a soldered cable is protected the same way. 5.1 kΩ on CC1/CC2
(UFP). VBUS goes through F1 (500 mA hold PTC) to `+5V`, which feeds the LEDs and the level shifter.
USBLC6-2SC6 ESD on D+/D- close to the connector. AP2112K-3.3 LDO (250 mV dropout, 600 mA) makes
`+3V3`; the RP2350 minimal design uses an NCP1117, but its ~1.1 V dropout leaves little margin from
a 4.75 V VBUS after the fuse.

**RP2350A.** Straight from *Hardware design with RP2350* (Minimal design, R4):

- Core supply from the on-chip switching regulator: `VREG_LX` → L1 3.3 µH → `+1V1` (DVDD ×3 and
  `VREG_FB`), C3 4.7 µF output, C4 4.7 µF on `VREG_VIN`, `VREG_AVDD` through R5 33 Ω / C5 4.7 µF.
  **L1 must be the polarity-marked Abracon AOTA-B201610S3R3-101-T, placed in the orientation and
  layout the guide shows.** Raspberry Pi explicitly says other layouts are at your own risk.
- `VREG_PGND` to GND, routed as the guide describes (not to an arbitrary via).
- **Layout: a copy of Raspberry Pi's RPI-RP2350A-MINIMAL R4-S1 board** (KiCad files, MIT), see
  *Core regulator* under Layout.
- 100 nF per power pin: C6-C11 IOVDD, C12-C14 DVDD, C15 ADC_AVDD, C16 shared by USB_OTP_VDD and
  QSPI_IOVDD (as in the reference).
- Crystal ABM8-272-T3 12 MHz, 15 pF load caps, 1 kΩ on XOUT. Do not substitute.
- USB 27 Ω series resistors R3/R4 close to the chip; D+/D- as a 90 Ω differential pair over
  unbroken GND.
- Flash W25Q32JVSSIQ (4 MB, same size as the RP2350-Zero, so the firmware image is identical).
  R7 (10 kΩ CS pull-up) is DNP as in the reference.
- BOOTSEL: no button. JP1 is a pair of bare pads (open solder jumper) that pull `QSPI_SS` low through
  R8 1 kΩ when bridged with tweezers or a wire while USB is plugged in (or RESET pressed).
  RESET: likewise pads, JP2, from `RUN` to GND; R9 10 kΩ keeps `RUN` high. Firmware updates do not
  need either: the running firmware reboots itself into USB boot (DS2000-Firmware#14, #15; DS2000#35).
- SWD on three bare pads on the bottom, TP1-TP3 (SWCLK, GND, SWDIO, the Debug Probe order); no connector.

**Keys and LEDs.** SW1-SW3 to GPIO0-2 and GND; the firmware uses the internal pull-ups (not
affected by the RP2350-E9 erratum, which concerns pull-downs). The LED data line leaves GPIO5 at
3.3 V and is shifted to 5 V by U5 (74AHCT1G125, TTL-level input), then R10 100 Ω, then the chain
D1 (mute) → D2 (deafen); D2's DOUT is unused. Each LED has its own 100 nF. SK6812 data input needs
0.7 × VDD = 3.5 V at 5 V, which a 3.3 V GPIO does not guarantee; hence the shifter.

## Pinout

| Function | GPIO | Net |
|---|---|---|
| Mute key | GP0 | `KEY_MUTE` |
| Deafen key | GP1 | `KEY_DEAFEN` |
| Disconnect key | GP2 | `KEY_DISCONNECT` |
| LED data (to U5) | GP5 | `LED_DIN_3V3` |

**Firmware impact** (tracked in Mechanix97/DS2000-Firmware#13): the six PWM LED pins (GP5-GP10) are gone. The firmware needs a
WS2812/SK6812 driver on GP5 (arduino-pico ships `Adafruit_NeoPixel`-compatible PIO drivers), and
`pins.h` changes accordingly. The serial protocol does not change: it already carries a colour for
each of the two status LEDs, which map one-to-one onto D1 and D2.

## Bill of materials

The MPN, manufacturer and LCSC number of every assembled part live in the schematic's fields, written
by `tools/bom/set_fields.py` (the parts table is there, with where each number was checked). The same
script copies them onto the board's footprints so the schematic parity check stays clean. Change a
part there and re-run it.

| Refs | Value | MPN | LCSC | Footprint |
|---|---|---|---|---|
| U3 | RP2350A | RP2350A | C42411118 | QFN-60 7×7 mm, thermal vias |
| U4 | Flash 4 MB | W25Q32JVSSIQ | C179173 | SOIC-8 5.3 mm |
| Y1 | 12 MHz | ABM8-272-T3 | C20625731 | 3225 4-pin |
| L1 | 3.3 µH | AOTA-B201610S3R3-101-T | C42411119 | 2016, polarity dot on pad 1 = +1V1 |
| U2 | 3.3 V LDO | AP2112K-3.3TRG1 | C51118 | SOT-23-5 |
| U1 | USB ESD | USBLC6-2SC6 | C7519 | SOT-23-6 |
| U5 | Buffer, TTL in | 74AHCT1G125GW,125 | C12495 | SOT-353 |
| D1, D2 | RGB LED | SK6812MINI-E | C5149201 | reverse mount 3.2×2.8, **bottom** |
| J1 | USB-C 16P | HRO TYPE-C-31-M-12 | C165948 | **bottom** |
| F1 | PTC 500 mA hold, 15 V | Littelfuse 1206L050/15YR | C151162 | 1206 (the 6 V 1206L050YR leaves little margin on VBUS) |
| C1, C2 | 10 µF 25 V X5R | CL21A106KAYNNNE | C15850 | 0805 |
| C3-C5 | 4.7 µF X5R | GRM155R60J475ME47D | C82453 | 0402 (C3/C4 wide land), as the RP2350 reference |
| C6-C16, C19-C22 | 100 nF 16 V X7R | CL05B104KO5NNNC | C1525 | 0402 (C21/C22 bottom) |
| C17, C18 | 15 pF C0G | 0402CG150J500NT | C1548 | 0402 |
| R1, R2 | 5.1 kΩ 1 % | 0402WGF5101TCE | C25905 | 0402 |
| R3, R4 | 27 Ω 1 % | RC0402FR-0727RL | C138021 | 0402, as the reference |
| R5 | 33 Ω 1 % | RC0402FR-0733RL | C138002 | 0402, as the reference |
| R6, R8 | 1 kΩ 1 % | 0402WGF1001TCE | C11702 | 0402 |
| R7 | 10 kΩ, **DNP** | 0402WGF1002TCE | C25744 | 0402 |
| R9 | 10 kΩ 1 % | 0402WGF1002TCE | C25744 | 0402 |
| R10 | 100 Ω 1 % | 0402WGF1000TCE | C25076 | 0402 |
| SW1-SW3 | Keys | Kailh Choc V1 (CPG1350) | — | soldered by hand |
| TP1-TP3, JP1, JP2, J3, H1-H4 | pads, jumpers, wire holes, M2 holes | — | — | bare copper |

**Ordering from JLCPCB.** CI builds the files on every change (KiBot's JLCPCB template, artifact
`kibot-out`, folder `JLCPCB/`): gerbers and drill zipped, the BOM and the placement (CPL) file with
JLC's rotation corrections. Upload the zip as the PCB, then the BOM and CPL for assembly:

- 4 layers, 1.6 mm, **black** mask, white silk, **ENIG**, JLC04161H-7628 stackup
- assembly on **both sides**: D1, D2, C21, C22 and J1 are on the bottom
- JLC's BOM page shows which lines are basic or extended parts (extended ones add a setup fee each)
- check the placement preview, above all the rotation of U3, U5, D1/D2 and J1, before confirming
- the switches are fitted by hand after assembly

## Layout

![rev A, routed](img/rev-a-iso.png)

**State:** placed and fully routed. ERC is clean; DRC reports no unconnected pads, no clearance or
edge errors and full schematic parity (Update PCB from Schematic reports no changes). The only DRC
item left is the intended USB-C footprint change described under *Face and branding*.

**Fixed (mechanical, agreed with the enclosure):**

| Item | Position |
|---|---|
| Outline | 72 × 46 mm, 3 mm corner radius |
| Keys | row of 3 at 18 mm pitch, centres 16 mm from the front edge, middle key on the board's centre line |
| LEDs | D1/D2 on the bottom, 4.7 mm south of the switch centre (the Choc V1 LED window, opposite the switch pins), turned so DOUT faces the next LED |
| Holes | 4 × M2, 4 mm in from each edge, clear of the keycaps |
| USB-C | bottom side, centred on the back edge, face **1.2 mm past the edge** (its front shield tabs keep 0.6 mm of board), opening facing back |
| Debug | **all on the bottom**, back right: SWD pads TP1-TP3 (CK, G, IO), BOOT (JP1), RST (JP2) |
| USB wire holes (J3) | back edge, left |

**Top side, around the RP2350A:** flash top-left by the QSPI pins, core regulator straight above the
VREG pins, USB series resistors beside it above D+/D-, crystal below XIN/XOUT, each decoupling
capacitor in line with its supply pin and its supply pad facing it.

**Core regulator.** Raspberry Pi says their regulator layout should be copied, not improvised: the
inductor's field upsets the output capacitor when it is the wrong way round or placed differently.
Rev A copies it from their KiCad files (RPI-RP2350A-MINIMAL R4-S1, MIT). Our U3 sits the same way
round as theirs, so every offset from VREG_LX (pin 48) carries over unchanged:

| Theirs | Ours | Part | From pin 48 (x, y), mm |
|---|---|---|---|
| C6 | C4 | 4.7 µF, VREG_VIN | (0, −1.16) |
| C7 | C3 | 4.7 µF, +1V1 output | (0, −2.10) |
| L1 | L1 | AOTA-B201610S3R3-101-T, dot (pad 1) on +1V1, left | (0, −3.75) |
| C9 | C5 | 4.7 µF, VREG_AVDD | (2.2, −1.60) |
| R3 | R5 | 33 Ω, VREG_AVDD filter | (3.65, −2.08) *(theirs: (2.2, −3.45))* |
| C12 | C16 | 100 nF, USB_OTP_VDD + QSPI_IOVDD | (−4.1, −3.95) |
| R7/R8 | R3/R4 | 27 Ω, USB | (−3.1 / −2.1, −3.95) |

- The two 4.7 µF caps use the reference's wide 0402 land (`DS2000:C_0402_1005Metric_Wide`, pads
  1.03 mm apart) so VREG_LX runs straight up between them to L1.
- VREG_PGND (47) ties to both caps' ground pads on the top layer, with two vias beside them, as in
  the reference; VREG_FB (50) is taken at the output cap; VREG_AVDD runs clear of L1.
- The tracks are hand-placed by `preroute.py` and locked; `vreg_pours.py` adds the reference's four
  small pours (PGND, VREG_LX, the +1V1 node, VREG_VIN) after autorouting.
- The reference's +3V3 pour under the package (joining VREG_VIN to pins 53/54) becomes a track in the
  same place, between the pin ring and the exposed pad, with one via to the In2 plane.
- **Two departures**, both forced by J1 underneath: the whole RP2350A cluster sits 0.5 mm lower than
  first placed so L1 and C16 clear J1's plastic pegs, and R5 lies beside C5 instead of above it,
  where J1's shell pin comes through. R5 only feeds the 200 µA AVDD filter, away from L1's field.
- No via lands on J1's bottom-side contacts: every via on the board is at least 0.4 mm clear of them.

**Face and branding** (`tools/pcb-generator/branding.py`, safe to re-run on the hand-edited board):

- F.Cu carries a GND pour as well, so all four layers are ground or +3V3 wherever there is no track.
  Its thermal reliefs may resolve to a single spoke (`DS2000.kicad_dru`): every top GND pad already
  reaches In1 through its own via.
- Every reference designator is visible, placed by a script at the first spot beside its part that
  clears pads, holes, vias, other text and the board edge. The three that find no room (C6, C11, R3,
  in the tightest spot around the RP2350A) stay hidden; they are still in the assembly drawings.
- Typography follows mechardo3d.xyz: Sora for "DS2000" and "mechardo labs", IBM Plex Mono for the
  key legends, references and debug labels. The fonts are embedded in the board file; `fonts/` has
  them for editing. KiCad reports `text_thickness` on some characters (5, 6, 9, G, a, e): its check
  measures the thinnest part of each glyph, where curves taper. The main strokes of Plex Mono Bold at
  0.8 mm are about 0.16 mm, above JLC's 0.153 mm minimum.
- The DS2000 logo (back left) is the product logo from mechardo3d.xyz
  (`static/images/DS2000/logo/ds2000-logo.webp`), traced by `tools/logo/gen_ds2000_logo.py` into
  `DS2000.pretty/Logo_DS2000_8.6mm`: the white lettering is silkscreen, the blue arcs become ENIG
  gold, since the board has no blue. "rev A" sits under it; the maker block (Mechardo mark with
  "mechardo / labs") sits back right.
- The Mechardo Labs mark is the mechardo3d.xyz favicon (`tools/logo/gen_logo.py` →
  `DS2000.pretty/Logo_Mechardo_5mm`): a rounded square of ENIG copper whose mask opening leaves the
  "m" covered, so it reads black on gold. The SVG's "m" is a single self-overlapping contour, so it is
  first resolved to its nonzero-fill union; taken as-is the overlaps rendered as holes.
- The USB-C's own silkscreen, which fell past the board edge, is on the fab layer; that is the one
  intended `lib_footprint_mismatch` in the DRC output.

**How it was routed** (`tools/pcb-generator/`, see `pipeline.py`):

1. `gen_pcb.py` builds the board from the schematic's netlist (footprints, nets, fields, symbol
   links), places it, and sets stackup, rules and net classes.
2. `preroute.py` hand-routes what the autorouter should not improvise, as locked tracks: the crystal
   loop (XIN 7.4 mm, XOUT 2.1 mm, crystal output 4.9 mm, no vias, the crystal turned so the two
   nets never cross) and IOVDD pin 20, which runs to its capacitor above the XIN run.
3. `fanout.py` connects every GND and +3V3 pad to its plane: RP2350A supply pins go by a short
   track straight to their decoupling capacitor, pins 53/54 share one via between the USB and QSPI
   escapes, and every other pad gets its own via, each checked for clearance before it is placed.
4. Freerouting routes the rest on F.Cu and B.Cu (In1 and In2 are planes). The top is the product's
   face, so `top_keepout.py` first puts a track keepout on F.Cu over everything but the component
   strip around the RP2350A (x 80.5-119, y 71-93.6): the keys, the logos and the sides stay free of
   tracks and every longer run (+5V to the LEDs, the debug lines, the keys) goes underneath. The
   keepout comes out again after routing. Incremental passes are kept only when KiCad's own DRC
   counts fewer unconnected items, and `cleanup_vias.py` drops any via left dangling.
5. `branding.py` finishes the face (see above) and `stitch.py` ties the F.Cu and B.Cu GND pours to
   In1 with a 3.5 mm grid of vias wherever they clear everything else (113 on rev A).

`pipeline.py` writes to `build/` and never overwrites the committed board: from now on the
`.kicad_pcb` is edited by hand in KiCad.

**3D models:** KiCad's library has no STEP for the Choc V1 switch, the HRO USB-C or the QFN-60, so
`tools/3d-models/gen_models.py` generates simplified ones from datasheet dimensions into
`3dmodels/DS2000.3dshapes/` (referenced through `${KIPRJMOD}`, so they travel with the project). The
switches also carry an MBK-style keycap model for previews and for fitting the enclosure. The Cherry MX
models stay in the generator for reference.

**Choc V1 footprint:** `DS2000.pretty/SW_Kailh_Choc_V1_1.00u`, written by `tools/footprints/gen_choc_v1.py`
from Kailh's CPG1350 datasheet; the geometry matches kiswitch's footprint of the same name (MIT). Its
courtyard follows the 13.8 mm lower housing: the 15 mm flange is 2.2 mm up, so the crystal and C18
tuck under its edge.

**Stackup and rules:** JLCPCB JLC04161H-7628, 4 layers, 1.6 mm, black mask, white silk, ENIG.
In1 is the GND plane, In2 the +3V3 plane, F.Cu and B.Cu GND pours (solid joins on B.Cu). Minimums set for
JLC: 0.1 mm track and clearance, 0.2 mm drill, 0.3 mm copper to edge (0.2 mm only for the LED
cut-outs, in `DS2000.kicad_dru`). Net classes: *Plane* (GND, +3V3) reached by vias, *Power* (+5V,
+1V1, VBUS, VREG_LX) 0.4 mm, *USB* 0.2 mm tracks / 0.2 mm gap.

**Review (2026-09-28).** Every net was checked against Raspberry Pi's RP2350 minimal design and
every footprint's pin mapping against its datasheet, including the SK6812MINI-E: its datasheet
numbers pins differently from KiCad's symbol, but KiCad's reverse-mount footprint is drawn mirrored,
so once placed on the bottom each pad lands on the right function. No wrong connection was found.
The review did find routing the autorouter had done poorly, since fixed: XIN was 14 mm with two
vias and the QSPI clock 35.5 mm with four (now 7.4 mm with none, and 11 mm with two). The USB data
lines carry a ~2 cm stub to the J3 wire holes, which is harmless at full speed (12 Mbit/s).

**Review before ordering:**

- Core regulator: copied from the reference (see above). At assembly, check L1's dot sits on the
  left, towards +1V1 (the silkscreen dot marks it).
- USB: confirm the 90 Ω pair geometry with JLC's impedance calculator for this stackup.
- Under the keycaps (outside each switch's 13.8 mm lower housing) parts are hidden but must stay under
  ~2 mm high: the switch flange is 2.2 mm up and a pressed Choc keycap comes down close to it.
- Confirm the LED side against your switches: the footprint assumes the LED window is on the side
  opposite the two switch pins, as in Kailh's CPG1350 drawing.

## Open items

- [ ] Review the routed board (see Layout, *Review before ordering*)
- [ ] Mute and deafen keycaps must be shine-through or translucent for their LEDs to be visible

## Regenerating the schematic

`tools/schematic-generator/gen_sch.py` produced the first version of `DS2000.kicad_sch`: one titled
box per stage, wired inside each stage, net labels only between stages. `check_netlist.py` compares
KiCad's netlist export with the connectivity declared in the generator; both it and ERC (0
violations) passed. From here on,
**the `.kicad_sch` is the source of truth**: edit it in KiCad. The generator is kept only as a
record of how the first version was derived.
