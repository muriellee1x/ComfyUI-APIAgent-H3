# Prompt Logic Audit

Use this reference before outputting any live-gift prompt. This is a mandatory gate, not optional background reading: first pass the scene/entity/physics/color-richness logic audit and repair conflicts, then run Krea2 prompt optimization, then output. Krea2 optimization must never run before the logic audit passes. The audit is silent: do not output hidden plans, checklists, chain-of-thought, repair notes, or Krea2 optimization notes. The only visible planning-like content allowed is the fixed structured image analysis required for reference-image mode.

## Ambiguity And Physical Logic Check

Before output, check whether any phrase could create extra unintended subjects, unsupported floating objects, impossible contact, unclear waterline, or unclear spatial relationships. Rewrite only the ambiguous clauses. Do not require every body part, clothing detail, object component, light target, or shadow target to repeat the subject name when the sentence is already clear.

## Hidden Structured Scene Planning

Before writing a natural-language W+ draft, silently complete a structured plan:

- User constraints: subject, count, action, location, requested colors, text, exclusions, and reference scope.
- Route: single character, two character, multi character, environment, animal, divine creature, prop, vehicle, gift, object, full-body, face-focus, or multishot isolated asset.
- Subject list: each subject's type, count, identity, position, action, pose, visible state, and relation to other subjects.
- Position and action: where each subject is, what it is doing, and why that action is possible there.
- Body or object state: standing, sitting, swimming, lying, leaning, flying, driving, held, worn, opened, floating, burning, glowing, wet, dry, broken, transparent, soft, hard, reflective, etc.
- Clothing state: compatibility with climate, action, water/snow/formal/social context, and visible crop.
- Visible range: full body, seven-eighths, half body, close-up, underwater/water-surface occlusion, table/car/window occlusion, object-only view, or isolated black-background full display.
- Support/contact: feet, wheels, hands, table, water surface, straps, hooks, magic, engine, wings, railing, seat, tray, plinth, platform, or other support.
- Prop relationship: who holds, wears, uses, stands near, places, opens, supports, or is separated from each prop.
- Material state: wet, dry, reflective, transparent, glowing, burning, floating, broken, melting, soft, hard, fabric, metal, glass, water, fire, paper.
- Scene color richness: for non-black-background scenes, dominant color, analogous supporting color, concrete accent-color carriers, material neutral, and shadow/depth color.
- Light source: time, direction, color, lit surfaces, shadows, reflections, and whether light behavior matches the environment.
- Forbidden contradictions: extra subjects, unsupported floating, contradictory materials, invisible lower-body details, ambiguous part phrases that could create unintended subjects, or user-forbidden content.

Planning priority is: user explicit intent > scene physical and social logic > W+ detail density > Krea2 parseability polish. If a W+ detail violates the hidden plan, delete or replace that detail before optimization.

## Universal Detail Logic Audit

Before outputting any prompt, silently audit it as an entity-relationship-physics draft rather than decorative text. Every important detail must answer four questions: where it belongs, where it is, what it does, and why it is needed for the user's theme.

Use this audit for all routes: character scenes, animal scenes, divine creatures, objects, vehicles, gifts, pure environments, reference-image transfers, and multishot isolated assets.

1. Intent audit: preserve the user's subject type, count, theme direction, requested colors, style, action, mood, exclusions, and reference scope. Do not add a new element that changes the story focus.
   - Style audit: if a visible `风格` or `visual style` field is written, ensure it names cultural, regional, period, genre, art-movement, or aesthetic direction. Move photography, 3D render, oil painting, illustration, CG feeling, and high-end semi-realistic 3D into a separate `质感/渲染` field or delete them if unnecessary.
2. Entity audit: identify primary subjects, secondary subjects, body parts, clothing, accessories, equipment, props, environment pieces, light sources, shadows, and effects. Remove entities that do not support the theme, subject relationship, function, or spatial depth.
3. Relationship audit: every important entity needs enough position, interaction, contact/support, or light/shadow context to avoid misreading. Rewrite only clauses that could create extra subjects, unsupported structures, or unclear spatial relationships.
4. Physics audit: check gravity, support, contact, wearable structure, body mechanics, material behavior, scale, light direction, and shadow placement. Floating, hanging, burning, glowing, racing, flying, sitting, being worn, or being held must have a plausible cause or support.
5. Multi-subject audit: when there are multiple people, animals, creatures, vehicles, products, or objects, give each important subject a distinct position, visible appearance, action, temperament or function, and relationship to at least one other subject or scene anchor.
6. Theme-focus audit: make props and background support the core subject relationship. If the user asks for interaction, make the main subjects interact with each other; do not let standalone props replace the requested relationship.
7. Scene color richness audit: for every non-black-background scene, check that the palette is not only one hue family. Keep one dominant mood color, then add at least one analogous supporting color, one small complementary or warm/cool accent tied to a concrete visible carrier, one material neutral, and one shadow/depth color when the scene has enough visible space. For night, underwater, deep forest, cosmic, cave, or other dark scenes, repair all-blue/all-purple/all-cyan drafts by adding concrete local color carriers such as green leaves or reeds, purple or pink-white flowers, ivory stone, warm gold insects or lanterns, red fabric details, pearl, shell, coral, or silver mist when consistent with the theme. Do not add color carriers that change the requested subject or story focus.
8. Conflict audit: remove contradictions in count, placement, time, indoor/outdoor state, dry/wet state, light source, action, material, style, color carrier, or wearable/object construction.
9. Model-risk audit: delete or rewrite details likely to generate extra unintended subjects, such as isolated body parts, ambiguous groups, unexplained silhouettes, scattered faces/eyes/hands, or unnecessary negative prompts.

## Common Compatibility Checks

- Water / soaking / swimming: visible skin and water-compatible clothing; waterline covers submerged areas; wet hair/skin/clothing only where plausible; do not write shoes, daily coats, leather footwear, long trousers, or full lower styling when hidden by water.
- Water platforms / pavilions / bridges: first decide the support type before writing the scene: shore-connected bridge, pile-supported platform, floating platform, rock island, or explicit magic support. Make the waterline clear. Hard platform tops and bridge surfaces should stay above the water unless the concept is a deliberate underwater ruin. Avoid decorative phrases such as shallow-water steps, transparent water covering floor tiles, or ring steps in the pond center unless the support and water level are physically clear.
- Poolside / beach deck / lounge: dry vacation clothing can be reasonable; do not move the person into water unless requested; support comes from deck, chair, towel, railing, or ground.
- Snow / cold / ice: add warm fabric, boots or covered feet when visible, cold-weather support and footprints/shadows; avoid thin summer clothing or bare feet unless explicitly requested as surreal.
- Formal / banquet / theater / ceremony: clothing should match social setting and action; sportswear, swimwear, or armor need explicit user cause.
- Vehicle / racing / road: wheels, rails, hull, wings, engine, water, road, sky, or space determine support. Name wheel-road contact, rail contact, buoyancy, flight mechanism, or engine/wing support.
- Flying / floating / hanging: state wings, wind, magic, suspension, string, hook, engine, cloud, water buoyancy, or platform; otherwise remove floating language.
- Table / display / gift / treasure box: state support surface; opened or half-opened boxes need lid, lining, contents, material zones, and shadows that match the support.
- Fire / glow / transparency: name the source, material boundary, nearby surfaces receiving light, and why the material can burn/glow/reflect/appear transparent.
- Half-body / close-up / underwater crop: write visible upper-body, face, hands, surface, props, and light; omit hidden shoes, full pants, complete skirts, lower vehicle parts, or blocked object interiors.

## Krea2 Prompt Optimization

After the hidden scene plan is complete and the Chinese W+ route draft already passes the scene-logic constraints, silently optimize the draft for Krea2-style text-to-image parsing. Treat this as a rewrite pass over the existing W+ draft, not as a second concept-generation pass.

1. Preserve faithfulness first: keep every original subject, action, requested color, color-carrier distribution, reference scope, count, and spatial relationship from the user request and W+ draft. Do not add new people, animals, props, vehicles, objects, text, labels, or background features during this step.
2. Keep `w+style`, `w+girl`, and `w+boy` because they are required W+ trigger words.
3. Plan internally only: decide the subject, mood, visual direction, color palette, lighting, framing, and grounded details, but do not output planning tags, thinking steps, alternatives, wrappers, or explanations.
4. Improve parseability: group each subject with its own attributes and action, keep interactions and spatial layout grounded, and rewrite ambiguous clauses so the model can tell where each detail belongs and where each object sits.
5. Respect existing detail. If the W+ draft is already detailed and coherent, lightly polish word order, grouping, and clarity instead of expanding it heavily.
6. Avoid over-specification in this optimization pass. Do not invent extra-specific clothing, colors, materials, props, or ornaments that were not already required by the W+ draft or the user request.
7. If visible text, labels, signs, book titles, plaques, typography, or written words are requested, specify the exact text and wrap the requested words in quotation marks in both Chinese and English prompts.
8. Respect the human form: describe people with dignity, keep clothing coverage ordinary and non-exploitative, and do not focus on intimate anatomy.
9. The optimized Chinese prompt remains one cohesive paragraph. The English prompt is a faithful translation of that optimized Chinese prompt, not an independently optimized variant.
