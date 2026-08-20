# W+ Prompt Patterns

Use this file to choose the dataset writing pattern and subject-writing pattern for a route. Use `wplus-prompt-rules.md` for output format and fixed W+ starts, `wardrobe-style-rules.md` for visible human clothing, `color-style-rules.md` for palette and environment composition, and `prompt-logic-audit.md` as the mandatory logic gate before Krea2 prompt polishing and output.

## High-Price Person-Framing Override

This section overrides every later full-body-sheet, A-pose, long-shot, wide-shot, background-figure, and multishot person pattern for the `image-live-gift-prompt-director` profile.

- When any person is visible, use a bust, chest-up, half-body, waist-up, thigh-up, knee-up, or calf-up close framing. Calf-up is the widest allowed crop.
- Keep feet completely out of frame. Never produce a head-to-toe or full-body view.
- Every visible person must occupy the main image area. Do not make people small, distant, or subordinate background figures in a broad environment.
- If the user or a reference image requests a full-body sheet, preserve identity, styling, and wardrobe design, but adapt the composition to calf-up or closer.
- Never select the `full-body sheet` route for people in this profile and never use A-pose.
- In both languages, state the allowed close crop, person prominence, and that feet remain out of frame.

## Route To Dataset Mapping

| Prompt route | Dataset folder pattern | Prompt start | Environment required | `w+girl` / `w+boy` use | Multishot behavior |
| --- | --- | --- | --- | --- | --- |
| `environment` | `01_scene` | `w+style，环境为...` | Yes | No, unless a visible human is explicitly part of the chosen route | Use as `场景`; do not include separated people, animals, divine creatures, or key props. Multishot scenes may keep scene-native crowd/background figures when the environment requires them |
| `animal` | `01_scene_animal` | `w+style，环境为...` for ordinary prompts; `w+style，动物全身图...` for isolated assets | Ordinary prompt: yes. Multishot isolated asset: no | No | If the animal is a main asset, split into one black-background `动物` prompt per animal |
| `divine creature` | `02_scene_divine` | `w+style，环境为...` for ordinary prompts; `w+style，神兽全身图...` for isolated assets | Ordinary prompt: yes. Multishot isolated asset: no | No | If the divine creature is a main asset, split into one black-background `神兽` prompt per creature |
| `prop/object/gift/vehicle` | `02_scene_prop` | `w+style，环境为...` for ordinary prompts; `w+style，道具完整展示...` for isolated props | Ordinary prompt: yes. Multishot isolated key prop: no | No | Split only key props that need independent design; ordinary scene props stay inside scene prompts |
| `single character` | `01_scene_girl` or `01_scene_boy` | `w+style，环境为...` with embedded `w+girl` or `w+boy` in the identity phrase | Yes | Yes, embedded once in the visible character phrase | Usually split into black-background `人物` asset plus separate scene when multishot requires separated assets |
| `two characters` | `01_scene_both`, or paired `01_scene_girl` / `01_scene_boy` logic | `w+style，环境为...` with each visible character trigger embedded once | Yes | Yes, one trigger per visible person | Split into `人物 1`, `人物 2`, etc.; do not output a combined two-person asset |
| `multi-character` | `01_scene_multi` | `w+style，环境为...` with visible character triggers only for people that require W+ identity triggers | Yes | Yes for visible human characters; keep count exact | Multishot splits main people into separate `人物` assets. Scene-native crowd/background figures can stay in `场景` only when they remain environmental and do not require W+ identity triggers |
| `full-body sheet` | `02_girl_fullbody` or `02_boy_fullbody` | `w+girl，人物全身图...` or `w+boy，人物全身图...` | No | Fixed prefix only | Used for every main person asset; one person per prompt, fixed A-pose |
| `face focus` | `03_girl_closeup` or `03_boy_closeup` | `w+girl，人物大头肖像...` or `w+boy，人物大头肖像...` | No | Fixed prefix only | Not used for default multishot assets unless explicitly requested |
| `multishot isolated assets` | Adapted from full-body, animal, divine, and prop patterns | `人物全身图`, `动物全身图`, `神兽全身图`, or `道具完整展示` starts | No | Only person assets use `w+girl` / `w+boy` | Always split by asset group and main subject; black background only |

## Shared W+ Grammar

- Write one cohesive paragraph per prompt block.
- Preserve required triggers exactly: `w+style`, `w+girl`, and `w+boy`.
- Scene and expanded subject prompts normally begin with `w+style，环境为...`.
- Full-body sheets begin with `w+girl，人物全身图，...` or `w+boy，人物全身图，...`. English full-body sheet prompts begin with `w+girl, 人物全身图, ` or `w+boy, 人物全身图, `.
- Face-focus portraits begin with `w+girl，人物大头肖像，...` or `w+boy，人物大头肖像，...`. English face-focus prompts also begin with `w+girl，人物大头肖像，` or `w+boy，人物大头肖像，`.
- In scene prompts, place `w+girl` or `w+boy` inside natural visible character phrases, such as `一位金发花冠精灵少女w+girl`; do not start scenes with disconnected trigger tags.
- Keep dataset-like density with concrete nouns, material, structure, visible state, light behavior, and composition.
- Write tangible design information, not only atmosphere. Every dominant subject needs readable structure, material, state, action or pose, and relationship to the scene or asset frame.
- Avoid empty quality filler such as `高清`, `高质量`, `电影感`, `高级质感`, `梦幻风格`, `唯美`, `超细节`, `大师级`, and `CG感`.

## Character Routes

### Single And Two-Character Scenes

Use this order:

1. Specific environment and palette.
2. Character identity with embedded `w+girl` or `w+boy`.
3. Meaningful action, posture, gaze, physical state, or relationship.
4. Visible hair, expression, clothing silhouette, construction, materials, placed decoration, accessories, and footwear or visibility limit.
5. Props and surroundings with material, shape, placement, and interaction.
6. Visible light source direction and affected surfaces.
7. Camera angle, composition, foreground framing, or background depth.

Keep every generated character's face directly visible unless the user explicitly asks otherwise. Do not use pure back view or mirror workarounds.

Default visible female and male characters to adults unless the user explicitly specifies a child or minor. Use natural and restrained makeup by default. Do not add blush, facial flush, heavy eye makeup, exaggerated eyeliner, dense eyelashes, or vivid glowing irises unless the user asks or the role needs it.

### Multi-Character Scenes

Use `multi-character` only for three or more people. One person is `single character`; two people are `two characters`. Define the group activity first, then assign foreground, middle-ground, background, left/right, or role anchors. Give the main foreground person or pair full density, and describe secondary people with enough clothing, action, and placement to make the group readable. Every important visible subject needs position, appearance, action, temperament or function, and relationship to another subject or scene anchor. Do not compress people into vague phrases such as `多人服饰统一` or `一群人互动`. Avoid mere color swaps and avoid applying the same descriptive formula to every subject unless the user requests uniformity.

### Full-Body Sheets

Full-body captions are character design sheets, not scenes. Use this order:

1. Hair and visible head details.
2. Main garment silhouette.
3. Complete upper-body and lower-body garments.
4. Fabric, construction, and placed decoration.
5. Accessories, gloves, armor, wings, cape, or veil where relevant.
6. Exact shoes or a visibility limit.
7. Standard standing pose or fixed multishot A-pose.
8. Fixed black-background tail. English full-body sheet prompts must end with `画面为纯黑色背景，严格纯黑色背景，轻微逆光，金色轮廓光。`.

For multishot `人物` assets, always use the fixed pose `双臂向两侧展开，做出标准的A-pose`.

### Face Focus

Close-ups are face-led portraits with visible clothing partials. Use this order:

1. Forward-facing crop and gaze.
2. Eyes, eyebrows, expression, and visible makeup when appropriate.
3. Hair color, hair length or volume, bangs, and hairstyle structure.
4. Headwear, earrings, necklaces, or facial accessories.
5. Visible neckline, collar, shoulder edge, fabric, or decoration.
6. Fixed black-background tail. English face-focus prompts begin with `w+girl，人物大头肖像，` or `w+boy，人物大头肖像，` and must end with `画面为纯黑色背景，严格纯黑色背景，轻微逆光，金色轮廓光。`.

Do not invent clothing outside the crop. Omit blush and facial flush by default unless the user asks for that visible effect.

## Expanded Subject Routes

### Environment / Architecture

Make one structure, landscape feature, light installation, building, tree, bridge, fountain, castle, city, garden element, or habitat the dominant subject. Name a concrete style for human-made spaces and at least two visible style carriers such as roof, arch, column, window, tile, railing, furniture, lantern, mural, paving, fabric, platform, or planting layout. For natural spaces, name habitat type, terrain, plants or geology, weather/time cue, and background depth.

### Animal

Make species, size, body covering, color pattern, face or eye direction, and action readable. Describe body mechanics or display state such as sitting, standing, leaping, flying, climbing, lying down, trotting, raising a paw, turning the head, stretching the neck, spreading wings, or complete isolated display.

Cats are cute-first by default unless the user requests a non-cute temperament. Use `身体圆润可爱，头大四肢短小，非常可爱`, but do not default to large round eyes unless requested. Dogs use cute 3D-character proportions by default unless the user requests non-cute temperament: round oversized eyes, large head, rounded body, short small limbs, soft plush-like volume, and adorable expression or action.

For non-cat and non-dog animals, use cute 3D proportions only when the user asks for cub, baby, cute, Q, cartoon, round, healing, or soft style. Suppress cute proportions when the user asks for majestic, fierce, heroic, realistic, strong, battle-ready, or cold temperament. If the animal wears styling, name exact items and placement: collar, bell, hat, scarf, saddle, bridle, blanket, chain, flower crown, bow, goggles, or harness.

Attach animal parts and light targets to the animal when ambiguity is possible, such as `小猫的前爪踩在窗台上`, `阳光照亮小羊的犄角和背部绒毛`, `小狗脖颈上的项圈铃铛`, or `奶牛猫的尾巴高高翘起`.

### Divine Creature

Name the creature type and lineage when useful: Chinese dragon, western dragon, phoenix, qilin, nine-tailed fox, unicorn, divine deer, jade elephant, auspicious lion, or spirit cub. Dragon defaults to Chinese dragon unless the user specifies another lineage. Describe anatomy and material: horns, mane, whiskers, scales, feathers, wings, tail, claws, hooves, fur, armor plates, crystal body, jade-like skin, flame hair, water-ribbon mane, or transparent wing membrane. Give the creature a readable spiritual action, stance, or complete isolated display: coiling, diving, soaring, landing, stepping onto a cliff, leaping over water, guarding a lotus platform, facing the viewer, or full-body black-background presentation.

Add ornaments only with placement and material: forehead jewel, chest armor, saddle cloth, tassel, chain, gem, metal ring, ribbon, halo, or glowing pattern. Ordinary divine-creature scenes need an element-matched environment such as cloud sea, moon palace, underwater temple, lava field, bamboo stream, crystal cave, snowy cliff, mountain sanctuary, or battlefield ruin. Multishot isolated divine-creature assets are an exception: use black background and describe only the creature.

Attach divine-creature anatomy and effects to the creature when ambiguity is possible, such as `中国龙背部的白色鳞片`, `火光沿凤凰的羽翼边缘发亮`, `神鹿幼崽额前的发光鹿角`, or `九尾狐身后的九条尾巴`.

### Prop / Vehicle / Object / Gift

Treat the object as a designed product, vehicle, ornament, gift, machine, or stage installation, not a generic prop label. Describe silhouette and components such as cockpit, wing, engine, wheel, grille, rail, hinge, lid, base, handle, tassel, frame, crystal core, platform, decorative plate, lantern body, sail, bottle shape, lock, lining, tray, or display support. Specify materials and surface behavior such as polished metal, velvet, glass, jade, translucent crystal, fabric, paper, wood, candy, cream, bright paint, glitter, carved gold edging, reflective lacquer, brocade, matte ceramic, or soft internal glow.

State physical state and support: flying, racing, floating, hanging, opened, glowing, tilted, displayed on a platform, drifting above water, parked on a bend, suspended by a cord, placed on a plinth, or supported by a tray. Ensure mechanics and placement are plausible: wheels touch road, trains sit on track, boats sit on water, rockets have tail flame, gifts rest on table or platform, and floating objects need fantasy, space, magic, water, or suspension logic.

Attach components to the object when ambiguity is possible, such as `未来赛车的前轮`, `礼盒顶部的红色丝带`, `长笛的玉石管身`, `飞船尾部的发动机光焰`, or `首饰盒内侧的绒面衬布`.

For abstract gift boxes or treasure boxes, default to opened or half-opened unless the user asks for a closed or simple box. Include lid, inner lining, layered structure, visible contents, material zoning, and a clear support surface.

### Shared Expanded Scene Order

Use this order for non-character-dominant scenes:

1. Specific environment and time or atmosphere.
2. Dominant subject and exact placement in the frame.
3. Subject structure, material, markings, decoration, or body features.
4. Visible action or physical state.
5. Foreground, surrounding objects, background depth, or habitat.
6. Light source and what it illuminates.
7. Camera angle and composition.
8. Specific composition mechanism: bind the ending to at least one concrete carrier, such as foreground occlusion, a path or bridge leading line, subject off-center placement, central axis, high or low camera, near-field pressure, or far-scale comparison. Do not end with only a generic viewing angle.

Do not treat non-human subjects as vague scenery. Animals, divine creatures, vehicles, gifts, and ornaments all need a clear visual state and physical relationship with the scene.

Scene prompts must not rely on negative tails. If the route is environment-only or multishot scene asset, avoid generating separated subjects by not describing them.

For multishot scene assets, environment-only does not force an empty venue. If the setting is socially crowd-required, such as a night market, ballroom, street, banquet hall, bazaar, parade, theater, audience area, classroom, or stadium, include small-scale background people as part of the environment layer. Keep them as pedestrians, guests, vendors, musicians, audience silhouettes, students, or small social clusters in the middle ground, background, or frame edges. Do not use `w+girl` or `w+boy` for these background figures, and do not describe any one of them as a named, centered, close-up, large foreground, or main-character-density subject.

## Multishot Pattern Overrides

- Multishot treats `人物`, `动物`, `神兽`, `道具`, and `场景` as separate generation assets.
- Main people use the full-body sheet dataset pattern, one person per prompt, black background, fixed A-pose.
- Main animals use the animal pattern for species, body structure, covering, styling, and complete display, but not the ordinary animal scene background.
- Main divine creatures use the divine creature pattern for anatomy, material, ornaments, and complete display, but not the ordinary divine creature scene background.
- Key props use the prop/object/gift pattern for object structure, components, material zones, physical state, and complete display, but not the ordinary object scene background.
- Scene prompts use environment or expanded scene patterns and must not include separated main people, animals, divine creatures, or key props. Crowd-required scenes may include background people as scene atmosphere when they do not become named, centered, close-up, or asset-level subjects.
- Black-background isolated assets use neutral subject-display lighting only. Do not describe light or reflections as coming from a story environment, time of day, landscape, architecture, water, sky, fire, stage, window, city, or celestial body.
- In multishot, main people, animals, divine creatures, and key props are usually split into separate assets instead of being combined into one prompt. Background crowd stays in `场景`; if any person is named, close-up, central, foreground-large, or described with main-character wardrobe/facial density, upgrade that person into a `人物` asset or an intentional character route instead of treating them as atmosphere.

## Checks Before Output

1. Confirm the route before writing: environment, animal, divine creature, prop/object/gift/vehicle, single character, two characters, multi-character, full-body sheet, face focus, or multishot isolated asset.
2. Confirm the mapped dataset pattern from `Route To Dataset Mapping`.
3. Ensure the prompt start matches the chosen route.
4. For human routes, count visible people exactly and use `w+girl` / `w+boy` only for those people.
5. For non-human routes, do not invent humans unless requested.
6. For ordinary animal, divine creature, prop, vehicle, object, and environment routes, include a complete environment and visible light behavior.
7. For multishot isolated assets, remove environment, scene light, external reflections, and unrelated props.
8. Attach body parts, clothing details, ornaments, wearable items, object components, contact points, action carriers, light targets, and shadow targets to a named subject when ambiguity could create extra unintended subjects.
9. Check physical support: feet, wheels, rails, hull, wings, table, platform, water, magic, suspension, or other support must make the state plausible.
10. For multishot scenes, check time and season continuity before output. Different scenes may use different time-of-day or lighting states only when they serve the story, but season, climate, plant state, clothing-weather logic, and weather cues must remain consistent unless the user explicitly asks for seasonal change.
11. End scene prompts with a named camera angle plus a concrete composition mechanism, such as foreground occlusion, leading line, off-center subject, central axis, high or low camera, near-field pressure, or far-scale comparison.



