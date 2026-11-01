#!/bin/bash
set -e
# Clean rally compilation: crops out YouTube UI + burned-in captions, blur-fills to 9:16, adds per-clip source credit.
# Missing: Screenrecorder-2026-11-01-16-01-07-550.mp4 (Drive connector could not fetch the 8MB file).
D="$(cd "$(dirname "$0")" && pwd)"; mkdir -p "$D/edit"
F=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf
# name|crop w:h:x:y|credit
segs=(
"16-02-02-161|1000:1110:140:480|@IndianNationalCongress"
"15-59-32-585|1020:1200:130:480|@Couple.Comrade"
"15-57-44-15|1020:1540:130:100|@IndianNationalCongress"
"15-59-46-736|1020:525:130:1075|@INCUttarPradesh"
"16-01-03-348|1020:1030:130:570|@IndianYouthCongress"
"16-00-19-775|880:530:130:625|@StreekaalStreeKaSamay / INC"
)
i=0; list=$D/edit/list.txt; : > $list
for s in "${segs[@]}"; do
  IFS='|' read n c cred <<< "$s"
  o=$D/edit/$i.mp4
  ffmpeg -v error -y -i "$D/raw/Screenrecorder-2026-11-01-$n.mp4" -filter_complex "
  [0:v]crop=$c,setsar=1,split[a][b];
  [a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=30:5,eq=brightness=-0.15[bg];
  [b]scale=1080:1920:force_original_aspect_ratio=decrease[fg];
  [bg][fg]overlay=(W-w)/2:(H-h)/2,fps=30,format=yuv420p,
  drawtext=fontfile=$F:text='Source\: $cred':fontsize=30:fontcolor=white@0.9:box=1:boxcolor=black@0.45:boxborderw=12:x=(w-text_w)/2:y=h-170[v];
  [0:a]aresample=44100,aformat=channel_layouts=stereo[a2]" \
  -map "[v]" -map "[a2]" -c:v libx264 -preset medium -crf 19 -c:a aac -b:a 160k -shortest "$o"
  echo "file '$o'" >> $list; i=$((i+1))
done
ffmpeg -v error -y -f concat -safe 0 -i $list -c copy -movflags +faststart $D/exports/short_9x16_1080x1920.mp4
ffprobe -v error -show_entries format=duration:stream=width,height -of compact $D/exports/short_9x16_1080x1920.mp4
