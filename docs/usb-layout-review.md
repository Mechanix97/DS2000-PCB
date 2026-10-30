# USB and ESD layout correction

Reviewed against main `963a34227c064155c3e0f300d7a433a718583071` on 2026-10-30.

J1 D− previously joined the route to R4 at a via, leaving approximately 3.4 mm of
track as a branch to U1. The connector-side netclass pattern also missed the leading
slash in the actual net names. This correction moves the J1 junctions onto U1's
signal pads and gives bottom-layer USB escapes an adjacent GND reference.

![USB copper before and after](img/usb-esd-review.png)

The rows show F.Cu, B.Cu and In2.Cu in board coordinates, viewed from the top.
On the final In2 view, the new rectangular region beneath J1 is GND; the surrounding
plane remains +3V3. The matching reference zone beneath J3 is outside this crop.

## Changes

- J1 D+ and D− vias connect to U1 pads 4 and 6 respectively; the routes to R3/R4
  leave those same pads. U1 remains a shunt protector, not a series component.
- Two priority-10 GND zones on In2 cover the J1 and J3 bottom escapes. Three new
  through GND vias connect these references to In1 and the outer ground pours.
  Each new reference zone fills as one connected island containing a stitching via.
- `/USB_CONN_P` / `/USB_CONN_N` and `/USB_P` / `/USB_N` use KiCad's recognized
  differential-pair suffixes. The USB netclass pattern is `/USB_*`.
- DRC enforces USB track widths of 0.15–0.25 mm and prohibits inner-layer USB tracks.
  The MCU-side pair is limited to 5 mm and 0.5 mm skew. Its unchanged track lengths
  are 4.061 mm and 3.818 mm, with 0.244 mm difference.
- Component positions, footprints, BOM, non-USB tracks and firmware pin mapping are
  unchanged. The regulator isolation introduced by PR #33 is preserved.

## Validation

- KiCad 10.0.4 ERC: zero violations.
- DRC with schematic parity: zero errors, zero unconnected pads, zero parity issues;
  the same 17 pre-existing library/silkscreen warnings remain.
- Every pad's normalized net, position, size and orientation matches the baseline;
  all non-USB tracks/vias match, apart from the three added GND vias.
- KiCad resolves both intended differential pairs and applies the USB class to all four nets.
- Negative checks on a disposable copy trigger each new rule: width, inner-layer
  routing, MCU length and MCU skew.
- Copper geometry checks retain zero In1 copper beneath LX, the isolated top PGND
  island and both regulator ground returns. No F.Cu USB track crosses the In1
  regulator keepout.

## Limits and prototype checks

J1 and J3 remain electrically parallel alternatives. The unused branch remains a
stub; this change does not provide population-selectable isolation. The connector
escapes and U1 approaches are not continuously coupled differential pairs, and the
netclass's preferred gap is not a board-wide gap constraint. Neither the 90 Ω
target nor ESD immunity is certified by these geometric checks.

Before production, validate the fabricated stackup and USB signal quality. On the
prototype, verify ROM USB boot, firmware enumeration and sustained transfers for
both J1 plug orientations and the J3 cable configuration. ESD immunity requires
physical testing; routing improvements alone do not establish a test rating.

References: [TI ESD Protection Layout Guide](https://www.ti.com/lit/an/slva680a/slva680a.pdf)
for avoiding remote TVS branches and providing short discharge paths, and
[KiCad 10 PCB Editor documentation](https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html)
for pair naming, netclass matching and custom-rule semantics.
