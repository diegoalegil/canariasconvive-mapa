# Canarias Convive · Mapa de Agentes

> Mapa interactivo **oficial** del programa **Canarias Convive** (Fundación General de la Universidad de La Laguna).
> **Este repositorio aloja el mapa real** que se muestra, en producción, en la web del programa.

🌍 **En producción:** <https://canariasconvive.com/mapa-interactivo/>

[![Mapa de agentes de Canarias Convive](captura-mapa.webp)](https://canariasconvive.com/mapa-interactivo/)

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
- Una **GitHub Action** (`.github/workflows/sync-sheet.yml`) lee la hoja **cada hora**, geocodifica las direcciones y regenera `entities.geojson`.
- El mapa carga ese archivo → cualquier **alta, cambio o baja** en la hoja se ve en el mapa en **menos de una hora**, sin tocar nada.

## Cómo está montado en la web

La página `canariasconvive.com/mapa-interactivo/` (WordPress, plantilla en blanco) incrusta el visor **a pantalla completa** con un `<iframe>`. El botón *“Volver a Canarias Convive”* devuelve al sitio principal.

[![El mapa integrado en canariasconvive.com](captura-web.webp)](https://canariasconvive.com/mapa-de-agentes/)

## Funcionalidades

- **Estilo Mapbox propio** con la paleta corporativa (verde `#0D4E47`, coral `#F55654`, oliva `#979C30`, burdeos `#B15265`) y tipografía Montserrat.
- **Clustering automático**: los marcadores se agrupan al solaparse; al hacer clic en un grupo, el mapa hace zoom y se desagrupa.
- **Marcadores coloreados por sector**, reconocibles de un vistazo.
- **Filtros dinámicos**: se generan **automáticamente desde las columnas de la hoja** (isla, sector, tipología, protagonista, municipio, entidades RECEX…). Añadir una columna nueva en el Sheet = filtro nuevo en el mapa, sin tocar código.
- **Vista 3D con terreno real** (Mapbox DEM, exageración 2.5×): Teide, Caldera de Taburiente y demás relieve en perspectiva.
- **Búsqueda** por substring, insensible a acentos y mayúsculas (nombre, municipio, provincia, dirección, sector, protagonista).
- **Panel de detalle** con dirección, teléfono, email, redes, logo y botón “Cómo llegar”.
- **Enlace directo a una entidad** vía `?entity={uuid}`; los filtros y la búsqueda se guardan en la URL (se puede compartir la vista exacta).
- **Responsive**: en móvil el panel pasa a ser una *bottom sheet* expandible.
- **Accesibilidad**: controles como `<button>` con `aria-pressed`, foco visible, zoom de usuario no bloqueado.

## Stack

- [Mapbox GL JS](https://docs.mapbox.com/mapbox-gl-js/) v3.21 + [Turf.js](https://turfjs.org/) v7.3 (geometrías 3D).
- JavaScript *vanilla*, sin frameworks ni *build*.
- **GitHub Pages** — hosting del visor y los datos.
- **GitHub Actions** — sincronización horaria con el Google Sheet (vía *service account*).
- Estilo: `mapbox://styles/canarias-convive/cmpeoky6e001s01sc9al820l5`. Terreno: `mapbox://mapbox.mapbox-terrain-dem-v1`.

## Estructura

```
.
├── mapa.html             # El visor self-contained — el que se incrusta en la web
├── index.html            # Variante con CSS externo (styles.css)
├── styles.css            # Estilos de index.html
├── guia.html             # Guía del sistema de mapas
├── entities.geojson      # Datos (los regenera la Action desde la hoja oficial)
├── entities-raw.json     # Volcado inicial de referencia
├── captura-mapa.webp     # Captura usada en este README
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
- [ ] Búsqueda con puntuación ponderada (nombre por encima de tipología).

## Licencia

MIT. Ver [LICENSE](LICENSE).

Datos del programa **Canarias Convive** — Fundación General de la Universidad de La Laguna.
