---
name: LexFlow Legal Intelligence
colors:
  surface: '#faf8ff'
  surface-dim: '#d2d9f4'
  surface-bright: '#faf8ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f3ff'
  surface-container: '#eaedff'
  surface-container-high: '#e2e7ff'
  surface-container-highest: '#dae2fd'
  on-surface: '#131b2e'
  on-surface-variant: '#434655'
  inverse-surface: '#283044'
  inverse-on-surface: '#eef0ff'
  outline: '#737686'
  outline-variant: '#c3c6d7'
  surface-tint: '#0053db'
  primary: '#004ac6'
  on-primary: '#ffffff'
  primary-container: '#2563eb'
  on-primary-container: '#eeefff'
  inverse-primary: '#b4c5ff'
  secondary: '#5a5f62'
  on-secondary: '#ffffff'
  secondary-container: '#dce0e4'
  on-secondary-container: '#5e6367'
  tertiary: '#006242'
  on-tertiary: '#ffffff'
  tertiary-container: '#007d55'
  on-tertiary-container: '#bdffdb'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dbe1ff'
  primary-fixed-dim: '#b4c5ff'
  on-primary-fixed: '#00174b'
  on-primary-fixed-variant: '#003ea8'
  secondary-fixed: '#dfe3e7'
  secondary-fixed-dim: '#c3c7cb'
  on-secondary-fixed: '#171c1f'
  on-secondary-fixed-variant: '#43474b'
  tertiary-fixed: '#6ffbbe'
  tertiary-fixed-dim: '#4edea3'
  on-tertiary-fixed: '#002113'
  on-tertiary-fixed-variant: '#005236'
  background: '#faf8ff'
  on-background: '#131b2e'
  surface-variant: '#dae2fd'
typography:
  headline-xl:
    fontFamily: Hanken Grotesk
    fontSize: 40px
    fontWeight: '700'
    lineHeight: 48px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Hanken Grotesk
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Hanken Grotesk
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 16px
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 4px
  gutter: 24px
  margin-mobile: 16px
  margin-desktop: 32px
  container-max-width: 1440px
---

## Brand & Style
The design system for LexFlow is engineered to evoke **authority, clarity, and efficiency**. As a legal Q&A application, the UI must bridge the gap between complex legal data and user-friendly accessibility. 

The style is defined as **Corporate Modern with a Minimalist touch**. It leverages high-quality typography and substantial whitespace to reduce cognitive load during research. The aesthetic prioritizes a "software as a tool" philosophy—reliable, precise, and unobtrusive—ensuring that the legal content remains the primary focus. Visual interest is generated through subtle depth and a vibrant primary blue that signifies intelligence and trust.

## Colors
The palette is rooted in a professional "Legal Blue" and a range of clinical neutrals.

- **Primary (#2563EB):** An energetic, high-contrast blue used for key actions, brand identity, and focus states. It ensures high visibility against the white background.
- **Secondary (#F1F5F9):** A soft, cool slate used for backgrounds, side drawers, and chat bubbles to provide gentle contrast without visual fatigue.
- **Tertiary (#10B981):** A "Success Green" reserved for verified legal citations and system status indicators.
- **Neutral (#0F172A):** A deep midnight blue-black for high-readability text and primary navigation icons.
- **Background:** Pure white (#FFFFFF) for the main canvas to maintain the "clean" and "professional" requirement.

## Typography
The typography strategy utilizes a dual-sans-serif approach to balance modern branding with high-density readability.

**Hanken Grotesk** is used for headlines. Its sharp, contemporary geometry provides a "tech-forward" legal feel. **Inter** is the workhorse for all body copy and UI labels, chosen for its exceptional legibility in long-form legal text and its neutral, systematic tone. 

Line heights are intentionally generous (1.5x - 1.6x for body) to ensure that dense legal paragraphs remain digestible and easy to scan.

## Layout & Spacing
This design system employs a **Fluid Grid** model based on an 8px base unit (with 4px increments for tighter components).

- **Desktop:** 12-column grid with a 1440px max-width. Large 24px gutters create an expansive, "premium" feel.
- **Tablet:** 8-column grid with 20px gutters.
- **Mobile:** 4-column grid with 16px margins. 

The chat interface is centered within the grid to maintain focus, while legal reference panels appear in a side drawer (typically 400px fixed width) on the right, shifting the main content rather than overlaying it when space permits.

## Elevation & Depth
Depth is communicated through **Tonal Layers** and **Low-Contrast Outlines**. 

To maintain a "flat/modern" aesthetic, heavy shadows are avoided. Instead:
- **Level 0 (Surface):** The main background (White).
- **Level 1 (Sectional):** Side drawers and inactive chat bubbles use the Secondary Slate (#F1F5F9).
- **Level 2 (Active/Floating):** Use a subtle 1px border (#E2E8F0) and an extremely soft ambient shadow (Blur: 10px, Opacity: 4%, Color: Neutral) to lift input fields and cards.

This approach creates a sense of hierarchy without breaking the clean, professional minimalism of the legal environment.

## Shapes
A **Rounded** (Level 2) shape language is applied across the system. 

- **Standard Buttons/Inputs:** 0.5rem (8px) corner radius. This provides a approachable yet structured look.
- **Chat Bubbles:** The user's bubble uses a 1rem radius on three corners and 2px on the anchor corner.
- **Suggested Chips:** Use "Pill-shaped" (Level 3) rounding to distinguish them from actionable buttons and static labels.

## Components

### Chat Bubbles
- **AI Response:** Secondary background (#F1F5F9), Neutral text. Aligned left. High-density padding (12px 16px).
- **User Prompt:** Primary background (#2563EB), White text. Aligned right.

### Input Field
- **Structure:** White background with a 1px border (#E2E8F0). Focus state uses a 2px Primary border with a soft glow.
- **Placement:** Anchored to the bottom with an integrated "Send" icon button and an attachment/document icon on the left.

### Suggested Chips
- **Style:** Ghost-style buttons with a Secondary background and Primary Blue text. On hover, the background darkens slightly. These are used for "Follow-up questions."

### Side Drawer
- **Style:** Slide-in from the right. Uses a full-height container with a light border separator. This is the primary home for "Document Source" views and "Legal Citations."

### Buttons
- **Primary:** Solid Primary Blue with White text. Bold weight.
- **Secondary:** Transparent background with Primary Blue border and text.