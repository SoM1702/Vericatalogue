---
format: 1920x1080
duration: 90s
message: "Industrial product data becomes usable only when every attribute carries proof."
arc: "Demo Loop — trust problem → source proof → review → bounded AI → safe SKU selection → catalog health"
audience: "UniHack judges and industrial-commerce evaluators"
mode: autonomous
music: none
---

## Frame 1 — The trust gap

- scene: Proof-first hook on a calm editorial field; “extract” becomes “trust” only when proof appears.
- voiceover: "AI can extract catalog data. But can a PIM trust it?"
- duration: 8s
- poster: 5s
- transition_in: cut
- status: outline
- src: compositions/frames/01-trust-gap.html
- type: hook
- persuasion: Pain validation
- beat: tension → curiosity
- blueprint: compose
- asset_candidates:
- focal: the word “proof”
- roles: no media asset; editorial type is the subject

Composition notes: an evidence-first editorial token cycle replaces a generic AI claim while preserving the short, type-led hook rhythm.
Scene 1 (0.0–2.0s): warm white field with the centred phrase “AI can extract” arriving as a per-word staggered reveal (`dynamic-content-sequencing`); centred layout, one dominant near-black line in the upper 70%, then hold.
Scene 2 (2.0–5.3s): “extract” hard-cuts to “structure” then “trust” through an in-place token cycle (`discrete-text-sequence`); each token lands only as the question advances, with a single primary type treatment and quiet proof-line support.
Scene 3 (5.3–8.0s): a thin evidence underline SVG self-draws (`svg-path-draw`) beneath “trust”, then the qualifying line “only when every field carries proof” resolves below; centred, spacious, still held read with no back-half drift.

narrativeRole: Establish the decision risk before showing any feature.
keyMessage: Extraction without retained evidence is not ready for industrial commerce.

## Frame 2 — Evidence at field level

- scene: Project-owned record screenshot framed beside a concise proof checklist: source file, page, snippet, raw value, normalized value.
- voiceover: "Every field keeps its source, its snippet, its raw value, and its normalization."
- duration: 14s
- poster: 8s
- transition_in: zoom-through
- status: outline
- src: compositions/frames/02-field-evidence.html
- type: product_intro
- persuasion: Show-don't-tell proof
- beat: clarity
- blueprint: device-surface-showcase
- asset_candidates: assets/vericatalog-proof-demo.png — project-owned evidence-backed product record screenshot
- focal: assets/vericatalog-proof-demo.png
- roles: assets/vericatalog-proof-demo.png = supporting product surface

Adapt: keep the held product-surface showcase; replace browser interaction with an evidence callout sequence around the real project UI.
Scene 1 (0.0–3.0s): project-owned UI screenshot enters as a framed product surface on the right 60%, while “A structured record is not enough.” arrives left in display type; asymmetric 40/60, three depth layers, smooth locked landing (`motion-blur-streak`).
Scene 2 (3.0–8.8s): as the sentence names each item, four attached callouts reveal sequentially around the screenshot — source file, page + snippet, raw value, normalized value — via per-word/card staggered reveal (`dynamic-content-sequencing`); UI stays readable and all important content remains above the caption band.
Scene 3 (8.8–14.0s): a restrained coordinate-target zoom (`coordinate-target-zoom`) moves toward the retained evidence area, then “Every field stays inspectable.” enters on the left; the screenshot and final callout hold still for the read.

narrativeRole: Make the product's distinct trust layer visible in the real interface.
keyMessage: A structured field is inspectable rather than an opaque AI answer.

## Frame 3 — Validate before export

- scene: The same real record moves through three measured stations: normalize, validate, route to human review; export remains after the decision.
- voiceover: "Normalize units. Detect conflicts. Route exceptions to a human before export."
- duration: 16s
- poster: 9s
- transition_in: crossfade
- status: outline
- src: compositions/frames/03-review-before-export.html
- type: feature_showcase
- persuasion: Friction reduction
- beat: control
- blueprint: spatial-pan-stations
- asset_candidates: assets/vericatalog-proof-demo.png — project-owned evidence and review workspace screenshot
- focal: assets/vericatalog-proof-demo.png
- roles: assets/vericatalog-proof-demo.png = supporting evidence workspace surface

Adapt: keep the virtual-camera passage through stations; the three stations are the actual workflow: normalize, validate, human review.
Scene 1 (0.0–4.0s): a wide connected workspace opens with “Normalize” large at the left and the real UI screenshot framed as the central evidence surface; layered-depth composition with a static initial camera and the first station appearing only with the first spoken cue.
Scene 2 (4.0–9.5s): virtual camera pans/focus-locks (`viewport-change`) across the connector into “Validate”; a compact card reveals unit conversion and conflict check while the screenshot remains an anchored source surface, asymmetric 60/40 composition.
Scene 3 (9.5–14.0s): the camera continues across the final station “Human review”; an evidence-first decision card arrives through cluster→outward expansion (`center-outward-expansion`), explicitly before the word export is shown.
Scene 4 (14.0–16.0s): “Export only after a human decision.” resolves on the final station; camera locks and the full three-step path holds, with no additional motion.

narrativeRole: Translate visible product features into a safer operational workflow.
keyMessage: A reviewer decides what reaches the PIM; evidence is never erased.

## Frame 4 — AI with boundaries

- scene: A source-quote card passes through an AI candidate gate and emerges as “Inferred — human review required,” never “Verified.”
- voiceover: "AI can map unfamiliar labels. It must quote the source. It cannot verify itself."
- duration: 15s
- poster: 8s
- transition_in: push-slide LEFT
- status: outline
- src: compositions/frames/04-bounded-ai.html
- type: feature_showcase
- persuasion: Risk reversal
- beat: trust
- blueprint: prompt-type-submit-generate
- asset_candidates:
- focal: the source-quote candidate gate
- roles: no media asset; the constrained mapping flow is the product surface

Adapt: keep the ask→response shape, but use source-quoted mapping rather than a free-form AI prompt; the signature submit-to-result handoff becomes a proof gate.
Scene 1 (0.0–3.5s): a small source quote card types on “Body material: SS304” with a caret (`discrete-text-sequence`, `context-sensitive-cursor`); centred upper-third composition, only the source appears at first.
Scene 2 (3.5–7.5s): the quote card slides into an “AI candidate mapper” gate while “Map unfamiliar labels” arrives beside it; the gate opens with a single card morph-anchor (`card-morph-anchor`) and source quote remains visibly attached.
Scene 3 (7.5–11.8s): a candidate card arrives marked “Inferred” and “human review required” through a sequential state reveal (`discrete-text-sequence`); no verified badge appears, and the frame remains visually calm rather than theatrical.
Scene 4 (11.8–15.0s): the final line “It cannot verify itself.” locks below the card; a small proof check self-draws (`svg-path-draw`) and the composition holds still.

narrativeRole: Answer the AI-innovation question without compromising the product's truth model.
keyMessage: AI assistance is constrained, grounded, server-side, and review-required.

## Frame 5 — Keep SKUs separate

- scene: Two catalog-row cards split from one supplier page; each retains only its own part number, material, size, and pressure evidence.
- voiceover: "A catalog page can contain many SKUs. VeriCatalog keeps their evidence separate."
- duration: 18s
- poster: 10s
- transition_in: squeeze
- status: outline
- src: compositions/frames/05-sku-separation.html
- type: benefit_highlight
- persuasion: Negative contrast
- beat: relief + confidence
- blueprint: comparison-split
- asset_candidates:
- focal: the two independently bounded SKU cards
- roles: no media asset; paired catalog rows are the comparison surface

Adapt: keep the mirrored book-open split as the signature move; each card is a distinct, explicitly labelled supplier record rather than a generic comparison.
Scene 1 (0.0–3.0s): top-centred title “One page. Two products.” slides down with a long-tail settle; below, one faint supplier-page band establishes the shared document, split-screen with the bottom caption band empty.
Scene 2 (3.0–9.5s): NFS-BV-2001 and NFS-BV-2002 cards enter from opposite wings with mirrored book-open tilts (`split-tilt-cards`); each holds only its own material, size, and pressure, while the shared supplier band recedes.
Scene 3 (9.5–14.5s): inner-edge badges arrive sequentially — “separate evidence” then “separate record” — using one restrained punctuation entrance (`spring-pop-entrance`); symmetry stays static after landing.
Scene 4 (14.5–18.0s): the statement “Never merge neighboring SKU values.” resolves between the pair and holds; at most a low-amplitude subtle jitter (`sine-wave-loop`) keeps the pair alive.

narrativeRole: Demonstrate the new safety behaviour that prevents cross-SKU value mixing.
keyMessage: If a record boundary is not proven, the system routes it for review instead of combining values.

## Frame 6 — Focus the human queue

- scene: Project-owned Catalog Health screenshot sits behind a focused closing statement and three status chips: Verified, Inferred, Conflict.
- voiceover: "Across a catalog, spend human attention where evidence is missing or sources disagree."
- duration: 19s
- poster: 11s
- transition_in: crossfade
- status: outline
- src: compositions/frames/06-catalog-health.html
- type: cta
- persuasion: Future pacing
- beat: confidence → action
- blueprint: titlecard-reveal
- asset_candidates: assets/vericatalog-health.png — project-owned Catalog Health review-queue screenshot
- focal: the closing operational outcome
- roles: assets/vericatalog-health.png = background product surface

Adapt: keep the calm title-card landing and still hold; the real health screen gives the statement operational context rather than inventing an impact metric.
Scene 1 (0.0–5.0s): the project-owned Catalog Health screenshot fills a softly cropped background plane, dimmed only enough for readability; upper-left eyebrow “CATALOG HEALTH” and the first line “Focus human attention” arrive with one restrained slide-up (`scale-swap-transition`).
Scene 2 (5.0–11.5s): three status chips reveal one at a time on the spoken cues — Verified, Inferred, Conflict — via discrete state sequencing (`discrete-text-sequence`); the screenshot remains visibly real and stable behind them.
Scene 3 (11.5–15.0s): a clean foreground card replaces the chips with “where evidence is missing or sources disagree”; the background screen stays as contextual proof and all elements settle.
Scene 4 (15.0–19.0s): final lockup “VeriCatalog Proof” and “Auditable product intelligence before PIM export” holds in a centred card above the caption band; fully still closing read, no fabricated CTA or metric.

narrativeRole: Close on the operational outcome and the product proposition.
keyMessage: VeriCatalog Proof makes product intelligence auditable before PIM export.

## Video direction

Use the adopted frame tokens exactly: `bg` white, `text` navy, `primary` amber, teal only as the adopted `text-muted` role, and red only as the `negative` inline conflict role. Type uses the display/body roles from `frame.md`; captions stay out of the bottom 17%. Motion uses smooth `power3`-style long-tail settles and reveals each claim only on its spoken cue across the full shot duration. Frames 1–5 develop sequentially; Frame 6 is the deliberate held breather/closing read. During holds, prefer stillness (a finite subtle jitter only where named), never lazy breathing or a back-half camera drift. Never use generic stock imagery, unmeasured metrics, browser chrome, shadows, off-palette gradients, slideshow front-load-and-freeze motion, or screensaver-style independent floating.
