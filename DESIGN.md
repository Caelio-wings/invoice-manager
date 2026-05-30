# Seline Analytics — Style Reference
> Crisp Data Canvas

**Theme:** light

Seline Analytics employs a focused, lightweight analytics dashboard aesthetic with a crisp, monochromatic base and a single vivid blue for active states and brand accent. Surfaces are airy with soft shadows, creating a sense of clarity and organization. Typography is precise and utilitarian, prioritizing readability with subtle letter-spacing. Components emphasize functionality over heavy styling, presenting data and controls in an approachable, streamlined manner.

## Colors

| Name | Value | Role |
|------|-------|------|
| Cloud White | `#ffffff` | Primary surface background, card surfaces, button backgrounds in nav, input backgrounds |
| Canvas Fog | `#fafaf9` | Page background, secondary surface where a subtle lift from Cloud White is needed |
| Slate Text | `#0c0a09` | Primary text, headings, strong text elements |
| Ash Gray | `#78716c` | Secondary text, muted helper text, iconography, default button text |
| Stone Border | `#e5e7eb` | Subtle borders, dividers, ghost button borders, inactive input borders |
| Platinum Outline | `#d6d3d1` | Input field borders, light separators, less prominent borders than Stone Border |
| Steel Gray | `#a8a29e` | Tertiary text, less important details, subtle icons |
| Hover Stone | `#c9c5c2` | Subtle hover states for text or borders |
| Ghost Ink | `#1c1917` | Background for certain ghost buttons on hover |
| Chartwell Blue | `#3ba6f1` | Primary action background, active navigation indicators, key data points, brand accents in icons and links |
| Sky Tint | `#c1e1f7` | Subtle background for certain body sections, providing a slight cool tint |

## Typography

### Inter — Body text, UI labels, small captions, navigation items, and descriptions. Prioritizes legibility over expressive flair.
- **Substitute:** system-ui
- **Weights:** 400, 500, 600
- **Sizes:** 12px, 13px, 14px, 15px, 16px, 18px
- **Line height:** 1.00, 1.29, 1.33, 1.43, 1.50, 1.53, 1.54, 1.56, 1.64, 1.67, 1.69, 1.77, 1.92
- **Letter spacing:** -0.005em at 18px, 0.003em at 16px, 0.004em at 12px

### roobert — Headings and prominent display text. Its distinct letter-spacing at larger sizes adds a subtle character while maintaining a technical feel.
- **Substitute:** sans-serif
- **Weights:** 400, 500
- **Sizes:** 16px, 18px, 20px, 32px, 52px
- **Line height:** 1.00, 1.12, 1.20, 1.22, 1.25, 1.69
- **Letter spacing:** -0.025em for 52px, -0.021em for 32px, -0.017em for 20px

### Type Scale

| Role | Size | Line Height | Letter Spacing |
|------|------|-------------|----------------|
| caption | 12px | 1.5 | 0.048px |
| heading-sm | 18px | 1.25 | -0.016px |
| heading | 20px | 1.2 | -0.017px |
| heading-lg | 32px | 1.12 | -0.021px |
| display | 52px | 1 | -0.025px |

## Spacing & Layout

**Base unit:** 4px

**Density:** compact

- **Section gap:** 48px
- **Card padding:** 24px
- **Element gap:** 8px

### Border Radius

- **tags:** 9999px
- **cards:** 10px
- **inputs:** 4px
- **buttons:** 9999px
- **largeCard:** 16px

## Components

### Primary Filled Button
**Role:** Call to action.

Background: Chartwell Blue (#3ba6f1), Text: Cloud White (#ffffff), Radius: 9999px. Padding: 0px.

### Ghost Button - Light
**Role:** Secondary actions or navigation items.

Background: rgba(0,0,0,0) (transparent), Text: Ash Gray (#78716c), Border: 1px solid Stone Border (#e5e7eb) or transparent. Radius: 0px. Used for navigation and dashboard filters.

### Ghost Button - Dark Text
**Role:** Secondary actions with higher text prominence.

Background: rgba(0,0,0,0) (transparent), Text: Slate Text (#0c0a09), Border: 1px solid Stone Border (#e5e7eb). Radius: 4px. Used for 'Live demo' button.

### Subtle Ghost Button
**Role:** Tertiary actions, tabs, or selections within confined spaces.

Background: rgba(120,114,109,0.1) (Ash Gray tinted transparent), Text: Slate Text (#0c0a09), Border: 1px solid Stone Border (#e5e7eb). Radius: 4px. Minor internal actions and tab switching.

### Dashboard Card
**Role:** Container for data visualizations and content blocks.

Background: Cloud White (#ffffff), Border Radius: 10px, Shadow: rgba(0,0,0,0.05) 0px 4px 16px 0px. Padding: 24px.

### Pill Card
**Role:** Small, contained content chip.

Background: Cloud White (#ffffff), Border Radius: 9999px, Shadow: rgba(0,0,0,0.05) 0px 4px 16px 0px. Padding: 4px 12px.

### Elevated Feature Card
**Role:** Prominent feature block.

Background: Cloud White (#ffffff), Border Radius: 16px, Shadow: rgba(17,12,46,0.12) 0px 12px 45px 0px. Padding: 8px.

### Standard Input Field
**Role:** Text input areas.

Background: Cloud White (#ffffff), Text: Slate Text (#0c0a09), Border: 1px solid Platinum Outline (#d6d3d1). Radius: 0px. Placeholder text: Ash Gray (#78716c).

### Rounded Input Field
**Role:** Filter input or search fields.

Background: Cloud White (#ffffff), Text: Ash Gray (#78716c), Border: 1px solid Platinum Outline (#d6d3d1). Radius: 6px. Padding: 4px 12px.

## Do's and Don'ts

### Do
- Prioritize Cloud White (#ffffff) for card backgrounds and Canvas Fog (#fafaf9) for main page backgrounds to reinforce a light, airy feel.
- Use Chartwell Blue (#3ba6f1) exclusively for primary calls to action, active states, and brand iconography to maintain its impact.
- Apply Slab Text (#0c0a09) for all headings and primary body text, ensuring high contrast and readability.
- Utilize Inter for all body copy and UI elements, paired with roobert for headlines to provide distinct typographic roles.
- Maintain a compact button design with minimal vertical padding and 9999px border-radius for a consistent modern pill shape.
- Implement 10px border-radius for all data cards and larger containers, providing soft, approachable corners.
- Use the rgba(0,0,0,0.05) 0px 4px 16px 0px shadow for most card elevations, reserving the deeper rgba(17,12,46,0.12) 0px 12px 45px 0px for features that require significant visual prominence.

### Don't
- Avoid introducing additional saturated colors beyond Chartwell Blue (#3ba6f1) to maintain the focused monochromatic aesthetic.
- Do not use heavy, dark backgrounds for sections or components; the system relies on lighter surfaces for visual clarity.
- Refrain from using strong, angular shapes or hard edges; stick to the established subtle curves and rounded corners.
- Do not use font weights above 500 for roobert or 600 for Inter; the system avoids heavy typography to feel lightweight.
- Avoid deep, dark shadows for components. Surface elevation should be subtle, using light, diffused shadows.
- Do not use generic system fonts in place of Inter or roobert for new UI elements; their specific letter-spacing and proportions are key to the brand's typographic identity.
- Do not vary line-height significantly from the established values; consistent line-height (1.5 for Inter, 1.25 for roobert) ensures a uniform content density.

## Elevation

- **Dashboard Card:** `rgba(0, 0, 0, 0.05) 0px 4px 16px 0px`
- **Pill Card:** `rgba(0, 0, 0, 0.05) 0px 4px 16px 0px`
- **Main Navigation/Buttons:** `rgba(0, 0, 0, 0.05) 0px 1px 2px 0px`
- **Elevated Feature Card:** `rgba(17, 12, 46, 0.12) 0px 12px 45px 0px`
- **Icons/Other elements:** `rgba(0, 0, 0, 0.1) 0px 4px 6px -1px, rgba(0, 0, 0, 0.1) 0px 2px 4px -2px`

## Surfaces

- **Canvas Fog** (`#fafaf9`) — Base page background. Provides a warm achromatic canvas for content.
- **Cloud White** (`#ffffff`) — Primary content surface for cards, modals, and primary UI elements. Sits directly above Canvas Fog.

## Imagery

The site uses a combination of product screenshots, abstract illustrations, and minimal iconography. Product screenshots are contained within cards, depicting a clean, functional dashboard UI. Abstract illustrations are sparse, featuring organic, cloud-like shapes in a light gray tone that blends with the background, acting as subtle atmospheric elements rather than focal points. Icons are outlined, typically in Ash Gray (#78716c) or Slate Text (#0c0a09), with some instances of Chartwell Blue (#3ba6f1) for emphasis. Imagery serves primarily to explain product functionality or provide decorative atmosphere at a low visual density.

## Layout

The page uses a maximum width containment for its main content, centered on the screen, but the navigation bar extends full-bleed across the top. The hero section features a large centered headline and calls to action over a Canvas Fog background, with an illustrative element visually balancing the right side. Content sections generally follow a vertical rhythm with consistent section gaps of 48px, often containing card grids or alternating text-and-image blocks. The layout is spaced and uncluttered, with a clear hierarchy established by abundant negative space and light visual dividers.

## Similar Brands

- **Plausible Analytics** — Shares a similar focus on simple, lightweight analytics with a clean UI and minimal, functional color palette.
- **Fathom Analytics** — Exhibits a comparable design with a light-themed interface, emphasis on clear data presentation, and a restrained use of brand color.
- **Linear** — Mirrors the use of very subtle, almost invisible borders and dividers, paired with a focus on functional typography and clean data display.
- **Vercel** — Employs a polished, minimalistic SaaS aesthetic, relying on a neutral palette with a single accent color for interaction and brand identity.
