# Exact solid-color background contract

Apply this rule only when the task contains `[APIAGENT_GIFT_BG_COLOR=#RRGGBB]`. The marker value is the sole source of truth for the background. Never sample, rename, approximate, complement, or replace it.

## Full-video invariant

- Fill every pixel behind the gift with one continuous, uniform, texture-free field using the exact `#RRGGBB` value.
- Keep hue, luminance, texture, and coverage unchanged from the first frame through the final frame.
- Keep the field visually stationary. Do not add gradients, seams, perspective, floor lines, horizon lines, environmental parallax, shadows cast onto the field, or lighting changes in the field.
- In 1:1, fill the frame directly. In 4:3, extend the identical color to full-frame coverage without a seam or luminance change.
- Keep foreground glows, trails, particles, smoke, reflections, and color spill localized to the subject or effect. They must not recolor, tint, illuminate, darken, texture, or occlude the background field.
- If the subject or effect fades or exits, change only the foreground opacity. The exact background remains fully visible and unchanged.

## Ref2VA binding

Do not invent or cite a background picture. The color string is authoritative and does not consume a `<Picture N>` label.

- `subject_definitions`: define one visible background subject as the full-frame uniform solid-color field using the exact `#RRGGBB`, with constant hue, luminance, texture, and coverage. Do not attribute it to a picture.
- `summary`: state that the gift performs on that background subject and repeat the exact `#RRGGBB`.
- `retention_analysis`: mark the background subject as `fully_preserved` from the task specification and repeat the exact `#RRGGBB`.
- `detailed_description`: require the background subject to fill every pixel behind the gift for the entire shot and repeat the exact `#RRGGBB`.

## Base H3 modes

For T2VA, I2VA, FL2VA, and L2VA, repeat the exact `#RRGGBB` in the main multimodal description and state the full-frame, uniform, texture-free, first-to-last-frame invariant. Exact endpoint images are assumed to have been prepared with the same background color; do not weaken either contract in the prompt.

## Final check

The prompt must contain only the selected background color. Reject any other background hex value, named replacement color, gradient, texture, environment replacement, or background recoloring instruction.
