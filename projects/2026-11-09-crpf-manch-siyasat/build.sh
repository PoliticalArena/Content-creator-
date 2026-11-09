#!/bin/bash
set -e
# CRPF मंच और सियासत — 59s 9:16 Short, cut to the creator's VO take (audio/vo_take_2026-11-09_1013.m4a).
# Timeline: S1 hook 0–8.6 (VO 1.02–9.12) | S2 PM clip 8.6–20.6 (raw 41.2–53.2, original audio)
#           S3 argument 20.6–39.3 (VO 9.52–27.56) | S4 CTA 39.3–59 (VO 28.0–46.8, incl. subscribe ask)
# Outputs:
#   exports/final_9x16.mp4           ready to post (VO + PM audio + BGM)
#   exports/final_noVO_9x16.mp4      same without VO (for re-recording)
#   exports/overlay_greenscreen.mp4  graphics only, slots pure green (#00FF00) for chroma-key
#   exports/bgm_drone.m4a            59s generated ambient drone (royalty-free)
D="$(cd "$(dirname "$0")" && pwd)"; W=$D/edit; mkdir -p "$W" "$D/exports"; RAW=$D/raw/modi.mp4; VO=$D/audio/vo_take_2026-11-09_1013.m4a
DUR=59; N=$((DUR*30))
# raw/modi.mp4 = Drive file 1cjugGQ_mg_3EREmHAeBBUr62YW979z07 (not committed: 176 MB)
[ -f "$RAW" ] || curl -sSL -o "$RAW" "https://drive.usercontent.google.com/download?id=1cjugGQ_mg_3EREmHAeBBUr62YW979z07&export=download&confirm=t"

# 1) graphics overlay frames (transparent PNG), 4 parallel workers
[ -f "$W/ov/$(printf %05d $((N-1))).png" ] || { for k in 0 1 2 3; do FROM=$((k*N/4)) TO=$(((k+1)*N/4)) node "$D/render.cjs" overlay "$W/ov" 30 $DUR & done; wait; }

# 2) BGM: low drone + soft impacts on scene cuts
hit(){ echo "gt(t,$1)*exp(-(t-$1)*3)*sin(2*PI*42*(t-$1))*0.9"; }
ffmpeg -v error -y -f lavfi -i "aevalsrc='0.30*sin(2*PI*55*t)*(0.65+0.35*sin(2*PI*0.07*t))+0.16*sin(2*PI*82.41*t)*(0.5+0.5*sin(2*PI*0.11*t+1))+0.07*sin(2*PI*110*t)+$(hit 0.05)+$(hit 8.6)+$(hit 20.6)+$(hit 39.3)':s=48000:d=$DUR" \
  -f lavfi -i "anoisesrc=c=brown:a=0.05:d=$DUR:r=48000" \
  -filter_complex "[1]lowpass=f=300[n];[0][n]amix=inputs=2:normalize=0,lowpass=f=900,afade=t=in:d=1.2,afade=t=out:st=$((DUR-3)):d=3,loudnorm=I=-24:TP=-3,aformat=channel_layouts=stereo" \
  -c:a aac -b:a 160k "$D/exports/bgm_drone.m4a"

# 3) picture: source 16:9 band at y438 of the 720x1280 repost; delogo the repost's IG watermark
V="[0:v]crop=720:404:0:438,delogo=x=48:y=270:w=56:h=56,delogo=x=48:y=334:w=150:h=32,setsar=1"
LOOK="eq=contrast=1.05:saturation=0.9,unsharp=5:5:0.6"
ffmpeg -v error -y -i "$RAW" -framerate 30 -i "$W/ov/%05d.png" -filter_complex "
$V,split=5[a][b][c][d][e];
[a]trim=8:16.6,setpts=PTS-STARTPTS[s1];[b]trim=41.2:53.2,setpts=PTS-STARTPTS[s2];
[c]trim=24:33,setpts=PTS-STARTPTS[s3a];[d]trim=60:69.7,setpts=PTS-STARTPTS[s3b];
[s1][s2][s3a][s3b]concat=n=4,fps=30,scale=960:540:flags=lanczos,$LOOK[top];
[e]trim=84:103.7,setpts=PTS-STARTPTS+39.3/TB,crop=420:394:168:4,scale=960:900:flags=lanczos,$LOOK,fps=30[face];
color=black:s=1080x1920:r=30:d=$DUR[bg];
[bg][top]overlay=60:330:eof_action=pass[t1];[t1][face]overlay=60:250:enable='gte(t,39.3)':eof_action=pass[t2];
[t2][1:v]overlay=shortest=1,format=yuv420p[v]" -map "[v]" -c:v libx264 -preset medium -crf 18 -t $DUR "$W/picture.mp4"

# 4) audio stems: PM clip, VO parts (light cleanup), BGM
ffmpeg -v error -y -i "$RAW" -af "atrim=41.2:53.2,asetpts=PTS-STARTPTS,afade=t=in:d=0.15,afade=t=out:st=11.6:d=0.4,loudnorm=I=-16:TP=-1.5,adelay=8600|8600,apad=whole_dur=$DUR,aformat=sample_rates=48000:channel_layouts=stereo" "$W/pm.wav"
vo(){ echo "[0:a]atrim=$1:$2,asetpts=PTS-STARTPTS,afade=t=in:d=0.05,afade=t=out:st=$(echo "$2-$1-0.12"|bc):d=0.12,adelay=$3|$3[$4]"; }
ffmpeg -v error -y -i "$VO" -filter_complex "
$(vo 1.00 9.20 300 v1);$(vo 9.45 27.62 20900 v2);$(vo 27.95 46.85 39600 v3);
[v1][v2][v3]amix=inputs=3:normalize=0,highpass=f=80,acompressor=threshold=-20dB:ratio=3:attack=10:release=150,loudnorm=I=-16:TP=-1.5,apad=whole_dur=$DUR,aformat=sample_rates=48000:channel_layouts=stereo" "$W/vo.wav"

# 5) mixes. BGM: 0.55 under VO, 0.35 under PM clip
BG="[2:a]volume='if(between(t,8.6,20.6),0.35,0.55)':eval=frame[bgm]"
ffmpeg -v error -y -i "$W/vo.wav" -i "$W/pm.wav" -i "$D/exports/bgm_drone.m4a" -filter_complex "$BG;[0][1][bgm]amix=inputs=3:normalize=0,atrim=0:$DUR,alimiter=limit=0.89[a]" -map "[a]" "$W/mix.wav"
ffmpeg -v error -y -i "$W/pm.wav" -i "$W/pm.wav" -i "$D/exports/bgm_drone.m4a" -filter_complex "$BG;[0][bgm]amix=inputs=2:normalize=0,atrim=0:$DUR[a]" -map "[a]" "$W/mix_novo.wav"
ffmpeg -v error -y -i "$W/picture.mp4" -i "$W/mix.wav" -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -movflags +faststart -t $DUR "$D/exports/final_9x16.mp4"
ffmpeg -v error -y -i "$W/picture.mp4" -i "$W/mix_novo.wav" -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -movflags +faststart -t $DUR "$D/exports/final_noVO_9x16.mp4"

# 6) green-screen overlay version
ffmpeg -v error -y -f lavfi -i "color=0x00FF00:s=1080x1920:r=30:d=$DUR" -framerate 30 -i "$W/ov/%05d.png" \
  -filter_complex "[0][1]overlay=shortest=1,format=yuv420p" -c:v libx264 -preset medium -crf 16 -movflags +faststart "$D/exports/overlay_greenscreen.mp4"
[ -n "$KEEP_FRAMES" ] || rm -rf "$W"
