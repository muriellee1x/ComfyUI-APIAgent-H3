---
name: h3-low-coin-gift-director
description: Write production-ready MiniMax H3 prompts for single-play Douyin live gifts priced from 99 through 999 coins. Use for deterministic low-tier duration, one-shot, silence, aspect-ratio, exact solid-color background, H3-mode, emotion, and task-selected motion references.
---

# H3 Low-Coin Gift Director

Create one compact, readable, production-ready 99-999-coin live-gift animation.

## Runtime workflow

1. Parse the structured price, H3 mode, effective duration, emotion, aspect ratio, optional `[APIAGENT_GIFT_BG_COLOR=#RRGGBB]`, original user constraints, creative request, and image-role markers from the task.
2. Apply the complete price rule and numeric profile loaded from `rules/price-effect-system.md` and `rules/price-effect-profile.json`. Reject prices outside 99-999.
3. For 99-499, require the exact background marker; the executor supplies `#00FF00` when its input is empty. For 500-999, activate the exact background only when the marker exists; otherwise keep the compact-scene-or-solid-field allowance.
4. When the marker exists, apply `rules/constant-solid-background.md` as a hard conditional rule. The color string is authoritative and consumes no picture label.
5. Enforce the derived hard contract: 73 frames/about 3.04 seconds for 99-299; 90 frames/3.75 seconds for 300-999; one continuous shot; silent audio; one single-play entrance-display-exit chain; and only 1:1 or 4:3.
6. Apply the complete shared H3 contract from `rules/h3-prompt-writing-base-en.txt`. In Ref2VA, also apply the complete full-reference contract from `rules/h3-prompt-writing-ref-en.txt`.
7. Apply the loaded common emotion guidance and exactly one selected emotion section from `rules/emotion-rules.md`. Keep it subordinate to the user's theme and low-tier capacity.
8. Use only the optional registry fragments supplied by the executor. Use the routed four-second motion fragments for directed rhythm, safe framing, component order, semantic climax, or final cooling; compress their logic for 99-299.
9. Preserve explicit subject identity, structure, materials, endpoint roles, and core action. When explicit content exceeds the tier, emit the required Chinese warning but retain all hard delivery constraints.
10. Return only the allowed Chinese warning followed by the complete English H3 prompt in the selected schema.

## Precedence

1. Exact H3 first-frame or last-frame contracts and the active exact background contract; endpoint images are expected to be pre-matched to the same color.
2. Low-tier hard production rules, including the default `#00FF00` for 99-499 when no color is entered.
3. Explicit user subject, identity, and core action.
4. Selected emotion direction.
5. Optional registry guidance and inferred decoration.

Conflicting user duration, shot count, audio, or aspect-ratio requests remain visible in the task but do not override the low-tier hard contract.

## Validation

Before returning, verify price scope, effective duration, exactly one `[Shot 1]`, no cut language, silent audio fields, valid aspect ratio, image labels, endpoint timing, causal motion, and completed exit or exact endpoint settle. When an exact background marker is active, verify that every required H3 field repeats the same `#RRGGBB` and keeps that full-frame field unchanged for the entire video. Do not output reasoning, alternatives, Markdown fences, negative-prompt tails, or `--wm false`.
