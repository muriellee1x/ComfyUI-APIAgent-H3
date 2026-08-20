# APIAgent Skills

This directory contains five API-only Skills bundled with ComfyUI-APIAgent-H3.

## Gift Skills

- `h3-low-coin-gift-director`: single-play H3 gifts priced from 99 through 999 coins.
- `h3-live-gift-director`: H3 gifts priced from 1000 through 3000 coins.

Each gift Skill uses the same progressive-disclosure layout:

```text
SKILL.md
giftmaster.json
registry.json
rules/
references/
```

`SKILL.md` defines the execution workflow. `rules/` contains deterministic price, H3-mode, and emotion contracts. `registry.json` describes selectable sections in `references/`. `evaluation-cases.md` remains inside `references/` for regression testing but is marked evaluation-only and is never injected into production requests.

The executor always loads the applicable price rule, the base H3 guide, the Ref2VA guide when needed, and the selected emotion section. It then makes one multimodal registry-routing request and loads only the selected optional sections. Invalid routing output is reported as an error and never falls back to loading every reference.

## General H3 Skill

- `h3-prompt-writing`: generic T2VA, I2VA, FL2VA, L2VA, and Ref2VA prompt formatting outside the live-gift price workflow.

## Image Prompt Skills

- `image-low-coin-gift-prompt-director`: bilingual W+ image prompts for gifts priced from 99 through 999 coins.
- `image-live-gift-prompt-director`: bilingual W+ image prompts for gifts priced from 1000 through 3000 coins.

The image Skills deterministically load price, color, prompt-pattern, emotion, and prompt-audit rules. One multimodal registry-routing request selects only the necessary visual-style and wardrobe sections. Reference images are soft references and are analyzed before one Chinese prompt and its faithful English translation are produced.
