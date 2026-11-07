# Printing the 3D Cutter

This guide covers the checked-in **open-rear** model and the editor's **flat-rear** model. For the current flat-rear / auto-offset version, download the STL or 3MF from the editor's **Downloads** section.

## Which version are you printing?

| Version | Source | Rear | Logo position | Supports |
|---|---|---|---|---|
| **Flat rear** | Editor → Downloads (recommended) | Complete flat disc | Auto-offset to the visual centre | **None** |
| **Open rear** | `lakeland_60mm_fondant_cutter_print.3mf` / `.stl` | Open cavity | Bounding-box centre | Tree supports under the internal plate |

The flat-rear version is the default in the editor. The checked-in STL/3MF files are the open-rear version.

## Files

| File | Purpose |
|---|---|
| `lakeland_60mm_fondant_cutter_print.3mf` | Checked-in open-rear Bambu model. |
| `lakeland_60mm_fondant_cutter_print.stl` | Checked-in open-rear STL, print orientation. |
| `lakeland_60mm_fondant_cutter.stl` | Design/inspection orientation — **not** for printing. |
| `preview.png` | Model layout and cross-section preview. |
| `editor_preview.png` | Editor screenshot. |
| `app.py`, `run_editor.sh` | Local 3D editor. |
| `requirements.txt` | Python dependencies. |
| `README.md` | Project overview and editor instructions. |

The 3MF is a **model-only** 3MF. Bambu Studio will slice it using the settings below; it is not a pre-sliced `.gcode.3mf`. If Bambu Studio does not import the 3MF, import the matching STL instead.

## Run the editor

```bash
cd "/Users/rayfoo/Desktop/Logo Cookie Cutter"
./run_editor.sh
```

The first run creates `.venv`, installs dependencies, starts the server, and opens **http://127.0.0.1:5050**. Use `NO_BROWSER=1 ./run_editor.sh` to skip auto-opening.

The editor:

- loads the model in a 3D viewer with orbit/zoom/pan;
- shows the ring, internal plate, flat rear, bird, shield, and lime background as separate parts;
- lets you change part visibility and colours;
- edits cut diameter, wall thickness, wall height, rim depth, flange width, emboss depths, logo scale, auto-offset/manual centring, rotation, flat rear, air vents, and **print nozzle**;
- auto-updates the 3D view after a short pause (or with **Regenerate**) and keeps the camera view;
- refreshes the STL/3MF downloads after each update.

### Logo placement

- **Auto offset** is on by default. It centres the logo using its visual mass.
- Uncheck **Auto offset** to fine-tune the X/Y offsets manually.
- **Center** re-enables auto offset and recentres the logo.
- **Top**, **Iso**, and **Rear** are fixed camera views. Rear view hides the front parts so you can inspect the flat back.
- The viewer shows the print orientation; the fondant imprint is the vertical mirror of that view. Centring is unaffected.
- Keep at least about 1.5 mm between the logo and the cutting ring; the editor warns if it gets too close or overlaps.

## Default dimensions

- **60.0 mm cut diameter**
- **71.6 mm overall diameter** at the press flange
- **18.0 mm wall height** by default
- **1.8 mm wall thickness**
- **10.0 mm rim depth** by default
- **1.5 mm bird emboss**, **1.0 mm shield emboss**, **0.5 mm lime background emboss**
- **3 mm fondant** design target
- Flat-rear default volume: approximately **36,808 mm³**
- Open-rear checked-in volume: approximately **19,844 mm³**
- Emblem clearance to the cutting ring: approximately **2.0 mm**

The logo is the **bird + shield emblem only**. The full “LAKELAND SENIOR HIGH SCHOOL” wording was omitted because it would be about 1.7 mm tall at 60 mm and would not print cleanly with a 0.4 mm nozzle.

## Wall height, rim depth, and flat rear

- **Wall height** is the outer ring height. With the flat rear it can go down to **7 mm** when the rim depth is 4 mm. The open rear needs at least **18 mm**. The editor clamps the wall height to a safe minimum based on rim depth and flat-rear mode.
- **Rim depth** is the cutting wall height below the embosser plate, adjustable from **4 to 12 mm**. The default is 10 mm. At 4 mm the plate is 1 mm above a 3 mm fondant sheet.
- **Flat rear** is on by default. It fills the back with a complete flat disc, so the rear is a solid, flat press surface. Print it rear-down with **no supports**. Air vents are disabled.
- **Open rear** restores the hollow-back version. Use tree supports under the internal plate; the air vents can be used.

## Material

**PETG is recommended** for durability, moisture resistance, and easier cleaning. Dry it before printing.

- PETG: 245 °C nozzle, 75 °C bed, 30–50 % part cooling.
- PLA: 210–220 °C nozzle, 60 °C bed, 100 % cooling — prototype/display only.

FDM parts are not inherently food-safe. See **Food safety** below.

## Print nozzle choice

The editor's **Print nozzle** setting changes the minimum feature cleanup, vent size, and recommended layer height. Choose the same nozzle in Bambu Studio.

| Nozzle | Recommended layer | Best for | Trade-off |
|---|---|---|---|
| **0.2 mm** | 0.08 mm | Maximum feather and eye detail | Slowest; finest features are more fragile |
| **0.4 mm** | 0.16 mm (0.12 mm fine) | **Recommended all-round detail** | Good balance of detail, strength, and speed |
| **0.6 mm** | 0.24 mm | Stronger cutter, faster print | Finest feather lines start to merge |
| **0.8 mm** | 0.32 mm | Fastest, strongest cutter | Logo becomes bold/simplified; fine detail is lost |

The checked-in open-rear files were generated for **0.4 mm** at a 0.16 mm layer height.

## Orientation and supports

### Flat rear (default)

- Place the **complete flat rear on the build plate**.
- The **logo faces up** inside the cutter.
- The **cutting edge is at the top**.
- **No supports.**
- First layer should be a **solid disc**. Add a **5 mm brim**.

### Open rear

- Place the **flange ring on the build plate**.
- The **logo faces up** inside the cutter.
- Use **tree/organic supports with “build plate only”** under the internal plate.
- Do not paint supports onto the logo features.
- Add a **5 mm brim**.

In both modes, do **not** rotate the print file. If the first layer shows the logo or the cavity instead of a solid disc, the model is upside down.

## Bambu Studio settings (P1S, selected nozzle)

| Setting | Value |
|---|---|
| Printer | Bambu Lab P1S with the selected nozzle (0.2 / 0.4 / 0.6 / 0.8 mm) |
| Filament | Generic PETG (dry) |
| Process | 0.16 mm Optimal, or 0.12 mm Fine for sharper logo detail (0.4 mm nozzle) |
| Wall loops | 4 |
| Top/bottom layers | 5 top / 4 bottom |
| Infill | 20 % gyroid |
| Supports | **None with Flat rear (default)**; with Flat rear off: tree (auto), build plate only, 30° threshold |
| Support top Z distance | 0.2 mm |
| Support interface layers | 2 |
| Brim | 5 mm |
| Raft | None |
| Ironing | Optional; skip for the first print (it can soften the 0.5 mm feather grooves) |
| Nozzle temperature | 245 °C (first layer 250 °C) |
| Bed temperature | 75 °C |
| Outer wall speed | 50 mm/s |
| Inner wall speed | 90 mm/s |
| Infill speed | 120 mm/s |
| Travel speed | 300–500 mm/s |
| Retraction | 0.8–1.2 mm at 20–30 mm/s |
| Z-hop | 0.2 mm |
| Build plate | Textured PEI + glue stick as release agent |

Expected print time is roughly **2–3 hours** at 0.16 mm, or **3–4 hours** at 0.12 mm, depending on supports and speeds.

## Bambu Studio workflow

1. Install/open **Bambu Studio**.
2. Select the **Bambu Lab P1S** with the same nozzle you chose in the editor, and **Generic PETG**.
3. Import the editor's `model.3mf` (flat rear) or the checked-in `lakeland_60mm_fondant_cutter_print.3mf` (open rear).
4. Confirm the orientation:
   - Flat rear: flat rear on the bed, logo up.
   - Open rear: flange on the bed, logo up.
5. Apply the settings above.
6. Supports:
   - Flat rear: **none**.
   - Open rear: **tree (auto)**, build plate only, 30° threshold, 0.2 mm top Z.
7. Add a **5 mm brim**.
8. Slice and preview:
   - Flat rear: first layer is a solid disc.
   - Open rear: first layer is the flange ring; supports under the internal plate only.
   - Top: cutting edge and raised logo features.
9. Send to the printer.

### LAN mode (P1S)

On the printer:

1. **Settings → Network → LAN Only Mode**.
2. Note the printer IP address and LAN access code.

In Bambu Studio:

1. Open the **Device** tab.
2. **Add Printer → LAN mode**.
3. Enter the IP address and access code.
4. Send the sliced print.

Alternatively, export the sliced `.gcode.3mf` to the SD card and print from the printer screen. The computer and printer must be on the same network for LAN transfer.

## Post-processing

1. Remove the brim.
2. Remove supports only if you printed the open-rear version. Use needle-nose pliers; avoid the logo faces.
3. Trim strings from the cutting edge with a sharp knife.
4. If the flange has elephant's foot, sand the outside edge lightly with 400–800 grit. Do not round the cutting edge.
5. Wash with warm water and mild soap, rinse, and dry fully.
6. For the open rear, check that both air vents are clear.

## Food safety

- FDM layer lines can harbour bacteria, and PETG/PLA filaments and colourants are not automatically food-safe.
- For occasional use, place a food-safe barrier (cling film or acetate) between the cutter and the fondant, or use a certified food-safe coating on contact surfaces.
- Hand wash only. Do **not** put it in a dishwasher; PETG can deform.
- Do not use with hot food or leave it in direct sunlight.
- For commercial or repeated food production, use a food-safe moulding process (for example, a silicone mould cast from this printed master) rather than bare FDM plastic.

## Using the cutter

1. Roll the fondant to **3 mm** thickness on a food-safe board.
2. Place the cutter with the **cutting edge down** and the **logo inside**.
3. Press down firmly and evenly on the **flat rear** (or flange) until the rim reaches the board.
4. The rim cuts the 60 mm disc; the emblem presses into the top surface.
5. Lift the cutter carefully. If the fondant sticks, push it out through the cutting-edge opening.
6. The bird is the deepest impression (1.5 mm), the shield is 1.0 mm, and the lime background is 0.5 mm. The feather lines and eye are raised details within the bird.

The **flat rear is the press surface**. The logo is on the opposite **cutting side**. If you are looking at a completely flat black surface, you are looking at the back — flip the cutter over.

The logo is **not mirrored**. It is on the underside of the plate, so the fondant imprint reads correctly.

## Troubleshooting

| Problem | Fix |
|---|---|
| The flat black side is completely flat | That is the rear/press side. The logo is on the opposite cutting side; flip the cutter over. |
| The black logo is flush on the cutting side | The print is upside down. The flat rear must be on the bed and the logo must face up. The first layer should be a solid disc. Use the print 3MF and do not rotate it. |
| Logo details are soft or missing | Use 0.12 mm layers, dry the PETG, lower outer-wall speed to 35–45 mm/s, and confirm no supports touch the logo. |
| Stringing | Dry the filament, lower nozzle to 240 °C, increase retraction slightly, enable z-hop. |
| Supports are difficult to remove | Use tree supports, 0.2 mm top Z, 2 interface layers; remove through the flange opening. Flat rear needs no supports. |
| First layer not sticking | Clean the PEI plate, apply glue stick, raise bed to 75–80 °C, keep the 5 mm brim. |
| Flange edge has a bulge (elephant's foot) | Sand the outside of the flange; the cutting edge is at the top and is not affected. |
| Cutter does not cut cleanly | The edge is a 0.4 mm flat with a 45° outside chamfer. Press firmly; if the fondant is thicker than 3 mm, roll it thinner. Lightly sharpen only the outside chamfer with 800 grit. |
| Emboss is too shallow | Press until the rim touches the board. The design gives 1.5 mm maximum depth. |
| Emboss is too deep | The fondant is thicker than 3 mm; roll it to 3 mm. |
| Wall height will not go lower | The editor clamps it to a safe minimum: 7 mm with the flat rear at a 4 mm rim; 18 mm with the open rear. |
| Print is slightly undersized | PETG shrinkage is small. If needed, scale to 100.2–100.5 % in Bambu Studio and test on scrap fondant. |
| 3MF will not import | Import the matching STL instead; it has the same print orientation. |

## Regenerating or editing

The editor uses `scripts/cutter_model.py`. The checked-in static files were generated with `scripts/generate_cutter.py` from `source/Lakeland - Transparent (1).dxf`:

```bash
python scripts/generate_cutter.py
```

Run it from a Python environment with the project dependencies installed.

- `scripts/generate_cutter.py` is the original static CLI and produces the open-rear checked-in files.
- `scripts/cutter_model.py` is the parametric model builder used by the editor and supports the flat rear, wall height, rim depth, auto offset, and nozzle settings.

## Repository and logo

<https://github.com/rayfoolshs/3d-cutter>

The Lakeland Senior High School name and logo remain the property of Lakeland Senior High School. The source artwork and 3D model are included for the school's cutter project.
