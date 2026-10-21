# Portfolio screen

Scope: only the introduction/portfolio. The other app screens are not implemented. The user's supplied references guide the grid backdrop, pixel typography, phosphor title, ocean, and cat characters. Generated assets use the built-in image generation tool. All assets and fonts are served locally; no animation or UI packages were added.

## Current direction

The revised portfolio fills the viewport without an outer frame. SONAR is centered with a brief, occasional pixel glitch; hot pink is the primary color, with cyan, yellow, red and violet accents drawn from the mascot. The brighter reef is on the left, and the solid pink introduction is on the right. Ten small fish swim at different speeds and scatter on reef hover; a stepped pixel wave joins the hero to the project description. The ocean cat, Pop Cat and the green cat react only while hovered. Banana Cat is smaller and links back to the top. The pause button was removed at the user's request; reduced-motion support remains.

## Artwork prompts

### `web/public/images/ocean-reef.png`

Asset: bright colorful 16-bit pixel-art coral reef backdrop for the SONAR portfolio. Redesign the supplied underwater scene in a new palette. Keep a side-on underwater game level, crisp deliberate square pixels and rich corals with spacious open water in the upper center for a separate cat mascot. Wide landscape 3:2. Color direction: hot pink #f50094 and bubblegum pink #ff68bc as the main reef colors, with vivid cyan #51d9fa, bright yellow #ffe65a, scarlet #ff554e and a few violet pixel edges from a chromatic black cat mascot. Water is rich dark graphite/petrol, not dull green. The reef must be significantly brighter, playful, vibrant and more colorful than the reference: hot-pink branching coral, cyan sea fans, yellow anemones, red coral, bright pink-and-cyan rocky terraces, lively colored marine plants. Clear underwater light rays made of hard pixel clusters, no glow blobs. Rich bright pixel clusters in bottom third and along sides, dark readable open water in upper center. No fish or cats because they will be animated separately. No UI, lettering, border, watermark, blurred painting or smooth gradients. Make a finished pixel game environment, not a pixelated photograph.

### `web/public/images/void-cat.png`

Reference: the supplied Void Cat image. Transparent background requested.

Use case: background-extraction. Asset type: transparent mascot sprite for a pixel-art website. Use the supplied cat reference as the sole subject. Remove the baked gray and white checkerboard background and make it genuinely transparent. Keep the exact recognizable black void-cat silhouette, the tiny two vertical white rectangular eyes, asymmetric pointed ears, squat body, and vibrant chunky cyan/violet edge on the left and red/yellow edge on the right. Preserve original intentional large square pixel clusters. Center the whole cat with comfortable transparent padding. No checkerboard, no floor, no shadows, no new features, no accessories, no text. Output only the cat on true transparent alpha. The sprite will be tilted and gently drifted underwater in CSS.

### web/public/images/alien-cat.png

Reference: supplied green alien cat. Transparent background requested.

Transparent pixel-art sprite asset. Reproduce the supplied green alien cat faithfully as one isolated character: antennae, pointed side ears, green face, lime pixel highlights, dark outline and two half-lidded eyes. Preserve the reference's blocky grid and expression, no redesign. Remove all white background, leave genuine transparent alpha. Clean crisp hard pixel edges, no soft glow, no shadow, no text or extra objects. Center entire character with tight but complete transparent padding.

### web/public/images/pop-cat.png

Reference: supplied pop cat. Transparent background requested.

Transparent pixel-art sprite asset. Reproduce the supplied pop cat faithfully as one isolated character: white cat body, orange/brown patches, pink ear interiors, huge open black-outlined mouth with red interior. Keep the original deliberate large pixel clusters, iconic silhouette and happy open mouth. Remove white background but preserve white fur inside the black character outline. Genuine transparent alpha, no white rectangle. Clean crisp hard pixel edges. No new accessories, shadows, text or objects. Center entire character with tight but complete transparent padding.

### web/public/images/banana-cat.png

Reference: supplied banana cat. Transparent background requested.

Transparent pixel-art sprite asset. Faithfully reproduce ONLY the banana-costumed cat from the reference. Preserve the tall curved bright yellow banana suit with brown stem, gray/brown cat face peeking out, little paws and feet, original blocky pixel clusters and funny expression. Remove the white background, the gray ground shadow, and the separate palette strip at the far right. Entire banana cat fully visible on genuine transparent alpha with clean crisp pixel edges and comfortable minimal padding. No floor, no added accessories, no lettering, no extra cats. Keep the yellow banana, don't recolor it pink.

## Fonts

Press Start 2P and VT323 from the Google Fonts repository. Their SIL Open Font License notices are included beside the fonts in `web/public/fonts/`.
