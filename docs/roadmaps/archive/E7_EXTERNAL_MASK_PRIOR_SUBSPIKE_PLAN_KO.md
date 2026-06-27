# E7 External Mask Prior Sub-Spike Plan

Date: 2026-06-22 KST

Status: E7.03 / E7.3 region precision planning artifact

Owner intent: Test whether external face parsing masks can reduce manual gold-mask drafting work by producing an `External Mask Prior` / `silver draft`, without treating external masks as official gold or product assets.

## 1. Core Decision

External face parsing masks are useful only as a prior.

They are not official gold, not direct UV atlas input, and not product/source assets. Official gold remains:

```txt
our app clean synchronized capture frame.png
+ matching arface_export.json from the same runtime moment
+ human-edited / human-approved region mask
```

The sub-spike question is:

```txt
external mask samples
-> normalized face-coordinate prior for lip / eye
-> landmark-based soft oval prior for cheek
-> warp to our app clean frame.png as a silver draft
-> human correction and approval
-> official gold
-> UV back-projection / atlas generation
```

This plan stays inside E7.03 / E7.3 region precision. It does not start runtime MediaPipe, runtime face parsing, runtime SAM, E7.4, E7.5, E7.6, product readiness, M7 Green, SDK readiness, backend upload, or commercial SDK work.

## 2. Why External Masks Cannot Be Gold

External dataset masks cannot be used directly as gold or direct UV atlas input because:

- They are labeled in the external image's pixel coordinate system, not in this app's ARFace mesh / UV coordinate system.
- They do not include this app's synchronized `arface_export.json`, screen-space vertices, UVs, indices, blendshapes, display transform, or clean-frame flags.
- They usually describe anatomical parsing classes, not cosmetic placement intent. This matters most for `cheek`, where "blush-safe zone" is not a standard dataset class.
- Their taxonomy differs from our validation target. For example, eye parsing may mark the visible eye opening, while our E7.3 target is a broad eyeshadow / eye tint zone.
- License and derivative-output constraints may prevent treating downloaded masks, pretrained weights, or generated outputs as product material.
- A single static prior may fit the calibration face but fail on a held-out person. That failure must be measured instead of hidden.

Therefore:

- External masks may seed a silver draft.
- A silver draft may reduce rough manual work.
- Only a human-reviewed mask on this app's clean synchronized frame can become official gold.

## 3. External Source Review

No external dataset, checkpoint, or model should be downloaded in the first implementation session until license, size, storage path, and purpose are reported and approved.

Current download-size decision:

- CelebAMask-HQ and LaPa official GitHub pages expose download links but do not provide a stable single total byte size in the readable repo text inspected for this plan.
- BiSeNet, SegFace, SAM, and MediaPipe model/checkpoint sizes depend on the selected pretrained file or bundle.
- Therefore the first implementation session must run a size/license review before download and record exact byte size from the chosen link or file metadata.

| Source | Useful signal | License / use caution | Download-size status | First-session role |
| --- | --- | --- | --- | --- |
| [CelebAMask-HQ](https://github.com/switchablenorms/CelebAMask-HQ) | 30,000 512x512 manually annotated masks; 19 labels including skin, eyes, mouth, upper lip, lower lip | Dataset and software are restricted to non-commercial research / educational use; do not copy assets into product source | Official GitHub exposes Google Drive / Baidu links but not a stable total byte size; verify before approval | Taxonomy and small approved sample only |
| [CelebAMask-HQ label list](https://raw.githubusercontent.com/switchablenorms/CelebAMask-HQ/master/face_parsing/README.md) | `skin`, `l_eye`, `r_eye`, `mouth`, `u_lip`, `l_lip` | Label map is useful for mapping classes, not for direct gold | Text reference only | Define lip/eye class mapping |
| [LaPa](https://github.com/jd-opensource/lapa-dataset) | More than 22,000 images; 11-category pixel label map plus 106 landmarks | Freely available for non-commercial purposes under license terms; verify before model/output use | Official GitHub exposes Google Drive / Baidu links but not a stable total byte size; verify before approval | Landmark-normalized prior candidate |
| [LaPa label map](https://raw.githubusercontent.com/jd-opensource/lapa-dataset/master/labelmap.txt) | `skin`, `left eye`, `right eye`, `upper lip`, `inner mouth`, `lower lip` | Good for lip/eye mapping; no cheek/blush class | Text reference only | Class mapping and landmark-region normalization |
| [BiSeNet face parsing](https://github.com/zllrunning/face-parsing.PyTorch) | Practical face parsing implementation trained on CelebAMask-HQ-style classes | Code and pretrained weights must be reviewed separately; generated outputs stay silver | No download before approval | Optional offline parsing baseline; medium difficulty because it is an older PyTorch workflow with separate pretrained model handling |
| [SegFace](https://github.com/Kartik-3004/SegFace) | Face parsing models for CelebAMask-HQ / LaPa / Helen, with downloadable weights | Code/weights/dataset terms must be reviewed; outputs remain reference-only until cleared | Hugging Face weights referenced; no download before approval | Optional newer offline parsing baseline; medium-high difficulty because it needs dataset-specific config, checkpoint selection, and local GPU/CPU feasibility check |
| [MediaPipe Face Landmarker](https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker) | 478 3D landmarks, blendshape scores, facial transformation matrices | Offline helper only in this sub-spike; runtime integration is out of scope | Model bundle not downloaded here | Normalize faces and compare geometry |
| [Segment Anything](https://github.com/facebookresearch/segment-anything) / [MediaPipe Interactive Segmenter](https://developers.google.com/edge/mediapipe/solutions/vision/interactive_segmenter) | Prompted / interactive segmentation on our clean frame | Mask drafting helper only; not semantic truth and not runtime dependency | Checkpoint/model download requires approval | Optional silver cleanup helper on our frame |

## 4. Normalized Face-Coordinate Prior

The first experiment should avoid AR runtime changes and large data movement.

Recommended normalization:

1. Select an approved small sample set: 20-50 external face images with masks.
2. For each sample, derive a stable 2D face coordinate system using available dataset landmarks or offline MediaPipe Face Landmarker output.
3. Normalize by eye centers, nose/mouth landmarks, face box, and orientation so masks can be accumulated into a canonical 2D face space.
4. Map dataset labels into our region roles:
   - `lip`: upper lip + lower lip; inner mouth stays outside or caution/negative.
   - `eye`: left eye + right eye as the seed, then expand into a broad eyeshadow zone using landmark-relative dilation and upward/side feather rules.
   - `cheek`: no dataset class by default; use landmark-based soft oval placement.
5. Accumulate per-region probability maps:
   - positive votes from region labels,
   - negative/caution votes from teeth/inner-mouth/skin spill zones where available,
   - unknown where source labels do not support the decision.
6. Store maps as prior artifacts, not gold artifacts.

The prior should produce these outputs:

```txt
evidence/e7-external-mask-prior/
  source_review/
    license_size_review.md
  samples/
    manifest.json
  normalized_priors/
    lip_prior_probability.png
    eye_seed_probability.png
    eye_eyeshadow_expanded_prior.png
    cheek_landmark_soft_oval_prior.png
    prior_meta.json
  app_frame_drafts/
    frame_0001/
      clean_frame_reference.txt
      lip_silver_draft.png
      eye_silver_draft.png
      cheek_silver_draft.png
      silver_overlay_contact_sheet.jpg
      human_review_notes.md
  held_out_tests/
    person_a_to_person_b_summary.md
```

All artifacts stay under `evidence/` unless a later plan explicitly promotes derived validation assets. Do not copy external dataset images, external masks, pretrained weights, or third-party template assets into Unity `Resources`, product source, or tracked app assets.

## 5. Region Expectations

### Lip

Expected benefit:

- Highest expected value from external parsing.
- External datasets often distinguish upper/lower lip and sometimes inner mouth.
- A normalized lip prior can reduce rough tracing time for neutral, smile, and mouth-open draft masks.

Known limits:

- Person-specific lip thickness, corners, cupid's bow, teeth exposure, and inner-mouth shape can break a static prior.
- Lipstick validation penalizes spill into skin, teeth, and inner mouth more than small misses.
- Human review must decide visible lip surface vs shadow, teeth, or open-mouth holes.

First test:

- Generate `lip_silver_draft.png` on 1-3 clean app frames.
- Human reviewer marks where the draft saved time and where it was misleading.
- Held-out person gate checks whether prior trained/tuned on person A overpaints or underpaints person B.

### Eye

Expected benefit:

- External parsing can identify visible eye regions and eye-adjacent anchors.
- MediaPipe or dataset landmarks can support a broader eyeshadow placement envelope.

Known limits:

- Face parsing `eye` is often too small for eyeshadow.
- Our E7.3 target is a broad eye / eyeshadow / soft tint zone, not only the visible sclera/eyelid opening.
- Blink, squint, eyelid crease, eyebrow distance, glasses, and gaze direction can make a static prior fragile.

First test:

- Treat external `left eye` / `right eye` as a seed, then generate an expanded eyeshadow-zone prior using landmark-relative dilation and feather.
- Fail the draft if it spills into lower face, forehead too high, cheek, or eyeball in a way a quick human edit cannot rescue.

### Cheek

Expected benefit:

- External datasets can help avoid obvious non-cheek areas such as lips, eyes, nose, and hair.
- Face landmarks can anchor a blush placement prior near cheek/apple/cheekbone zones.

Known limits:

- Public face parsing datasets usually do not provide a `cheek` or `blush` class.
- Blush is cosmetic placement, not a strict anatomy label.
- The best first-pass cheek prior is a landmark-based soft oval with strong feather, not a dataset class.

First test:

- Generate `cheek_landmark_soft_oval_prior.png` from eye/nose/mouth/face-width anchors.
- Human review focuses on centroid, softness, symmetry, and avoiding jaw, nose fold, under-eye, and mouth-corner spill.

## 6. Static, Parametric, and Runtime Hybrid Paths

Use this ladder to prevent scope creep:

| Path | Meaning | E7.03 role | Promotion / stop rule |
| --- | --- | --- | --- |
| Static prior | One canonical normalized mask per region, warped to the app frame | First experiment | Keep only if held-out person drift is small enough for quick human correction |
| Parametric prior | Prior with face shape, landmark distance, expression, local scale, offset, or feather parameters | Next offline improvement | Use when static prior helps but fails predictably by face shape or expression |
| Runtime ML / hybrid | Live or near-live semantic model, MediaPipe, SAM, face parsing, or multi-tracker path | Out of scope here | Write a new boundary proposal only if offline evidence shows static/parametric prior cannot reach Q3 |

If static prior fails on a held-out person, record it as evidence. Do not hide it and do not call the method failed in a vague way. The useful conclusion may be: `single static UV prior is insufficient; runtime semantic or parametric hybrid may be required for this region`.

## 7. First Experiment Scope

Small first-pass scope:

- External samples: 20-50 images/masks after license and size approval.
- App frames: 1-3 clean synchronized app frames. Prefer one `lip` frame first, then add one `eye` and one `cheek` frame only if the lip flow is clear.
- People: at least two identities if available:
  - calibration person/group A,
  - held-out person/group B.
- Regions: `lip`, `eye`, `cheek` only.
- Outputs: prior probability maps, silver draft masks, overlay contact sheet, human review notes, and held-out summary.

Do not:

- Build Unity/RN.
- Add runtime MediaPipe / face parsing / SAM.
- Download full datasets without approval.
- Copy external assets into Unity or RN source.
- Claim E7.03 Green, E7.4 readiness, E7.6 performance, product readiness, SDK readiness, or M7 Green.

## 8. Held-Out Person / Generalization Gate

This gate is mandatory because the key risk is whether a single static prior fits real people.

Procedure:

1. Build or tune the normalized prior using person/group A samples.
2. Apply the same prior to person/group B app frame(s) without person-specific hand tuning.
3. Compare the silver draft against human judgment:
   - `lip`: skin/teeth/inner-mouth spill, corner miss, thickness mismatch.
   - `eye`: too-small seed, brow/forehead spill, lower-face spill, blink/squint drift risk.
   - `cheek`: centroid too high/low, jaw/nose/under-eye/mouth-corner spill, hard-edge appearance.
4. Label each region:
   - Green: draft is close enough that human correction is small and predictable.
   - Yellow: draft saves rough work but needs clear region-specific correction rules.
   - Red: draft misleads the author or fails across face shape enough that static prior should not be promoted.

Passing this gate does not make the mask gold. It only says the prior is useful enough to assist gold authoring.

## 9. Success / Failure Criteria

Success for this sub-spike:

- External sources are reviewed with label, license, size-status, storage, and reference-only notes.
- A small prior can produce silver drafts on our clean app frame(s).
- Human reviewer can explain what work was saved and what still needed correction.
- Held-out person behavior is recorded instead of guessed.
- The output clarifies whether to continue static prior, move to parametric prior, or propose a future runtime hybrid plan.

Failure / stop criteria:

- License or size review blocks local sampling.
- External labels do not map cleanly enough to our `lip` / `eye` / `cheek` targets.
- Warped silver drafts are so misleading that manual gold authoring from scratch is faster.
- Held-out person drift is large and unpredictable for `lip` or `eye`.
- Cheek prior behaves like anatomy segmentation instead of cosmetic blush placement.

Failure is still useful if it tells the team that a static prior is not enough.

## 10. Evidence and Storage Policy

Evidence policy:

- Store local validation artifacts under `evidence/e7-external-mask-prior/`.
- Do not commit `evidence/`, external downloads, generated masks, pretrained weights, raw recordings, or selected face frames unless repo policy explicitly changes.
- Keep raw external datasets outside tracked source.
- Store only the minimum selected local artifacts needed for decision review.
- If a raw recording is used to extract representative frames, retain metadata/contact sheets/representative frames and delete the raw recording when no longer needed.
- Every silver artifact must record:
  - source,
  - source URL,
  - license note,
  - sample count,
  - command/tool/model version if generated,
  - whether it was human-reviewed,
  - whether it remains silver or was promoted to gold.

Suggested manifest fields:

```json
{
  "planId": "e7-external-mask-prior",
  "status": "planning",
  "role": "silver_draft_only",
  "officialGoldRequiresHumanApproval": true,
  "externalDownloadsApproved": false,
  "sourceReviews": [],
  "appFrames": [],
  "heldOutTests": [],
  "privacy": {
    "rawRecordingStored": false,
    "offDeviceUpload": false,
    "externalAssetsInProductSource": false
  }
}
```

## 11. Relationship to Reference-Driven UV Atlas

This plan does not replace `E7_REFERENCE_DRIVEN_UV_ATLAS_PLAN_KO.md`.

Relationship:

- The reference-driven UV atlas plan defines the official gold -> UV back-projection -> atlas path.
- This external prior plan defines a possible way to create faster silver drafts before human gold review.
- UV atlas input must still be official gold on our clean synchronized app frame.
- External dataset masks and parsing-model outputs remain support material unless they are re-authored or approved by a human on our app frame.

Suggested execution order:

1. Validate one clean synchronized capture pair and one-frame round-trip from the UV atlas plan.
2. In parallel or after that, run this External Mask Prior sub-spike offline.
3. Promote only human-approved masks into the gold path.
4. Use held-out person results to decide whether static prior is enough or a stronger parametric/hybrid plan is needed.

## 12. Next Implementation Session Checklist

1. Re-read `AGENTS.md` and `TECH_VALIDATION_RESULT.md` Current Session Snapshot.
2. Confirm E7.3 remains the active boundary and E7.4/E7.5/E7.6 remain out of scope.
3. Create `evidence/e7-external-mask-prior/` skeleton and `manifest.json` only if the session is explicitly implementing this sub-spike.
4. Fill `source_review/license_size_review.md` before downloading any dataset, checkpoint, or model.
5. If approved, sample only 20-50 external masks and record exact storage location.
6. Generate normalized `lip`, expanded `eye`, and landmark-soft-oval `cheek` priors.
7. Warp priors to 1-3 app clean frames as silver drafts.
8. Run human review and held-out person scoring.
9. Decide: continue static prior, add parametric prior, or propose future runtime hybrid boundary.
10. Do not build Unity/RN unless a later approved Build Gate explicitly asks for it.

## 13. Short Korean Summary

이 방식으로 줄일 수 있는 수작업:

- `lip`과 `eye`의 첫 마스크 초안을 만드는 시간을 줄일 수 있다.
- 외부 parsing mask와 landmark를 normalized face-coordinate prior로 누적하면, 사람이 빈 화면에서 시작하지 않고 silver draft 위에서 수정할 수 있다.
- `cheek`은 dataset mask보다 landmark 기반 soft oval blush prior로 시작하는 편이 현실적이다.

여전히 사람이 해야 하는 gold 검수:

- 외부 mask, model output, SAM draft는 모두 silver다.
- official gold는 반드시 우리 앱의 clean synchronized `frame.png` 위에서 사람이 수정/승인한 mask다.
- 사람별 입술 두께, 입꼬리, inner mouth, eye/eyeshadow zone, cheek blush placement는 사람이 최종 판단해야 한다.

다음 구현 세션에서 바로 할 3-5개 작업:

1. 외부 source별 license / label / size / 저장 위치를 먼저 기록하고 승인 전 다운로드를 멈춘다.
2. 20-50개 외부 샘플과 1-3개 app clean frame 기준의 작은 offline prior 실험을 만든다.
3. `lip`, 확장된 `eye`, landmark 기반 `cheek` silver draft를 생성한다.
4. A 인물 기준 prior를 B 인물에 적용하는 held-out person gate를 실행한다.
5. 결과를 보고 static prior 유지, parametric prior 보강, 또는 future runtime hybrid proposal 필요 여부를 결정한다.
