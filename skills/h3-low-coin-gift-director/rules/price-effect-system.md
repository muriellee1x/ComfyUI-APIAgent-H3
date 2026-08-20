# Price-effect system: 99-999 Douyin coins

## Scope and invariants

Calibrate only single-play gifts priced from 99 through 999 coins. Route 1000-3000 coins to `h3-live-gift-director`. There is no calibrated video-gift tier below 99 coins.

Keep these requirements invariant throughout this range:

- one continuous shot;
- 3 seconds for 99-299 coins and 4 seconds for 300-999 coins;
- 1:1 or 4:3 only;
- no soundscape and no music;
- one entrance-display-exit chain;
- stable identity, object construction, motion mechanics, and background;
- single-play price only, with no combo, loop, or accumulated-price logic.

Use [price-effect-profile.json](price-effect-profile.json) as the numeric source of truth.

## Tier matrix

| Price | Duration | Background | Content capacity |
| --- | --- | --- | --- |
| 99-299 | 3 seconds | uniform solid field required | one subject, one immediate motion or state change, one readable gift beat, one exit |
| 300-499 | 4 seconds | uniform solid field required | one developed action chain plus one subordinate material or effect response |
| 500-999 | 4 seconds | compact scene or solid field | one developed action chain plus a compact setting or one subordinate environmental response |

The extra second above 299 buys readability and development, not another shot or a second plot. The background allowance at 500 buys context, not a large environment reveal.

When a ComfyUI task supplies an H3-aligned effective duration, use 73 frames / 3.04 seconds for the 3-second product tier and 90 frames / 3.75 seconds for the 4-second product tier. Use the aligned value in I2VA, FL2VA, or L2VA endpoint instructions and timestamp validation.

## Solid-background keying contract

For every gift below 500 coins, make the whole frame behind the subject one unbroken solid-color field using the exact `[APIAGENT_GIFT_BG_COLOR=#RRGGBB]` value. The executor supplies `#00FF00` when its color input is empty.

- Treat the marker value as authoritative even when a reference image contains another background. Preserve the referenced foreground subject and replace only the incompatible background.
- Never sample, rename, approximate, complement, or replace the exact color value.
- Keep hue, luminance, coverage, and texture uniform from the first frame through the completed exit.
- Keep the background stationary while the subject, trail, particles, or prop move.
- When the subject fades, change the subject and effect opacity only; keep the field unchanged.
- Treat replacement of an incompatible scene background as a delivery-format requirement, not loss of the referenced subject.

For 500-999 coins, preserve a supplied compact background or use a solid field when no exact color marker is present. When the marker is present, replace the compact setting with the exact full-frame solid field and apply the same first-to-last-frame invariant.

## Normal inferred ceiling

Do not infer these elements for a missing low-price concept:

- multiple locations, editorial cuts, or a hidden second shot;
- large ensembles or several independent character actions;
- adult divine beasts, prestige creatures, cosmic civilizations, royal megastructures, or world-scale miracles;
- extensive solid-gold, gemstone, or jewel-encrusted systems;
- full-frame effect storms, multiple unrelated effect families, or environment-wide transformations;
- a setup, journey, and climax that require more time than the single action chain.

Ordinary props, stylized people, stylized or lightly realistic animals, compact fantasy objects, flowers, books, gift boxes, fans, badges, instruments, toys, and small vehicles are suitable.

## Explicit-content exception

When the user or a reference explicitly supplies higher-value content:

1. Give one short Chinese warning that the subject or effect normally exceeds the 99-999 tier.
2. Preserve the supplied subject, core action, and visual identity.
3. Keep the price-derived duration, one-shot structure, aspect ratio, silence, and background delivery rule.
4. Continue without waiting for confirmation.

Suggested warning:

`该主体或动效通常高于99–999抖币礼物的常规价效表达；以下保留原始设计，并按本档单镜头、时长、静音与背景规格生成。`

## Single-image default

When this skill is explicitly invoked with one image and no usable text input, assume 499 coins, 4 seconds, 1:1, one continuous shot, the default exact `#00FF00` full-frame background, no audio, and Ref2VA. Treat the image as subject/style guidance rather than an exact first or last frame unless the user says otherwise.
