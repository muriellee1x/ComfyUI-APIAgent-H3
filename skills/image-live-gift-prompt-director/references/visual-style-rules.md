# Visual Style Rules

Use this reference whenever a live-gift workflow analyzes or writes a `风格`, `visual style`, `整体风格`, or style-like field.

## Definition

In this skill suite, `风格` means cultural, regional, period, genre, art-movement, or aesthetic direction. It does not mean rendering medium, image quality, camera method, or texture finish.

Valid style categories:

- Cultural or regional style: `中式`, `日式`, `欧式`, `波斯风`, `北欧风`, `东南亚风`, `国风`.
- Period style: `古代`, `复古`, `维多利亚时代`, `80 年代`, `未来主义`, `近未来`.
- Genre style: `赛博朋克`, `蒸汽朋克`, `奇幻`, `科幻`, `暗黑童话`, `极简主义`, `超现实主义`.
- Art movement or aesthetic direction: `巴洛克`, `洛可可`, `包豪斯`, `浮世绘`, `水墨`, `Art Deco`.

Not style:

- Rendering or medium terms: `摄影`, `摄影风格`, `3D写实渲染`, `高端轻写实3D`, `油画`, `插画`, `CG感`.
- Quality or production-value terms: `高清`, `高质量`, `电影感`, `高级质感`, `超细节`, `大师级`.
- Generic mood-only terms: `唯美`, `梦幻风格`, `氛围感`.

## Output Discipline

- If an analysis needs to keep rendering or medium information, write it under a separate field such as `质感/渲染` or `媒介/渲染`, not under `风格`.
- In prompt text, use style terms to guide subject identity, architecture, wardrobe, decoration, and environment language. Use rendering or material terms only when they clarify surface, lighting, or production finish.
- Do not write `风格：高端轻写实3D`, `风格：摄影风格`, `风格：油画`, or `风格：插画`.
- When a user asks for a rendering medium explicitly, preserve it as rendering direction while still choosing or inferring a valid theme style when a `风格` field is required.

## Examples

- Theme: `赛博城市里的机械礼盒`
  - Correct: `风格：近未来赛博朋克`
  - Correct: `质感/渲染：金属与玻璃的写实 3D 渲染`
  - Wrong: `风格：3D写实渲染`

- Theme: `唐代宫灯街，花神祝福`
  - Correct: `风格：唐代中式国风`
  - Correct: `质感/渲染：细腻插画感或轻写实 3D`
  - Wrong: `风格：插画`

- Theme: `复古舞会香水发布`
  - Correct: `风格：Art Deco 复古宴会审美`
  - Correct: `质感/渲染：玻璃、金属和天鹅绒的高端产品渲染`
  - Wrong: `风格：电影感高级质感`
