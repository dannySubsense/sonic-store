# UI Specification: Horizon 1 — Derivative Feature Indicators
**Version:** 1.1
**Date:** 2026-04-16
**Status:** DRAFT
**Author:** @ui-spec-writer
**Inputs:** specs/horizon-1/01-REQUIREMENTS.md (US-04, AC-10), specs/horizon-1/02-ARCHITECTURE.md (Sections 7, 4.2), specs/05-SONIC-ALPHA.md (Layer 2 table), ui/index.html, ui/app.js, ui/style.css

---

## 1. Scope

### In Scope (the four additions)

1. **BPM sparkline** — inline line chart showing BPM trajectory across the last N=10 chunks, positioned adjacent to the existing BPM readout in `#feature-dashboard`.
2. **Energy sparkline** — same treatment for `rms_energy`, positioned adjacent to the existing Energy readout.
3. **Spectral direction arrow** — a single directional symbol (upward / downward / rightward) derived from `spectral_trend`, positioned adjacent to the existing Spectral centroid readout.
4. **Energy regime pill** — a small colored badge showing the `energy_regime` string value, positioned adjacent to the existing Energy readout (alongside the sparkline).

All four elements are read-only display widgets. None of them require user interaction.

**AC-10 (BPM trajectory visibility):** The requirement that BPM trajectory be visible in the UI (AC-10 in 01-REQUIREMENTS.md) is satisfied by the BPM sparkline's visible slope. No separate BPM direction arrow is needed or added.

### Explicitly NOT in Scope

- No new pages, tabs, or routes.
- No layout restructuring or reordering of existing sections (`#panel-visual`, `#panel-chroma`, `#panel-ai`).
- No interactive chart zooming, panning, or tooltips (beyond static ones noted below).
- No historical session playback controls.
- No per-indicator drill-down views.
- No configuration UI for window size N or thresholds.
- No dark/light mode changes.
- No new canvases beyond the inline sparkline elements.
- No indicators beyond the four defined here (chroma_entropy, chroma_volatility, key_stability, onset_regularity, bpm_volatility, energy_momentum are all out of scope for the UI in Horizon 1).

---

## 2. Data Contract

### Source

The UI consumes the extended WebSocket payload defined in **02-ARCHITECTURE.md Section 7.2 (Schema #3 — FeatureMessage-v2)**:

```
{
  "type": "features",
  "data": FeatureVector,          // Layer 1, 20 keys
  "indicators": IndicatorDict | null  // Layer 2, or null during warm-up
}
```

The `"indicators"` field is `null` when `compute_indicators` returns `{"available": false, ...}` (i.e., fewer than N=10 chunks in history). Once sufficient history accumulates, `indicators` is a populated dict.

### Field Mapping Per Element

| UI Element | Primary Field | Source Object | Notes |
|------------|--------------|---------------|-------|
| BPM sparkline | `bpm` (scalar, current chunk) | `msg.data` | Client accumulates chunk-by-chunk into rolling buffer |
| Energy sparkline | `rms_energy` (scalar, current chunk) | `msg.data` | Client accumulates chunk-by-chunk into rolling buffer |
| Spectral direction arrow | `spectral_trend` (float) | `msg.indicators` | Null when indicators unavailable |
| Energy regime pill | `energy_regime` (string) | `msg.indicators` | Null when indicators unavailable |

### Client-Side History Buffer for Sparklines

The sparklines do NOT read a pre-computed trail from `msg.indicators`. They maintain their own client-side rolling buffer, updated on every `features` message regardless of indicator availability. The implementation maintains one circular buffer per sparkline, capped at a fixed display length of 10 entries. On each incoming `features` message, the current `data.bpm` and `data.rms_energy` values are appended to their respective buffers. This means sparkline data begins populating from chunk 1 — before indicators are available — giving the user immediate visual feedback on the signal shape, even in the "warming up" state.

The sparkline buffer size is **fixed at 10 entries and does NOT track the server's `HORIZON1_WINDOW_N`**. `HORIZON1_WINDOW_N` is env-overridable on the server; the UI's buffer is a hardcoded display constant. If the server operates at a different N (via env override), the UI sparkline still shows the last 10 chunks received. This mismatch is acceptable for Horizon 1 — the sparkline is a trajectory display, not a replication of the server's computation window.

### Indicator Availability Signal

`msg.indicators === null` is the canonical cold-start signal from the server (02-ARCHITECTURE.md Section 7.2). The UI uses this as the gate:
- `indicators === null` → show warming-up state for arrow and pill.
- `indicators !== null` → read `indicators.spectral_trend` and `indicators.energy_regime` for arrow and pill.

The sparklines do NOT depend on `indicators` availability — they render from `msg.data` at all times.

---

## 3. Element Specifications

### 3.1 BPM Sparkline

**Visual description**

A narrow inline line chart rendered in a small inline `<canvas>` element. The canvas is no taller than the existing `.feature-value` text height (approximately one line of text, roughly 20px rendered height). Width spans the available space to the right of the BPM numeric value, within the existing `.feature-row` layout. The line traces the sequence of BPM values in the buffer from left (oldest) to right (newest). No axes, no tick marks, no labels — the sparkline is a pure shape indicator. Line color is neutral (matches the existing `#4f4` green used for energy bar fill), consistent with the dashboard's established data-active color.

**Placement**

Inside the existing `.feature-row` for BPM in `#feature-dashboard`:

```
[ BPM label ]  [ numeric value ]  [ sparkline canvas ]
```

The sparkline sits to the right of `#val-bpm` in the same flex row. No new row or section is added.

**Data binding**

On each `features` message: append `msg.data.bpm` to the BPM sparkline buffer (max 10 entries, oldest entry dropped when full). Redraw the sparkline canvas with `requestAnimationFrame` on each update, consistent with existing canvas draw calls in `handleFeatureMessage`. The sparkline's visible slope over the 10-entry window is the mechanism by which BPM trajectory is visible in the UI, satisfying AC-10.

**Transitions and animation**

The sparkline redraws on every incoming chunk. No explicit animation beyond the natural cadence of chunk arrival (~2s). No interpolation between points — draw straight line segments connecting data points. The line shifts left as new data arrives (oldest point drops off the left edge).

**Empty / cold-start state (chunks 1-9)**

The sparkline begins rendering immediately from chunk 1. With fewer than 10 data points in the buffer, the sparkline draws only the available points from the left edge, leaving the right portion of the canvas blank (filled with background color). This is informative: the user sees the line "growing" rightward as data accumulates. No "warming up" text on the sparkline itself — the partial line is self-explanatory and avoids text clutter in the compact row.

**Error state**

If `msg.data.bpm` is missing or not a finite number, skip the buffer append and do not redraw. The sparkline retains the previous state. This should not occur in normal operation given the v1 FeatureVector contract.

---

### 3.2 Energy Sparkline

**Visual description**

Identical treatment to the BPM sparkline. Same size, same line style, same canvas approach. Traces `rms_energy` values (range 0.0 to 1.0). Because `rms_energy` is bounded to [0, 1], the sparkline's y-axis maps the canvas height directly to this range (0.0 = bottom, 1.0 = top) with no additional normalization needed.

**Placement**

Inside the existing `.feature-row` for Energy in `#feature-dashboard`, to the right of `#val-energy` and to the left of the regime pill (see 3.4):

```
[ Energy label ]  [ bar ]  [ numeric value ]  [ sparkline canvas ]  [ regime pill ]
```

The existing energy bar (`#bar-energy`) and numeric value (`#val-energy`) remain in place. The sparkline and pill are additions to the same flex row.

**Data binding**

On each `features` message: append `msg.data.rms_energy` to the energy sparkline buffer (max 10 entries). Redraw with `requestAnimationFrame`.

**Transitions and animation**

Same as BPM sparkline. Redraws on every chunk. No interpolation.

**Empty / cold-start state**

Same as BPM sparkline: partial line growing from left as data accumulates.

**Error state**

Same as BPM sparkline: if value missing or non-finite, retain previous state, skip append.

---

### 3.3 Spectral Direction Arrow

**Visual description**

A single Unicode directional character displayed as a text element adjacent to the spectral centroid readout. Three possible symbols:
- `↑` (upward arrow) — `spectral_trend` is positive and above SPECTRAL_TREND_BRIGHTENING_THRESHOLD (50 Hz/step)
- `↓` (downward arrow) — `spectral_trend` is negative and below SPECTRAL_TREND_DARKENING_THRESHOLD (-50 Hz/step)
- `→` (rightward arrow) — `spectral_trend` is within the threshold band (neutral / stable)

Color rule:
- `↑` rendered in a bright accent color (distinct from neutral) to signal brightening
- `↓` rendered in a dimmed or cooler color to signal darkening
- `→` rendered in the same neutral gray used for existing `.feature-label` text (`#888`) — neutral condition should not visually shout

Size: same font size as existing `.feature-value` elements (approximately 16px), so the arrow reads at the same visual weight as the numeric value beside it.

**Placement**

Inside the existing `.feature-row` for Spectral in `#feature-dashboard`, immediately after `#val-spectral`:

```
[ Spectral label ]  [ numeric value ]  [ direction arrow ]
```

The arrow element (`<span id="arrow-spectral">`) is appended to the existing row. No new row or section.

**Text tooltip / label**

Because the arrow's meaning is not immediately obvious to a demo viewer, the element carries a `title` attribute with a plain-text description. The `title` renders as a browser tooltip on hover. The tooltip text is derived from the current state:
- `↑` → `title="Spectral centroid brightening"`
- `↓` → `title="Spectral centroid darkening"`
- `→` → `title="Spectral centroid stable"`

This satisfies accessibility requirement: color and symbol alone are insufficient; the tooltip provides text context (see Section 5).

**Data binding**

Read `msg.indicators.spectral_trend` on each `features` message. Apply threshold comparison to determine which symbol to display. **Decision (resolves OQ-UI-02):** The UI hardcodes the threshold literals directly in `app.js` as `const SPECTRAL_TREND_BRIGHTENING_THRESHOLD = 50; // SYNC WITH src/features/thresholds.py` and `const SPECTRAL_TREND_DARKENING_THRESHOLD = -50; // SYNC WITH src/features/thresholds.py`. If threshold values change in `src/features/thresholds.py`, the matching literals in `app.js` must be updated manually. Exposing thresholds via the `/status` endpoint is explicitly out of scope for Horizon 1.

**Transitions and animation**

The arrow symbol and color update immediately on each message. No animation. No smoothing — a single threshold crossing causes an immediate symbol swap. This is intentional: the arrow should be a crisp signal, not a gradual transition.

**Empty / cold-start state (indicators === null)**

When `msg.indicators === null`, the arrow element displays `—` (em dash) in the neutral gray color. No arrow direction is shown. The tooltip becomes `title="Warming up — need more history"`. This tells the demo viewer the system is collecting data, without presenting a misleading directional signal.

**Error state**

If `indicators` is non-null but `indicators.spectral_trend` is `null` or non-finite, treat as cold-start: display `—`. This covers any mid-session anomaly (should not occur after warm-up per the architecture, but the fallback is defined).

---

### 3.4 Energy Regime Pill

**Visual description**

A small inline badge element (a `<span>` with a visually distinct background) positioned to the right of the energy sparkline within the Energy feature row. The pill always contains its text label in full — the text label is the primary encoding (not color alone). Three states:

| State | Text | Color rule |
|-------|------|------------|
| `"rising"` | `rising` | Background in a warm/positive tone (e.g., a muted green tint) |
| `"falling"` | `falling` | Background in a cool/warning tone (e.g., a muted amber or red tint) |
| `"stable"` | `stable` | Background in a neutral tone (e.g., the dashboard's dark gray) |

Shape: rounded pill, compact — text-sized height, enough horizontal padding to make the background visually distinct from the surrounding row. Inherits the dashboard's monospace font.

**Placement**

Inside the existing `.feature-row` for Energy, to the right of the energy sparkline:

```
[ Energy label ]  [ bar ]  [ numeric value ]  [ sparkline canvas ]  [ regime pill ]
```

The flex row expands to accommodate both sparkline and pill. No new row or section.

**Data binding**

Read `msg.indicators.energy_regime` on each `features` message. The string value (`"rising"` / `"falling"` / `"stable"`) directly sets the pill's text content and drives the color rule.

**Transitions and animation**

The pill text and background update immediately on regime change. A brief CSS transition on the background color is acceptable (200ms ease) to soften the swap — this matches the existing energy bar's `transition: width 0.2s ease` pattern. The text itself updates without animation.

**Empty / cold-start state (indicators === null)**

When `msg.indicators === null`, the pill displays `warming up` text in the neutral style (no distinctive background color — same appearance as the `stable` neutral state but with placeholder text). This communicates to the demo viewer that the regime signal is not yet available.

**Error state**

If `indicators` is non-null but `energy_regime` is `null` or an unexpected string, fall back to the neutral/stable visual with an empty or `—` label. The pill should never crash or disappear — it always occupies its space in the row.

---

## 4. User Flow — Extended Demo Perception

The core demo flow is unchanged from v1: user starts mic (or hits Demo), audio ingestion runs, features are extracted, a generation prompt is built, MusicGen produces a clip, the clip becomes playable. The following narrates what a viewer or musician additionally perceives with the four new elements.

**Pre-session (page load, no data)**

All four new elements are in their empty state. BPM and Energy sparklines are blank canvases. The spectral arrow shows `—`. The regime pill shows `warming up`. The existing numeric readouts show `--`. The existing status indicator shows `Disconnected` until the WebSocket connects.

**Chunks 1-2 (early data, no indicators yet)**

After starting the mic or demo, the first feature messages arrive. The numeric readouts (`#val-bpm`, `#val-energy`, etc.) immediately populate with live values. The BPM sparkline begins drawing: chunk 1 places a single point at the left edge. The energy sparkline places a single point for `rms_energy`. The spectral arrow remains `—` (indicators still null). The regime pill remains `warming up`. The viewer sees the system processing audio even before indicators are ready — the sparklines are already moving.

**Chunks 3-9 (partial sparkline, still warming up)**

The sparklines grow rightward with each chunk. By chunk 5, the BPM sparkline has 5 points forming a visible line shape. The viewer can already see whether BPM is steady, rising, or jagged — even before Layer 2 indicators are computed. The spectral arrow and regime pill remain in warm-up state.

**Chunk 10 (indicators first appear)**

At chunk 10, the server has enough history to compute indicators. For the first time, `msg.indicators` is non-null. The UI simultaneously:
1. The spectral direction arrow transitions from `—` to one of `↑` / `↓` / `→` based on the first computed `spectral_trend`.
2. The regime pill transitions from `warming up` to one of `rising` / `falling` / `stable` with the appropriate color, based on `energy_regime`.

This is a visible moment in the demo: the indicators "light up" together, signaling that the system now has enough context to describe trajectory. A demo presenter can narrate: "Now the system has 10 chunks — it understands where the music is going."

**Chunks 11+ (live trajectory tracking)**

All four elements update continuously with each chunk (~2s cadence):
- The BPM sparkline scrolls: newest value enters at the right, oldest drops off the left.
- The energy sparkline scrolls the same way.
- If the musician accelerates tempo, the BPM sparkline slopes upward over several chunks. `delta_bpm` eventually crosses the threshold, and if the generation prompt reflects "accelerating," the prompt display (existing `#ai-prompt` element) will show a v2 prompt string with trajectory language.
- If energy is rising, the regime pill shows `rising` in its warm color. When energy plateaus or decreases, the pill transitions to `stable` or `falling` with a brief background transition.
- If the musician shifts to a brighter register, the spectral arrow flips from `→` to `↑`, signaling the timbre change.

**Generation message arrival**

When a `generation` message arrives (unchanged from v1), the `#ai-prompt` element updates with the v2 prompt string. For sessions past chunk 10, this string may include trajectory phrases such as "building energy, accelerating, harmonically stable in D minor." The viewer sees the connection between what the indicators show (regime pill = rising, sparkline trending up) and what the prompt says. This is the demo's key perceptual moment: the system is not just reading a snapshot — it's reading direction.

---

## 5. Accessibility and Affordance Notes

**Color alone is not sufficient.** The regime pill always shows text (`rising`, `falling`, `stable`) as its primary encoding. Color is a secondary reinforcement. A viewer who cannot distinguish colors reads the word. This satisfies AC-10's implicit display requirement and addresses the Scope constraint.

**Direction arrow meaning is not universally obvious.** The arrow's `title` attribute provides a hover tooltip with plain text (`"Spectral centroid brightening"` etc.). This is the minimum viable text affordance without adding layout space. For a demo setting, this is sufficient — the presenter can verbally label the arrow during explanation.

**Sparklines are display-only.** They have no interactivity and require no keyboard focus. They are decorative indicators, not interactive controls. No ARIA labels are required beyond what the surrounding `<span>` labels already provide via the `.feature-label` element in the same row.

**The warm-up state is always named.** The regime pill says `warming up` (not blank or invisible). The spectral arrow shows `—` (not nothing). A viewer immediately understands the system is initializing, not broken. Blank elements are ambiguous; named states are not.

---

## 6. v2 Prompt String Display

The existing prompt display is `<div id="ai-prompt">` in `#panel-ai`. In `app.js`, the `handleGenerationMessage` function sets:

```javascript
aiPrompt.textContent = data.prompt;
```

This is a plain string assignment. The v2 prompt builder output is a single natural-language string (no JSON, no newlines, no special tokens — per AC-08 and FR-03j). The existing `aiPrompt.textContent` assignment handles this transparently: a longer string with trajectory phrases ("building energy, accelerating") will simply render as longer text in the same `<div>`.

**No changes to the prompt display element are needed.** The v2 prompt renders correctly in the existing element for the following reasons:
- The element has no fixed height constraint in `style.css` — it will expand if the string is longer.
- `font-style: italic` and `color: #aaa` already give the prompt text a visually distinct presentation.
- The natural-language trajectory phrases are grammatically consistent with the existing prompt format and need no special badging or highlighting.

The UI spec takes no action on the prompt display. The implementation should verify that `#ai-prompt` has no `overflow: hidden` or line-clamp applied that would truncate longer v2 prompt strings. Based on the current `style.css` (no height or overflow constraints on `#ai-prompt`), this is confirmed: no issue.

---

## 7. Screens and Component Hierarchy

There is a single screen: the existing SonicStore dashboard. Horizon 1 makes no new screens.

### Layout Structure (unchanged, with additions annotated)

```
┌────────────────────────────────────────────────────────────────┐
│ Header: SonicStore title | Start / Stop / Demo controls | status│
├────────────────────────────────────────────────────────────────┤
│ Error banner (hidden unless error)                              │
├─────────────────────────────┬──────────────────────────────────┤
│ #panel-visual               │                                  │
│  ┌───────────────────────┐  │                                  │
│  │ Waveform canvas       │  │ #feature-dashboard               │
│  └───────────────────────┘  │  BPM     [value] [SPARKLINE NEW] │
│                             │  Key     [value]                 │
│                             │  Energy  [bar] [value]           │
│                             │          [SPARKLINE NEW]         │
│                             │          [REGIME PILL NEW]       │
│                             │  Spectral [value] [ARROW NEW]    │
│                             │  Onset   [value]                 │
├─────────────────────────────┴──────────────────────────────────┤
│ #panel-chroma: Chroma Heatmap canvas (unchanged)               │
├────────────────────────────────────────────────────────────────┤
│ #panel-ai: AI Response                                         │
│   [model banner]                                               │
│   [prompt text — now may include trajectory phrases]           │
│   [Play button] [gen time]                                     │
└────────────────────────────────────────────────────────────────┘
```

### Component Hierarchy (additions only)

```
#feature-dashboard
├── .feature-row (BPM)
│   ├── .feature-label "BPM"                [existing]
│   ├── #val-bpm .feature-value             [existing]
│   └── #sparkline-bpm <canvas>             [NEW — inline sparkline]
│
├── .feature-row (Key)                      [unchanged]
│
├── .feature-row (Energy)
│   ├── .feature-label "Energy"             [existing]
│   ├── #bar-energy > #bar-fill             [existing]
│   ├── #val-energy .feature-value          [existing]
│   ├── #sparkline-energy <canvas>          [NEW — inline sparkline]
│   └── #regime-pill <span>                 [NEW — text pill]
│
├── .feature-row (Spectral)
│   ├── .feature-label "Spectral"           [existing]
│   ├── #val-spectral .feature-value        [existing]
│   └── #arrow-spectral <span>              [NEW — direction symbol + title]
│
└── .feature-row (Onset)                    [unchanged]
```

---

## 8. State Visibility

| State | Visible In | Updated By | Cadence |
|-------|------------|------------|---------|
| `msg.data.bpm` | `#val-bpm` (existing), `#sparkline-bpm` (new) | WS `features` message | Each chunk (~2s) |
| `msg.data.rms_energy` | `#val-energy`, `#bar-fill` (existing), `#sparkline-energy` (new) | WS `features` message | Each chunk (~2s) |
| `msg.data.spectral_centroid_hz` | `#val-spectral` (existing) | WS `features` message | Each chunk (~2s) |
| `msg.indicators.spectral_trend` | `#arrow-spectral` (new) | WS `features` message | Each chunk (~2s) |
| `msg.indicators.energy_regime` | `#regime-pill` (new) | WS `features` message | Each chunk (~2s) |
| `indicators === null` | `#arrow-spectral` → `—`, `#regime-pill` → `warming up` | WS `features` message | While history < N=10 |
| Client BPM buffer (10-entry) | `#sparkline-bpm` | Client append on each `features` message | Each chunk (~2s) |
| Client energy buffer (10-entry) | `#sparkline-energy` | Client append on each `features` message | Each chunk (~2s) |

---

## 9. Interaction Patterns

There are no new interaction patterns in Horizon 1. All four new elements are read-only display widgets.

| Trigger | Component | Behavior |
|---------|-----------|---------|
| WS `features` message received | All four new elements | Update data binding, redraw sparklines, update arrow symbol and pill text/color |
| `indicators === null` in message | `#arrow-spectral`, `#regime-pill` | Show warm-up state; sparklines continue updating normally |
| `indicators !== null` in message | `#arrow-spectral`, `#regime-pill` | Show live indicator values; warm-up state clears |
| WS disconnect | All elements | Retain last known state; existing reconnect logic applies |

---

## 10. Out of Scope

This section is an explicit non-goals declaration to prevent scope creep in the forge sprint:

- No new pages or views.
- No interactive chart zooming, panning, brushing, or time-range selection on sparklines.
- No historical session playback or replay controls.
- No per-indicator drill-down (e.g., clicking the regime pill does not open a detail view).
- No configuration UI for window size N or threshold values.
- No dark/light mode toggle or theme changes.
- No display of indicators beyond the four defined: `chroma_entropy`, `chroma_volatility`, `key_stability`, `onset_regularity`, `bpm_volatility`, and `energy_momentum` do not appear in the UI in Horizon 1.
- No animated gauge or radial chart for any indicator.
- No audio-reactive visual effects (pulsing, beat-synchronization) on the new elements.
- No export or copy-to-clipboard of indicator data.
- No display of the raw float values for `spectral_trend` or `energy_momentum` — only the derived representations (arrow symbol, regime string).
- No serving of threshold values via `/status` or any endpoint (OQ-UI-02 resolved: hardcoded in `app.js`).

---

## 11. Open Questions

**OQ-UI-01: Sparkline canvas sizing within the existing flex row**

The `.feature-row` is a flex row with `gap: 8px` and no explicit width constraint on `.feature-value` beyond its content. The sparkline canvas needs a defined width (e.g., 60-80px) to fit alongside the existing elements without causing the row to overflow the `#feature-dashboard` container (`min-width: 200px`). The implementation should verify that adding sparkline + arrow/pill does not push the dashboard wider than the containing `#panel-visual` flex layout. If space is tight, the sparkline canvas can be made narrower (down to ~40px) without losing visual utility at 10 data points. This is an implementation sizing call — the spec does not prescribe pixel values.

**OQ-UI-02: Threshold values in UI code — RESOLVED**

Decision: The UI hardcodes the spectral direction threshold literals directly in `app.js` as:
```javascript
const SPECTRAL_TREND_BRIGHTENING_THRESHOLD = 50;  // SYNC WITH src/features/thresholds.py
const SPECTRAL_TREND_DARKENING_THRESHOLD = -50;   // SYNC WITH src/features/thresholds.py
```
If threshold values change in `src/features/thresholds.py`, the matching literals in `app.js` must be updated manually. Exposing thresholds via the `/status` endpoint is explicitly out of scope for Horizon 1. The sync comment is mandatory in the implementation.

**OQ-UI-03: Energy row flex layout with four elements**

The Energy `.feature-row` now contains five elements: label, bar, numeric value, sparkline, and regime pill. The existing `display: flex; gap: 8px` layout will attempt to fit all five in a single row. Depending on actual rendered widths, this may require the Energy row to wrap or the bar to shrink. The implementer should verify the layout renders cleanly on the demo hardware screen resolution and adjust only if visual overflow occurs. The spec's intent is a single row — wrapping is acceptable as a fallback if single-row layout is not achievable without CSS restructuring.

---

*UI Specification by: @ui-spec-writer*
*Inputs: specs/horizon-1/01-REQUIREMENTS.md, specs/horizon-1/02-ARCHITECTURE.md, specs/05-SONIC-ALPHA.md, ui/index.html, ui/app.js, ui/style.css*
*Locked by: TD Decision OQ-07*
