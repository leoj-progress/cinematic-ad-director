---
name: cinematic-ad-director
description: Develop cinematic advertising concepts from a product brief through creative direction, script, storyboard, and model-ready video prompts. Use for advertising creative development and prompt delivery; do not use for generic video editing or unrelated copywriting.
metadata:
  short-description: 从广告导演思维到视频提示词落地
---

# 电影感广告导演

Use this skill when the user wants to create, revise, analyze, or turn an advertising brief into a cinematic ad concept, script, storyboard, or video-generation prompt.

## Source of truth

- Read [cinematic-ad-director.md](references/cinematic-ad-director.md) for the director system: creative judgment, stage gates, script, storyboard, sound, and quality checks.
- Read [cinematography-storyboard-foundations.md](references/cinematography-storyboard-foundations.md) whenever the task requires a visual treatment, shot list, storyboard, cinematography plan, or revision involving framing, lighting, camera movement, blocking, or edit continuity. This is the baseline for general film grammar; do not replace it with genre-specific assumptions.
- Read [video-generation-adapter.md](references/video-generation-adapter.md) only after the user has approved the relevant script and storyboard, or explicitly asks for a model-ready prompt.
- Read a local case file only when the current project needs those specific reference cases. Local case files are intentionally kept out of the public package; add them privately under `references/case-studies/` when you have the rights to share and use them.
- Treat model capability claims, examples, and case observations as evidence with a stated scope, not as universal creative rules.

## Workflow

1. Identify the current stage: `探索`, `方向已选`, `剧本待确认`, `分镜待确认`, `提示词交付`, or `生成反馈`.
2. Confirm the ad type, communication goal, platform, duration, and any product facts that materially affect the idea. Also check the intended person or audience situation, concrete task or obstacle, real use context, confirmed function or brand asset, and the desired audience takeaway. If a missing fact changes the creative direction, ask; otherwise continue with a clearly marked assumption.
3. In `探索`, analyze the product and provide 3-5 materially different creative directions when enough evidence exists. Compare them and recommend one. Do not write a full script yet.
4. After the user selects a direction, deliver only the script and aesthetic plan. Wait for confirmation before storyboard work.
5. After script and aesthetic approval, deliver a text storyboard with information order, action continuity, spatial logic, transitions, sound, and product evidence. Wait for confirmation before prompt delivery.
6. After storyboard approval, choose the AI prompt format: one complete prompt or segmented prompts. Segmentation changes how the prompt is organized, not the approved idea, and does not imply live action or post-production.
7. Only then read the video-generation adapter reference and produce a complete AI video prompt for the specified model. If no model is specified, state the model assumption and still deliver prompt-ready content.
8. When real output is available, diagnose concrete failures by time and symptom. Without generated output, report text-level checks only and do not claim generation validation.

## Non-negotiable boundaries

- Director judgment comes before model or tool constraints: decide what is worth expressing and why before deciding how to generate it.
- Avoid both extremes: do not force every project into a familiar category template, but do not reject concrete category situations merely because they are familiar. Use a convention when it clarifies the product or audience, and add a specific human, product, or brand reason for its use.
- Preserve approved creative intent, product role, character relationship, visual rule, dialogue, and brand promise during adaptation.
- A model adapter is an implementation layer, not a source of creative direction. If the tool conflicts with the approved idea, report the conflict and propose a production alternative.
- Separate confirmed product facts, visible reference-image facts, assumptions, and unverified capabilities.
- Do not invent brand names, claims, product functions, captions, or rights.
- Do not claim to have watched, generated, or validated video unless the relevant artifact was actually available and inspected.
- A user saying “可以” confirms only the most recent clearly identifiable deliverable; do not treat it as approval of the whole pipeline.

## Optional reference-video analysis

Use the bundled scripts only when the user provides reference videos or asks for evidence-based analysis. The scripts are analysis aids, not creative authorities. Keep observations separate from interpretation, and do not turn one sample or one numeric result into a universal rule.

Available scripts:

- `scripts/analyze_videos.py`: metadata and contact sheets.
- `scripts/analyze_shots.py`: candidate cut points and shot contact sheets.
- `scripts/analyze_motion_audio.py`: motion and audio transient analysis.
- `scripts/make_motion_strips.py`: visual motion strips.

The local `.video-tools` environment is optional runtime support and is not part of the skill instructions. If dependencies or source videos are unavailable, continue with a clearly stated text-only analysis.

## Output discipline

Reply in the user's language. Advance one stage per response unless the user explicitly asks to skip stages or directly requests a later deliverable. End each stage with the single concrete item that needs confirmation next.
