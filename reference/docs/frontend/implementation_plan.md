# Emergency Medical Triage — Frontend UI Implementation Plan

## Goal

Build a premium, medical-grade UI for the AI-powered Emergency Medical Triage platform using **Next.js (App Router), TypeScript, Tailwind CSS, and Fetch/Axios** (no heavy UI frameworks). The result must feel professional, calm under pressure, trustworthy, and AI-native — comparable to modern SaaS healthcare products.

> [!IMPORTANT]
> **This is a plan-only document.** No frontend code will be written until the user completes the planning phase via Stitch MCP.

---

## Current State

| Item | Status |
|---|---|
| Framework | Next.js (planned) |
| Language | TypeScript (mandatory) |
| Styling | Tailwind CSS |
| Data Fetching | Fetch / Axios (single abstraction) |
| Backend APIs | Not yet implemented (will use mock data) |

---

## Proposed Changes

The build is organized into **6 phases**, each independently demo-able.

---

### Phase 1 — Foundation: Design System & Shell

> Establish the design tokens, theme engine, global styles, and app shell before any screens.

#### [NEW] [tokens.css](file:///Users/akilanvj/Workspace/Aws_AI_Bharat/emergency-medical-triage/frontend/src/styles/tokens.css)
- CSS custom properties for the entire design system
- **Colors**: Light mode palette (white/soft gray base, medical blues `#2563EB` / greens `#059669`), dark mode palette (charcoal `#1A1D23` surfaces, soft contrast `#242830`, vibrant accents)
- **Severity system**: Critical `#DC2626`, High `#EA580C`, Medium `#D97706`, Low `#16A34A`
- **Typography**: `Inter` from Google Fonts, type scale (12/14/16/18/20/24/32/40px), weights (400/500/600/700)
- **Spacing**: 8pt grid — `--space-1: 4px` through `--space-12: 96px`
- **Radii**: 8px (default), 12px (cards), 16px (modals), 100px (pills)
- **Shadows**: Light mode (subtle box-shadows), dark mode (soft elevation glow via `box-shadow` with accent color)
- **Transitions**: `--transition-fast: 150ms`, `--transition-normal: 250ms`, `--transition-slow: 400ms`

#### [NEW] [global.css](file:///Users/akilanvj/Workspace/Aws_AI_Bharat/emergency-medical-triage/frontend/src/styles/global.css)
- CSS reset / normalize, base body styles, scrollbar styling, selection color
- Font loading (Inter via Google Fonts `<link>`)
- Utility classes: `.sr-only`, `.container`, `.grid-*`, responsiveness breakpoints

#### [NEW] [components.css](file:///Users/akilanvj/Workspace/Aws_AI_Bharat/emergency-medical-triage/frontend/src/styles/components.css)
- **Buttons**: Primary, secondary, ghost, danger variants + disabled + hover/active micro-animations
- **Badges**: Severity badges (Critical/High/Medium/Low) with pulsing animation for Critical
- **Cards**: Hospital card, stat card, info card — subtle shadows (light) / soft glow (dark)
- **Forms**: Input fields, select, textareas, radio/checkbox — clean floating labels, focus ring
- **Tables**: Zebra-striped rows, sticky headers, sortable column indicators
- **Progress ring**: SVG-based circular confidence score visualizer (0–100%)
- **Alerts/Banners**: Offline banner, warning alerts, success toasts
- **Navigation**: Bottom tab bar (mobile), sidebar (desktop), top bar with role badge
- **Modal/Overlay**: Centered overlay with blur backdrop for guidance steps
- **Skeleton loaders**: Shimmer placeholders during API loading

#### [NEW] [theme.js](file:///Users/akilanvj/Workspace/Aws_AI_Bharat/emergency-medical-triage/frontend/src/utils/theme.js)
- Theme toggle (light ↔ dark) via `data-theme` attribute on `<html>`
- Persist preference in `localStorage`, respect `prefers-color-scheme`

#### [NEW] [router.js](file:///Users/akilanvj/Workspace/Aws_AI_Bharat/emergency-medical-triage/frontend/src/utils/router.js)
- Lightweight hash-based SPA router (no library)
- Route definitions mapping to page render functions
- Animated page transitions (fade/slide)

#### [MODIFY] [index.html](file:///Users/akilanvj/Workspace/Aws_AI_Bharat/emergency-medical-triage/frontend/index.html)
- Update `<title>` to "MedTriage AI"
- Add meta description, favicon, Google Fonts `<link>` for Inter
- Add `<meta name="theme-color">` for mobile browsers

#### [MODIFY] [main.js](file:///Users/akilanvj/Workspace/Aws_AI_Bharat/emergency-medical-triage/frontend/src/main.js)
- Bootstrap app: init router, theme, render app shell
- App shell: sidebar/navbar + main content area + offline banner slot

#### [DELETE] [counter.js](file:///Users/akilanvj/Workspace/Aws_AI_Bharat/emergency-medical-triage/frontend/src/counter.js)
#### [DELETE] [javascript.svg](file:///Users/akilanvj/Workspace/Aws_AI_Bharat/emergency-medical-triage/frontend/src/javascript.svg)
#### [MODIFY] [style.css](file:///Users/akilanvj/Workspace/Aws_AI_Bharat/emergency-medical-triage/frontend/src/style.css)
- Replace placeholder styles with import of `tokens.css`, `global.css`, `components.css`

---

### Phase 2 — Auth & Language

#### [NEW] [login.js](file:///Users/akilanvj/Workspace/Aws_AI_Bharat/emergency-medical-triage/frontend/src/pages/login.js)
- Clean login screen: logo, email/phone input, password, "Sign In" button
- Biometric auth placeholder (fingerprint icon button)
- Role indicator after auth (Healthcare Worker / Hospital Staff / Admin)

#### [NEW] [language-selector.js](file:///Users/akilanvj/Workspace/Aws_AI_Bharat/emergency-medical-triage/frontend/src/components/language-selector.js)
- Horizontal pill-style selector at top of screen post-login
- 7 languages: Hindi, English, Tamil, Telugu, Bengali, Marathi, Gujarati
- Persists in `localStorage`

#### [NEW] [auth.js](file:///Users/akilanvj/Workspace/Aws_AI_Bharat/emergency-medical-triage/frontend/src/utils/auth.js)
- Mock auth service (hardcoded users for each role)
- Session management, role-based route guards

---

### Phase 3 — Core Triage Flow (The Star Feature)

#### [NEW] [triage-wizard.js](file:///Users/akilanvj/Workspace/Aws_AI_Bharat/emergency-medical-triage/frontend/src/pages/triage-wizard.js)
- **4-step guided wizard** with animated progress bar + step dots
  1. **Patient Info** — Age, gender, GPS auto-detect, medical history, allergies
  2. **Symptoms** — Multi-select grid + free-text + voice button, duration, severity
  3. **Vital Signs** — HR, BP, temp, SpO2, respiratory rate, consciousness (AVPU)
  4. **AI Results** — Severity badge (animated), confidence ring, model consensus, actions, disclaimers, override button
- Smooth slide transitions, validation per step
- Offline → shows offline triage + `OFFLINE MODE` banner

#### [NEW] [triage-report.js](file:///Users/akilanvj/Workspace/Aws_AI_Bharat/emergency-medical-triage/frontend/src/pages/triage-report.js)
- Structured report view (printable), "Proceed to Hospital Matching" CTA

#### [NEW] [mock-triage.js](file:///Users/akilanvj/Workspace/Aws_AI_Bharat/emergency-medical-triage/frontend/src/data/mock-triage.js)
- Mock AI responses with varied severity/confidence, simulated 1–2s delay

---

### Phase 4 — Hospital Matching & Routing

#### [NEW] [hospital-match.js](file:///Users/akilanvj/Workspace/Aws_AI_Bharat/emergency-medical-triage/frontend/src/pages/hospital-match.js)
- **Card-based** top 3 recommendations: name, distance/ETA, beds bar, specialist status, match score ring, "Navigate" button
- Sort/filter, unavailability state → auto-suggest next

#### [NEW] [navigation.js](file:///Users/akilanvj/Workspace/Aws_AI_Bharat/emergency-medical-triage/frontend/src/pages/navigation.js)
- Map placeholder, floating action panel (ETA, turn-by-turn steps, re-route, change hospital)
- Arrival → "Generate Handoff Report"

#### [NEW] [mock-hospitals.js](file:///Users/akilanvj/Workspace/Aws_AI_Bharat/emergency-medical-triage/frontend/src/data/mock-hospitals.js)
- 5–6 realistic Indian hospital entries with departments, beds, coordinates

---

### Phase 5 — RMP Dashboard & Training

#### [NEW] [rmp-dashboard.js](file:///Users/akilanvj/Workspace/Aws_AI_Bharat/emergency-medical-triage/frontend/src/pages/rmp-dashboard.js)
- Competency score rings, cases/success stats, level badge, achievement row, quick actions, recent cases

#### [NEW] [guidance-overlay.js](file:///Users/akilanvj/Workspace/Aws_AI_Bharat/emergency-medical-triage/frontend/src/components/guidance-overlay.js)
- Slide-up panel: numbered procedural steps, educational callouts, telemedicine escalation

#### [NEW] [learning.js](file:///Users/akilanvj/Workspace/Aws_AI_Bharat/emergency-medical-triage/frontend/src/pages/learning.js)
- Module cards grid, progress bars, achievements, peer leaderboard

---

### Phase 6 — Admin & Hospital Staff Portals

#### [NEW] [admin-dashboard.js](file:///Users/akilanvj/Workspace/Aws_AI_Bharat/emergency-medical-triage/frontend/src/pages/admin-dashboard.js)
- Analytics stat cards, data tables (RMPs, triage logs, audit), outbreak alerts, system health

#### [NEW] [hospital-portal.js](file:///Users/akilanvj/Workspace/Aws_AI_Bharat/emergency-medical-triage/frontend/src/pages/hospital-portal.js)
- Incoming patient alerts, capacity management forms, handoff reports viewer

#### [NEW] [mock-admin.js](file:///Users/akilanvj/Workspace/Aws_AI_Bharat/emergency-medical-triage/frontend/src/data/mock-admin.js)
- Mock analytics, RMP lists, audit logs, system health data

---

## File Structure Summary

```
frontend/
├── index.html                          (MODIFY)
├── package.json
├── public/
│   └── favicon.svg                     (NEW)
├── src/
│   ├── main.js                         (MODIFY)
│   ├── style.css                       (MODIFY)
│   ├── styles/
│   │   ├── tokens.css                  (NEW)
│   │   ├── global.css                  (NEW)
│   │   └── components.css              (NEW)
│   ├── utils/
│   │   ├── theme.js                    (NEW)
│   │   ├── router.js                   (NEW)
│   │   └── auth.js                     (NEW)
│   ├── components/
│   │   ├── language-selector.js        (NEW)
│   │   └── guidance-overlay.js         (NEW)
│   ├── pages/
│   │   ├── login.js                    (NEW)
│   │   ├── triage-wizard.js            (NEW)
│   │   ├── triage-report.js            (NEW)
│   │   ├── hospital-match.js           (NEW)
│   │   ├── navigation.js              (NEW)
│   │   ├── rmp-dashboard.js            (NEW)
│   │   ├── learning.js                 (NEW)
│   │   ├── admin-dashboard.js          (NEW)
│   │   └── hospital-portal.js          (NEW)
│   └── data/
│       ├── mock-triage.js              (NEW)
│       ├── mock-hospitals.js           (NEW)
│       └── mock-admin.js              (NEW)
│   (DELETE counter.js, javascript.svg)
```

**Total: ~25 files** (3 modified, 20 new, 2 deleted)

---

## User Review Required

> [!IMPORTANT]
> **Technology choice**: The current scaffold is **vanilla JS + Vite** (no framework). This plan keeps it framework-free for simplicity and speed. If you'd prefer React, Vue, or another framework, let me know before I start — it would change the file structure significantly.

> [!IMPORTANT]
> **Mock data approach**: Since the backend APIs don't exist yet, all screens will use hardcoded mock data with simulated loading delays. The code structure makes it easy to swap mocks for real `fetch()` calls later.

> [!WARNING]
> **Map integration**: The navigation screen will use a static map placeholder or generated image. A real interactive map (e.g. Google Maps, Leaflet) would require an API key and additional dependency. Should I include a basic Leaflet integration, or keep it as a visual mockup for now?

---

## Verification Plan

### Build Verification
```bash
cd /Users/akilanvj/Workspace/Aws_AI_Bharat/emergency-medical-triage/frontend
npm run build
```
Must succeed with zero errors.

### Browser Verification
After each phase, I will:
1. Run `npm run dev` in the `frontend/` directory
2. Open in the browser and visually verify:
   - All screens render in both **light mode** and **dark mode**
   - Mobile responsive layout at 375px width
   - All interactive elements function correctly
   - Micro-animations and transitions work
   - Severity badges show correct colors
   - Offline banner displays
   - Role-based navigation shows correct menu items
3. Capture screenshots for the walkthrough

### Manual Verification (User)
After implementation, you can:
1. Open the dev server URL in your browser
2. Toggle light/dark mode via the theme switch
3. Walk through the triage wizard (4 steps)
4. Check hospital matching cards and navigation screen
5. Switch roles (RMP / Hospital Staff / Admin) via login
6. Resize browser to mobile width for responsive check
