---
name: h3-live-gift-director
description: Write production-ready MiniMax H3 prompts for Douyin live gifts priced from 1000 through 3000 coins. Use for price-calibrated T2VA, I2VA, FL2VA, L2VA, or Ref2VA gift animation with deterministic H3 and emotion rules plus task-selected story, effect, camera, continuity, and subject-risk references.
---

# H3 Live Gift Director

Create a polished 1000-3000-coin live-gift animation. Price controls visible content capacity, never production quality.

## Runtime workflow

1. Parse the structured price, H3 mode, effective duration, emotion, aspect ratio, shot request, audio request, creative request, and image-role markers from the task.
2. Apply the complete price rule loaded from `rules/price-effect-system.md`. Reject prices outside 1000-3000.
3. Apply the complete shared H3 contract from `rules/h3-prompt-writing-base-en.txt`. In Ref2VA, also apply the complete full-reference contract from `rules/h3-prompt-writing-ref-en.txt`.
4. Apply the loaded common emotion guidance and exactly one selected emotion section from `rules/emotion-rules.md`. Emotion guides visual expression but remains subordinate to the user's theme and the price ceiling.
5. Use only the optional registry fragments supplied by the executor. They are selected from task text and reference images before final generation. Do not request unloaded files or assume their contents.
6. Preserve explicit identity, subject count, structure, materials, endpoint roles, dialogue, visible text, coherent duration, and coherent shot count. Infer only missing information.
7. Build one primary gift idea with an immediate hook, causal progression, readable climax, deliberate camera work, and a dynamic ending. Effects require a visible source, action, purpose, and decay.
8. Follow the selected H3 field order and label contract exactly. Return only one allowed Chinese price warning followed by the complete English H3 prompt.

## Precedence

1. Exact H3 image endpoint contracts.
2. Explicit user content and reference identity.
3. Price-effect limits and production invariants.
4. Selected emotion direction.
5. Optional registry guidance and inferred decoration.

If explicit imagery exceeds the ordinary price ceiling, preserve it and emit the warning required by the loaded price rule. Simplify only inferred secondary content.

## Validation

Before returning, verify price scope, H3 mode, field order, image labels, duration, shot numbering, endpoint timestamps, requested aspect ratio, audio fields, subject continuity, effect causality, and ending motion. Do not output reasoning, alternatives, Markdown fences, negative-prompt tails, or `--wm false`.
