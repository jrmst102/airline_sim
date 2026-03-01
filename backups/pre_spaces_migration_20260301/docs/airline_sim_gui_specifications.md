# Airline Competitive Strategy Simulation
## GUI Specifications

**Project:** airline_sim  
**Resolution Target:** 1440 x 900 (Primary Layout Standard)  
**Aspect Ratio:** 16:10  
**Design Philosophy:** Structured, data-driven, decision-centric interface optimized for classroom and laptop environments.

---

# 1. Design Objectives

The GUI must:

- Fit entirely within 1440 x 900 without vertical scrolling during decision entry.
- Keep strategic KPIs visible at all times.
- Minimize cognitive overload.
- Support rapid comparison of competitive metrics.
- Maintain consistency across all modules.

The interface should reflect a professional strategic dashboard (clean, analytical, executive-style).

---

# 2. Global Layout Structure

## 2.1 Overall Grid

- **Header (Top Bar):** 90px height
- **Sidebar (Left Navigation):** 260px width
- **Main Content Area:** Flexible width (~900px usable area)
- **Right Insight Panel (Optional but Recommended):** 190px width

Layout Model:

```
-----------------------------------------------------
| Header (90px)                                     |
-----------------------------------------------------
| Sidebar | Main Content Area | Insight Panel       |
| 260px   | ~900px            | ~190px              |
-----------------------------------------------------
```

No horizontal scrolling permitted.

---

# 3. Header Specifications

Height: 90px  
Background: Dark (e.g., #1F2937 or similar)  
Text: White or light gray

## Required Components

Left:
- Simulation Name
- Company Name

Center:
- Current Round
- Total Rounds
- Phase (Decision / Results / Closed)

Right:
- Cash Balance
- Market Share
- Net Profit
- Alert Icon (warnings, deadlines)

All KPIs must update dynamically.

---

# 4. Sidebar Navigation

Width: 260px  
Background: Slightly lighter than header  
Font Size: 14–15px  
Icons: 18–20px aligned left

## Navigation Items

1. Home
2. Enter Decisions
3. Display Current Decisions
4. Move to Next Round
5. Display Round Results
6. Display End Results
7. Industry Report
8. Change Parameters (Live)
9. Backup Simulation
10. Restore Simulation
11. End Simulation
12. Destroy Simulation

Active page indicator must be visually distinct.

---

# 5. Main Content Area

Maximum Width: ~900px  
Padding: 20px internal margin  
Section spacing: 20px vertical  
Card spacing: 15px

All sections must use a consistent "Card" design:

Card Structure:
- Title (16px bold)
- Divider line
- Content area

Cards must not exceed 420px height to avoid vertical overflow.

---

# 6. Insight Panel (Right Panel)

Width: ~190px  
Purpose: Real-time strategic indicators

## Components

- Mini Market Share Chart
- Cost Structure Snapshot
- Competitor Price Average
- Demand Forecast
- Strategic Position Indicator

Charts should be compact (max 160px height).

Panel must remain visible during scrolling inside main content (sticky behavior).

---

# 7. Decision Entry Screens

## 7.1 Table Design

- Row Height: 36px
- Header Row: Slight background shading
- Numeric fields right-aligned
- Editable fields clearly differentiated

## 7.2 Input Components

- Sliders for pricing
- Numeric input boxes for quantities
- Dropdowns for strategic posture
- Toggle switches for binary decisions

Every decision entry must immediately update projected KPIs on screen.

---

# 8. Typography Standards

Primary Font: Inter / Roboto / System UI  

- Header Titles: 20px bold
- Section Titles: 16px bold
- Body Text: 14px
- Table Text: 13–14px
- KPI Numbers: 16–18px bold

Line height: 1.4–1.6

---

# 9. Color System

## Primary Colors

- Primary Accent: Deep Blue (#2563EB or similar)
- Success: Green (#16A34A)
- Warning: Amber (#F59E0B)
- Danger: Red (#DC2626)
- Neutral Background: Light Gray (#F3F4F6)

## Rules

- Use color only for strategic meaning.
- Avoid decorative colors.
- Maintain high contrast for accessibility.

---

# 10. Charts & Visualizations

Charts must:

- Be simple and legible.
- Avoid 3D effects.
- Use consistent axis scales across rounds.
- Display tooltips on hover.

Recommended Chart Types:

- Line Chart → Profit trend
- Bar Chart → Market share comparison
- Stacked Bar → Cost breakdown
- Radar Chart → Competitive positioning

Maximum chart height: 300px

---

# 11. Responsiveness Requirements

Primary Target: 1440 x 900  
Secondary Compatibility: 1280 x 800 (minimum)

At 1280 x 800:
- Insight panel collapses into toggle drawer
- Sidebar reduces to icon-only mode
- No layout breakage permitted

---

# 12. Usability Requirements

- No more than 3 clicks to reach any core module
- Autosave every 30 seconds during decision entry
- Confirmation modal before ending or destroying simulation
- Undo Round must be accessible only if allowed by parameters

---

# 13. Accessibility Requirements

- Contrast ratio ≥ 4.5:1
- All buttons keyboard accessible
- Tooltips for all icons
- Charts must include numeric summaries

---

# 14. Performance Requirements

- Page load under 1 second (local CSV environment)
- Instant KPI recalculation (<200ms)
- No full-page reload between modules

---

# 15. Design Principles Summary

The GUI must embody:

- Strategic clarity
- Quantitative precision
- Minimal distraction
- Professional executive dashboard aesthetic

The interface should feel like a real competitive strategy control room rather than a classroom tool.

---

End of File.

