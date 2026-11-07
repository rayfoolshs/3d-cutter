from __future__ import annotations

import os
import re
import shutil
import threading
import uuid
import webbrowser
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from scripts.cutter_model import Params, build_parts, export_outputs
from scripts.image_to_dxf import image_to_dxf

BASE = Path(__file__).resolve().parent
WEB = BASE / "web"
OUT = BASE / "web_output"
DXF = BASE / "source" / "Lakeland - Transparent (1).dxf"
DEFAULT_ID = "default"
ID_PATTERN = re.compile(r"^(default|[a-f0-9]{12})$")

PARTS = [
    {"name": "ring", "label": "Ring + flange", "color": "#7fa9c4", "visible": True},
    {"name": "plate", "label": "Internal plate", "color": "#a8cfe3", "visible": True},
    {"name": "back", "label": "Flat rear", "color": "#b6d8ea", "visible": True},
    {"name": "bird", "label": "Bird", "color": "#1f4e79", "visible": True},
    {"name": "shield", "label": "Shield", "color": "#2b8a4b", "visible": True},
    {"name": "lime", "label": "Lime background", "color": "#b9d84a", "visible": True},
    {"name": "print_model", "label": "Print model (union)", "color": "#4aa3a3", "visible": False},
]

app = Flask(__name__, static_folder=str(WEB), static_url_path="/web")
UPLOAD_DIR = OUT / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
lock = threading.Lock()
default_lock = threading.Lock()
default_info = None
default_params = Params()


def urls_for(model_id: str):
    prefix = f"/output/{model_id}"
    return {
        "glb": f"{prefix}/model.glb",
        "stl": f"{prefix}/model.stl",
        "3mf": f"{prefix}/model.3mf",
    }


def build_model(params: Params, model_id: str):
    logo_dxf_path = None
    if params.logo_dxf:
        candidate = UPLOAD_DIR / Path(params.logo_dxf).name
        if candidate.exists():
            logo_dxf_path = candidate
    parts, _regions, info = build_parts(DXF, params, logo_dxf_path)
    out_dir = OUT / model_id
    export_outputs(parts, out_dir, stem="model")
    return info


def cleanup_outputs(keep=20):
    if not OUT.exists():
        return
    folders = [p for p in OUT.iterdir() if p.is_dir() and p.name != DEFAULT_ID]
    folders.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    for folder in folders[keep:]:
        shutil.rmtree(folder, ignore_errors=True)


def ensure_default():
    global default_info
    if default_info is not None:
        return default_info
    with default_lock:
        if default_info is not None:
            return default_info
        with lock:
            default_info = build_model(default_params, DEFAULT_ID)
        return default_info


@app.after_request
def no_cache_api(response):
    if request.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/")
def index():
    return send_from_directory(WEB, "index.html")


@app.get("/api/default")
def api_default():
    try:
        info = ensure_default()
    except Exception as exc:
        app.logger.exception("Default model build failed")
        return jsonify({"error": str(exc)}), 500
    return jsonify(
        {
            "params": info.get("resolved_params", default_params.dict()),
            "info": info,
            "urls": urls_for(DEFAULT_ID),
            "parts": PARTS,
        }
    )


@app.post("/api/generate")
def api_generate():
    data = request.get_json(silent=True) or {}
    try:
        params = Params.from_dict(data)
    except (TypeError, ValueError) as exc:
        return jsonify({"error": f"Invalid parameters: {exc}"}), 400
    model_id = uuid.uuid4().hex[:12]
    try:
        with lock:
            info = build_model(params, model_id)
    except Exception as exc:
        app.logger.exception("Model generation failed")
        return jsonify({"error": str(exc)}), 500
    cleanup_outputs()
    return jsonify(
        {
            "params": info.get("resolved_params", params.dict()),
            "info": info,
            "urls": urls_for(model_id),
            "parts": PARTS,
        }
    )


@app.get("/output/<model_id>/<path:filename>")
def output_file(model_id: str, filename: str):
    if not ID_PATTERN.match(model_id):
        return jsonify({"error": "Not found"}), 404
    folder = OUT / model_id
    if not folder.is_dir():
        return jsonify({"error": "Not found"}), 404
    return send_from_directory(folder, filename)

# Image upload endpoint
@app.post("/api/upload")
def api_upload():
    if "image" not in request.files:
        return jsonify({"error": "No image file provided"}), 400
    file = request.files["image"]
    filename = file.filename
    if not filename:
        return jsonify({"error": "Empty filename"}), 400
    from werkzeug.utils import secure_filename

    filename = secure_filename(filename)
    save_path = UPLOAD_DIR / filename
    file.save(save_path)

    stem = Path(filename).stem
    dxf_name = f"{stem}.dxf"
    dxf_path = UPLOAD_DIR / dxf_name
    try:
        image_to_dxf(save_path, dxf_path)
        dxf_url = f"/upload/{dxf_name}"
    except Exception:
        app.logger.exception("Image to DXF conversion failed")
        dxf_name = None
        dxf_url = None

    return jsonify(
        {
            "url": f"/upload/{filename}",
            "dxf_url": dxf_url,
            "dxf_name": dxf_name,
        }
    )


# Serve uploaded files
@app.get("/upload/<filename>")
def serve_upload(filename: str):
    return send_from_directory(UPLOAD_DIR, filename)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    port = int(os.environ.get("PORT", "5050"))
    host = os.environ.get("HOST", "127.0.0.1")
    url = f"http://{host}:{port}"
    print(f"Lakeland Cutter Studio: {url}")
    if os.environ.get("NO_BROWSER") != "1":
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    app.run(host=host, port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
