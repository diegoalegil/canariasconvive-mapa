# Canarias Convive — Mapa de agentes

Rediseño del mapa público del programa **Canarias Convive** (Gobierno de Canarias + Universidad de La Laguna). Sustituye el mapa por defecto de Mapbox por un estilo cartográfico custom alineado con la identidad visual del programa, añade clustering, filtros, búsqueda y vista 3D.

🔗 **Demo en vivo:** [diegoalegil.github.io/canariasconvive-mapa](https://diegoalegil.github.io/canariasconvive-mapa/)

![Mapa de agentes Canarias Convive — demo con estilo Mapbox custom](screenshot.png)

## El problema

El mapa público en `canariasconvive.com/mapa-de-agentes/` carga vía iframe una aplicación SvelteKit que muestra ~237 entidades del archipiélago canario. La implementación actual tiene varios problemas de UX:

- Estilo base de Mapbox sin personalizar — colores saturados que compiten con los marcadores.
- 237 marcadores apilados en zonas urbanas (Las Palmas, Santa Cruz) sin clustering — resulta ilegible.
- Filtros enterrados en un modal con dropdowns confusos.
- Sin coherencia visual con el resto de la web (paleta, tipografía).

## La solución

Este repo es una demo standalone que rediseña esa experiencia:

- **Estilo Mapbox custom** diseñado en Mapbox Studio con la paleta corporativa: verde `#0D4E47`, coral `#F55654`, oliva `#979C30`, burdeos `#B15265`. Tipografía Montserrat (coherente con la web).
- **Clustering automático** — los marcadores se agrupan cuando se solapan; un clic en el cluster hace zoom y se desagrupan.
- **Marcadores coloreados por sector** — el sector de cada entidad se reconoce de un vistazo por el color del punto.
- **Sidebar persistente** con buscador por nombre, filtros por sector clicables, contador en vivo y botones de vista (2D / 3D / centrar archipiélago).
- **Popups limpios** con nombre, sector, tipología, protagonista y enlaces a web, Facebook, Instagram, Twitter.
- **Vista 3D** activable con un botón — Mapbox Standard incluye edificios 3D al ampliar.

## Tecnología

- HTML / CSS / JavaScript vanilla. Sin frameworks.
- [Mapbox GL JS](https://docs.mapbox.com/mapbox-gl-js/) 3.9 para el render del mapa.
- Estilo custom publicado: `mapbox://styles/canarias-convive/cmpeoky6e001s01sc9al820l5`.
- Datos obtenidos de la API REST que utiliza la aplicación oficial (`api.canariasconvive.com/rest/queryEntities`, descubierta inspeccionando el bundle de la web pública).
- Tipografía: [Montserrat](https://fonts.google.com/specimen/Montserrat) vía Google Fonts.

## Cómo correrlo en local

Necesitas un token público de Mapbox (gratis):

1. Crea una cuenta en [mapbox.com](https://account.mapbox.com/auth/signup/).
2. Copia el **Default public token** desde [Access Tokens](https://account.mapbox.com/access-tokens/).
3. Sirve el repo con cualquier servidor estático. Por ejemplo:
   ```bash
   python3 -m http.server 8000
   ```
   Y abre `http://localhost:8000`.
4. La primera vez te pedirá el token — pégalo, se guarda en `localStorage`.

## Estructura

```
.
├── index.html           # App completa (HTML + CSS + JS en un único archivo)
├── entities.geojson     # 234 entidades como FeatureCollection
├── entities-raw.json    # Respuesta original del endpoint REST (para referencia)
└── README.md
```

## Roadmap

- [ ] Logos de las entidades en los popups (requiere descubrir el patrón de URL del CDN de logos).
- [ ] Compartir un agente concreto vía URL (`?entity={uuid}`).
- [ ] Vista lista alternativa al mapa para accesibilidad / móvil pequeño.
- [ ] Cache local de datos para que cargue offline.

## Licencia

MIT. Ver [LICENSE](LICENSE).

Datos del programa Canarias Convive — Fundación General de la Universidad de La Laguna.
