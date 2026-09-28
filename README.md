# DS-2000 PCB

KiCad design for the DS-2000, a three-key Discord control deck: mute, deafen and disconnect. Mute
and deafen are lit from underneath by an RGB LED; disconnect has none. The board is also the device's visible top face; it sits in a
3D-printed tray.

| | |
|---|---|
| MCU | Raspberry Pi RP2350A |
| Keys | 3× Cherry MX compatible in a row, soldered (5-pin footprint, 3-pin fits) |
| LEDs | 2× SK6812MINI-E, reverse-mounted under the mute and deafen keys |
| Connector | USB-C (USB 2.0 full speed), or a cable soldered to J3 |
| Board | 4 layers, 1.6 mm, 72 × 46 mm, black mask, ENIG. RP2350A on show on top; USB-C, LEDs and debug pads underneath |
| Tool | **KiCad 10** |

![DS-2000 rev A](docs/img/rev-a-iso.png)

Design decisions, block descriptions, BOM and open items: [`docs/design-rev-a.md`](docs/design-rev-a.md).

## Pinout

The pinout is defined by the firmware (`DS-2000-Firmware/include/pins.h`). Change it there first.

| Function | GPIO |
|---|---|
| Mute key | GP0 |
| Deafen key | GP1 |
| Disconnect key | GP2 |
| LED data (SK6812 chain, via 5 V level shifter) | GP5 |

## Checks

```sh
kicad-cli sch erc --severity-all DS2000.kicad_sch
kicad-cli sch export netlist --format kicadsexpr -o /tmp/ds2000.net DS2000.kicad_sch
```

## Related repositories

- [DS-2000](https://github.com/Mechanix97/DS-2000): desktop application
- [DS-2000-Firmware](https://github.com/Mechanix97/DS-2000-Firmware): firmware
- [DS2000-Enclosure](https://github.com/Mechanix97/DS2000-Enclosure): enclosure (Fusion 360)

## License

AGPL-3.0, see [`LICENSE`](LICENSE). Whether the hardware should move to CERN-OHL-S is discussed
in #16.
