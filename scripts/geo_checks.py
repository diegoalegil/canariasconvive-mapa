#!/usr/bin/env python3
"""Validación geográfica de entities.geojson contra los límites de Canarias.

Comprueba, para cada entidad:
  - que la coordenada cae dentro del archipiélago (rango duro),
  - que cae en tierra (point-in-polygon contra los municipios vendorizados),
  - que el municipio real coincide con el declarado en el Sheet,
  - que el nombre de municipio declarado existe oficialmente.

No corrige nada: emite un informe. Lo usan la GitHub Action (resumen por sync)
y scripts/audit_geo.py (auditoría completa con sugerencias).

Uso:
    python3 scripts/geo_checks.py entities.geojson [--summary]

--summary emite Markdown pensado para GITHUB_STEP_SUMMARY. Siempre sale con
código 0: los problemas de datos no deben tumbar el sync.
"""

import argparse
import json
import math
import os
import sys
import unicodedata

# Rango duro del archipiélago (con margen). Una coordenada fuera de esto no es
# un dato canario válido se mire como se mire.
CANARIAS_RANGE = {"lng": (-18.6, -13.2), "lat": (27.3, 29.6)}

# Bounding boxes por isla (incluyen islotes: La Graciosa va con Lanzarote).
# Más anchos que los del visor: aquí son para detectar isla declarada ≠ coordenada.
ISLAND_BOUNDS = {
    "Tenerife": ((-16.95, 27.95), (-16.10, 28.62)),
    "Gran Canaria": ((-15.90, 27.70), (-15.30, 28.22)),
    "Lanzarote": ((-13.97, 28.78), (-13.30, 29.48)),
    "Fuerteventura": ((-14.60, 27.95), (-13.78, 28.80)),
    "La Palma": ((-18.05, 28.40), (-17.65, 28.90)),
    "La Gomera": ((-17.40, 27.95), (-17.05, 28.25)),
    "El Hierro": ((-18.22, 27.55), (-17.85, 27.90)),
}

# Errores de escritura conocidos en la columna Municipio del Sheet.
# Clave normalizada (minúsculas, sin acentos) → nombre oficial.
MUNI_ALIASES = {
    "puerto la cruz": "Puerto de la Cruz",
}

# Un punto a menos de esta distancia de un municipio se considera costero
# legítimo (la simplificación de los polígonos mete ~20 m de error).
SEA_TOLERANCE_M = 150

DEFAULT_MUNIS_PATH = os.path.join(os.path.dirname(__file__), "canarias-municipios.geojson")


def normalize_name(s):
    s = unicodedata.normalize("NFD", str(s or "").lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn").strip()


def load_municipios(path=DEFAULT_MUNIS_PATH):
    with open(path) as fh:
        return json.load(fh)["features"]


def in_canarias_range(lng, lat):
    return (CANARIAS_RANGE["lng"][0] <= lng <= CANARIAS_RANGE["lng"][1]
            and CANARIAS_RANGE["lat"][0] <= lat <= CANARIAS_RANGE["lat"][1])


def in_island_bounds(lng, lat, island):
    b = ISLAND_BOUNDS.get(island)
    if not b:
        return None  # isla desconocida: no podemos comprobar
    (w, s), (e, n) = b
    return w <= lng <= e and s <= lat <= n


def _point_in_ring(lng, lat, ring):
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if ((yi > lat) != (yj > lat)) and (lng < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def _point_in_geom(lng, lat, geom):
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    for poly in polys:
        if _point_in_ring(lng, lat, poly[0]) and not any(_point_in_ring(lng, lat, h) for h in poly[1:]):
            return True
    return False


def find_municipality(lng, lat, munis):
    """Municipio cuyo polígono contiene el punto, o None (mar / fuera)."""
    for m in munis:
        if _point_in_geom(lng, lat, m["geometry"]):
            return m["properties"]["name"]
    return None


def _dist_m(lng1, lat1, lng2, lat2):
    return math.hypot((lng2 - lng1) * 111320 * math.cos(math.radians(lat1)),
                      (lat2 - lat1) * 110540)


def distance_to_land_m(lng, lat, munis):
    """Distancia aproximada (m) al vértice de costa más cercano."""
    best = None
    for m in munis:
        geom = m["geometry"]
        polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        for poly in polys:
            for px, py in poly[0]:
                d = _dist_m(lng, lat, px, py)
                if best is None or d < best:
                    best = d
    return best


def official_names(munis):
    return {normalize_name(m["properties"]["name"]): m["properties"]["name"] for m in munis}


def resolve_muni_name(raw, officials):
    """Nombre oficial para un valor del Sheet, o None si no se reconoce."""
    key = normalize_name(raw)
    if not key:
        return None
    if key in officials:
        return officials[key]
    if key in MUNI_ALIASES:
        return MUNI_ALIASES[key]
    return None


def audit_features(features, munis):
    """Devuelve dict de listas de problemas. Cada problema referencia la entidad."""
    officials = official_names(munis)
    issues = {
        "out_of_range": [],   # fuera del rango duro de Canarias
        "in_sea": [],         # en ningún municipio y lejos de la costa
        "island_mismatch": [],  # isla declarada no contiene la coordenada
        "muni_mismatch": [],  # municipio real ≠ declarado
        "muni_unknown": [],   # nombre de municipio no oficial (typo)
        "muni_empty": [],     # municipio vacío
    }
    for f in features:
        lng, lat = f["geometry"]["coordinates"]
        p = f.get("properties", {})
        name = p.get("name", "?")
        declared_muni = p.get("municipality", "")
        declared_island = p.get("island", "")
        ent = {"name": name, "lng": lng, "lat": lat,
               "municipality": declared_muni, "island": declared_island,
               "address": p.get("address", ""), "id": p.get("id", "")}

        if not in_canarias_range(lng, lat):
            issues["out_of_range"].append(ent)
            continue

        if declared_island and in_island_bounds(lng, lat, declared_island) is False:
            issues["island_mismatch"].append(ent)

        actual = find_municipality(lng, lat, munis)
        if actual is None:
            dist = distance_to_land_m(lng, lat, munis)
            if dist is None or dist > SEA_TOLERANCE_M:
                issues["in_sea"].append({**ent, "dist_m": round(dist or -1)})
        else:
            ent["actual_municipality"] = actual

        if not declared_muni.strip():
            issues["muni_empty"].append(ent)
        else:
            official = resolve_muni_name(declared_muni, officials)
            if official is None:
                issues["muni_unknown"].append(ent)
            elif actual is not None and normalize_name(actual) != normalize_name(official):
                issues["muni_mismatch"].append(ent)
    return issues


def summary_markdown(issues, total):
    lines = ["### Calidad de datos geográficos", ""]
    n_problems = sum(len(v) for v in issues.values())
    if n_problems == 0:
        lines.append(f"Sin incidencias: las {total} entidades caen en tierra, en su isla y municipio declarados.")
        return "\n".join(lines) + "\n"
    labels = {
        "out_of_range": "Fuera de Canarias (no se publican)",
        "in_sea": "En el mar",
        "island_mismatch": "Isla declarada no coincide",
        "muni_mismatch": "Municipio declarado no coincide",
        "muni_unknown": "Municipio no reconocido (¿typo?)",
        "muni_empty": "Municipio vacío",
    }
    lines.append(f"{n_problems} incidencias sobre {total} entidades — corregir en el Sheet:")
    lines.append("")
    for key, label in labels.items():
        rows = issues[key]
        if not rows:
            continue
        lines.append(f"**{label}** ({len(rows)}):")
        for e in rows:
            extra = ""
            if key == "in_sea" and e.get("dist_m", -1) >= 0:
                extra = f" — a {e['dist_m']} m de la costa"
            elif key == "muni_mismatch":
                extra = f" — declara «{e['municipality']}», cae en «{e.get('actual_municipality', '?')}»"
            elif key == "muni_unknown":
                extra = f" — «{e['municipality']}»"
            elif key == "island_mismatch":
                extra = f" — declara «{e['island']}»"
            lines.append(f"- {e['name']}{extra}")
        lines.append("")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("geojson", help="ruta a entities.geojson")
    ap.add_argument("--municipios", default=DEFAULT_MUNIS_PATH)
    ap.add_argument("--summary", action="store_true", help="salida Markdown para GITHUB_STEP_SUMMARY")
    args = ap.parse_args()

    with open(args.geojson) as fh:
        features = json.load(fh)["features"]
    munis = load_municipios(args.municipios)
    issues = audit_features(features, munis)

    if args.summary:
        sys.stdout.write(summary_markdown(issues, len(features)))
    else:
        json.dump(issues, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    # Siempre 0: el informe no debe tumbar el sync.
    return 0


if __name__ == "__main__":
    sys.exit(main())
