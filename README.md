# Canarias Convive · Mapa de Agentes

<p>
  <img alt="Estado: en producción" src="https://img.shields.io/badge/estado-en%20producci%C3%B3n-2EA043?style=flat-square" />
  <a href="https://canariasconvive.com/mapa-interactivo/"><img alt="Ver en vivo" src="https://img.shields.io/badge/ver%20en%20vivo-canariasconvive.com-0D4E47?style=flat-square" /></a>
  <img alt="Mapbox GL JS 3.21" src="https://img.shields.io/badge/Mapbox%20GL%20JS-3.21-000000?style=flat-square&logo=mapbox&logoColor=white" />
  <img alt="Datos: sync horario" src="https://img.shields.io/badge/datos-sync%20horario-blue?style=flat-square&logo=githubactions&logoColor=white" />
  <img alt="Licencia MIT" src="https://img.shields.io/badge/licencia-MIT-555?style=flat-square" />
</p>

> Mapa interactivo **oficial** del programa **Canarias Convive** (Fundación General de la Universidad de La Laguna).
> **Este repositorio aloja el mapa real** que se muestra, en producción, en la web del programa.

🌍 **En producción:** <https://canariasconvive.com/mapa-interactivo/>

<p align="center">
  <a href="https://canariasconvive.com/mapa-interactivo/">
    <img alt="Canarias Convive — Mapa de agentes" src="canarias-convive.svg" width="440" />
  </a>
</p>

---

## Qué es

Un mapa interactivo de las **234 entidades** del archipiélago canario que trabajan en la gestión de los procesos migratorios y en la promoción de la convivencia intercultural. Sustituye al mapa anterior con un diseño cartográfico propio, *clustering*, filtros, búsqueda, vista 3D con terreno y panel de detalle.

## Datos siempre al día (sin tocar código)

La fuente de verdad es un **Google Sheet** del equipo. El mapa **no** tiene los datos escritos a mano: se regeneran solos.

```
Formulario de alta  →  Hoja oficial "Canarias Convive" (Google Sheets)
                    →  GitHub Actions  (cada hora)
                    →  entities.geojson
                    →  Mapa
```

- El equipo aprueba las entidades en la hoja oficial.
- Una **GitHub Action** (`.github/workflows/sync-sheet.yml`) lee la hoja **cada hora** y regenera `entities.geojson`.
- El mapa carga ese archivo → cualquier **alta, cambio o baja** en la hoja se ve en el mapa en **menos de una hora**, sin tocar nada.
- Cada sync **valida las ubicaciones** (coordenadas dentro de Canarias y en tierra, isla y municipio coherentes con el punto) y publica el resultado en el resumen del run, para corregir el Sheet en cuanto un dato venga mal.

## Cómo está montado en la web

La página `canariasconvive.com/mapa-interactivo/` (WordPress, plantilla en blanco) incrusta el visor **a pantalla completa** con un `<iframe>`. El botón *“Volver a Canarias Convive”* devuelve al sitio principal.

[![El mapa integrado en canariasconvive.com](captura-web.webp)](https://canariasconvive.com/mapa-de-agentes/)

## Funcionalidades

- **Estilo Mapbox propio** con la paleta corporativa (verde `#0D4E47`, coral `#F55654`, oliva `#979C30`, burdeos `#B15265`) y tipografía Montserrat.
- **Clustering automático anclado en tierra**: los marcadores se agrupan al solaparse y el círculo del grupo se dibuja siempre sobre uno de sus miembros (nunca en el mar). Al hacer clic, el mapa hace zoom y se desagrupa; si varias entidades comparten sede, se muestra la lista para elegir.
- **Marcadores coloreados por sector**, reconocibles de un vistazo.
- **Filtros dinámicos**: se generan **automáticamente desde las columnas de la hoja** (isla, sector, tipología, protagonista, municipio, entidades RECEX…). Añadir una columna nueva en el Sheet = filtro nuevo en el mapa, sin tocar código.
- **Vista 3D con terreno real** (Mapbox DEM): Teide, Caldera de Taburiente y demás relieve en perspectiva.
- **Búsqueda** por substring, insensible a acentos y mayúsculas (nombre, municipio, provincia, dirección, sector, protagonista).
- **Panel de detalle** con dirección, teléfono, email, redes, logo y botón “Cómo llegar”.
- **Enlace directo a una entidad** vía `?entity={uuid}`; los filtros y la búsqueda se guardan en la URL (se puede compartir la vista exacta).
- **Responsive**: en móvil el panel pasa a ser una *bottom sheet* expandible.
- **Accesibilidad**: controles como `<button>` con `aria-pressed`, foco visible, zoom de usuario no bloqueado.

## Stack

- [Mapbox GL JS](https://docs.mapbox.com/mapbox-gl-js/) v3.21 + [supercluster](https://github.com/mapbox/supercluster) v8 (clustering anclado en tierra).
- JavaScript *vanilla*, sin frameworks ni *build*.
- **GitHub Pages** — hosting del visor y los datos.
- **GitHub Actions** — sincronización horaria con el Google Sheet (vía *service account*).
- Estilo: `mapbox://styles/canarias-convive/cmpeoky6e001s01sc9al820l5`. Terreno: `mapbox://mapbox.mapbox-terrain-dem-v1`.

## Estructura

```
.
├── mapa.html             # El visor self-contained — el que se incrusta en la web
├── canarias-convive.svg  # Logo animado de carga (SVG/SMIL) — cabecera del README
├── index.html            # Variante con CSS externo (styles.css)
├── styles.css            # Estilos de index.html
├── guia.html             # Guía del sistema de mapas
├── entities.geojson      # Datos (los regenera la Action desde la hoja oficial)
├── entities-raw.json     # Volcado inicial de referencia
├── scripts/
│   ├── geo_checks.py             # Validación geográfica (la usa la Action en cada sync)
│   ├── audit_geo.py              # Auditoría completa + informe de correcciones del Sheet
│   └── canarias-municipios.geojson  # Límites municipales (ISTAC vía Opendatasoft, simplificados)
├── captura-mapa.webp     # Captura del visor en producción
├── captura-web.webp      # Captura de la página de agentes en canariasconvive.com
└── .github/workflows/
    └── sync-sheet.yml     # Sincronización horaria: hoja → entities.geojson
```

## Correrlo en local

```bash
python3 -m http.server 8000
# abre http://localhost:8000/mapa.html
```

El token de Mapbox del repo está restringido por URL; para servirlo desde otro dominio, usa tu propio *Default public token* y restríngelo a tu URL.

## Roadmap

- [x] Compartir un agente concreto vía URL (`?entity={uuid}`).
- [x] Persistir filtros (isla/sector/búsqueda) en la URL.
- [x] Leyenda con conteos por sector vinculados al filtro activo.
- [x] Estado seleccionado sincronizado entre marcador y card.
- [x] GitHub Actions que refresca `entities.geojson` automáticamente.
- [x] CI que audita los enlaces externos del geojson.
- [x] Búsqueda con puntuación ponderada (las coincidencias en el nombre van primero).

## Licencia

MIT. Ver [LICENSE](LICENSE).

Datos del programa **Canarias Convive** — Fundación General de la Universidad de La Laguna.
