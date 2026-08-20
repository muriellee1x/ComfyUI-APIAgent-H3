# Color And Style Rules

Use these rules for every live-gift prompt route that writes an environment, scene background, character scene, animal scene, divine-creature scene, object scene, or multishot scene asset. These rules guide color, environment/theme style carriers, structure, material hierarchy, light, and composition. Use `scene-composition-rules.md` to choose composition function and concrete framing mechanism before final scene wording. Use `visual-style-rules.md` for the definition of `风格`; rendering media such as photography, 3D render, oil painting, illustration, and high-end semi-realistic 3D are not `风格`. Do not expose hidden palette planning unless the user explicitly asks for color reasoning.

## Palette Planning

Before writing an environment prompt, silently infer the theme mood, time, setting, and visual focus. Choose one coherent palette pattern, then decide the dominant color, supporting color, shadow color, and any small accent color before composing the final prompt.

Recommended palette patterns:

- Warm yellow-green / golden forest: cream yellow, olive green, and fresh leaf green, with a small orange-red accent for a focal character, leaves, birds, or light details.
- Ivory white / green garden: ivory white, beige stone, olive green, and warm gray shadows for classical courtyards, statues, fountains, quiet gardens, and restrained romance.
- Bright yellow-green / clear garden: yellow-green, cyan-green, gray white, and watery blue, with a small pink-orange accent for flowers, sunlight, or tiny props.
- Vermilion / Chinese warm palette: cinnabar red, gold, pale pink blossoms, ink brown, and a small cyan-green balance for Chinese weddings, palace walls, festivals, lantern scenes, or ceremonial themes.
- Blue-purple / cyan fantasy night: deep blue, violet, magenta, cyan-blue, and black silhouettes for glowing forests, night oceans, bioluminescent plants, magic, or mysterious night scenes.
- Pink-purple / sweet dream palette: pink, pale blue, milk white, rose red or lavender, with a little deep green to stabilize amusement parks, perfume, dessert-like, romantic, or soft fantasy themes.

## Palette Constraints

- State a harmonious palette with a clear dominant color, supporting color, and shadow color when writing scene prompts.
- The dominant color must be a visible medium- or high-saturation color occupying a meaningful large area. Low-saturation neutrals such as `奶油白`, `米白`, `象牙白`, `浅木色`, `浅灰`, `柔灰棕`, and `米色` may be supporting colors, material colors, shadow colors, or negative space, but they must not be the only palette family.
- Dark colors are valid when the theme naturally calls for dark environments, such as `星空`, `宇宙`, `银河`, `太空`, `夜空`, `黑夜`, `夜晚`, `月夜`, `深夜`, `暗夜`, `深海`, `地下洞穴`, `哥特`, `恐怖`, `神秘`, or `暗黑`. The dark dominant color must carry hue and saturation, such as `深蓝`, `午夜蓝`, `靛蓝`, `蓝紫`, `深紫`, `孔雀蓝黑`, `墨蓝`, or `深海蓝`.
- Do not use `黑色`, `灰黑`, `暗灰`, or `深灰` alone as the dominant color. If black or gray-black values are needed, place them in background depth, cast shadow, dark areas, negative space, or edge framing, and pair them with a hue-bearing dark dominant color.
- For ordinary daytime, indoor, pastoral, gift, cute pet, garden, and bright festival scenes without dark-theme wording, do not put dark color words such as `深蓝`, `深紫`, `深绿`, `深红`, `墨色`, `黑色`, `酒红阴影`, or `深檀木阴影` inside the main palette phrase. Describe dark areas later as `投影`, `暗部`, `边缘遮挡`, or `背景纵深` when needed.
- Do not use three low-saturation neutral colors as the full palette, such as `奶油白、浅木色和柔灰棕阴影`, `米白、浅灰和浅木色`, or `象牙白、米色和灰褐阴影`.
- A small saturated accent does not count as the dominant color. Let the dominant color occupy the largest visual area; use neighboring supporting colors to keep the scene unified.
- Use high-saturation accent colors only in small areas, such as a character detail, flower, light spot, or key prop.
- Use dark colors for foreground, edge framing, silhouettes, and shadow depth; concentrate bright colors around the visual center.
- In cool palettes, add a little warm light when the scene needs intimacy or story warmth. In warm palettes, add a little cool green or cyan-green when the scene needs freshness or balance.

## Scene Color Richness

For non-black-background scene prompts, avoid one-note color. A scene should feel unified, but it should not collapse into one hue family. Before writing the final sentence, silently plan a layered palette with:

- Dominant color: the largest visible mood color or environmental color.
- Analogous supporting color: a neighboring hue that keeps the image harmonious.
- Small complementary or warm/cool accent: a small-area color that adds contrast and visual life.
- Material neutral: stone, pearl, ivory, wood, metal, mist, sand, fabric, or other grounding color.
- Shadow/depth color: a hue-bearing dark or muted color that creates distance and framing.

Accent colors must attach to concrete visible carriers, not abstract palette words. Use plants, flowers, fabric trim, gems, fruit, ribbons, lanterns, candles, fireflies, water plants, tiles, murals, metal inlay, glass reflections, small props, architecture details, or light particles as color carriers.

Night, underwater, deep forest, cosmic, cave, and other dark scenes may use deep blue, indigo, violet, blue-purple, teal-black, or deep cyan as the dominant mood, but they must still include visible local colors when the theme allows. Good carriers include green lotus leaves, cyan reeds, moss, purple hydrangeas, pink-white flowers, ivory stone steps, warm gold fireflies, amber lanterns, red ribbons, pale shell, coral, silver mist, or pearl highlights. Avoid all-blue, all-purple, all-cyan, or all-gray scenes unless the user explicitly requests a monochrome look.

Use color ratio thinking instead of listing equal colors. Let the dominant color occupy the largest area, the analogous support carry secondary surfaces, and the complementary or warm/cool accent appear only in small high-value details around the visual focus. A useful default is roughly dominant/support/accent, such as 60/30/10, but do not output numeric ratios in the final prompt.

When writing a scene prompt, express color through spatial carriers. Prefer `午夜蓝池水、深绿莲叶、紫色绣球花、银白月光、暖金萤火` over `蓝紫色调，点缀绿色和金色`. The final prompt should make the color distribution visible in foreground, middle-ground, background, and focal details.

## Environment And Composition

- Scene prompts must include foreground, middle-ground, and background details that support one visual story.
- Do not default every scene to a complete wide establishing view. Before writing the prompt, choose a composition function from `scene-composition-rules.md`: establish space, ritual center, local intimacy, foreground occlusion, path guidance, or macro overhead.
- Avoid repeating generic endings such as `平视略高角度构图让 A、B、C 形成清晰中心`. Use a concrete composition mechanism instead: foreground occluder, leading line, off-center subject, central axis, high or low camera, near-field pressure, or far-scale comparison.
- Describe the environment's structure, proportion, material hierarchy, light source, shadows, and camera angle before finalizing the prompt. This prevents visually expensive scenes from becoming structurally confusing or physically impossible.
- For indoor, outdoor, architecture, courtyard, garden, city, festival, or other human-made settings, state a concrete environment/theme style. Prefer high-aesthetic general styles unless the user asks for a specific region: `现代原木风格客厅`, `美式田园客厅`, `法式复古公寓`, `英式壁炉书房`, `现代简约大平层`, `轻奢酒店套房`, `复古玩具工坊`, `木质宠物咖啡馆`, `阳光玻璃花房`, `现代花艺工作室`, `现代庭院花园`, `美式乡村庭院`, `英式玫瑰花园`, `法式几何喷泉花园`, `地中海白石露台`, `托斯卡纳石墙庭院`, `现代泳池庭院`, `城市屋顶花园`, `现代美术馆中庭`, `Art Deco 宴会厅`, `包豪斯玻璃住宅`, `复古火车站台`, `海边度假酒店`, `玻璃温室植物园`, `城市滨水步道`, `欧式拱廊街`, `现代展览馆`, `未来太空站`, or `云端水晶城市`.
- For Chinese settings, use concrete styles such as `中式文人庭院`, `江南水榭庭院`, `苏式园林`, `徽派白墙黛瓦巷院`, `新中式宅院`, `唐代宫灯街`, `宋式木构亭廊`, `明清王府花园`, `中式书房窗边`, `中式灯会屋顶街区`, `竹林山门庭院`, or `青砖灰瓦茶室`.
- For mythic or fantasy human-made settings, use concrete styles such as `海底神殿遗迹`, `月宫露台`, `莲花宫阙`, `云海神殿`, `水晶洞穴祭坛`, `雪山神庙`, `古代山门祭坛`, `沉没石殿`, or `发光圆阵展台`.
- For human-made settings, describe at least two visible style carriers: roof, arch, column, window, tile, railing, furniture, lantern, mural, paving, fabric, platform, or planting layout.
- For natural backgrounds, state habitat type, terrain, plants or geology, weather/time cue, and background depth. For mythic natural backgrounds, name the mythic setting style, such as Dunhuang sacred city, Chinese mountain sanctuary, moon palace terrace, underwater temple ruin, lotus palace, ancient battlefield ruin, snowy cliff shrine, crystal cave altar, or cloud-sea divine hall.
- State a visible light source direction or visible light state, the color of the light, the surfaces it illuminates, and the color tendency retained in shadow.
- State an explicit camera angle in every environment prompt, including environment-only prompts: `平视视角`, `俯视视角`, `仰视视角`, `低角度仰视`, `高角度俯视`, or `鱼眼近景视角`.
- Choose composition because it serves the story. Use wide establishing composition only when scale, architecture, or world identity is central. Use close-range, foreground-occluded, off-center, over-table, low-angle, high-angle, diagonal, or leading-line composition when intimacy, reveal, encounter, ritual action, or object emphasis is the real subject.
- End scene prompts with the camera angle, named composition, foreground relationship, or background depth. Do not use `正方形构图`.

## Material Discipline

- Express value through scale, structure, material hierarchy, controlled reflections, and coherent lighting.
- Prefer stable premium materials such as pearl, glass, silver, velvet, bone china, carved stone, clear crystal, silk, polished wood, soft internal glow, and controlled reflections.
- Use laser, holographic, rainbow-reflective, or highly iridescent crystal materials only when the user explicitly asks for that look or the theme truly depends on it. Do not use them as a shortcut for expensive, ceremonial, or high-value expression.

