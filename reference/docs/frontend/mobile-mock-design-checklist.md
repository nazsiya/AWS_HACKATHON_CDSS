# Android Mobile App — Mock Design Checklist

Use this checklist before development. Complete the mock design, get agreement, then implement against it.

---

## 1. Screens to design (priority set: 1–9 + offline)

| # | Screen | Fidelity | Notes |
|---|--------|----------|--------|
| 1 | **Login** | Wireframe | Email/phone + password, Sign in, optional biometric icon |
| 2 | **Language selector** | Wireframe | 7 languages: Hindi, English, Tamil, Telugu, Bengali, Marathi, Gujarati (pills/chips) |
| 3 | **App shell (home)** | Wireframe | Bottom nav (Triage, Hospitals, Dashboard, More), top bar + role badge, **offline banner** slot |
| 4 | **Triage Step 1 — Patient info** | Wireframe | Age, gender, location (GPS), optional history/allergies |
| 5 | **Triage Step 2 — Symptoms** | Wireframe | Multi-select + free text, duration, severity; optional voice button |
| 6 | **Triage Step 3 — Vitals** | Wireframe | HR, BP, temp, SpO2, respiratory rate, consciousness (AVPU) |
| 7 | **Triage Step 4 — Result** | **Low-fi** | Severity badge, confidence ring/%, actions, disclaimers, override; &lt;85% → “Flag for doctor review” |
| 8 | **Triage report** | Wireframe | Summary; primary CTA: “Proceed to Hospital Matching” |
| 9 | **Hospital match** | **Low-fi** | Top 3 cards: name, distance/ETA, beds, specialist, match score; “Navigate” per card |
| — | **Offline state** | Wireframe | “OFFLINE MODE — LIMITED FUNCTIONALITY” + last sync; where it sits (e.g. under top bar) |

**Out of scope for first mock:** Navigation screen, RMP dashboard, guidance overlay, learning (wireframe later if needed).

---

## 2. Wireframes (main flow)

- [ ] **Login** — Layout: logo/title, email/phone field, password field, Sign in button, biometric placeholder.
- [ ] **Language selector** — Layout: title, 7 language pills in 2 rows or list; “Continue” or auto-into shell.
- [ ] **App shell** — Layout: top bar (title + role badge + optional menu), main content area, bottom nav (4 items), reserved strip for offline banner.
- [ ] **Triage Step 1** — Layout: step indicator (1/4), form fields (age, gender, location with GPS hint, optional history/allergies), Next.
- [ ] **Triage Step 2** — Layout: step indicator (2/4), symptom multi-select, free-text area, duration, severity, optional voice button, Next.
- [ ] **Triage Step 3** — Layout: step indicator (3/4), vitals inputs (HR, BP, temp, SpO2, resp rate, AVPU), Next / Assess.
- [ ] **Triage report** — Layout: severity summary, key findings, “Proceed to Hospital Matching” primary button.
- [ ] **Offline banner** — Placement and content: full-width strip under top bar; text “OFFLINE MODE — LIMITED FUNCTIONALITY” + last sync time.

---

## 3. Low-fi mockups (result + hospital cards)

- [ ] **Triage result screen (Step 4)**
  - Severity badge: 🔴 Critical / 🟠 High / 🟡 Medium / 🟢 Low (use exact colors).
  - Confidence: ring or % (e.g. 0–100%).
  - Recommended actions: 3–5 bullet lines.
  - Safety disclaimers: visible block (e.g. small text, icon).
  - Low-confidence state: show “Treat as HIGH priority” + “Flag for doctor review”.
  - Buttons: Override (secondary), Proceed to Report or to Hospital Match (primary).
- [ ] **Hospital match screen**
  - Top 3 cards; each card: hospital name, distance/ETA, bed availability (e.g. bar or number), specialist on-call (Y/N or icon), match score (e.g. ring or %).
  - Per card: “Navigate” button.
  - Optional: sort/filter (wireframe-level is enough).

---

## 4. Design principles (apply everywhere)

- [ ] **Tone:** Medical-grade, calm, trustworthy (no playful or noisy UI).
- [ ] **Severity colors:** Critical `#DC2626`, High `#EA580C`, Medium `#D97706`, Low `#16A34A` (or product tokens).
- [ ] **Safety:** Disclaimers always visible on triage result; low confidence (&lt;85%) clearly surfaced as high priority + “Flag for doctor review”.
- [ ] **Offline:** Banner does not block primary actions; clear “OFFLINE MODE” and last sync.
- [ ] **Localization:** All labels/buttons suitable for 7 languages (flexible text length, e.g. Hindi).
- [ ] **Accessibility:** Touch targets ≥ 48dp, readable font size, sufficient contrast.

---

## 5. Deliverables and format

Choose one or both; tick when done.

| Deliverable | Format | Owner |
|------------|--------|--------|
| **Wireframes (screens 1–6, 8 + offline)** | Figma / Penpot / PDF / paper photos | |
| **Low-fi mockups (screens 7, 9)** | Figma / PDF / image exports | |
| **Checklist / spec doc** | This markdown file, updated with “Done” and links to files | |

**Handoff:** Dev implements from wireframes + low-fi mockups + this checklist. No high-fi required for first release.

**Suggested location in repo:**  
- Figma: link in this doc or in `docs/frontend/README.md`.  
- Exports: e.g. `emergency-medical-triage/frontend/mobile-android/design/` (create when adding assets).

---

## 6. Sign-off before development

- [ ] Product/stakeholder reviewed wireframes (main flow).
- [ ] Product/stakeholder reviewed low-fi (triage result + hospital cards).
- [ ] Design principles and severity/offline/safety behavior agreed.
- [ ] Deliverables and format agreed (Figma vs doc vs both).
- [ ] Dev has access to all artifacts and this checklist.

---

## 7. After mock design — development order

Once this checklist is signed off, implement in this order (see `android-mobile-plan.md`):

1. **Phase 1** — Project + design system + app shell + offline banner.  
2. **Phase 2** — Auth + language (screens 1–2).  
3. **Phase 3** — Triage wizard + result + report (screens 4–8).  
4. **Phase 4** — Hospital match + navigation + handoff (screen 9 + nav screen).  
5. **Phase 5** — RMP dashboard, guidance, learning (later wireframes if needed).

---

*Last updated: add date when you complete or change this checklist.*
