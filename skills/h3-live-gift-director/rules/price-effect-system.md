# Price-effect system: 1000-3000 Douyin coins

## Scope boundary

This system calibrates only explicitly priced gifts from 1000 through 3000 coins, inclusive. If the requested price is outside that interval, report the scope mismatch and stop. This boundary is different from an in-range price paired with unusually expensive imagery: the latter uses the explicit-content exception below and still receives a prompt.

## Core principle

Price changes content capacity, not production quality. Every gift in this range requires polished camera motion, natural transitions, stable identity and structure, physical causality, readable staging, and a dynamic ending.

## Default tiers

| Price | Typical duration | Typical shots | Content capacity |
| --- | --- | --- | --- |
| 1000-1499 | 4 seconds | one continuous shot preferred; two when necessary | one principal subject, one causal event, one climax, compact environment |
| 1500-2199 | 5 seconds | one or two | clear setup-change-result progression, moderate environment response |
| 2200-3000 | 5-6 seconds | two preferred; three used rarely | two-stage progression, richer spatial reveal, several coordinated environment responses |

These are defaults, not rigid limits. Obey explicit user duration and shot count when coherent.

## Normal content ceiling

When inventing missing content, do not introduce:

- adult dragons, phoenixes, or similarly prestigious complete divine beasts;
- giant adult lions, tigers, elephants, or equivalent symbols of dominance and prestige;
- outer space, cosmic civilizations, planets, or interstellar settings;
- extremely vast royal cities, divine palaces, civilization-scale monuments, or world-scale miracles;
- extensive solid gold, diamond, gemstone, or jewel-encrusted material systems;
- full-frame energy floods, prolonged explosive particle storms, or excessively dazzling effects;
- more than three shots or stories that visibly exceed six seconds of action capacity.

Ordinary animals, juveniles, small fantasy creatures, lantern versions, silhouettes, patterns, local ruins, gardens, streets, parks, valleys, interiors, and restrained metallic or crystalline accents are normally suitable.

## Explicit-content exception

The ceiling restricts only content inferred by the skill. If the reference image or user explicitly includes higher-value imagery:

1. Preserve it faithfully.
2. Do not downgrade, replace, shrink, or remove it.
3. Give one short Chinese warning before the H3 prompt, for example: `该主体或场景通常高于1000–3000抖礼物的常规价效表达；以下仍按原始设计生成。`
4. Continue without asking for confirmation.

## What higher price buys inside this range

Increase only the appropriate dimensions:

- duration and visible action capacity;
- number of meaningful story phases;
- subject or object expression complexity;
- environment scale within the range;
- number of coordinated environmental responses;
- effect layering and duration without obscuring the subject;
- time available for the climax and dynamic cover.

Never describe lower-priced gifts as accepting rough camera motion, weak composition, hard transitions, unstable structure, or poor animation.

## Single-image default

With one image and no usable text input, assume:

- about 2000 coins;
- 5 seconds;
- 1:1;
- one continuous shot or two shots based on visual affordances;
- one primary story archetype;
- one restrained in-world transition or continuous camera climax;
- roughly 0.6-0.8 seconds of dynamic cover presentation in a five-second multi-shot gift;
- no soundscape and no music.

Use Ref2VA as the single-image default. Use L2VA only when the user explicitly assigns the image to the final frame or exact ending.
