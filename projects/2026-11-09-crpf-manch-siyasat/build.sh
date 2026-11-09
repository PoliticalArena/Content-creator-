#!/bin/bash
set -e
# CRPF मंच और सियासत — 42s 9:16 Short. Creator records the voiceover separately (0–6s and 18–42s);
# 6–18s plays the PM's original speech audio (raw 41.2–53.2s).
# Outputs:
#   exports/final_noVO_9x16.mp4      graphics + footage + original speech + BGM → add your VO and post
#   exports/overlay_greenscreen.mp4  graphics only, slots pure green (#00FF00) → chroma-key over your own clips/face-cam
#   exports/bgm_drone.m4a            42s generated ambient drone (royalty-free), -24 LUFS bed
D="$(cd "$(dirname "$0")" && pwd)"; W=$D/edit; mkdir -p "$W" "$D/exports"; RAW=$D/raw/modi.mp4
# raw/modi.mp4 = Drive file 1cjugGQ_mg_3EREmHAeBBUr62YW979z07 (not committed: 176 MB)
[ -f "$RAW" ] || curl -sSL -o "$RAW" "https://drive.usercontent.google.com/download?id=1cjugGQ_mg_3EREmHAeBBUr62YW979z07&export=download&confirm=t"

# 1) graphics overlay frames (transparent PNG), 4 parallel workers
N=1260; for k in 0 1 2 3; do FROM=$((k*N/4)) TO=$(((k+1)*N/4)) node "$D/render.cjs" overlay "$W/ov" 30 42 & done; wait

# 2) BGM: low drone (55/82.4/110 Hz swells) + soft impacts on scene cuts
hit(){ echo "gt(t,$1)*exp(-(t-$1)*3)*sin(2*PI*42*(t-$1))*0.9"; }
ffmpeg -v error -y -f lavfi -i "aevalsrc='0.30*sin(2*PI*55*t)*(0.65+0.35*sin(2*PI*0.07*t))+0.16*sin(2*PI*82.41*t)*(0.5+0.5*sin(2*PI*0.11*t+1))+0.07*sin(2*PI*110*t)+$(hit 0.05)+$(hit 6)+$(hit 18)+$(hit 32)':s=48000:d=42" \
  -f lavfi -i "anoisesrc=c=brown:a=0.05:d=42:r=48000" \
  -filter_complex "[1]lowpass=f=300[n];[0][n]amix=inputs=2:normalize=0,lowpass=f=900,afade=t=in:d=1.2,afade=t=out:st=39.5:d=2.5,loudnorm=I=-24:TP=-3,aformat=channel_layouts=stereo" \
  -c:a aac -b:a 160k "$D/exports/bgm_drone.m4a"

# 3) footage into slots. Source video band (16:9) sits at y438 in the 720x1280 repost → crop out the caption/IG handle.
#    S1 0–6 raw 8–14 (jawans → PM) | S2 6–18 raw 41.2–53.2 (the quote, audio ON) | S3 18–25 raw 24–31, 25–32 raw 85–92 | S4 32–42 raw 92–102 (tight face crop)
V="[0:v]crop=720:404:0:438,delogo=x=48:y=270:w=56:h=56,delogo=x=48:y=334:w=150:h=32,setsar=1"
ffmpeg -v error -y -i "$RAW" -framerate 30 -i "$W/ov/%05d.png" -i "$D/exports/bgm_drone.m4a" -filter_complex "
$V,split=5[a][b][c][d][e];
[a]trim=8:14,setpts=PTS-STARTPTS[s1];[b]trim=41.2:53.2,setpts=PTS-STARTPTS[s2];
[c]trim=24:31,setpts=PTS-STARTPTS[s3a];[d]trim=85:92,setpts=PTS-STARTPTS[s3b];
[s1][s2][s3a][s3b]concat=n=4,fps=30,scale=960:540:flags=lanczos,eq=contrast=1.05:saturation=0.9,unsharp=5:5:0.6[top];
[e]trim=92:102,setpts=PTS-STARTPTS,crop=431:404:165:0,scale=960:900:flags=lanczos,eq=contrast=1.05:saturation=0.9,unsharp=5:5:0.6,fps=30[face];
color=black:s=1080x1920:r=30:d=42[bg];
[bg][top]overlay=60:330:eof_action=pass[t1];[t1][face]overlay=60:250:enable='gte(t,32)':eof_action=pass[t2];
[t2][1:v]overlay=shortest=1,format=yuv420p[v];
[0:a]atrim=41.2:53.2,asetpts=PTS-STARTPTS,afade=t=in:d=0.15,afade=t=out:st=11.6:d=0.4,adelay=6000|6000,apad=whole_dur=42,loudnorm=I=-15:TP=-1.5[sp];
[2:a]volume='if(between(t,6,18),0.4,1)':eval=frame[bgm];
[sp][bgm]amix=inputs=2:normalize=0:duration=longest,atrim=0:42[a]" \
  -map "[v]" -map "[a]" -c:v libx264 -preset medium -crf 18 -c:a aac -b:a 192k -ar 48000 -t 42 -movflags +faststart "$D/exports/final_noVO_9x16.mp4"

# 4) green-screen overlay version
ffmpeg -v error -y -f lavfi -i "color=0x00FF00:s=1080x1920:r=30:d=42" -framerate 30 -i "$W/ov/%05d.png" \
  -filter_complex "[0][1]overlay=shortest=1,format=yuv420p" -c:v libx264 -preset medium -crf 16 -movflags +faststart "$D/exports/overlay_greenscreen.mp4"
rm -rf "$W"
