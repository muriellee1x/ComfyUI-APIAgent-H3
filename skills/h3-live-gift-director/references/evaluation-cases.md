# Evaluation cases

Use these cases for initial and regression testing. Judge routing, price reasoning, continuity, timing, and H3 validity rather than prose style.

| Case | Input | Expected behavior |
| --- | --- | --- |
| 1 | One ordinary animal image, no text | infer about 2000 coins, 5s, 1:1, one or two shots, Ref2VA by default, audio N/A |
| 2 | One polished character cover plus gift name | default to Ref2VA, preserve identity, infer a compact story and dynamic cover, and do not treat visual polish as an implicit tail-frame request |
| 3 | One image and “start exactly from this frame” | route to I2VA and preserve the 0.00-second anchor |
| 4 | One image explicitly called an intermediate keyframe | route to Ref2VA, reach it briefly, continue moving afterward |
| 5 | Two images explicitly assigned first and last | route to FL2VA with correct endpoint alignment |
| 6 | Two images separately defining character and environment | route to Ref2VA with stable Subject labels, not FL2VA |
| 7 | 2000-coin request with adult dragon or cosmic palace | warn once in Chinese, preserve content, continue without downgrade or confirmation |
| 8 | Four-second one-take compact object gift | use only Shot 1, one hook and one climax, no hidden actual cut |
| 9 | Six-second two-shot vehicle chase | preserve unique front, route, speed, wheel direction, full-occlusion continuity, dynamic ending |
| 10 | Six-second three-shot request overloaded with events | preserve explicit priorities, compress inferred decoration, keep readable phases and timing |
| 11 | Character playing guitar | specify correct fretting and strumming, string vibration and decay, stable hands and instrument |
| 12 | “No sound effects” with no music request | set both audio fields to N/A |
| 13 | Only an image containing a large gold palace | infer story from the image, warn if price-effect conflict is clear, do not remove the palace |
| 14 | One-shot POV with a hand-covered viewpoint change | keep Shot 1 only and describe continuous occluded perspective conversion rather than a cut |
| 15 | Explicit price of 999 or 3001 coins | report that the skill covers only 1000-3000 and do not apply this tier's calibration |
| 16 | Five-second two-shot flower-street character cover | confidently invent a compatible shop-interior, bouquet preparation, bicycle arrival, or other off-frame premise for Shot 1; Shot 2 cuts to the exterior street cover; no mandatory magic trail or pavement light ring |
| 17 | Five-second two-shot aurora couple cover | Shot 1 may use a close tent, cabin window, sled arrival, or snowy forest approach; Shot 2 cuts to a wide rear aurora landscape; do not invent a crystal guide or cyan trail |
| 18 | Six-second two-shot island with sailboat and Ferris wheel | Shot 1 may track underwater beneath the boat, follow the deck approach, or show a shoreline arrival; Shot 2 cuts to a substantially different aerial island view; do not connect the boat to the wheel with a beam, wake, or activation ripple unless requested |
| 19 | Two-shot balloon train gift | preserve the successful contrast: single balloon and moving train first, then a clear cut to opened doors and a wide platform filled with balloons; effects remain optional |
| 20 | Ordinary realistic reference with no supernatural request | output may contain no magical effects; use material, wind, water, mechanics, and camera staging for value |
| 21 | Single image explicitly assigned as a tail frame plus two-shot request | use L2VA, invent a coherent Shot 1 outside the visible frame, and let Shot 2 recover the reference through a seamless bridge rather than a nearby hard cut |
| 22 | Five-second two-shot car in a wheat field | use a low wheel-height moving detail for Shot 1; let physically bent wheat cover every edge; emerge into a high wide rear three-quarter field reveal; preserve car direction and wheat motion but reset camera height, scale and axis |
| 23 | Five-second two-shot yacht final cover explicitly requested as the ending | use L2VA with an interior cockpit or throttle macro for Shot 1; let a bow-wave splash fully cover the windshield; emerge into an exterior ultra-low water-level wide; preserve yacht identity and travel direction without preserving the interior camera path |
| 24 | Two-shot seamless transition request with no plausible occluder | design clearly different shots first, then use a motivated match cut or clean editorial cut; do not invent magic particles, a guidance object, or an arbitrary screen wipe |
| 25 | Five-second quiet moonlit woman cover with two shots | preserve contemplative pacing; use an intimate object, hand, lantern, reflection, or exterior establishing premise, then cut to the woman already safely seated in the reference pose; do not compress stand, walk, turn, sit and pose into the final shot |
| 26 | Five-second flower-cottage couple with woman on a window sill | do not make her open the window and immediately climb or drop into the final pose; use a compatible prelude or editorial time jump, begin the later shot with her stably seated, and let one or two existing cats perform natural secondary actions |
| 27 | Instrument performer with an explicitly requested hand close-up | lock the first 0.6-0.8 seconds to fingers, strings, bridge and cuff; explicitly keep face and full body outside frame; show contact, vibration and release before widening |
| 28 | Six-second three-shot princess staircase gift | assign three distinct jobs and scales, such as dress or foot detail, overhead staircase geometry, then low wide hero cover; do not render three similar medium views |
| 29 | Quiet two-shot cover with little plot | use shot contrast to reveal new information or space, not to force extra body movement; let wind, foliage, water, animals or practical lights carry restrained secondary motion |
| 30 | Seamless cut across a complex posture change | permit an editorial time jump under a motivated bridge; preserve identity and story geography, but begin the incoming shot in the completed stable pose rather than matching an unsafe or unreadable limb phase |
| 31 | Five-second two-shot quiet character cover with a hand detail | lock the hand detail for about 0.6-0.8 seconds, then use a seamless bridge into a medium-to-large camera reveal; do not spend two seconds in macro framing or reduce the main camera to a small slow push |
| 32 | Five-second two-shot where foreground foliage is available | let real defocused foliage cover the view and emerge at a new scale and axis; do not write a literal hard-cut phrase or reuse an arbitrary sleeve wipe |
| 33 | Six-second three-shot gift with two transitions | choose two different transition families, such as action match followed by traversal or depth cover; do not repeat full-frame entity occlusion twice |
| 34 | Dense three-shot character gift | assign hook/preparation, spatial advance/state change, and climax/cover; keep one primary action chain plus one environmental response per shot and remove Level 3 decoration first |
| 35 | Tail-frame prompt requiring a bright reference cover | describe stable exposure, full color, and continuing motion through the last frame; do not include a negative-prompt tail or name fade, black-frame, white-frame, identity-drift, extra-finger, or deformation failure tokens |
| 36 | One polished fantasy image with no endpoint wording | route to Ref2VA, define reusable subjects and environment, let the climax pass through or reinterpret the composition, and continue camera and environmental motion afterward |
| 37 | Default single-image Ref2VA output | use all six full-reference fields in order, begin summary with `[reference generation]`, define reusable image content as Subjects citing Picture 1 inside definitions, and omit any last-frame alignment instruction |

## Acceptance checklist

- Correct H3 mode and reference role.
- A single image defaults to Ref2VA; L2VA requires explicit last-frame, tail-frame, exact-ending, or final-convergence intent.
- Ref2VA follows the six-section H3 format with consistent Subject labels and no base-mode endpoint-alignment line.
- No invented high-value imagery unless supplied explicitly or present in the image.
- No quality downgrade at lower price.
- Hook is visible early and the climax is identifiable.
- Emotional temperature and subject-action density match the reference; quiet subjects may still receive one confident medium-to-large camera reveal.
- Shot count and duration match the request.
- Every shot has a distinct camera job; any promised functional close-up explicitly locks included and excluded content for a readable interval.
- Explicit multi-shot requests contain visible editorial changes in framing and information while remaining perceptually seamless by default.
- A literal hard cut appears only when explicitly requested or when no coherent transition family is available.
- Transition family is selected from entity occlusion, action match, shape match, direction match, depth-of-field cover, traversal, or sourced natural material; three-shot videos avoid repeating one family at consecutive boundaries.
- Occlusion is used only when it supports a genuine viewpoint or spatial jump.
- For seamless multi-shot transitions, the incoming viewpoint is declared immediately, full coverage is physically caused, and only necessary action or material continuity survives the camera reset.
- The frame before coverage and the frame after clearing are visibly different in scale, axis, space, or information.
- Every invented effect passes a clear source-purpose-necessity test; zero effects is valid.
- No unjustified guiding object or activation beam is introduced.
- Subject count, identity, structure, and action phase remain stable.
- Complex posture changes are either shown with enough time and physical clarity or bridged through a deliberate editorial time jump.
- Each shot contains at most one primary action chain and one environmental response; Level 3 reference details yield before Level 1 or Level 2 anchors.
- One or two existing environmental actors provide causal secondary motion when useful; decorative effects are not used as a substitute.
- Audio defaults to N/A.
- No `--wm false`.
- Final composition remains at stable exposure and full color with natural motion through the last frame.
- Generated H3 text contains positive mechanics rather than a negative-prompt tail or named failure artifacts.
