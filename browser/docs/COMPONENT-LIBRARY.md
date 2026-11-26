# Component Library Integration Guide

## Overview

The Xynolog Browser leverages **`@xynolog/react-ui`**, a framework-
agnostic React component library, reusable across different
applications and frameworks. This document
explains the package boundary, what lives where, and how the Browser
composes the library.

## Architecture

### Separation of Concerns

```
┌─────────────────────────────────────┐
│         browser               │
│    (Vite + React Router v7)         │
│                                     │
│  • Routing & pages                  │
│  • Authentication wiring            │
│  • i18next                          │
│  • App-specific composition         │
└─────────────┬───────────────────────┘
              │ uses
              ▼
┌─────────────────────────────────────┐
│    packages/typescript/react-ui                │
│  (Framework-agnostic library)       │
│                                     │
│  • UI components                    │
│  • Flow state units (RxJS)          │
│  • Providers and hooks              │
│  • API integration                  │
│  • Semantic CSS (BEM)               │
└─────────────────────────────────────┘
```

### What Lives in `@xynolog/react-ui`

#### Components
- **Core UI** — Toolbar, StatusDisplay, Toast
- **Resource viewer** — ResourceViewer, ResourceViewerPage
- **Annotation system** — panels (Comments, References, Tags, Assessments, Highlights), entry components, popups
- **Navigation** — NavigationMenu, SkipLinks, SimpleNavigation, CollapsibleResourceNavigation, SortableResourceTab
- **Modals** — SearchModal, ReferenceWizardModal, ResourceGenerateModal, KeyboardShortcutsHelpModal, SessionEndedModal, PermissionDeniedModal, KbIdentityConflictModal
- **Layout** — UnifiedHeader, LeftSidebar, PageLayout
- **Session** — SessionTimer, SessionExpiryBanner
- **Branding** — XynologBranding

#### Hooks and utilities
- `useObservable`, `useShellStateUnit`, `useResourceContent`, `useMediaToken`, `useLineNumbers`, `useHoverDelay`, `useKeyboardShortcuts`, `useToast`, `useSessionExpiry`, `useTheme`
- `useXynolog`, `useEventSubscription`, `useEventSubscriptions`

#### Providers and contexts
- `XynologProvider` — puts the `XynologBrowser` singleton (sessions, KBs, the per-KB `XynologClient`) into context; read via `useXynolog()`
- `TranslationProvider` — pluggable i18n manager
- `AnnotationProvider`, `ResourceAnnotationsProvider` — annotation + workspace state
- `ThemeProvider`, `LineNumbersProvider`, `ToastProvider`, `LiveRegionProvider` — theming, line-number display, toasts, a11y live region

#### Flow state units (from `@xynolog/sdk`, re-exported)
- `createMarkStateUnit`, `createGatherStateUnit`, `createMatchStateUnit`, `createYieldStateUnit`, `createBeckonStateUnit`

#### Page state units (react-ui's own)
- Shell and resource-page composition: `createShellStateUnit`, `createResourceViewerPageStateUnit`

### What Stays in `browser`

#### Routing and app shell
- Vite + React Router v7 routes
- Locale-scoped layouts (`[locale]/know`, `[locale]/moderate`)
- `AuthShell` composition and protected boundaries
- Per-route data loading

#### App-specific pages
- Home
- The sign-in hand-off pages (`auth/connect`, `auth/callback`, `auth/error`)
- Know pages (discover, compose, resource)
- Moderation pages (recent, entity tags, tag schemas)

#### Framework integration
- React Router `Link` component adapter
- Route builders and locale prefixing
- Custom hooks (e.g. `useMergedTranslationManager`) that bridge app state into library providers

## Provider Composition

The Browser mounts library providers directly — there is no app-side
wrapper layer to maintain.

### The Provider Stack

Global providers are mounted once at the app root
(`browser/src/app/providers.tsx`). The `XynologBrowser` singleton
behind `XynologProvider` carries all session state, so there is **no**
per-layout auth/client provider:

```tsx
import { KeyboardShortcutsProvider } from '@/contexts/KeyboardShortcutsContext';
import { NavigationHandler } from '@/components/knowledge/NavigationHandler';
import { useMergedTranslationManager } from '@/hooks/useMergedTranslationManager';

export function Providers({ children }: { children: React.ReactNode }) {
  const translationManager = useMergedTranslationManager();

  return (
    <TranslationProvider translationManager={translationManager}>
      <XynologProvider>            {/* sessions, KBs, the per-KB XynologClient */}
        <ToastProvider>
          <LiveRegionProvider>
            <KeyboardShortcutsProvider>
              <ThemeProvider>
                <LineNumbersProvider>
                  <NavigationHandler />
                  {children}
                </LineNumbersProvider>
              </ThemeProvider>
            </KeyboardShortcutsProvider>
          </LiveRegionProvider>
        </ToastProvider>
      </XynologProvider>
    </TranslationProvider>
  );
}
```

The protected routes share one layout (`ProtectedLayout` in `src/App.tsx`) that mounts
`AuthShell`, which adds the protected error boundary and the session-ended,
permission-denied and KB-identity-conflict modals (they read the active
session's signals):

```tsx
import { Outlet } from 'react-router';
import { AuthShell } from '@/contexts/AuthShell';

function ProtectedLayout() {
  return (
    <AuthShell>
      <Outlet />
    </AuthShell>
  );
}
```

The library owns provider implementations; the Browser owns the
decision about where to mount them. For the provider/session API reference
(props, hooks, behavior), see
[docs' `builder/react-ui/SESSION.md`](https://github.com/xynolog/docs/blob/main/builder/react-ui/SESSION.md).

## Using Library Components

### Basic usage

```tsx
import { Toolbar, ResourceViewer, useXynolog } from '@xynolog/react-ui';
```

Provider-reading components (`Toolbar`, `SearchModal`, `SessionEndedModal`,
anything calling `useXynolog()`) read from the provider stack via hooks — no explicit props
for the client, event bus, or token. Layouts mount providers once; any
component in the subtree has access. The bring-your-own-session ones
(`ResourceViewer`, the annotation panels and their entries) take the
`XynologSession` as a prop instead.

### Subscribing to observable data

Flow VMs and namespace methods return RxJS Observables. The
`useObservable` hook bridges them into React state:

```tsx
import { useXynolog, useObservable } from '@xynolog/react-ui';
import { readyValue } from '@xynolog/sdk';

function ResourceTitle({ resourceId }: { resourceId: ResourceId }) {
  // The client lives on the active session (null until one is active)
  const client = useObservable(useXynolog().activeSession$)?.client;
  const state = useObservable(client?.browse.resource(resourceId)); // CacheState<ResourceDescriptor>
  const resource = state && readyValue(state);
  return <h1>{resource?.name}</h1>;
}
```

Most components reach for a dedicated hook (`useResourceContent`,
`useMediaToken`, the flow state units) rather than reading the client
directly.

Cache invalidation, refetching, and bus-driven updates happen inside
`BrowseNamespace` — the component only sees the current `CacheState`.

### Custom styling

Library components carry semantic CSS class names (BEM-style) with
default styles. Apps layer layout utilities over them; they should not
override component-internal styling.

```tsx
<>
  {/* Good — layout utility only */}
  <Button variant="primary" className="mt-4 w-full">Submit</Button>

  {/* Bad — overrides component styling */}
  <Button variant="primary" className="bg-blue-500">Submit</Button>
</>
```

## Benefits

1. **Framework independence** — `@xynolog/react-ui` works with any React framework (Vite, Next.js, etc.). Nothing in the library imports framework-specific modules.
2. **Consistent design system** — shared components and tokens across apps.
3. **Testing split** — components + flow VMs tested in isolation in react-ui; app tests focus on composition.
4. **Clear dependency direction** — `browser` depends on `@xynolog/react-ui`, never the reverse.
5. **Observable-first** — dynamic state is modeled as RxJS Observables end-to-end, so consumers can compose and transform without framework coupling.

## Development Workflow

### Local development

When developing features that span both packages:

```bash
# Rebuild react-ui after changing it (the Browser consumes its dist/)
npm run build --workspace=@xynolog/react-ui

# Run the Browser
cd browser && npm run dev
```

### Adding components

Decide where the component lives:

- **Framework-agnostic UI, reusable outside the Browser** → `@xynolog/react-ui`.
- **App-specific (routing, auth wiring, feature composition)** → `browser`.

For library components:

1. Create in `packages/typescript/react-ui/src/components/`
2. Export from `packages/typescript/react-ui/src/index.ts`
3. Add tests in `packages/typescript/react-ui/src/components/__tests__/`
4. Add styles in `packages/typescript/react-ui/src/styles/`

For Browser components: create in `browser/src/`, compose
library components as needed, use framework-specific APIs directly.

### Testing strategy

- Unit tests for library components + hooks live in `packages/typescript/react-ui`.
- Integration tests (provider stack, page-level behavior) live in `browser`.
- E2E tests live at the repo root.

## Platform-Agnostic Components

Library components that need framework-specific capabilities accept
them as props rather than importing them. Example — a navigation
component takes the host's `Link` and icon set as props rather than
importing `react-router` or an icon library (condensed from
`src/components/knowledge/KnowledgeNavigation.tsx`):

```tsx
import { CollapsibleResourceNavigation } from '@xynolog/react-ui';
import { PlusIcon, ChevronLeftIcon, Bars3Icon } from '@heroicons/react/24/outline';
import { Link, routes } from '@/lib/routing';

<CollapsibleResourceNavigation
  Link={Link}
  icons={{ chevronLeft: ChevronLeftIcon, bars: Bars3Icon }}
  onNavigate={navigate}
  getResourceHref={(id) => routes.resourceDetail(id)}
  fixedItems={[{ name: 'Compose', href: '/know/compose', icon: PlusIcon }]}
  resources={openResources}
  isCollapsed={isCollapsed}
  currentPath={pathname}
  translations={{ title: 'Knowledge' }}
/>
```

Same pattern for anything that would otherwise force a framework
dependency.

## Troubleshooting

**Styles not loading**: import the package CSS once in your app entry:

```css
@import '@xynolog/react-ui/styles';
```

**Provider errors (`useX must be used within XProvider`)**: check
provider nesting in the layout. Auth-dependent providers must be
inside `AuthShell`.

**Type mismatches after schema changes**: the types are the SDK's. Run
`make generate` in the sdk checkout, then build against it:

```bash
make test-browser SDK_REPO=../sdk
```

## Best Practices

1. **Don't duplicate** — if a component exists in `@xynolog/react-ui`, use it.
2. **Extend, don't override** — add layout classes, not styling overrides.
3. **Mount providers once** — at the layout level, not in components.
4. **Prefer Observables for shared state** — the library uses RxJS for anything dynamic; stay on that rail.
5. **Test at the right level** — unit in react-ui, integration in the Browser.

## Related Documentation

- [`@xynolog/react-ui` README](https://github.com/xynolog/sdk/blob/main/typescript/react-ui/README.md)
- [`@xynolog/react-ui` providers](https://github.com/xynolog/docs/blob/main/builder/react-ui/SESSION.md)
- [`@xynolog/react-ui` architecture](https://github.com/xynolog/sdk/blob/main/typescript/react-ui/docs/ARCHITECTURE.md)
- [API Integration](API-INTEGRATION.md)
- [Browser Architecture](ARCHITECTURE.md)
