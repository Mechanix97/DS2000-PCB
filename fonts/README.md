# Fonts

The board's silkscreen uses the typography of [mechardo3d.xyz](https://mechardo3d.xyz):

| Face | Used for |
|---|---|
| Sora Bold | "DS2000" |
| Sora SemiBold | "mechardo labs" |
| IBM Plex Mono SemiBold | key legends |
| IBM Plex Mono Bold | references, debug labels, "rev A" |

`DS2000.kicad_pcb` embeds them, so KiCad renders the board correctly without installing anything.
To **edit** those texts, install the files in this folder first.

`SoraSemiBold-Regular.ttf` is a static instance of the variable Sora font at weight 600, renamed to
the family "Sora SemiBold" so KiCad can pick it by name.

Both families are under the SIL Open Font License 1.1 (`OFL-*.txt`).
