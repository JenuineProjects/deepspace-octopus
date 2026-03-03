# DeepSpace — Phase 1 Blueprint

> Synthesized by Purple Manager | 2026-03-03
> Sources: @researcher market-brief.json, @designer system-architecture.md + ui-schema.json

---

## 1. Product Vision

**DeepSpace** is a minimalist desktop application that blocks distracting websites and uses AI to break large user goals into 25-minute actionable sprints.

**Master Intent:** Absolute simplicity and zero-configuration. The user starts a focus session in exactly one click.

**Core Thesis (from Research):** Configuration IS the distraction. Every settings screen consumes the same prefrontal cortex resources the user is trying to protect. The competitive moat is simplicity itself.

---

## 2. Competitive Landscape Summary

Eight productivity apps were analyzed. The data reveals a clear pattern:

| App | Config Complexity | Onboarding Friction | User Base |
|-----|:-:|:-:|---|
| Forest | 3/10 | 2/10 | Top app in 136 countries, 2M+ paying |
| Flow | 3/10 | 2/10 | 500K+ users |
| Endel | 2/10 | 2/10 | Strong dev adoption |
| Serene | 7/10 | 7/10 | Limited adoption |

**Conclusion:** Lower friction = larger user base. Every competitor with friction above 5/10 struggles with adoption. DeepSpace targets 1/10 on both axes.

**Key psychological backing:** Decision fatigue, paradox of choice, Zeigarnik effect, and flow state research all confirm that pre-work configuration actively undermines focus. The 23-minute refocus cost means even 5 minutes of setup can waste 40% of a 25-minute sprint.

---

## 3. Architecture Overview

Five decoupled components communicating through a central Event Bus:

```
┌─────────────────────────────────────────────────────┐
│                  DeepSpace App Shell                 │
│                                                      │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ UI Layer │  │ Notification │  │ Tray / Daemon │  │
│  └────┬─────┘  └──────┬───────┘  └──────┬────────┘  │
│       │               │                 │            │
│  ┌────▼───────────────▼─────────────────▼──────────┐ │
│  │              Event Bus / Message Layer           │ │
│  └──┬─────────┬──────────────┬─────────────┬───────┘ │
│     │         │              │             │         │
│  ┌──▼───┐ ┌──▼──────────┐ ┌▼──────────┐ ┌▼───────┐ │
│  │Timer │ │ Distraction │ │AI Sprint  │ │Session │ │
│  │Engine│ │ Blocker     │ │Planner    │ │Store   │ │
│  └──────┘ └─────────────┘ └───────────┘ └────────┘ │
└─────────────────────────────────────────────────────┘
```

### 3.1 Timer Engine
- State machine: IDLE → FOCUSING → PAUSED → BREAK → COMPLETED
- Default 25-min focus / 5-min short break / 15-min long break (every 4th sprint)
- Thread-safe, all state transitions explicit and validated

### 3.2 Distraction Blocker
- Primary: hosts-file approach (redirect blocked domains to 127.0.0.1)
- Fallback: local proxy for environments without admin access
- Ships with sensible default blocklist (social, video, news — 17 domains)
- User never needs to configure a blocklist
- Crash recovery: startup routine detects and cleans stale blocks

### 3.3 AI Sprint Planner
- Takes free-text goal, calls LLM API, returns up to 8 sprint cards
- **Critical design decision:** Timer NEVER waits for the AI planner. The planner enriches the experience but is not on the critical startup path.
- Graceful degradation: no API key = generic sprint card. App works fully without AI.

### 3.4 Session Store
- Local-first, file-based persistence (JSON or SQLite)
- Tracks sessions, sprint completions, streaks, and settings
- Thread-safe with atomic writes

### 3.5 Notification System
- OS-native notifications at session boundaries
- Optional audio cues
- Subtle in-app toasts for blocked domain attempts

---

## 4. UI Blueprint

### 4.1 Design Philosophy
- **Progressive Disclosure:** T0 (always visible) = start button + timer. T1-T3 features hidden until needed.
- **Dark-first:** Deep space theme (#0A0E1A background, #6366F1 accent)
- **One interaction to value:** First sprint starts within 30 seconds of first launch

### 4.2 Screens

| Screen | State | Key Elements |
|--------|-------|-------------|
| **Home** | IDLE | "Start Focus" button (hero), collapsed goal input, ghost history/settings icons |
| **Focus** | FOCUSING | Hero countdown timer with progress ring, sprint card (if AI available), pause button (Space), subtle abort (X) |
| **Focus (Paused)** | PAUSED | Frosted glass overlay, resume button, auto-aborts after 30 min idle |
| **Break** | BREAK | Lighter visual tone, break countdown, next sprint preview, "Start Next Sprint" option |
| **Completed** | COMPLETED | "Great work!" message, session stats, auto-dismisses after 10s |
| **History** | HISTORY | Session log list, streak/stats summary bar |
| **Settings** | SETTINGS | Tiered disclosure sections (Timer, Blocker, AI, Notifications, Data) |

### 4.3 Keyboard Shortcuts
- **Enter** — Start Focus (from idle)
- **Space** — Pause / Resume (during focus)
- **Escape** — Back / Dismiss

### 4.4 Window Spec
- Default: 400x500px, resizable, always-on-top option
- System tray presence for background awareness

---

## 5. Data Models

Five core schemas defined:

| Model | Purpose | Key Fields |
|-------|---------|-----------|
| **Session** | Full focus session record | id, goal, status, total_focus_ms, sprints[], blocked_attempts[] |
| **SprintCard** | AI-generated task card | title (action-verb-first), description, estimated_minutes, order |
| **SprintRecord** | Outcome of a sprint | sprint_card_id, status (completed/skipped/aborted), actual_focus_ms |
| **Settings** | User preferences (all with defaults) | timer config, blocker config, AI config, notification prefs |
| **Blocklist** | Default + custom blocked domains | categories (social, video, news, custom), disabled_categories |

---

## 6. One-Click-Start Critical Path

This is the sequence that delivers on the master intent:

```
1. App launches → loads settings (or creates defaults)
2. Blocker checks for stale blocks from previous crash → cleans up
3. UI renders: single "Start Focus" button + collapsed goal field
4. User clicks "Start Focus"
   → Timer starts immediately (25 min default)
   → Blocker activates with default blocklist
   → AI planner runs async in background (if goal entered + API configured)
   → Notification: "Focus session started"
5. User is focusing. Total elapsed time: < 1 second from click.
```

**The timer never waits for AI.** The planner enriches but never blocks.

---

## 7. Research-Backed Design Decisions

| Decision | Research Basis |
|----------|---------------|
| Zero-config default | Iyengar jam study: 10x activation with fewer choices |
| AI as invisible config layer | Endel's zero-config model: AI handles personalization, UI stays simple |
| 30-second time-to-value | Duolingo's 60s-to-value drives retention; DeepSpace halves it |
| Auto blocklist (no user config) | Freedom's predefined lists are its most praised feature |
| Sprint cards as implementation intentions | Gollwitzer research: concrete plans reduce cognitive load |
| Adaptive enforcement (future) | Opal's three-tier model, but automatic instead of user-configured |

---

## 8. Lateral Triggers Integrated

The researcher flagged 5 patterns with high applicability. Integration status:

| Trigger | Pattern | Integrated Into |
|---------|---------|----------------|
| LT-001 | Endel's zero-config AI model | AI Sprint Planner design (async, graceful degradation) |
| LT-002 | Duolingo's 60s-to-value | One-click-start critical path (< 30s target) |
| LT-003 | Forest's emotional stakes | Noted for v2 (space-themed ambient visualization) |
| LT-004 | Opal's adaptive enforcement | Noted for v2 (auto-escalating block strength) |
| LT-005 | Flow's ambient timer | Window spec includes always-on-top + system tray |

---

## 9. Technical Constraints

- **Language-agnostic:** Architecture does not dictate implementation language
- **Stdlib-first:** Minimize external dependencies
- **Python 3.8+ compatible** if Python is chosen
- **Local-first:** All data stays on device. No telemetry.
- **Admin elevation:** Only requested when blocker first activates, not on startup

---

## 10. Open Questions for Build Phase

1. **Implementation language:** Python (tkinter) for rapid prototyping, or Electron/Tauri for richer UI?
2. **AI provider default:** OpenAI, Anthropic, or local LLM for sprint planning?
3. **Hosts file vs proxy:** Which blocker strategy to implement first?
4. **Scope for v1:** Include AI sprint planner in first build, or ship timer + blocker first?

---

## 11. Recommendation

Proceed to Build Phase with a **two-stage approach:**

**Stage 1 (MVP):** Timer engine + distraction blocker + UI. One-click-start with zero AI dependency. Validate the core loop.

**Stage 2 (Enhancement):** Add AI sprint planner, session history, and progressive disclosure settings.

This mirrors the master intent: ship the simplest thing that delivers value, then layer intelligence on top.

---

*Awaiting human principal approval to proceed to Build Phase.*
