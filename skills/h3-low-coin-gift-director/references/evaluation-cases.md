# Evaluation cases

Use these cases for regression and forward testing. Judge routing, hard production rules, motion capacity, background stability, and H3 validity rather than prose style.

| Case | Input | Expected behavior |
| --- | --- | --- |
| 1 | Explicit price 98 | report out of scope and stop |
| 2 | Explicit price 99 | use 3 seconds, one shot, silent audio, solid background |
| 3 | Explicit price 299 | remain in the 3-second solid-background tier |
| 4 | Explicit price 300 | use 4 seconds and remain on a solid background |
| 5 | Explicit price 499 | use 4 seconds and require a solid background |
| 6 | Explicit price 500 with a supplied compact scene and no color input | use 4 seconds and preserve the compact scene |
| 7 | Explicit price 999 with `#112233` | use 4 seconds, one shot, and replace the setting with the exact unchanged solid field |
| 8 | Explicit price 1000 | route to `h3-live-gift-director` and stop |
| 9 | Explicit low-tier invocation with one image and no price | default to 499 coins, 4 seconds, 1:1, one shot, silent Ref2VA |
| 10 | Generic unpriced live-gift request without explicit low-tier intent | do not implicitly take over from the existing gift skill |
| 11 | One ordinary image with a solid blue background | preserve that exact visible field throughout; do not replace it with a named default color |
| 12 | 199-coin subject image with a scene background | preserve the subject but replace the scene with a uniform solid field |
| 13 | T2VA below 500 with no color supplied to the executor | use the injected default `#00FF00` exactly |
| 14 | 700-coin subject with no background request | use a solid field or compact setting according to subject needs; do not invent a large environment |
| 15 | Kite reference | choose trajectory: enter, trace one readable path, display, exit |
| 16 | Book, gift box, fan, badge, or flower reference | choose state change with explicit A-state, mechanics, B-state, and exit/recovery |
| 17 | Stylized bear holding a rose | choose subject action with one presentation gesture, one subordinate response, and exit |
| 18 | User requests two shots at 399 coins | warn once and stage the important beats as one continuous `[Shot 1]` |
| 19 | User requests 5 seconds at 250 coins | warn once and use 3 seconds |
| 20 | User requests 9:16 at 700 coins | warn once and use 1:1 unless a valid 4:3 layout is supplied |
| 21 | User requests music or sound effects | warn once and set both audio fields to `N/A` |
| 22 | User supplies a dragon or palace below 1000 | warn once, preserve explicit subject, keep duration, one shot, silence, and background rule |
| 23 | Ordinary reference with no effect request | zero added effects is valid |
| 24 | Moving wand or small vehicle with a trail | allow one sourced trajectory system and decay it with the exit |
| 25 | Subject fade-out on a solid background | reduce subject/effect opacity only; keep the background field unchanged |
| 26 | Ref2VA single image | use six fields in order, `[reference generation]`, stable labels, and no endpoint-alignment line |
| 27 | Explicit exact first frame | use I2VA and the required 0.00-second alignment line |
| 28 | Explicit exact last frame | use L2VA and the required final-time alignment line while remaining one shot |
| 29 | Explicit first and last images | use FL2VA and one continuous interpolation path |
| 30 | Two images defining subject and motion style | use Ref2VA, not FL2VA |
| 30a | L2VA last frame still contains the subject | settle into that exact final composition; do not force an exit and reappearance |
| 30b | Reference video contains audio but only supplies visual motion | ignore its audio track and do not define `<Audio N>` |
| 31 | Prompt contains `[Shot 2]` | fail validation |
| 32 | Prompt includes sound in either audio field | fail validation |
| 33 | Sub-500 prompt lacks the injected exact hex value or a stable solid-background statement | fail validation |
| 34 | Prompt appends `--wm false` or a negative-prompt tail | fail or warn according to deterministic validator rules |

## Acceptance checklist

- Price is within 99-999 or is routed out correctly.
- 99-299 uses 3 seconds; 300-999 uses 4 seconds.
- Output contains only `[Shot 1]`.
- The action reads as entrance, one primary display/change/action, then a completed exit or an exact endpoint settle.
- Both audio fields are exactly `N/A`.
- Aspect ratio is 1:1 or 4:3.
- Below 500, the background uses the exact injected hex value and remains one uniform solid field whose hue, luminance, texture, and coverage do not change.
- At 500-999, any background remains compact and subordinate to the subject.
- Trajectory, state-change, or subject-action mechanics remain causal and readable.
- Explicit over-value content is warned about and preserved without relaxing the hard production requirements.
- Correct H3 mode, field order, alignment instruction, reference labels, and timing are used.
- The prompt contains positive desired mechanics and no watermark flag.
