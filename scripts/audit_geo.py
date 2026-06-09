#!/usr/bin/env python3
"""Auditoría completa de ubicaciones del mapa + informe de correcciones.

Sobre los checks de geo_checks.py añade:
  - detección de marcadores casi solapados (pares a < 20 m),
  - re-geocodificación con Nominatim (OSM) de las filas con problemas, para
    sugerir la corrección: o bien nuevas coordenadas (si la dirección resuelve
    dentro del municipio declarado) o bien corregir el municipio del Sheet
    (si la coordenada actual ya coincide con la dirección).

El resultado es un informe Markdown para que el equipo corrija el Google Sheet.

Uso:
    python3 scripts/audit_geo.py entities.geojson --out informe.md [--geocode]

--geocode llama a Nominatim (1 petición/segundo, solo filas con problemas).
Sin él, el informe lista los problemas sin sugerencias de coordenadas.
"""

import argparse
import json
import math
import re
import sys
import time
import urllib.parse
import urllib.request

import geo_checks

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "canariasconvive-mapa-audit/1.0 (auditoría de datos del mapa de agentes)"
STACKED_THRESHOLD_M = 20


def dist_m(lng1, lat1, lng2, lat2):
    return math.hypot((lng2 - lng1) * 111320 * math.cos(math.radians(lat1)),
                      (lat2 - lat1) * 110540)


def stacked_pairs(features, threshold_m=STACKED_THRESHOLD_M):
    pts = [(f["properties"].get("name", "?"), *f["geometry"]["coordinates"]) for f in features]
    pairs = []
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            d = dist_m(pts[i][1], pts[i][2], pts[j][1], pts[j][2])
            if d < threshold_m:
                pairs.append((round(d), pts[i][0], pts[j][0]))
    return sorted(pairs)


def geocode(query):
    """Primer resultado de Nominatim para la consulta, o None."""
    url = NOMINATIM_URL + "?" + urllib.parse.urlencode(
        {"q": query, "format": "json", "limit": 1, "countrycodes": "es"})
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())
    except Exception as exc:
        print(f"  aviso: Nominatim falló para {query!r}: {exc}", file=sys.stderr)
        return None
    if not data:
        return None
    return {"lng": float(data[0]["lon"]), "lat": float(data[0]["lat"]),
            "display": data[0].get("display_name", "")}


def suggest_fix(ent, munis, officials, do_geocode):
    """Sugerencia de corrección para una entidad con problema de ubicación.

    Devuelve (tipo, texto). Tipos: 'coords', 'municipio', 'revisar'.
    """
    declared = geo_checks.resolve_muni_name(ent.get("municipality", ""), officials)
    actual = ent.get("actual_municipality")
    address = (ent.get("address") or "").strip()
    # La dirección del Sheet repite municipio y provincia tras el primer punto
    # ("Calle X, 9. Municipio, Provincia"); para geocodificar basta la calle.
    street = address.split(".")[0].strip()

    if not do_geocode:
        return ("revisar", "ejecutar con --geocode para obtener sugerencia")
    if not street:
        return ("revisar", "sin dirección en el Sheet; verificar a mano")

    def try_geocode(anchor):
        result = geocode(f"{street}, {anchor}" if anchor else street)
        time.sleep(1.1)  # política de uso de Nominatim: máx 1 req/s
        if result is None and re.search(r"\d", street):
            # Reintento sin el número de portal (suele romper el match).
            bare = re.sub(r"[,\s]*\d+[a-zA-Z]?\s*$", "", street).strip()
            if bare and bare != street:
                result = geocode(f"{bare}, {anchor}" if anchor else bare)
                time.sleep(1.1)
        return result

    # 1) ¿La dirección existe en el municipio declarado? → corregir coordenadas.
    if declared:
        res = try_geocode(declared)
        if res:
            res_muni = geo_checks.find_municipality(res["lng"], res["lat"], munis)
            if res_muni and geo_checks.normalize_name(res_muni) == geo_checks.normalize_name(declared):
                return ("coords", f"Latitud {res['lat']:.6f} / Longitud {res['lng']:.6f} "
                                  f"({res['display'][:80]})")

    # 2) ¿La dirección existe donde está hoy el punto? → el dato malo es el
    # Municipio del Sheet, no la coordenada.
    if actual and (not declared or geo_checks.normalize_name(actual) != geo_checks.normalize_name(declared)):
        res = try_geocode(actual)
        if res and dist_m(res["lng"], res["lat"], ent["lng"], ent["lat"]) < 500:
            return ("municipio", f"la coordenada es correcta; corregir Municipio a «{actual}»")

    # 3) Sin municipio declarado: anclar a la isla, como pista para revisión.
    if not declared and ent.get("island"):
        res = try_geocode(ent["island"])
        if res:
            return ("revisar", f"sin municipio declarado; candidata Latitud {res['lat']:.6f} / "
                               f"Longitud {res['lng']:.6f} ({res['display'][:60]}) — verificar")

    return ("revisar", f"no se pudo verificar la dirección «{street}» en OSM; revisar a mano")


def build_report(features, munis, do_geocode):
    officials = geo_checks.official_names(munis)
    issues = geo_checks.audit_features(features, munis)
    pairs = stacked_pairs(features)

    lines = [
        "# Informe de correcciones — Mapa de agentes Canarias Convive",
        "",
        f"Auditoría de las {len(features)} entidades publicadas en el mapa. Las",
        "correcciones se aplican en el Google Sheet oficial (columnas Latitud,",
        "Longitud y Municipio); el mapa se actualiza solo en menos de una hora.",
        "",
    ]

    loc_problems = (issues["out_of_range"] + issues["in_sea"] + issues["muni_mismatch"])
    seen = set()
    loc_unique = []
    for e in loc_problems:
        if e["name"] not in seen:
            seen.add(e["name"])
            loc_unique.append(e)

    lines += ["## 1. Ubicaciones erróneas (corregir Latitud/Longitud o Municipio)", ""]
    if not loc_unique:
        lines.append("Ninguna. Todas las entidades caen en su municipio declarado.")
    else:
        lines += ["| Entidad | Dirección en el Sheet | Problema | Corrección sugerida |",
                  "|---|---|---|---|"]
        for e in loc_unique:
            if any(e["name"] == x["name"] for x in issues["out_of_range"]):
                problem = "coordenada fuera de Canarias"
            elif any(e["name"] == x["name"] for x in issues["in_sea"]):
                d = next(x for x in issues["in_sea"] if x["name"] == e["name"]).get("dist_m", -1)
                problem = f"**en el mar** (a {d} m de la costa)" if d >= 0 else "**en el mar**"
            else:
                problem = (f"declara «{e['municipality']}» pero la coordenada cae en "
                           f"«{e.get('actual_municipality', '?')}»")
            kind, text = suggest_fix(e, munis, officials, do_geocode)
            print(f"  - {e['name'][:50]}: {kind}", file=sys.stderr)
            lines.append(f"| {e['name']} | {e.get('address', '')} | {problem} | {text} |")
    lines.append("")

    # Typos conocidos: el pipeline los normaliza con MUNI_ALIASES, pero el dato
    # del Sheet sigue mal escrito y conviene corregirlo en origen.
    typo_rows = [f["properties"] for f in features
                 if geo_checks.normalize_name(f["properties"].get("municipality", ""))
                 in geo_checks.MUNI_ALIASES]

    lines += ["## 2. Municipios mal escritos o vacíos (corregir columna Municipio)", ""]
    rows = issues["muni_unknown"] + issues["muni_empty"] + typo_rows
    if not rows:
        lines.append("Ninguno.")
    else:
        lines += ["| Entidad | Valor actual | Corrección |", "|---|---|---|"]
        for e in issues["muni_unknown"]:
            lines.append(f"| {e['name']} | «{e['municipality']}» | nombre no oficial; revisar |")
        for p in typo_rows:
            alias = geo_checks.MUNI_ALIASES[geo_checks.normalize_name(p["municipality"])]
            lines.append(f"| {p['name']} | «{p['municipality']}» | «{alias}» |")
        for e in issues["muni_empty"]:
            actual = e.get("actual_municipality") or geo_checks.find_municipality(e["lng"], e["lat"], munis)
            fix = f"«{actual}» (según la coordenada)" if actual else "vacío y coordenada en el mar; revisar"
            lines.append(f"| {e['name']} | (vacío) | {fix} |")
    lines.append("")

    lines += ["## 3. Entidades en el mismo punto (informativo)", "",
              "Pares de entidades a menos de 20 m. Si comparten sede es correcto",
              "(el mapa las agrupa y muestra la lista al pulsar); si no, revisar la dirección.", ""]
    if not pairs:
        lines.append("Ninguno.")
    else:
        for d, a, b in pairs:
            lines.append(f"- {d} m: {a} ↔ {b}")
    lines.append("")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("geojson", help="ruta a entities.geojson")
    ap.add_argument("--municipios", default=geo_checks.DEFAULT_MUNIS_PATH)
    ap.add_argument("--out", help="ruta del informe Markdown (por defecto, stdout)")
    ap.add_argument("--geocode", action="store_true",
                    help="consultar Nominatim para sugerir correcciones (1 req/s)")
    args = ap.parse_args()

    with open(args.geojson) as fh:
        features = json.load(fh)["features"]
    munis = geo_checks.load_municipios(args.municipios)

    report = build_report(features, munis, args.geocode)
    if args.out:
        with open(args.out, "w") as fh:
            fh.write(report)
        print(f"Informe escrito en {args.out}", file=sys.stderr)
    else:
        sys.stdout.write(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
