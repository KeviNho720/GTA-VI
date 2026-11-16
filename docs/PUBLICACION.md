# Plan de publicación — ZONA SEIS

Lanzamiento de GTA 6: **jueves 19 de noviembre de 2026, 00:00 hora local**.

## Calendario recomendado (hora peninsular)

| Cuándo | Vídeo | Por qué entonces |
|---|---|---|
| Mar 17 · 18:00 | 02 · ¿A qué hora sale GTA 6? | La búsqueda «a qué hora sale» se dispara 48 h antes |
| Mar 17 · 20:00 | 03 · Precio y ediciones | Última ventana de compra antes del lanzamiento |
| Mié 18 · 13:00 | 04 · PS5, PS5 Pro o Xbox | Dudas de última hora sobre rendimiento y PS4/Xbox One |
| Mié 18 · 18:00 | 01 · Todo lo que sabemos | Vídeo «puerta de entrada»: fíjalo en la portada del canal |
| Jue 19 · 10:00 | 05 · Mapa de Leonida | Día 1: la gente empieza a explorar |
| Jue 19 · 13:00 | 06 · Personajes | Día 1 |
| Jue 19 · 17:00 | 07 · ¿GTA 6 en PC? | Los jugadores de PC buscan respuestas el día de salida |
| Jue 19 · 20:00 | 08 · ¿Tiene online? | Pregunta recurrente al terminar la primera sesión |
| Vie 20 · 18:00 | 09 · GTA 6 vs GTA 5 | Comparativas: tráfico estable toda la semana |
| Sáb 21 · 12:00 | 10 · 13 años de espera | Contenido atemporal de fin de semana |

Puedes programarlos todos hoy en YouTube Studio («Programar»).

## Checklist por vídeo (YouTube Studio)

1. Sube `NN-slug.mp4` (1080p, 30 fps, H.264, audio AAC a −14 LUFS).
2. Título, descripción (con capítulos ya calculados) y etiquetas: cópialos de `metadata.md`.
3. Miniatura: `NN-slug-miniatura.png` (1280×720).
4. Subtítulos: sube `NN-slug.srt` como «Español». Los subtítulos ya van incrustados en el vídeo; el SRT ayuda al SEO y a la traducción automática.
5. Lista de reproducción: **«GTA 6: guía de lanzamiento»** (todos los vídeos).
6. Pantalla final: últimos 10–12 s (la escena final ya deja hueco y anuncia el siguiente vídeo). Añade «Suscribirse» y «Vídeo: el siguiente de la lista».
7. Público: **no es contenido para niños**. Categoría: Videojuegos.
8. Comentario fijado: está en `metadata.md`.
9. Antes de publicar 01 y 03, comprueba el precio de la Ultimate en la PlayStation Store de tu país (ver `INVESTIGACION.md`).

## Imagen del canal (carpeta `output/canal/`)

- `banner-2560x1440.png` → Personalización › Imagen de banner.
- `avatar-800x800.png` → Foto de perfil.
- `marca-de-agua-150x150.png` → Marca de agua del vídeo.
- Nombre y lema: `channel/brand.yaml` (si cambias el nombre, vuelve a generar todo con `make all`).

## Siguientes vídeos, con el juego en la mano (a partir del jueves)

Son las búsquedas más fuertes de la semana de lanzamiento, pero **no se pueden hacer con rigor antes de jugar**:

1. Trucos de GTA 6 (si los hay) · 2. Cómo ganar dinero rápido · 3. Los primeros 30 minutos: consejos para empezar ·
4. Mejores coches y dónde encontrarlos · 5. Secretos y easter eggs · 6. Todas las armas · 7. Ajustes recomendados.

Para estos, graba tu partida (la captura de la consola vale) y usa el motor para las gráficas, la voz y el montaje: añade una escena por clip con tu narración.

## Nota sobre la voz y la monetización

La narración es una voz sintética (Piper, `es_ES-davefx`). Funciona, pero YouTube puede limitar la monetización de canales con contenido «producido en masa» o poco original. Para el Programa de Socios conviene:
- grabar tu propia voz leyendo el guion (`metadata.md` › «Guion narrado»), o
- añadir comentario y opinión personal en los vídeos con partida real.

Los gráficos, las animaciones y la música son originales del canal (generados por código): no usan material de Rockstar.
