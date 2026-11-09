# CRPF मंच और सियासत — 42s Short (9:16)

**Footage:** Drive `Modi` (1cjugGQ_mg_3EREmHAeBBUr62YW979z07). It's an ANI clip reposted by @saket.gokhale. The build crops out the repost caption and blurs the IG watermark. The ANI bug stays on screen and is credited as "वीडियो: ANI".

## Files
| File | Use |
|---|---|
| `exports/final_noVO_9x16.mp4` | **Main file.** Graphics, footage, PM's original audio (6–18s) and BGM. Add your VO on top and post. |
| `exports/overlay_greenscreen.mp4` | Graphics only, with the slots in pure green. Chroma-key it over your own clips or face-cam in CapCut. |
| `exports/bgm_drone.m4a` | 42s ambient drone, generated here, so no copyright claims. Already mixed into the main file. |

## Voiceover: record 3 takes and place them at these times
**0:06–0:18 has no VO.** The PM's own words play here. The real audio is stronger proof than a paraphrase.

| Time | Screen | VO (read slow and steady, analytical tone) |
|---|---|---|
| **0:00–0:06** | Jawans → PM · "CRPF मंच और सियासत?" | "देश के सुरक्षा बलों की वर्दी अराजनीतिक होती है… लेकिन जब उन्हीं के मंच से राजनीतिक विरोधियों को घेरा जाए, तो सवाल उठना लाज़िमी है।" |
| 0:06–0:18 | PM audio: "कई राजनीतिक दलों में… दिमागी नक्सलियों ने अपनी घुसपैठ कर ली है" | — *(silent)* |
| **0:18–0:32** | संसद/चुनाव → जवान vs सियासत → तटस्थता? | "लोकतंत्र में दलों और विचारधाराओं की लड़ाई संसद और चुनाव के मैदान में लड़ी जाती है। जब देश के सबसे बड़े संवैधानिक पद से, जवानों के सामने, यह कहा जाए कि राजनीतिक दलों में 'दिमागी नक्सलियों' ने घुसपैठ कर ली है — तो क्या यह संस्थाओं की तटस्थता पर सवाल नहीं खड़ा करता?" |
| **0:32–0:42** | Poll · "आपकी क्या राय है?" | "नक्सलवाद के खिलाफ लड़ना जवानों का कर्तव्य है, लेकिन राजनीतिक विरोधियों से निपटना लोकतंत्र का काम। क्या सुरक्षा बलों के कार्यक्रमों में ऐसी बातें होनी चाहिए? अपनी राय कमेंट्स में बताइए।" |

**I changed one line in the Gemini script (0:18–0:32).** The PM did **not** call parties "दिमागी नक्सली". His words were "कई राजनीतिक दलों में, अलग-अलग संगठनों में भी इन दिमागी नक्सलियों ने अपनी घुसपैठ कर ली है… हमें इन्हें पहचानना है, परास्त करना है" (raw 41–60s). The VO above says what he actually said, so the video can't be called a misquote. "बस्तर" was also dropped because the clip doesn't confirm the location. Add it back only if you have a source for it.

Optional stronger hook (0:00–0:03): *"प्रधानमंत्री ने CRPF जवानों से कहा — इन्हें पहचानो, परास्त करो। 'इन्हें' कौन?"*

## CapCut steps
1. Import `final_noVO_9x16.mp4` and add your VO takes at 0:00, 0:18 and 0:32.
2. Mix: VO at **0 dB** and the video track at **−6 dB**. Keep the 6–18s PM audio at full volume.
3. Auto-captions: generate them from **your VO only**. Keep them off 6–18s, where the on-screen quote already acts as captions. Place them at y ≈ 1500–1600.
4. Face-cam for 32–42s (optional): put your close-up on the main track. Overlay `overlay_greenscreen.mp4`, then Chroma key → green, intensity ~40. The slot is x60 y250, 960×900.

## Slot map (for overlay_greenscreen.mp4)
- 0–32s: x60 y330, 960×540 (16:9)
- 32–42s: x60 y250, 960×900

## Post copy
- **Title:** CRPF मंच से सियासत? PM के 'दिमागी नक्सली' बयान पर सवाल
- **Description:** CRPF जवानों के सामने PM मोदी ने कहा कि कई राजनीतिक दलों में "दिमागी नक्सलियों" ने घुसपैठ कर ली है। क्या सुरक्षा बलों के मंच से ऐसी बात होनी चाहिए? आपकी राय कमेंट में। वीडियो: ANI · विश्लेषणात्मक टिप्पणी।
- **Hashtags:** #CRPF #PMModi #UrbanNaxal #Democracy #IndianPolitics #Shorts

## Repurpose
- **Carousel (4 slides):** quote → "संसद vs जवानों का मंच" → "संस्थाओं की तटस्थता?" → poll. Use frames from 0:15, 0:24, 0:30 and 0:40.
- **X/Twitter:** the verbatim quote plus your one-line question, with the 12s PM clip attached.
- **Community post poll:** "क्या सुरक्षा बलों के कार्यक्रम में राजनीतिक बयान होने चाहिए? हाँ / नहीं"

## Rebuild
`./build.sh`. It downloads the raw file if it's missing (raw/ is gitignored) and needs ffmpeg, Node and Playwright.
