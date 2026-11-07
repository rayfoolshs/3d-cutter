# Build Notes and Prompt Log

This document records how the image‑to‑DXF workflow was added to the Lakeland Cutter Studio and how the project is put together.

## Architecture

| Layer | Files | Purpose |
|---|---|---|
| Flask server | `app.py` | Serves the editor, exposes JSON APIs, runs model generation. |
| Model builder | `scripts/cutter_model.py` | Builds parametric cutter parts with `trimesh` and `shapely`. |
| Image tracer | `scripts/image_to_dxf.py` | Converts raster images into DXF outlines. |
| Front end | `web/index.html`, `web/app.js`, `web/style.css` | Three.js viewer, parameter controls, upload UI, downloads. |
| Asset source | `source/Lakeland - Transparent (1).dxf` | Original emblem artwork used when no upload is active. |

## Image → DXF → 3D pipeline

1. **Upload** – the browser sends the chosen image to `POST /api/upload` as multipart form data (`image` field).
2. **Store** – the server sanitises the filename with `secure_filename` and saves it under `web_output/uploads/`.
3. **Trace** – `scripts/image_to_dxf.py`:
   - Loads the image with Pillow and converts it to grayscale.
   - Resizes the longest side to 512 px.
   - Computes an Otsu threshold and builds a binary mask (inverting the mask when the foreground exceeds 50 %).
   - Extracts contours with Matplotlib’s `contour` at level 0.5.
   - Converts contours to Shapely polygons, determines parent/child relationships, and subtracts holes.
   - Normalises the result to a 200 mm span and writes a DXF with `OUTER` and `HOLE` layers.
4. **Return metadata** – the API responds with:
   ```json
   {
     "url": "/upload/<image>",
     "dxf_url": "/upload/<image>.dxf",
     "dxf_name": "<image>.dxf"
   }
   ```
5. **Regenerate** – the front end stores `dxf_name` in `state.params.logo_dxf` and calls the normal regeneration flow.
6. **Build geometry** – `build_parts()` detects `logo_dxf_path`; `load_uploaded_logo()` unions the `OUTER` polygons, subtracts `HOLE` polygons, scales the result to the cutter’s fit radius, and returns the same region structure as the original DXF loader.
7. **Download** – the generated DXF is served from `/upload/<name>.dxf` and linked in the Downloads panel.

## API reference

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Serves `web/index.html`. |
| `GET` | `/api/default` | Builds or returns the default model and metadata. |
| `POST` | `/api/generate` | Regenerates the model from the supplied parameters. Accepts `logo_dxf`. |
| `GET` | `/output/<model_id>/<filename>` | Serves generated `.glb`, `.stl`, and `.3mf` files. |
| `POST` | `/api/upload` | Uploads an image and converts it to DXF. |
| `GET` | `/upload/<filename>` | Serves uploaded images and DXFs. |

### Example: generate from an uploaded DXF

```bash
curl -X POST http://127.0.0.1:5050/api/generate \
  -H "Content-Type: application/json" \
  -d '{"logo_dxf":"my-logo.dxf"}'
```

## Prompt log

The following prompts drove this build:

1. “Load the project” → explored the repository and summarised its structure.
2. “Duplicate this project to another directory and call it template” → copied the project to `/Users/rayfoo/Desktop/template`.
3. “Load the website” / “load the site” → started the Flask editor and opened `http://127.0.0.1:5050`.
4. “I want to modify this so I can upload any image and it will fit into the cutter” → added `/api/upload`, the upload UI, and an initial texture overlay.
5. “Uploaded an image but it didn’t change the 3D model” → fixed the overlay rotation, duplicate code block, missing radius field, and cache busting.
6. “I want the uploaded file to be converted to a DXF file so it can be put in 3D space” → added `scripts/image_to_dxf.py`, `Params.logo_dxf`, `load_uploaded_logo()`, DXF download link, and automatic regeneration.
7. “Remove Lakeland SHS from the title” → removed the eyebrow label from the panel header.
8. “Create any MD files relevant to this build or prompts and upload this to GitHub and GitHub Pages” → added this file, updated `README.md`, and prepared the repository for publishing.

## GitHub Pages

GitHub Pages can host static files only. The interactive editor depends on the Flask API, so the full application cannot run on Pages. The Pages site in `docs/` is a static project landing page that links to the repository and explains how to run the editor locally.

To run the real editor, use:

```bash
./run_editor.sh
# open http://127.0.0.1:5050
```

## Dependencies

- Python 3.9+
- Flask, trimesh, shapely, numpy, scipy, ezdxf, matplotlib, Pillow, manifold3d, mapbox-earcut, networkx

See `requirements.txt`.
