#!/bin/bash
set -e
# &TV clip (screen-recorded, letterboxed): crop black bars, blur-fill to 9:16 and 1:1, add source credit.
# Broadcaster's &tv logo is kept on purpose (attribution). Last ~27s (1:55-2:22) has no audio in the source.
D="$(cd "$(dirname "$0")" && pwd)"
IN=$D/raw/VID_20261110_190537.mp4
F=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf
CROP=1080:596:0:510   # from cropdetect
render() { # w h out
  ffmpeg -v error -y -i "$IN" -filter_complex "
  [0:v]crop=$CROP,setsar=1,split[a][b];
  [a]scale=$1:$2:force_original_aspect_ratio=increase,crop=$1:$2,boxblur=30:5,eq=brightness=-0.15[bg];
  [b]scale=$1:$2:force_original_aspect_ratio=decrease[fg];
  [bg][fg]overlay=(W-w)/2:(H-h)/2,format=yuv420p,
  drawtext=fontfile=$F:text='Source\: &TV':fontsize=30:fontcolor=white@0.9:box=1:boxcolor=black@0.45:boxborderw=12:x=(w-text_w)/2:y=h-$4[v]" \
  -map "[v]" -map 0:a -c:v libx264 -preset medium -crf 19 -c:a aac -b:a 160k -movflags +faststart "$3"
}
render 1080 1920 "$D/exports/short_9x16_1080x1920.mp4" 170
render 1080 1080 "$D/exports/post_1x1_1080x1080.mp4" 90
for f in "$D"/exports/*.mp4; do ffprobe -v error -show_entries format=duration:stream=width,height -of compact "$f"; done
