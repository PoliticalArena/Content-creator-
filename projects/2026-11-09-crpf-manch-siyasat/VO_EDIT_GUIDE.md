# CRPF मंच और सियासत — 59s Short (9:16)

**Footage:** Drive `Modi` (1cjugGQ_mg_3EREmHAeBBUr62YW979z07). It's an ANI clip reposted by @saket.gokhale. The build crops out the repost caption and blurs the IG watermark. The ANI bug stays on screen and is credited as "वीडियो: ANI".

## Files
| File | Use |
|---|---|
| `exports/final_9x16.mp4` | **Ready to post.** 59s with your VO (take 09-11-2026 10:13), the PM's original audio and BGM. |
| `exports/final_noVO_9x16.mp4` | The same video without VO, in case you re-record. |
| `exports/overlay_greenscreen.mp4` | Graphics only, with green slots for chroma-keying your own clips or face-cam. |
| `exports/bgm_drone.m4a` | 59s generated ambient drone (no copyright claims). |

## Timeline (cut to your VO take)
| Time | Screen | Audio |
|---|---|---|
| 0:00–0:08.6 | "CRPF मंच और सियासत?" + the speech footage | VO: "देश के सुरक्षा बलों की वर्दी… सवाल उठना लाज़िमी है" |
| 0:08.6–0:20.6 | The quote, revealed line by line | **PM's original audio** |
| 0:20.6–0:39.3 | संसद/चुनाव → संवैधानिक पद → 'दिमागी नक्सली'? → तटस्थता? | VO: "लोकतंत्र में दलों… सवाल नहीं खड़ा करता" |
| 0:39.3–0:59 | Close-up · poll · Subscribe | VO: "नक्सलवाद के खिलाफ… share करें" |

Your take is 47s long. Rather than speeding it up, I stretched the video to 59s to fit it.

**I changed one line in the Gemini script (0:18–0:32).** The PM did **not** call parties "दिमागी नक्सली". His words were "कई राजनीतिक दलों में, अलग-अलग संगठनों में भी इन दिमागी नक्सलियों ने अपनी घुसपैठ कर ली है… हमें इन्हें पहचानना है, परास्त करना है" (raw 41–60s). The VO above says what he actually said, so the video can't be called a misquote. "बस्तर" was also dropped because the clip doesn't confirm the location. Add it back only if you have a source for it.

Optional stronger hook (0:00–0:03): *"प्रधानमंत्री ने CRPF जवानों से कहा — इन्हें पहचानो, परास्त करो। 'इन्हें' कौन?"*

## CapCut steps (optional, since `final_9x16.mp4` is already mixed)
1. Auto-captions: generate them, then delete the ones between 0:08.6 and 0:20.6, where the on-screen quote already acts as captions. Place them at y ≈ 1500–1600.
2. Face-cam for 39.3–59s (optional): put your close-up on the main track. Overlay `overlay_greenscreen.mp4`, then Chroma key → green, intensity ~40.

## Slot map (for overlay_greenscreen.mp4)
- 0–39.3s: x60 y330, 960×540 (16:9)
- 39.3–59s: x60 y250, 960×900

## Post copy
- **Title:** CRPF मंच से सियासत? PM के 'दिमागी नक्सली' बयान पर सवाल
- **Description:** CRPF जवानों के सामने PM मोदी ने कहा कि कई राजनीतिक दलों में "दिमागी नक्सलियों" ने घुसपैठ कर ली है। क्या सुरक्षा बलों के मंच से ऐसी बात होनी चाहिए? आपकी राय कमेंट में। वीडियो: ANI · विश्लेषणात्मक टिप्पणी।
- **Hashtags:** #CRPF #PMModi #UrbanNaxal #Democracy #IndianPolitics #Shorts

## Repurpose
- **Carousel (4 slides):** quote → "संसद vs जवानों का मंच" → "संस्थाओं की तटस्थता?" → poll. Use frames from 0:19, 0:29, 0:37 and 0:50.
- **X/Twitter:** the verbatim quote plus your one-line question, with the 12s PM clip (0:08.6–0:20.6) attached.
- **Community post poll:** "क्या सुरक्षा बलों के कार्यक्रम में राजनीतिक बयान होने चाहिए? हाँ / नहीं"

## Rebuild
`./build.sh`. It downloads the raw file if it's missing (raw/ is gitignored) and needs ffmpeg, Node and Playwright.
