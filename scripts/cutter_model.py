from __future__ import annotations

import math
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path

import ezdxf
import numpy as np
import trimesh
from shapely.affinity import rotate, scale as shapely_scale, translate
from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
from shapely.validation import make_valid

SECTIONS = 192
FLANGE_THICKNESS = 3.0
EDGE_FLAT = 0.4
CHAMFER_HEIGHT = 1.4
GROOVE_DEPTH = 0.5
SIMPLIFY = 0.02
NOZZLE_OPTIONS = (0.2, 0.4, 0.6, 0.8)


@dataclass
class Params:
    cut_diameter: float = 60.0
    wall: float = 1.8
    height: float = 18.0
    rim_depth: float = 10.0
    flange_width: float = 4.0
    bird_depth: float = 1.5
    shield_depth: float = 1.0
    lime_depth: float = 0.5
    logo_scale: float = 1.0
    logo_offset_x: float = 0.0
    logo_offset_y: float = 0.0
    logo_rotation: float = 0.0
    logo_auto_offset: bool = True
    flat_back: bool = True
    nozzle: float = 0.4
    vents: bool = True
    logo_dxf: str = ""

    @property
    def cut_radius(self) -> float:
        return self.cut_diameter / 2.0

    @property
    def fit_radius(self) -> float:
        return max(5.0, (self.cut_radius - 2.25) * self.logo_scale)

    @property
    def bird_face_z(self) -> float:
        return 3.0 - self.bird_depth

    @property
    def shield_face_z(self) -> float:
        return 3.0 - self.shield_depth

    @property
    def lime_face_z(self) -> float:
        return 3.0 - self.lime_depth

    @property
    def groove_floor_z(self) -> float:
        return self.bird_face_z + GROOVE_DEPTH

    @property
    def flange_bottom(self) -> float:
        return self.height - FLANGE_THICKNESS

    @property
    def plate_top(self) -> float:
        return self.rim_depth + 2.0

    @property
    def feature_top(self) -> float:
        return self.rim_depth + 0.2

    @property
    def min_feature(self) -> float:
        return max(0.4, self.nozzle * 2.0)

    @property
    def bird_buffer(self) -> float:
        return max(0.125, self.nozzle * 0.625)

    @property
    def detail_buffer(self) -> float:
        return max(0.125, self.nozzle * 0.625)

    @property
    def vent_radius(self) -> float:
        return max(0.4, self.nozzle * 0.55)

    @property
    def min_piece_area(self) -> float:
        return max(0.02, 0.05 * (self.nozzle / 0.4) ** 2)

    @property
    def groove_overlap(self) -> float:
        return max(0.01, self.nozzle * 0.05)

    @property
    def recommended_layer_height(self) -> float:
        return round(self.nozzle * 0.4, 2)

    @property
    def upper_cavity(self) -> float:
        return self.flange_bottom - self.plate_top

    def normalized(self) -> "Params":
        def clamp(value, low, high):
            return max(low, min(high, float(value)))

        def as_bool(value):
            if isinstance(value, str):
                return value.strip().lower() not in {"0", "false", "no", "off"}
            return bool(value)

        try:
            requested_nozzle = float(self.nozzle)
        except (TypeError, ValueError):
            requested_nozzle = 0.4
        nozzle = min(NOZZLE_OPTIONS, key=lambda value: abs(value - requested_nozzle))
        rim_depth = clamp(self.rim_depth, 4.0, 12.0)
        flat_back = as_bool(self.flat_back)
        min_height = max(7.0, rim_depth + 3.0) if flat_back else max(18.0, rim_depth + 6.0)

        return Params(
            cut_diameter=clamp(self.cut_diameter, 40.0, 90.0),
            wall=clamp(self.wall, 1.2, 3.0),
            height=clamp(self.height, min_height, 30.0),
            rim_depth=rim_depth,
            flange_width=clamp(self.flange_width, 2.0, 8.0),
            bird_depth=clamp(self.bird_depth, 0.8, 2.5),
            shield_depth=clamp(self.shield_depth, 0.2, 2.0),
            lime_depth=clamp(self.lime_depth, 0.2, 1.5),
            logo_scale=clamp(self.logo_scale, 0.5, 1.0),
            logo_offset_x=clamp(self.logo_offset_x, -10.0, 10.0),
            logo_offset_y=clamp(self.logo_offset_y, -10.0, 10.0),
            logo_rotation=clamp(self.logo_rotation, -180.0, 180.0),
            logo_auto_offset=as_bool(self.logo_auto_offset),
            flat_back=flat_back,
            nozzle=nozzle,
            vents=as_bool(self.vents),
            logo_dxf=str(self.logo_dxf or ""),
        )

    @classmethod
    def from_dict(cls, data: dict | None) -> "Params":
        data = data or {}
        defaults = cls()
        return cls(
            cut_diameter=data.get("cut_diameter", defaults.cut_diameter),
            wall=data.get("wall", defaults.wall),
            height=data.get("height", defaults.height),
            rim_depth=data.get("rim_depth", defaults.rim_depth),
            flange_width=data.get("flange_width", defaults.flange_width),
            bird_depth=data.get("bird_depth", defaults.bird_depth),
            shield_depth=data.get("shield_depth", defaults.shield_depth),
            lime_depth=data.get("lime_depth", defaults.lime_depth),
            logo_scale=data.get("logo_scale", defaults.logo_scale),
            logo_offset_x=data.get("logo_offset_x", defaults.logo_offset_x),
            logo_offset_y=data.get("logo_offset_y", defaults.logo_offset_y),
            logo_rotation=data.get("logo_rotation", defaults.logo_rotation),
            logo_auto_offset=data.get("logo_auto_offset", defaults.logo_auto_offset),
            flat_back=data.get("flat_back", defaults.flat_back),
            nozzle=data.get("nozzle", defaults.nozzle),
            vents=data.get("vents", defaults.vents),
            logo_dxf=data.get("logo_dxf", defaults.logo_dxf),
        ).normalized()

    def dict(self) -> dict:
        return asdict(self)


def largest_polygon(geom):
    if geom.is_empty:
        return geom
    if geom.geom_type == "Polygon":
        return geom
    if geom.geom_type == "MultiPolygon":
        return max(geom.geoms, key=lambda g: g.area)
    if geom.geom_type == "GeometryCollection":
        polys = [g for g in geom.geoms if g.geom_type in ("Polygon", "MultiPolygon")]
        if not polys:
            return Polygon()
        return largest_polygon(unary_union(polys))
    return Polygon()


def clean(geom):
    if geom.is_empty:
        return geom
    if not geom.is_valid:
        geom = make_valid(geom)
    return geom


def filter_pieces(geom, min_area=0.05):
    geom = clean(geom)
    if geom.is_empty:
        return geom
    if geom.geom_type == "Polygon":
        return geom if geom.area >= min_area else Polygon()
    if geom.geom_type == "MultiPolygon":
        pieces = [g for g in geom.geoms if g.area >= min_area]
        return unary_union(pieces) if pieces else Polygon()
    if geom.geom_type == "GeometryCollection":
        pieces = []
        for g in geom.geoms:
            if g.geom_type == "Polygon" and g.area >= min_area:
                pieces.append(g)
            elif g.geom_type == "MultiPolygon":
                pieces.extend([p for p in g.geoms if p.area >= min_area])
        return unary_union(pieces) if pieces else Polygon()
    return Polygon()


def max_radius(geom):
    if geom.is_empty:
        return 0.0
    if geom.geom_type == "Polygon":
        return max(math.hypot(x, y) for x, y in geom.exterior.coords)
    if geom.geom_type == "MultiPolygon":
        return max((max_radius(g) for g in geom.geoms), default=0.0)
    if geom.geom_type == "GeometryCollection":
        return max((max_radius(g) for g in geom.geoms), default=0.0)
    return 0.0


def load_uploaded_logo(dxf_path: Path, params: Params):
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()

    outers = []
    holes = []
    for entity in msp.query("LWPOLYLINE"):
        pts = [(float(x), float(y)) for x, y in entity.get_points("xy")]
        if len(pts) < 3:
            continue
        poly = largest_polygon(clean(Polygon(pts)))
        if poly.is_empty or poly.area <= 0:
            continue
        layer = (entity.dxf.layer or "").strip().upper()
        if layer == "HOLE":
            holes.append(poly)
        else:
            outers.append(poly)

    if not outers:
        raise ValueError("No outer logo polylines found in the uploaded DXF.")

    logo = unary_union(outers)
    if holes:
        logo = logo.difference(unary_union(holes))
    if logo.is_empty:
        raise ValueError("The uploaded DXF produced an empty logo shape.")

    min_x, min_y, max_x, max_y = logo.bounds
    cx = (min_x + max_x) / 2.0
    cy = (min_y + max_y) / 2.0

    boundary_points = []

    def collect_points(geom):
        if geom.is_empty:
            return
        if geom.geom_type == "Polygon":
            boundary_points.extend(geom.exterior.coords)
            for interior in geom.interiors:
                boundary_points.extend(interior.coords)
        elif geom.geom_type == "MultiPolygon":
            for piece in geom.geoms:
                collect_points(piece)
        elif geom.geom_type == "GeometryCollection":
            for piece in geom.geoms:
                collect_points(piece)

    collect_points(logo)
    if not boundary_points:
        raise ValueError("The uploaded DXF has no usable boundary points.")

    emblem_max_radius = max(math.hypot(x - cx, y - cy) for x, y in boundary_points)
    if emblem_max_radius <= 0:
        raise ValueError("The uploaded DXF logo has zero radius.")
    scale = params.fit_radius / emblem_max_radius

    def base_transform(geom):
        transformed = translate(
            shapely_scale(geom, xfact=scale, yfact=scale, origin=(0, 0)),
            xoff=-cx * scale,
            yoff=-cy * scale,
        )
        if params.logo_rotation:
            transformed = rotate(
                transformed,
                -params.logo_rotation,
                origin=(0, 0),
                use_radians=False,
            )
        return transformed

    base_bird = base_transform(logo)

    def apply_offset(geom):
        if geom.is_empty:
            return geom
        return translate(geom, xoff=params.logo_offset_x, yoff=-params.logo_offset_y)

    bird_s = apply_offset(base_bird)

    bird_b = clean(bird_s.buffer(params.bird_buffer, join_style=2, mitre_limit=3)).simplify(
        SIMPLIFY, preserve_topology=True
    )
    bird_face = clean(bird_b).simplify(SIMPLIFY, preserve_topology=True)
    empty = Polygon()
    logo_max_radius = max_radius(bird_b)
    bounds = base_bird.bounds
    scaled_bbox = [bounds[2] - bounds[0], bounds[3] - bounds[1]] if not base_bird.is_empty else [0.0, 0.0]

    return {
        "bird_b": bird_b,
        "bird_face": bird_face,
        "groove": empty,
        "green": empty,
        "lime": empty,
        "info": {
            "logo_max_radius": logo_max_radius,
            "ring_clearance": params.cut_radius - logo_max_radius,
            "fit_radius": params.fit_radius,
            "min_feature": params.min_feature,
            "recommended_layer_height": params.recommended_layer_height,
            "logo_offset_x": params.logo_offset_x,
            "logo_offset_y": params.logo_offset_y,
            "logo_rotation": params.logo_rotation,
            "logo_auto_offset": params.logo_auto_offset,
            "scaled_bbox": scaled_bbox,
        },
    }


def load_regions(dxf_path: Path, params: Params):
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()
    raw = []
    for entity in msp.query("LWPOLYLINE"):
        pts = [(float(x), float(y)) for x, y in entity.get_points("xy")]
        if len(pts) < 3:
            continue
        poly = largest_polygon(clean(Polygon(pts)))
        if poly.is_empty or poly.area <= 0:
            continue
        raw.append({"layer": entity.dxf.layer.strip(), "poly": poly, "pts": pts})

    emblem = [p for p in raw if max(y for x, y in p["pts"]) > 60.0]
    if not emblem:
        raise ValueError("No emblem polylines found in the DXF.")
    navy = [p for p in emblem if p["layer"] == "NAVY"]
    if not navy:
        raise ValueError("No NAVY emblem polylines found in the DXF.")
    bird = max(navy, key=lambda p: p["poly"].area)
    details = unary_union([p["poly"] for p in navy if p is not bird])
    green = unary_union([p["poly"] for p in emblem if p["layer"] == "GREEN"])
    lime = unary_union([p["poly"] for p in emblem if p["layer"] == "LIME"])

    xs = [x for p in emblem for x, y in p["pts"]]
    ys = [y for p in emblem for x, y in p["pts"]]
    cx = (min(xs) + max(xs)) / 2.0
    cy = (min(ys) + max(ys)) / 2.0
    emblem_max_radius = max(math.hypot(x - cx, y - cy) for x, y in zip(xs, ys))
    scale = params.fit_radius / emblem_max_radius

    def base_transform(geom):
        transformed = translate(
            shapely_scale(geom, xfact=scale, yfact=scale, origin=(0, 0)),
            xoff=-cx * scale,
            yoff=-cy * scale,
        )
        if params.logo_rotation:
            transformed = rotate(
                transformed,
                -params.logo_rotation,
                origin=(0, 0),
                use_radians=False,
            )
        return transformed

    base_bird = base_transform(bird["poly"])
    base_details = base_transform(details)
    base_green = base_transform(green)
    base_lime = base_transform(lime)

    if params.logo_auto_offset:
        emblem_union = unary_union([base_bird, base_green, base_lime])
        if not emblem_union.is_empty:
            centroid = emblem_union.centroid
            params.logo_offset_x = round(-centroid.x, 1)
            params.logo_offset_y = round(centroid.y, 1)

    def apply_offset(geom):
        return translate(
            geom,
            xoff=params.logo_offset_x,
            yoff=-params.logo_offset_y,
        )

    bird_s = apply_offset(base_bird)
    details_s = apply_offset(base_details)
    green_s = apply_offset(base_green)
    lime_s = apply_offset(base_lime)

    bird_b = clean(bird_s.buffer(params.bird_buffer, join_style=2, mitre_limit=3)).simplify(
        SIMPLIFY, preserve_topology=True
    )
    details_b = clean(
        details_s.buffer(params.detail_buffer, join_style=2, mitre_limit=3).intersection(bird_b)
    ).simplify(SIMPLIFY, preserve_topology=True)
    bird_face = clean(bird_b.difference(details_b)).simplify(SIMPLIFY, preserve_topology=True)
    green_clean = filter_pieces(
        green_s.difference(bird_b).simplify(SIMPLIFY, preserve_topology=True),
        params.min_piece_area,
    )
    lime_clean = filter_pieces(
        lime_s.difference(green_s).difference(bird_b).simplify(SIMPLIFY, preserve_topology=True),
        params.min_piece_area,
    )

    logo_max_radius = max(
        max_radius(bird_b),
        max_radius(green_clean),
        max_radius(lime_clean),
    )
    return {
        "bird_b": bird_b,
        "bird_face": bird_face,
        "groove": details_b,
        "green": green_clean,
        "lime": lime_clean,
        "info": {
            "logo_max_radius": logo_max_radius,
            "ring_clearance": params.cut_radius - logo_max_radius,
            "fit_radius": params.fit_radius,
            "min_feature": params.min_feature,
            "recommended_layer_height": params.recommended_layer_height,
            "logo_offset_x": params.logo_offset_x,
            "logo_offset_y": params.logo_offset_y,
            "logo_rotation": params.logo_rotation,
            "logo_auto_offset": params.logo_auto_offset,
            "scaled_bbox": [
                (max(xs) - min(xs)) * scale,
                (max(ys) - min(ys)) * scale,
            ],
        },
    }


def extrude_geometry(geom, z0, z1):
    if geom.is_empty:
        return []
    if geom.geom_type == "GeometryCollection":
        meshes = []
        for g in geom.geoms:
            meshes.extend(extrude_geometry(g, z0, z1))
        return meshes
    if geom.geom_type == "MultiPolygon":
        meshes = []
        for g in geom.geoms:
            meshes.extend(extrude_geometry(g, z0, z1))
        return meshes
    if geom.geom_type != "Polygon":
        return []
    g = orient(clean(geom), sign=1.0)
    if g.is_empty or g.area < 1e-6:
        return []
    mesh = trimesh.creation.extrude_polygon(g, height=z1 - z0)
    mesh.apply_translation([0.0, 0.0, z0])
    return [mesh]


def union_meshes(meshes):
    meshes = [m for m in meshes if m is not None and len(m.faces) > 0]
    if not meshes:
        return None
    if len(meshes) == 1:
        return meshes[0]
    return trimesh.boolean.union(meshes, engine="manifold")


def build_parts(dxf_path: Path, params: Params, logo_dxf_path: Path | None = None):
    params = params.normalized()
    if params.flat_back:
        params.vents = False
    if logo_dxf_path is not None and Path(logo_dxf_path).exists():
        regions = load_uploaded_logo(Path(logo_dxf_path), params)
    else:
        regions = load_regions(dxf_path, params)
    cut_r = params.cut_radius

    profile = np.array(
        [
            (cut_r, 0.0),
            (cut_r + EDGE_FLAT, 0.0),
            (cut_r + params.wall, CHAMFER_HEIGHT),
            (cut_r + params.wall, params.flange_bottom),
            (cut_r + params.wall + params.flange_width, params.flange_bottom),
            (cut_r + params.wall + params.flange_width, params.height),
            (cut_r, params.height),
            (cut_r, 0.0),
        ],
        dtype=float,
    )
    ring = trimesh.creation.revolve(profile, sections=SECTIONS)

    plate_base = trimesh.creation.cylinder(
        radius=cut_r + 0.2,
        height=params.plate_top - params.rim_depth,
        sections=SECTIONS,
    )
    plate_base.apply_translation([0.0, 0.0, (params.rim_depth + params.plate_top) / 2.0])

    plate = plate_base
    if params.vents:
        vents = []
        for angle_deg in (45.0, 225.0):
            angle = math.radians(angle_deg)
            vent = trimesh.creation.cylinder(radius=params.vent_radius, height=4.0, sections=32)
            vent.apply_translation(
                [(cut_r - 1.0) * math.cos(angle), (cut_r - 1.0) * math.sin(angle), params.rim_depth + 1.0]
            )
            vents.append(vent)
        plate = trimesh.boolean.difference([plate_base] + vents, engine="manifold")
    plate.merge_vertices()
    plate.update_faces(plate.nondegenerate_faces())
    plate.update_faces(plate.unique_faces())
    plate.remove_unreferenced_vertices()
    plate.fix_normals()

    back = None
    if params.flat_back:
        back = trimesh.creation.cylinder(
            radius=cut_r,
            height=params.height - params.plate_top,
            sections=SECTIONS,
        )
        back.apply_translation([0.0, 0.0, (params.plate_top + params.height) / 2.0])
        back.merge_vertices()
        back.update_faces(back.nondegenerate_faces())
        back.update_faces(back.unique_faces())
        back.remove_unreferenced_vertices()
        back.fix_normals()

    bird_face_meshes = extrude_geometry(regions["bird_face"], params.bird_face_z, params.feature_top)
    groove_meshes = extrude_geometry(
        regions["groove"].buffer(params.groove_overlap, join_style=2),
        params.groove_floor_z,
        params.feature_top,
    )
    shield_meshes = extrude_geometry(regions["green"], params.shield_face_z, params.feature_top)
    lime_meshes = extrude_geometry(regions["lime"], params.lime_face_z, params.feature_top)

    bird = union_meshes(bird_face_meshes + groove_meshes)
    shield = union_meshes(shield_meshes)
    lime = union_meshes(lime_meshes)

    parts_for_union = [ring, plate]
    if back is not None:
        parts_for_union.append(back)
    for part in (bird, shield, lime):
        if part is not None:
            parts_for_union.append(part)
    union = trimesh.boolean.union(parts_for_union, engine="manifold")
    union.merge_vertices()
    union.update_faces(union.nondegenerate_faces())
    union.update_faces(union.unique_faces())
    union.remove_unreferenced_vertices()
    union.fix_normals()

    parts = {
        "ring": ring,
        "plate": plate,
        "back": back,
        "bird": bird,
        "shield": shield,
        "lime": lime,
        "print_model": union,
    }
    parts = {name: mesh for name, mesh in parts.items() if mesh is not None and len(mesh.faces) > 0}

    warnings = []
    if regions["info"]["ring_clearance"] < 0.5:
        warnings.append(
            "Logo overlaps the cutting ring. Reduce the logo scale or move it back toward the centre."
        )
    elif regions["info"]["ring_clearance"] < 1.5:
        warnings.append(
            f"Logo is close to the cutting ring ({regions['info']['ring_clearance']:.2f} mm clearance)."
        )
    if not params.flat_back and params.upper_cavity < 2.0:
        warnings.append("Upper cavity is very shallow; increase the height or rim depth.")
    vent_clearance = (cut_r - 1.0 - params.vent_radius) - (regions["info"]["logo_max_radius"])
    if params.vents and vent_clearance < 0.4:
        warnings.append(f"Air vent clearance is tight ({vent_clearance:.2f} mm).")
    if params.nozzle >= 0.6:
        warnings.append("0.6/0.8 mm nozzle: the finest feather lines will merge. Use 0.4 mm for detail.")
    if params.nozzle <= 0.2:
        warnings.append("0.2 mm nozzle: excellent detail, but slower and more fragile.")

    info = {
        "cut_diameter": params.cut_diameter,
        "overall_diameter": 2.0 * (cut_r + params.wall + params.flange_width),
        "height": params.height,
        "rim_depth": params.rim_depth,
        "plate_top": params.plate_top,
        "wall": params.wall,
        "flange_width": params.flange_width,
        "emboss_bird": params.bird_depth,
        "emboss_shield": params.shield_depth,
        "emboss_lime": params.lime_depth,
        "logo_scale": params.logo_scale,
        "logo_fit_radius": regions["info"]["fit_radius"],
        "ring_clearance": regions["info"]["ring_clearance"],
        "logo_offset_x": params.logo_offset_x,
        "logo_offset_y": params.logo_offset_y,
        "logo_rotation": params.logo_rotation,
        "logo_auto_offset": params.logo_auto_offset,
        "flat_back": params.flat_back,
        "nozzle": params.nozzle,
        "min_feature": params.min_feature,
        "recommended_layer_height": params.recommended_layer_height,
        "vent_radius": params.vent_radius,
        "upper_cavity": params.upper_cavity,
        "volume": float(union.volume),
        "watertight": bool(union.is_watertight),
        "warnings": warnings,
        "resolved_params": params.dict(),
    }
    return parts, regions, info


def transform_to_print(mesh):
    transform = trimesh.transformations.rotation_matrix(math.pi, [1.0, 0.0, 0.0])
    printed = mesh.copy()
    printed.apply_transform(transform)
    printed.apply_translation([0.0, 0.0, -printed.bounds[0][2]])
    return printed


def write_3mf(mesh, path: Path):
    vertices = mesh.vertices
    faces = mesh.faces
    vertex_lines = [
        f'<vertex x="{x:.6f}" y="{y:.6f}" z="{z:.6f}"/>' for x, y, z in vertices
    ]
    face_lines = [
        f'<triangle v1="{int(a)}" v2="{int(b)}" v3="{int(c)}"/>' for a, b, c in faces
    ]
    model = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<model unit="millimeter" xml:lang="en-US" '
        'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">\n'
        '  <metadata name="Title">Lakeland Fondant Cutter</metadata>\n'
        '  <metadata name="Designer">OpenCode</metadata>\n'
        '  <resources>\n'
        '    <object id="1" type="model">\n'
        '      <mesh>\n'
        '        <vertices>\n          '
        + "\n          ".join(vertex_lines)
        + "\n        </vertices>\n"
        '        <triangles>\n          '
        + "\n          ".join(face_lines)
        + "\n        </triangles>\n"
        '      </mesh>\n'
        '    </object>\n'
        '  </resources>\n'
        '  <build>\n'
        '    <item objectid="1"/>\n'
        '  </build>\n'
        '</model>\n'
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
        '  <Default Extension="rels" '
        'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
        '  <Default Extension="model" '
        'ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>\n'
        '</Types>\n'
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
        '  <Relationship Target="/3D/3dmodel.model" Id="rel0" '
        'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>\n'
        '</Relationships>\n'
    )
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", rels)
        archive.writestr("3D/3dmodel.model", model)


def export_outputs(parts, out_dir: Path, stem="model", include_design=False):
    out_dir.mkdir(parents=True, exist_ok=True)
    print_parts = {
        name: transform_to_print(mesh)
        for name, mesh in parts.items()
        if name != "print_model"
    }
    union_print = transform_to_print(parts["print_model"])

    stl_path = out_dir / f"{stem}.stl"
    tmf_path = out_dir / f"{stem}.3mf"
    glb_path = out_dir / f"{stem}.glb"
    union_print.export(stl_path, file_type="stl")
    write_3mf(union_print, tmf_path)

    scene = trimesh.Scene()
    for name, mesh in print_parts.items():
        scene.add_geometry(mesh, node_name=name, geom_name=name)
    scene.add_geometry(union_print, node_name="print_model", geom_name="print_model")
    scene.export(glb_path, file_type="glb")

    result = {
        "stl": stl_path,
        "3mf": tmf_path,
        "glb": glb_path,
    }
    if include_design:
        design_path = out_dir / f"{stem}_design.stl"
        parts["print_model"].export(design_path, file_type="stl")
        result["design_stl"] = design_path
    return result
