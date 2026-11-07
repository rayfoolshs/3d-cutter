from __future__ import annotations

import math
from pathlib import Path

import ezdxf
import numpy as np
from PIL import Image
from shapely.geometry import Polygon
from shapely.ops import unary_union


def _otsu_threshold(gray: np.ndarray) -> int:
    hist = np.bincount(gray.ravel(), minlength=256)
    total = gray.size
    sum_total = float(np.dot(np.arange(256), hist))
    sum_b = 0.0
    w_b = 0
    max_var = 0.0
    threshold = 127
    for t in range(256):
        w_b += int(hist[t])
        if w_b == 0:
            continue
        w_f = total - w_b
        if w_f == 0:
            break
        sum_b += t * hist[t]
        m_b = sum_b / w_b
        m_f = (sum_total - sum_b) / w_f
        var = w_b * w_f * (m_b - m_f) ** 2
        if var > max_var:
            max_var = var
            threshold = t
    return threshold


def _mask_from_image(img: Image.Image) -> np.ndarray:
    gray = img.convert("L")
    max_dim = 512
    longest = max(gray.size)
    if longest > max_dim:
        scale = max_dim / longest
        gray = gray.resize(
            (max(1, int(gray.width * scale)), max(1, int(gray.height * scale))),
            Image.Resampling.LANCZOS,
        )
    arr = np.asarray(gray)
    threshold = _otsu_threshold(arr)
    mask = arr <= threshold
    if mask.mean() > 0.5:
        mask = ~mask
    return mask


def _contours_from_mask(mask: np.ndarray):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig = plt.figure()
    ax = fig.add_subplot(111)
    contour_set = ax.contour(mask.astype(float), levels=[0.5])
    segments = contour_set.allsegs[0] if contour_set.allsegs else []
    plt.close(fig)
    return segments


def image_to_dxf(image_path: Path, dxf_path: Path) -> dict:
    img = Image.open(image_path)
    mask = _mask_from_image(img)
    height, width = mask.shape
    segments = _contours_from_mask(mask)

    polygons = []
    for segment in segments:
        if len(segment) < 3:
            continue
        points = [(float(x), float(height - 1 - y)) for x, y in segment]
        if points[0] != points[-1]:
            points.append(points[0])
        try:
            polygon = Polygon(points)
            if not polygon.is_valid:
                polygon = polygon.buffer(0)
        except Exception:
            continue
        if polygon.is_empty or polygon.area < 4.0:
            continue
        polygons.append(polygon)

    if not polygons:
        raise ValueError("No contours found in the uploaded image.")

    polygons.sort(key=lambda p: p.area, reverse=True)

    parents = []
    for i, polygon in enumerate(polygons):
        best = None
        best_area = math.inf
        point = polygon.representative_point()
        for j, other in enumerate(polygons):
            if i == j:
                continue
            if other.area > polygon.area and other.contains(point):
                if other.area < best_area:
                    best_area = other.area
                    best = j
        parents.append(best)

    children: dict[int, list[int]] = {i: [] for i in range(len(polygons))}
    for i, parent in enumerate(parents):
        if parent is not None:
            children[parent].append(i)

    top_level = []
    for i, polygon in enumerate(polygons):
        if parents[i] is not None:
            continue
        holes = [polygons[j] for j in children[i]]
        if holes:
            polygon = polygon.difference(unary_union(holes))
        if not polygon.is_empty:
            top_level.append(polygon)

    if not top_level:
        raise ValueError("Could not build valid polygons from the image.")

    all_points = []
    for polygon in top_level:
        if polygon.geom_type == "Polygon":
            all_points.extend(polygon.exterior.coords)
        elif polygon.geom_type == "MultiPolygon":
            for piece in polygon.geoms:
                all_points.extend(piece.exterior.coords)
    if not all_points:
        raise ValueError("No valid polygon coordinates found.")

    xs = [x for x, y in all_points]
    ys = [y for x, y in all_points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span = max(max_x - min_x, max_y - min_y)
    if span <= 0:
        raise ValueError("Degenerate image bounds.")

    target_span = 200.0
    scale = target_span / span

    def transform(x: float, y: float) -> tuple[float, float]:
        return ((x - min_x) * scale, (y - min_y) * scale)

    doc = ezdxf.new(dxfversion="R2010")
    doc.layers.add("OUTER")
    doc.layers.add("HOLE")
    msp = doc.modelspace()

    def add_polygon(polygon):
        if polygon.geom_type == "Polygon":
            outer = [transform(x, y) for x, y in polygon.exterior.coords]
            msp.add_lwpolyline(outer, dxfattribs={"layer": "OUTER"})
            for interior in polygon.interiors:
                hole = [transform(x, y) for x, y in interior.coords]
                msp.add_lwpolyline(hole, dxfattribs={"layer": "HOLE"})
        elif polygon.geom_type == "MultiPolygon":
            for piece in polygon.geoms:
                add_polygon(piece)

    for polygon in top_level:
        add_polygon(polygon)

    doc.saveas(dxf_path)
    return {
        "dxf": str(dxf_path),
        "polygons": len(top_level),
        "width": max_x - min_x,
        "height": max_y - min_y,
    }