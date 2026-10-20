#!/usr/bin/env bash
# Rebuilds every edit/export for this project from raw/.
# Usage: ./build.sh   (run from anywhere)
set -euo pipefail
cd "$(dirname "$0")"

RAW=raw/screenrecording_original.mp4
FONT=/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf
FONT_MED=/usr/share/fonts/opentype/inter/Inter-SemiBold.otf
ENC=(-c:v libx264 -crf 18 -preset slow -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart)

# On-screen copy (edit here)
HOOK_1="LOOK AT THIS CROWD"
HOOK_2="Rally night. Full energy."
CTA="Follow for more"

# 1) Crop the reel out of the Facebook UI (rows 591-1796 of the recording)
ffmpeg -v error -y -i "$RAW" -vf "crop=1206:1206:0:591" \
  -c:v libx264 -crf 16 -preset slow -pix_fmt yuv420p -c:a copy -movflags +faststart \
  edit/cropped_1206x1206.mp4

# 2) Remove the like/comment counters, normalise to 1080x1080
ffmpeg -v error -y -i edit/cropped_1206x1206.mp4 \
  -vf "delogo=x=1058:y=795:w=136:h=380,crop=1200:1200:0:3,scale=1080:1080:flags=lanczos" \
  -c:v libx264 -crf 16 -preset slow -pix_fmt yuv420p -c:a copy -movflags +faststart \
  edit/clean_1080x1080.mp4

# Text helpers: fade in over 0.3s from $start, fade out over 0.3s to $end
fade() { echo "alpha='if(lt(t,$1),0,if(lt(t,$1+0.3),(t-$1)/0.3,if(lt(t,$2-0.3),1,if(lt(t,$2),($2-t)/0.3,0))))'"; }

# 3) 9:16 Short / Reel: blurred fill background, square video centred, hook on top
ffmpeg -v error -y -i edit/clean_1080x1080.mp4 -filter_complex "
[0:v]split[bgsrc][fg];
[bgsrc]scale=1920:1920,crop=1080:1920,gblur=sigma=40,eq=brightness=-0.18[bg];
[bg][fg]overlay=0:420,
drawtext=fontfile=$FONT:text='$HOOK_1':fontsize=86:fontcolor=white:borderw=6:bordercolor=black@0.85:x=(w-tw)/2:y=230:$(fade 0 3.5),
drawtext=fontfile=$FONT_MED:text='$HOOK_2':fontsize=60:fontcolor=white:borderw=5:bordercolor=black@0.85:x=(w-tw)/2:y=250:$(fade 3.5 12.3),
drawtext=fontfile=$FONT:text='$CTA':fontsize=58:fontcolor=black:box=1:boxcolor=white@0.95:boxborderw=24:x=(w-tw)/2:y=1600:$(fade 9 12.3)[v]" \
  -map "[v]" -map 0:a "${ENC[@]}" exports/short_9x16_1080x1920.mp4

# 4) 1:1 feed post: clean square with hook lower-third for the first 3.5s
ffmpeg -v error -y -i edit/clean_1080x1080.mp4 -vf "
drawtext=fontfile=$FONT:text='$HOOK_1':fontsize=72:fontcolor=white:box=1:boxcolor=black@0.6:boxborderw=22:x=(w-tw)/2:y=h-200:$(fade 0 3.5),
drawtext=fontfile=$FONT:text='$CTA':fontsize=52:fontcolor=black:box=1:boxcolor=white@0.95:boxborderw=20:x=(w-tw)/2:y=h-180:$(fade 9 12.3)" \
  "${ENC[@]}" exports/post_1x1_1080x1080.mp4

echo "Done:"; ls -lh edit exports
