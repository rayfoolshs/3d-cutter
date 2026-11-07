# 3D Cutter

A local 3D editor for generating a 60 mm fondant cutter and embosser, with parametric controls, STL/3MF downloads, and an image → DXF → 3D logo workflow.

> **Note:** The interactive editor runs on a local Flask server. GitHub Pages hosts only this static overview page. To use the editor, clone the repository and run it locally.

## Features

- Parametric cutter: cut diameter, wall thickness, wall height, rim depth, flange width, emboss depths.
- Flat-rear and open-rear print variants.
- Three.js viewer with orbit, top, rear, and iso views.
- Toggle individual parts, change colours, and exploded view.
- Download STL and 3MF directly from the browser.
- Upload a PNG/JPG logo; the server converts it to DXF and regenerates the cutter geometry.
- Download the generated DXF for editing in CAD software.

## Quick start

```bash
git clone https://github.com/rayfoolshs/3d-cutter.git
cd 3d-cutter
./run_editor.sh
```

Open <http://127.0.0.1:5050>.

## Image → DXF pipeline

1. Upload an image in the **Logo placement** panel.
2. The server thresholds and traces the image into outlines.
3. A DXF is written to `web_output/uploads/`.
4. The cutter model is regenerated using that outline as the emboss shape.
5. The DXF appears as a download card in the **Downloads** section.

See [BUILD.md](https://github.com/rayfoolshs/3d-cutter/blob/main/BUILD.md) for implementation details.

## Repository

<https://github.com/rayfoolshs/3d-cutter>

## License and artwork

The Lakeland Senior High School name and logo remain the property of Lakeland Senior High School. The repository contains the supplied source artwork and a 3D model generated from it for the school's cutter project.
