# Xynolog Browser Style Guide

## CSS Architecture Overview

The Xynolog Browser uses a hybrid CSS architecture that combines:
1. **Semantic CSS from @xynolog/react-ui** - Framework-agnostic component styles with modular organization
2. **Tailwind CSS** - For app-specific styling and utilities

### Technical Implementation

#### @xynolog/react-ui Styles
All React UI components from `@xynolog/react-ui` come with semantic CSS classes following BEM methodology. These styles are imported in `globals.css`, ahead of Tailwind:

```css
/* browser/src/app/globals.css */
@import '@xynolog/react-ui/styles';
@import "tailwindcss";
```

The styles are organized into a modular architecture:
- **Core UI Elements** (`core/`) - Fundamental elements like buttons, toggles, sliders, inputs, tags
- **Patterns** (`patterns/`) - Shared panel and card structures
- **Panels** (`panels/`) - Styles for individual panels
- **Motivations** (`motivations/`) - W3C Web Annotation standard styles
- **Features** (`features/`) - Feature-specific styling
- **Component-level CSS** - Composed components (modals, navigation, resource panels, toolbar) keep their CSS beside their code

This provides all component styles with the `xynolog-` prefix:
- `xynolog-button`, `xynolog-button--primary` (from `core/buttons.css`)
- `xynolog-card` (from `patterns/cards.css`)
- `xynolog-panel`, `xynolog-panel-header__title` (from `patterns/panels-base.css`)
- `xynolog-toggle`, `xynolog-progress`, `xynolog-slider` (from `core/`)
- And more...

#### Tailwind Configuration
The Browser app uses Tailwind for its own components and layout. `globals.css` loads `tailwind.config.js` with `@config` and names the source Tailwind scans for class names, the Browser's own `src`. `@xynolog/react-ui` uses only its own `xynolog-*` classes, from `@xynolog/react-ui/styles`, so Tailwind does not scan it:

```css
/* browser/src/app/globals.css */
@config "../../tailwind.config.js";
@plugin "@tailwindcss/typography";
@source "../../src";
```

### Using @xynolog/react-ui Components

When using components from @xynolog/react-ui, they already have all necessary styling:

```tsx
import { Button, Toolbar } from '@xynolog/react-ui';

// Components come pre-styled with semantic classes
<Button variant="primary">Click me</Button>
```

### Dark Mode Support

`ThemeProvider` from @xynolog/react-ui resolves the theme (`light`, `dark`, or `system`) and sets `data-theme` on the `<html>` element. The react-ui styles and the Browser's `globals.css` key their dark rules off `[data-theme="dark"]`.

The Browser's `tailwind.config.js` sets `darkMode: ['selector', '[data-theme="dark"]']`, so Tailwind's `dark:` variants respond to the same attribute: a `dark:` class applies exactly when react-ui's dark rules do.

### Custom Styling Approach

#### For @xynolog/react-ui Components
If you need to customize a react-ui component, add additional classes without overriding the semantic ones:

```tsx
// Good - adds spacing without breaking component styles
const spaced = <Button className="mt-4" variant="primary">Submit</Button>;

// Bad - don't override semantic classes
const overridden = <Button className="my-custom-button" variant="primary">Submit</Button>;
```

#### For App-Specific Components
Use Tailwind utilities freely for components defined in the Browser app:

```tsx
// App-specific component using Tailwind
<div className="flex items-center gap-4 p-6 bg-white dark:bg-gray-800">
  <span className="text-lg font-semibold">Custom content</span>
</div>
```

## Color System

### Design Tokens
The design system uses CSS custom properties from @xynolog/react-ui:
- `--xynolog-color-primary-*`: Blue color scale
- `--xynolog-color-gray-*`: Neutral color scale
- `--xynolog-color-red-*`, `--xynolog-color-green-*`, etc.: Semantic colors
- `--xynolog-color-yellow-*`: Full yellow palette for highlights
- `--xynolog-color-orange-*`, `--xynolog-color-amber-*`: For tagging motivations

### Panel Design Tokens
Centralized tokens ensure consistency across all panels:
- `--xynolog-panel-padding`: 1rem
- `--xynolog-panel-title-size`: var(--xynolog-text-lg)
- `--xynolog-panel-title-weight`: var(--xynolog-font-semibold)
- `--xynolog-panel-header-margin-bottom`: 0.75rem
- `--xynolog-panel-section-gap`: 1.5rem
- `--xynolog-panel-icon-size`: 1.125rem

### Primary Colors
The Xynolog design system uses a **blue/cyan** color palette as its primary theme:

- **Primary Blue:** `--xynolog-color-blue-500` (RGB: 59, 130, 246) - Used for primary actions, links, and selections
- **Cyan Accent:** `--xynolog-color-cyan-500` (RGB: 6, 182, 212) - Used in gradients and accent elements
- **Cyan/Blue Gradient:** `--xynolog-gradient-primary` - Cyan-500 to blue-500 at 20% opacity, deepening to cyan-600 → blue-600 on hover

### Secondary Colors
- **Yellow:** Reserved exclusively for text highlights (yellow-200 light / yellow-900 at 50% dark)
- **Green:** Success states and completion messages
- **Red:** Error states and destructive actions
- **Gray:** Neutral UI elements, backgrounds, and disabled states

### Color Usage Guidelines

#### Blue/Cyan for Primary UI Elements
Use blue and cyan colors for:
- Primary buttons and call-to-action elements
- Selected states and active filters
- Progress indicators and loading states
- Links and interactive elements
- Entity type tags and reference tags
- Focus rings and form inputs
- Detection progress and AI-powered features

#### Yellow for Highlights
Yellow is reserved exclusively for text highlights in documents. This creates a clear visual distinction between highlighted text and interactive references.

#### Gradients
The cyan-to-blue gradient (`--xynolog-gradient-primary`) marks primary action buttons (`xynolog-button--primary`). Reference annotations carry a lighter cyan-to-blue gradient (`--xynolog-motivation-reference-bg`).

## Core UI Elements from @xynolog/react-ui

The react-ui package provides fundamental UI elements in the `core/` directory:

### Toggle Switches
```tsx
// From core/toggles.css
const [isOn, setIsOn] = useState(false);

<label className="xynolog-toggle-label">
  <span className="xynolog-toggle-label__text">Line numbers</span>
  <button
    type="button"
    role="switch"
    aria-checked={isOn}
    onClick={() => setIsOn(!isOn)}
    className={`xynolog-toggle ${isOn ? 'xynolog-toggle--active' : ''}`}
  >
    <span className={`xynolog-toggle__slider ${isOn ? 'xynolog-toggle__slider--active' : ''}`} />
  </button>
</label>
```

### Progress Bars
```tsx
// From core/progress.css
<div className="xynolog-progress">
  <div className="xynolog-progress__fill" style={{width: '60%'}}></div>
</div>
```

### Range Sliders
```tsx
// From core/sliders.css
<input type="range" className="xynolog-slider" min="0" max="100" />
```

### Tags
```tsx
// From core/tags.css
<>
  <span className="xynolog-tag">Category</span>
  <span className="xynolog-tag xynolog-tag--secondary">Secondary</span>
</>
```

## W3C Web Annotation Motivations

The react-ui package includes dedicated styles for W3C Web Annotation standard motivations, one file per motivation in `motivations/`.

### Available Motivation Classes
- `.annotation-reference` - Cyan to blue gradient (linking)
- `.annotation-highlight` - Yellow background (highlighting)
- `.annotation-assessment` - Red wavy underline (assessing)
- `.annotation-comment` - Dashed outline (commenting)
- `.annotation-tag` - Orange to amber gradient (tagging)

Which class an annotation gets is decided by the `ANNOTATORS` registry — see [Annotation Styles](#annotation-styles).

## Component Styling Guidelines

### Using @xynolog/react-ui Components

Components from @xynolog/react-ui come with built-in semantic CSS classes. Here's how to use them:

#### Buttons
```tsx
import { Button } from '@xynolog/react-ui';

// Primary button - renders class="xynolog-button" data-variant="primary"
const primary = <Button variant="primary">Primary Action</Button>;

// Secondary button - renders class="xynolog-button" data-variant="secondary"
const secondary = <Button variant="secondary">Secondary Action</Button>;

// With additional spacing (combines semantic + utility)
const spaced = <Button variant="primary" className="mt-4">Submit</Button>;
```

#### Cards
```tsx
// A card is a class, not a component
<div className="xynolog-card">
  <h3>Title</h3>
  <p>Content here</p>
</div>
```

#### Panels
```tsx
// Using semantic classes directly
<div className="xynolog-panel">
  <div className="xynolog-panel-header">
    <h2 className="xynolog-panel-header__title">Panel Title</h2>
  </div>
  <div className="xynolog-panel__content">
    Panel content
  </div>
</div>
```

### Button Class Strings

For a plain `<button>`, `@xynolog/react-ui` exports `buttonStyles`: ready-made `xynolog-button` class strings. The Browser's home page renders its Begin button with `buttonStyles.primary.base`.

#### Primary Buttons
**When to use:** Main call-to-action buttons that represent the primary action on a page or in a modal.

**Style:** Cyan/blue gradient with hover effects

**Examples:**
- "Sign In" / "Sign Up"
- "Create Reference" (in selection popup)
- "New Document"
- "Save" (when it's the main action)

```tsx
import { buttonStyles } from '@xynolog/react-ui';

<>
  <button className={buttonStyles.primary.base}>Primary Action</button>
  <button className={buttonStyles.primary.large}>Large Primary Action</button>
</>
```

#### Secondary Buttons
**When to use:** Supporting actions that are important but not the primary focus.

**Style:** Gray with subtle black/white outline

**Examples:**
- "Search"
- "Cancel"
- "Learn More"
- "Back"

```tsx
<>
  <button className={buttonStyles.secondary.base}>Secondary Action</button>
  <button className={buttonStyles.secondary.withScale}>Secondary with Hover Scale</button>
</>
```

#### Tertiary Buttons
**When to use:** Less important actions, navigation items, or options within a set.

**Style:** Minimal, with just text and hover background

**Examples:**
- Entity type selection buttons (when unselected)
- Navigation items
- "View More" links
- Filter options

```tsx
<button className={buttonStyles.tertiary.base}>Tertiary Action</button>
```

`buttonStyles.danger.base` covers destructive actions.

## Special Cases

### Highlight Button
For a highlight action, use the amber `buttonStyles.warning.base` (`xynolog-button--warning`), which matches the visual language of highlights:

```tsx
<button className={buttonStyles.warning.base}>Highlight</button>
```

### Selected States
When showing selected items, use blue backgrounds:
- **Entity type selections:** `bg-blue-100 dark:bg-blue-900/30`
- **Document/reference selections:** `bg-blue-50 dark:bg-blue-900/20`
- **Active filters:** `bg-blue-100 dark:bg-blue-900/30 border border-blue-300`

### Disabled States
Every `xynolog-button` dims to 50% opacity with a `not-allowed` cursor when it is `:disabled` or carries `data-disabled="true"`. Always disable buttons when:
- An action is in progress
- Required fields are empty
- The action is not available

## Annotation Styles

Each motivation's class name lives in the `ANNOTATORS` registry ([`@xynolog/react-ui/src/lib/annotation-registry.ts`](https://github.com/xynolog/sdk/blob/main/typescript/react-ui/src/lib/annotation-registry.ts)); its colours live in [`@xynolog/react-ui/src/styles/motivations/`](https://github.com/xynolog/sdk/tree/main/typescript/react-ui/src/styles/motivations).

### Highlights
- **Background:** Yellow (`--xynolog-motivation-highlight-bg`: yellow-200; yellow-900 at 50% in dark mode)
- **Border:** Dashed outline in dark mode
- **Hover:** Deeper yellow (yellow-300; yellow-900 at 60% in dark mode)
- **Purpose:** Visual prominence for highlighted text

### References (All Types)
- **Background:** Cyan/blue gradient (`--xynolog-motivation-reference-bg`: cyan-200 → blue-200)
- **Border:** Dashed cyan outline in dark mode
- **Hover:** Deeper gradient (cyan-300 → blue-300)
- **Purpose:** Show connections between documents and entities
- **Note:** All references use the same blue/cyan styling for consistency

### Usage
```tsx
import { ANNOTATORS } from '@xynolog/react-ui';

// The annotator whose motivation matches supplies the class
const annotator = Object.values(ANNOTATORS).find((a) => a.matchesAnnotation(annotation));

<span className={annotator?.className}>Annotated text</span>
```

### Administrative/Moderation
- **Active nav items:** Blue (`bg-blue-50 dark:bg-blue-900/20`)
- **All tags:** Blue (`bg-blue-100 dark:bg-blue-900/30`)
- **Focus states:** Blue ring (`focus:ring-blue-500`)

## Form Elements

### Text Inputs
Inputs take react-ui's `xynolog-input` (`core/inputs.css`), as the Browser's `KnowledgeBasePanel` form does. A labelled field wraps it in the `core/forms.css` classes:

```tsx
<div className="xynolog-form__field">
  <label htmlFor="host" className="xynolog-form__label">Host</label>
  <input id="host" type="text" className="xynolog-input" />
  <p className="xynolog-form__help">Helper text</p>
</div>
```

### Select Dropdowns
```tsx
<select className="xynolog-select">
  <option value="http">HTTP</option>
  <option value="https">HTTPS</option>
</select>
```

## Layout Patterns

### Modal/Popup Structure
1. **Header:** Sticky top with title and close button
2. **Content:** Scrollable main area with consistent padding (`p-4`)
3. **Actions:** Bottom area with primary/secondary buttons

### Card Components
```tsx
<div className="xynolog-card">
  {/* Card content */}
</div>
```

### Navigation Sidebars
The knowledge and moderation layouts use react-ui's `LeftSidebar`, styled by its own `LeftSidebar.css`.

## XynologBranding Component

The `XynologBranding` component is our main brand identity element: the "XYNOLOG" wordmark over a tagline, which it renders as `t('tagline')` — "make meaning" under the Browser's `Home` messages. It's resizable and used in different contexts throughout the application.

### Component Props
```tsx
<XynologBranding
  t={tHome}               // required: renders t('tagline')
  size="lg"               // 'sm' | 'md' | 'lg' | 'xl'; default 'lg'
  showTagline={true}      // default true
  animated={true}         // fade-in animation; default true
  compactTagline={false}  // wider tagline letter-spacing; default false
  className=""            // appended to xynolog-branding
/>
```

### Size Variants

#### Small (`size="sm"`)
**When to use:** Headers and navigation bars where space is limited

**Where used:**
- `UnifiedHeader` (the branding button that opens the navigation menu)
- `LeftSidebar`, expanded, without the tagline

**Example:**
```tsx
<XynologBranding
  t={tHome}
  size="sm"
  showTagline={true}
  compactTagline={true}
  animated={false}
/>
```

#### Medium (`size="md"`)
**When to use:** General use

**Example:**
```tsx
<XynologBranding t={tHome} size="md" />
```

#### Large (`size="lg"`)
**When to use:** Feature sections, about pages. `lg` is the default size.

**Example:**
```tsx
<XynologBranding t={tHome} />
```

#### Extra Large (`size="xl"`)
**When to use:** Hero sections and landing pages

**Where used:**
- The Browser's home page (`src/app/[locale]/page.tsx`), above the Begin button

**Example:**
```tsx
<XynologBranding
  t={tHome}
  size="xl"
  animated={true}
  className="mb-8"
/>
```

### Styling Details

The component uses the Orbitron font for "XYNOLOG" and includes:
- **Gradient text:** Black → primary-600 → black, and white → primary-400 → white in dark mode
- **Animation:** Optional fade-in effect for landing pages
- **Responsive sizing:** Title and tagline sizes are set per `data-size` in `Branding.css`, and the title steps up at the 640px and 768px breakpoints
- **Dark mode support:** Adjusts gradient and colors for dark backgrounds

### Usage Guidelines

1. **Headers:** Use `size="sm"` with `compactTagline={true}` to keep navigation compact
2. **Landing pages:** Use `size="xl"` with `animated={true}` for visual impact
3. **Click behavior:** In headers, wrap with Link to make it navigate to home/dashboard
4. **Spacing:** The component doesn't include outer margin/padding - add via `className` prop

## Best Practices

### CSS Architecture
1. **Component Organization:** @xynolog/react-ui styles are organized into:
   - `core/` - Fundamental UI elements (buttons, toggles, sliders, inputs)
   - `patterns/` - Shared panel and card structures
   - `panels/` - Styles for individual panels
   - `motivations/` - W3C Web Annotation standard styles
   - CSS beside each composed component under `src/components/`
2. **Use Design Tokens:** Leverage panel design tokens and CSS variables for consistency
3. **App Styles:** Use Tailwind for app-specific components and layouts
4. **Don't Mix:** Avoid overriding semantic classes from @xynolog/react-ui with Tailwind utilities
5. **Custom Properties:** Use CSS variables from @xynolog/react-ui (colors, spacing, typography)

### Style Guidelines
1. **Consistency:** Always use the predefined styles rather than creating custom classes
2. **Hierarchy:** Use primary buttons sparingly - typically one per view/modal
3. **Feedback:** Show loading states with spinners or "..." text
4. **Accessibility:** Include proper ARIA labels and keyboard navigation support
5. **Dark Mode:** Always include both light and dark mode styles
6. **Transitions:** Use `transition-all duration-300` for smooth hover effects

## Importing Styles

### For App Components
Import button styles from `@xynolog/react-ui` at the top of your component:

```typescript
import { buttonStyles } from '@xynolog/react-ui';
```

### For Combining Classes
```tsx
// Combining semantic + utility classes
<button className={`${buttonStyles.primary.base} w-full`}>Save</button>
```

react-ui's `Button` merges its `className` prop after `xynolog-button`, so `<Button className="mt-4">` combines the two the same way.

## File Organization

### Browser App Files
- `src/app/globals.css` - Global styles, the @xynolog/react-ui import, and the Tailwind setup
- `tailwind.config.js` - Tailwind configuration (`darkMode`, theme extensions)

### @xynolog/react-ui Style Organization
- `@xynolog/react-ui/styles/` - Main styles directory
  - `index.css` - Entry point that imports all styles, including component-level CSS
  - `variables.css` - Design tokens and CSS custom properties
  - `base/` - Reset and semantic utility classes
  - `core/` - Fundamental UI elements
    - `buttons.css`, `toggles.css`, `progress.css`, `sliders.css`
    - `inputs.css`, `checkboxes.css`, `textareas.css`, `selects.css`, `forms.css`
    - `badges.css`, `tags.css`, `indicators.css`
  - `patterns/` - Shared panel and card structures
  - `panels/` - History and user panel styles
  - `motivations/` - W3C Web Annotation standard (5 motivation styles)
  - `features/` - Feature-specific styling
  - `layout/` - Page and container layouts
  - `utilities/` - Accessibility and interaction helpers
