#!/bin/sh
# Copia los entregables finales de output/ a entregables/ (lo que se sube a YouTube).
set -e
cd "$(dirname "$0")/.."
mkdir -p entregables/canal
for d in output/[0-9][0-9]-*/; do
  n=$(basename "$d")
  mkdir -p "entregables/$n"
  cp "$d$n.mp4" "$d$n-miniatura.png" "$d$n.srt" "${d}metadata.md" "entregables/$n/"
done
cp output/canal/*.png entregables/canal/
du -sh entregables
