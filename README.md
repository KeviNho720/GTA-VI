# ZONA SEIS — canal de GTA 6 listo para el lanzamiento

Diez vídeos completos (guion, voz, gráficos, animación, música y montaje) para un canal de YouTube en español sobre GTA 6, preparados para la semana de lanzamiento (jueves 19 de noviembre de 2026), con miniaturas, títulos, descripciones con capítulos, etiquetas, subtítulos SRT e imagen de canal.

Todo el material visual y sonoro es **original y generado por código**: no se usan imágenes, vídeos, logotipos ni música de Rockstar Games.

## Los 10 vídeos

| # | Vídeo | Duración | Guion |
|---|---|---|---|
| 01 | GTA 6: todo lo que sabemos (resumen sin spoilers) | 3:37 | `videos/01-todo-lo-que-sabemos.yaml` |
| 02 | ¿A qué hora sale GTA 6? Horario por país + precarga | 2:35 | `videos/02-a-que-hora-sale.yaml` |
| 03 | Precio y ediciones: ¿Estándar o Ultimate? | 1:58 | `videos/03-precio-y-ediciones.yaml` |
| 04 | PS5, PS5 Pro o Xbox: 30 FPS, PSSR, PS4 y Xbox One | 2:25 | `videos/04-ps5-pro-xbox-rendimiento.yaml` |
| 05 | El mapa de Leonida: las 6 regiones | 1:44 | `videos/05-mapa-de-leonida.yaml` |
| 06 | Personajes: Jason, Lucia y los secundarios | 2:21 | `videos/06-personajes.yaml` |
| 07 | ¿Cuándo sale GTA 6 en PC? | 1:24 | `videos/07-gta-6-pc.yaml` |
| 08 | ¿Tiene GTA 6 modo online? | 1:17 | `videos/08-gta-6-online.yaml` |
| 09 | GTA 6 vs GTA 5 | 2:01 | `videos/09-gta-6-vs-gta-5.yaml` |
| 10 | 13 años de espera: la historia de GTA 6 | 1:53 | `videos/10-historia-de-gta-6.yaml` |

- Qué busca la gente y fuentes de cada dato: [`docs/INVESTIGACION.md`](docs/INVESTIGACION.md)
- Calendario de publicación y checklist de subida: [`docs/PUBLICACION.md`](docs/PUBLICACION.md)

**Los vídeos terminados, listos para subir, están en [`entregables/`](entregables/)** (vídeo, miniatura, subtítulos y ficha con título, descripción y etiquetas), junto con la imagen de canal en `entregables/canal/`.

## Cómo se generan

```bash
make setup     # entorno Python + voz española (Piper es_ES-davefx)
make all       # 10 vídeos + miniaturas + imagen de canal en output/
make video V=02-a-que-hora-sale      # un solo vídeo
make preview V=02-a-que-hora-sale    # vista previa rápida a 540p
make qa        # control de pronunciación con Whisper (opcional)
```

Por cada vídeo, en `output/NN-slug/`:

- `NN-slug.mp4` — 1920×1080, 30 fps, H.264 + AAC, sonido normalizado a −14 LUFS
- `NN-slug-miniatura.png` — 1280×720
- `NN-slug.srt` — subtítulos
- `metadata.md` — título, títulos alternativos, descripción con capítulos, etiquetas, comentario fijado y guion

## Cómo editar un vídeo

Cada guion es un YAML con escenas. Cada escena tiene un `type` (aspecto visual) y `lines` (frases narradas; cada frase es un subtítulo y marca el ritmo de las animaciones). Ejemplo:

```yaml
- type: verdict
  chapter: "¿Hay versión de PC?"     # aparece en los capítulos de la descripción
  question: "¿Hay una versión de PC anunciada?"
  verdict: "No"                       # sello animado (aparece con la 2.ª frase)
  note: "Ni Rockstar ni Take-Two han dado fecha."
  lines:
    - "¿Hay una versión de PC anunciada?"
    - "La respuesta corta es no."
    - {text: "Texto del subtítulo", say: "texto que lee la voz"}   # si hace falta forzar pronunciación
```

Tipos de escena: `title`, `chapter`, `statement`, `bullets`, `stat`, `compare`, `table`, `verdict`, `map`, `profile`, `timeline`, `checklist`, `quote`, `cards`, `versus`, `outro`.

La pronunciación de nombres propios (Jason, Lucia, Vice City, Port Gellhorn, PS5…) se corrige en `engine/tts.py` (lista `PRON`).

## Estructura

```
engine/        motor: gfx (Skia), fondos, escenas, voz, audio, render, miniaturas, imagen de canal
videos/        guiones YAML (uno por vídeo)
channel/       identidad del canal (nombre, lema, pie de descripción)
assets/        fuentes (OFL) e iconos Lucide (ISC)
docs/          investigación de búsquedas y plan de publicación
tools/         control de calidad de la voz
```

Licencias de terceros: fuentes Anton, Bebas Neue y Montserrat (SIL OFL 1.1), iconos Lucide (ISC), voz Piper `es_ES-davefx-medium` (dataset CC0). Canal de fans no oficial; GTA y Grand Theft Auto son marcas de Take-Two Interactive.
