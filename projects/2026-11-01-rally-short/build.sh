#!/bin/bash
set -e
# Clean rally compilation (~59s): crops out YouTube UI + burned-in captions, blur-fills to 9:16,
# slow-mo on crowd shots, bold Hindi on-screen text (libass for correct Devanagari shaping),
# per-clip source credit. Also renders the 9:16 thumbnail.
# Missing: Screenrecorder-2026-11-01-16-01-07-550.mp4 (Drive connector could not fetch the 8MB file).
D="$(cd "$(dirname "$0")" && pwd)"; mkdir -p "$D/edit" "$D/exports" "$D/thumbnail"
F=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf

# name | crop w:h:x:y | slow factor (1 = normal) | credit | line1 (yellow) | line2 (white)
SLOW=1.888   # stretches 25.4s of crowd footage to ~48s -> total ~59s
segs=(
"16-02-02-161|1000:1110:140:480|$SLOW|@IndianNationalCongress|रुको! ये देखो…|दिल्ली में इतनी भीड़?!"
"15-59-32-585|1020:1200:130:480|$SLOW|@Couple.Comrade|यकीन नहीं होगा!|रामलीला मैदान FULL"
"15-57-44-15|1020:1540:130:100|$SLOW|@IndianNationalCongress|LAST तक देखना!|हर तरफ़ झंडे ही झंडे"
"15-59-46-736|1020:525:130:1075|$SLOW|@INCUttarPradesh|अब होगा बड़ा खेल?|चलो दिल्ली आरंभ!"
"16-01-03-348|1020:1030:130:570|$SLOW|@IndianYouthCongress|ये भीड़ नहीं…|तूफ़ान है!"
"16-00-19-775|880:530:130:625|1|@StreekaalStreeKaSamay / INC|सरकार की टेंशन बढ़ी?|ये तो बस शुरुआत है…"
)

ass=$D/edit/text.ass
cat > $ass <<'ASS'
[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: K,FreeSerif,84,&H00FFFFFF,&H00FFFFFF,&H000000D0,&H99000000,1,0,0,0,100,100,0,0,3,16,0,8,30,30,110,1
Style: Y,FreeSerif,124,&H0000FFFF,&H00FFFFFF,&H00000000,&H99000000,1,0,0,0,100,100,0,0,1,11,6,8,30,30,260,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
ASS
ts() { python3 -c "import sys;x=float(sys.argv[1]);print('%d:%02d:%05.2f'%(x//3600,x%3600//60,x%60))" "$1"; }

i=0; t=0; list=$D/edit/list.txt; : > $list
for s in "${segs[@]}"; do
  IFS='|' read n c k cred l1 l2 <<< "$s"
  o=$D/edit/$i.mp4
  if [ "$k" = "1" ]; then vs="fps=30"; as="anull"
  else
    vs="setpts=$k*PTS,minterpolate=fps=30:mi_mode=blend"
    a=$(python3 -c "print((1/$k)**0.5)"); as="atempo=$a,atempo=$a"
  fi
  ffmpeg -v error -y -i "$D/raw/Screenrecorder-2026-11-01-$n.mp4" -filter_complex "
  [0:v]crop=$c,setsar=1,$vs,split[a][b];
  [a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=30:5,eq=brightness=-0.15[bg];
  [b]scale=1080:1920:force_original_aspect_ratio=decrease[fg];
  [bg][fg]overlay=(W-w)/2:(H-h)/2,format=yuv420p,
  drawtext=fontfile=$F:text='Source\: $cred':fontsize=30:fontcolor=white@0.9:box=1:boxcolor=black@0.45:boxborderw=12:x=(w-text_w)/2:y=h-170[v];
  [0:a]aresample=44100,aformat=channel_layouts=stereo,$as[a2]" \
  -map "[v]" -map "[a2]" -c:v libx264 -preset medium -crf 19 -c:a aac -b:a 160k -shortest "$o"
  echo "file '$o'" >> $list
  dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$o")
  te=$(ts $(python3 -c "print($t+$dur-0.05)"))
  pop="\\fscx60\\fscy60\\t(0,160,\\fscx108\\fscy108)\\t(160,260,\\fscx100\\fscy100)"
  echo "Dialogue: 1,$(ts $t),$te,K,,0,0,0,,{\\fad(80,0)$pop}$l1" >> $ass
  echo "Dialogue: 0,$(ts $(python3 -c "print($t+0.25)")),$te,Y,,0,0,0,,{\\fad(80,0)$pop}$l2" >> $ass
  t=$(python3 -c "print($t+$dur)"); i=$((i+1))
done

ffmpeg -v error -y -f concat -safe 0 -i $list -c copy $D/edit/joined.mp4
ffmpeg -v error -y -i $D/edit/joined.mp4 -vf "ass=$ass" -c:v libx264 -preset medium -crf 19 -c:a copy -movflags +faststart $D/exports/short_9x16_1080x1920.mp4
ffprobe -v error -show_entries format=duration:stream=width,height -of compact $D/exports/short_9x16_1080x1920.mp4

# Thumbnail: red-flag "Toofan" crowd frame + bold text
ffmpeg -v error -y -ss 0.4 -i $D/raw/Screenrecorder-2026-11-01-16-01-03-348.mp4 -frames:v 1 -filter_complex "
[0:v]crop=1020:1030:130:570,eq=contrast=1.15:saturation=1.5:brightness=0.05,unsharp=5:5:0.8,split[a][b];
[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:4,eq=brightness=-0.3[bg];
[b]scale=1080:-2[fg];[bg][fg]overlay=0:700,ass=$D/thumbnail/thumb.ass" -q:v 2 $D/thumbnail/thumbnail_9x16.jpg
[ -n "$KEEP" ] || rm -rf "$D/edit"
