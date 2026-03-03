# DeepSpace — System Architecture

> **Design Agent**: Red-Orange Designer
> **Date**: 2026-03-03
> **Note**: Researcher market brief was not available at design time. Architecture proceeds from the master intent (absolute simplicity, zero-configuration, one-click start) and the designer's own competitive analysis.

---

## 1. High-Level Component Map

```
┌─────────────────────────────────────────────────────────┐
│                     DeepSpace App Shell                 │
│                                                         │
│  ┌───────────┐  ┌──────────────┐  ┌──────────────────┐ │
│  │  UI Layer  │  │ Notification │  │  Tray / Daemon   │ │
│  │ (Screens)  │◄─┤   System     │  │  (background)    │ │
│  └─────┬──────┘  └──────┬───────┘  └────────┬─────────┘ │
│        │                │                    │           │
│  ┌─────▼────────────────▼────────────────────▼─────────┐│
│  │                  Event Bus / Message Layer           ││
│  └──┬──────────┬──────────────┬──────────────┬─────────┘│
│     │          │              │              │           │
│  ┌──▼───┐ ┌───▼────────┐ ┌──▼───────┐ ┌───▼────────┐  │
│  │Timer │ │Distraction  │ │AI Sprint │ │ Session    │  │
│  │Engine│ │Blocker      │ │Planner   │ │ Store      │  │
│  └──────┘ └─────────────┘ └──────────┘ └────────────┘  │
└─────────────────────────────────────────────────────────┘
```

All components communicate through a central **Event Bus**. Components are decoupled: any component can be replaced or disabled without breaking the others. The app must boot and function even if the AI Sprint Planner has no API key configured (graceful degradation).

---

## 2. Component Specifications

### 2.1 Timer Engine

**Responsibility**: Owns all timing state. The single source of truth for "what phase are we in?"

**State Machine**:

```
                    ┌─────────┐
         ┌─────────│  IDLE   │◄──────────────────┐
         │         └────┬────┘                    │
         │              │ START (one-click or     │
         │              │ with goal)              │
         │         ┌────▼─────┐                   │
         │    ┌───►│ FOCUSING │───── PAUSE ──┐    │
         │    │    └────┬─────┘              │    │
         │    │         │                ┌───▼───┐│
         │  RESUME      │ TIMER_DONE     │PAUSED ││
         │    │         │                └───┬───┘│
         │    │    ┌────▼─────┐              │    │
         │    └────│  BREAK   │◄─────────────┘    │
         │         └────┬─────┘   (resume goes    │
         │              │          to break if     │
         │              │ BREAK_DONE timer done   │
         │              │          while paused)   │
         │    ┌─────────▼──────────┐              │
         │    │ Has next sprint?   │              │
         │    │  YES → FOCUSING    │              │
         │    │  NO  → COMPLETED   │              │
         │    └────────┬───────────┘              │
         │        ┌────▼──────┐                   │
         └────────│ COMPLETED │───────────────────┘
                  └───────────┘       (auto after 3s
                                       or on dismiss)
```

**Interface**:

| Method / Event         | Direction | Description                                      |
|------------------------|-----------|--------------------------------------------------|
| `start(goal?: string)` | In        | Transition IDLE → FOCUSING. Goal is optional.    |
| `pause()`              | In        | FOCUSING → PAUSED                                |
| `resume()`             | In        | PAUSED → FOCUSING (or BREAK if timer expired)    |
| `skip()`               | In        | FOCUSING → BREAK, or BREAK → next FOCUSING       |
| `abort()`              | In        | Any → IDLE. Saves partial session.               |
| `onTick(remaining_ms)` | Out       | Emitted every second on the Event Bus.           |
| `onStateChange(state)` | Out       | Emitted on every state transition.               |

**Configuration (with defaults)**:

| Parameter       | Default  | Notes                        |
|-----------------|----------|------------------------------|
| `focus_duration`| 25 min   | Classic Pomodoro             |
| `short_break`   | 5 min    | After each sprint            |
| `long_break`    | 15 min   | After every 4th sprint       |
| `auto_start_break` | true | Break starts automatically   |
| `auto_start_next`  | false| Next sprint requires a click |

---

### 2.2 Distraction Blocker

**Responsibility**: Prevents access to distracting websites during FOCUSING state. Automatically activates/deactivates based on Timer Engine state changes.

**Strategy — Hosts-file approach (primary)**:

```
Timer Engine                   Distraction Blocker             OS Hosts File
     │                              │                              │
     │──onStateChange(FOCUSING)────►│                              │
     │                              │──Write blocked domains──────►│
     │                              │  (redirect to 127.0.0.1)    │
     │                              │                              │
     │──onStateChange(BREAK/IDLE)──►│                              │
     │                              │──Restore original hosts─────►│
     │                              │                              │
```

**Fallback strategy — Local proxy**: If the app lacks OS-level write permissions, fall back to a local proxy server that intercepts HTTP requests and returns a "You're in a focus session" page for blocked domains.

**Data flow**:

1. On FOCUSING: Blocker reads `blocklist` from Settings, writes entries to hosts file (or activates proxy).
2. On BREAK or IDLE: Blocker restores the original hosts file (or deactivates proxy).
3. Blocker keeps a backup of the original hosts file before any modification.
4. On crash recovery: a startup routine checks for and cleans stale blocks.

**Default blocklist** (ships with app, user never needs to configure):

```
social: [twitter.com, x.com, facebook.com, instagram.com, reddit.com, tiktok.com]
video: [youtube.com, netflix.com, twitch.tv]
news: [news.ycombinator.com, cnn.com, bbc.com/news]
```

**Interface**:

| Method / Event             | Direction | Description                                |
|----------------------------|-----------|--------------------------------------------|
| `activate(blocklist)`      | In        | Start blocking listed domains              |
| `deactivate()`             | In        | Stop blocking, restore original state      |
| `isActive() → boolean`    | Out       | Current blocking status                    |
| `onBlockedAttempt(domain)` | Out       | Emitted when a user hits a blocked domain  |

---

### 2.3 AI Sprint Planner

**Responsibility**: Takes a free-text user goal and breaks it into a sequence of 25-minute sprint cards using an LLM API.

**Data flow**:

```
User types goal ──► AI Sprint Planner ──► LLM API (cloud)
                         │
                         ▼
                   Sprint Card Queue
                   [card1, card2, card3, ...]
                         │
                         ▼
                   Timer Engine reads
                   current card from queue
```

**Graceful degradation**: If no API key is configured, or if the API call fails, the planner returns a single generic sprint card: `{ title: "Focus Sprint", description: <the raw goal or "Deep work session"> }`. The app never blocks on AI availability.

**Interface**:

| Method / Event                         | Direction | Description                                    |
|----------------------------------------|-----------|------------------------------------------------|
| `planSprints(goal: string) → Sprint[]` | In/Out    | Async. Returns ordered sprint cards.           |
| `isAvailable() → boolean`             | Out       | Whether the LLM API is configured and reachable |

**LLM Prompt Strategy** (guidance for implementer):

The system prompt should instruct the LLM to:
- Break the goal into concrete, actionable tasks each completable in ~25 minutes.
- Return structured JSON (array of `{title, description, estimated_minutes}`).
- Cap at 8 sprints per goal (avoid overwhelm).
- Each sprint title should start with an action verb.

---

### 2.4 Session Store

**Responsibility**: Persists session history, sprint completions, streaks, and user settings. Local-first, file-based (JSON or SQLite — implementer's choice).

**Data flow**:

```
Timer Engine ──onStateChange──► Session Store
                                     │
                                     ├── writes session record on completion/abort
                                     ├── updates streak counter
                                     └── exposes history for UI queries

Settings UI ──save──► Session Store ──► flat file / DB
```

**Interface**:

| Method                                        | Direction | Description                                  |
|-----------------------------------------------|-----------|----------------------------------------------|
| `saveSession(session: Session)`               | In        | Persist a completed or aborted session       |
| `getSessions(filter?) → Session[]`            | Out       | Query session history                        |
| `getStats() → Stats`                          | Out       | Aggregate stats (total focus time, streaks)  |
| `getSettings() → Settings`                    | Out       | Load user settings                           |
| `saveSettings(settings: Settings)`            | In        | Persist user settings                        |
| `getBlocklist() → Blocklist`                  | Out       | Load blocklist (default + user customizations)|

---

### 2.5 Notification System

**Responsibility**: Delivers alerts at session boundaries. Uses OS-native notifications plus optional audio cues.

**Triggers**:

| Timer State Transition     | Notification                              |
|----------------------------|-------------------------------------------|
| IDLE → FOCUSING            | "Focus session started. Let's go."        |
| FOCUSING → BREAK           | "Sprint done! Take a break."              |
| BREAK → FOCUSING           | "Break's over. Ready for the next sprint?"|
| Any → COMPLETED            | "All sprints complete. Great work!"        |
| `onBlockedAttempt(domain)` | Subtle in-app toast: "Blocked: {domain}"  |

**Interface**:

| Method                          | Direction | Description                         |
|---------------------------------|-----------|-------------------------------------|
| `notify(type, message, options)`| In        | Send a notification                 |
| `setQuietMode(boolean)`        | In        | Suppress audio / visual alerts      |

---

## 3. Event Bus — Central Communication

All inter-component messaging flows through a publish/subscribe Event Bus. This keeps components decoupled.

**Event catalog**:

| Event Name            | Payload                                    | Publisher        | Subscribers                         |
|-----------------------|--------------------------------------------|------------------|-------------------------------------|
| `timer:stateChange`   | `{ from, to, session_id }`                | Timer Engine     | UI, Blocker, Notifications, Store   |
| `timer:tick`           | `{ remaining_ms, elapsed_ms, phase }`     | Timer Engine     | UI                                  |
| `blocker:activated`    | `{ domain_count }`                        | Blocker          | UI                                  |
| `blocker:deactivated`  | `{}`                                      | Blocker          | UI                                  |
| `blocker:attempt`      | `{ domain, timestamp }`                   | Blocker          | Notifications, Store                |
| `planner:result`       | `{ sprints: Sprint[] }`                   | AI Planner       | UI, Timer Engine                    |
| `planner:error`        | `{ error_message }`                       | AI Planner       | UI (shows fallback)                 |
| `session:saved`        | `{ session_id }`                          | Store            | UI (history refresh)                |
| `settings:changed`     | `{ key, value }`                          | Store            | All (react to setting changes)      |

---

## 4. Startup Sequence (One-Click-Start Flow)

This is the critical path that delivers on the "zero-configuration" promise:

```
1. App launches
2. Session Store loads settings (or creates defaults on first run)
3. Blocker checks for stale blocks from a previous crash → cleans up
4. UI renders IDLE screen: single "Start Focus" button + collapsed goal field
5. User clicks "Start Focus"
   5a. IF goal field is empty:
       - Timer Engine starts with default 25-min focus, no sprint cards
       - Blocker activates with default blocklist
   5b. IF goal field has text:
       - AI Sprint Planner runs async
       - Timer Engine starts IMMEDIATELY (does not wait for AI)
       - When planner returns, sprint cards populate the UI
       - If planner fails, a single generic card is shown
6. Notification fires: "Focus session started."
7. Session is active. User sees countdown.
```

**Key design decision**: The timer NEVER waits for the AI planner. The planner enriches the experience but is not on the critical path. This guarantees one-click-start latency is near-zero.

---

## 5. Crash Recovery & Edge Cases

| Scenario                          | Behavior                                                  |
|-----------------------------------|-----------------------------------------------------------|
| App crashes during FOCUSING       | On next launch, detect orphaned session, offer to resume  |
| Hosts file left dirty             | Startup cleanup routine restores backup                   |
| LLM API key missing               | Planner returns generic card; app works fully             |
| LLM API timeout                   | Same as missing key — graceful fallback                   |
| User closes app during session    | Treat as abort; save partial session; clean hosts file    |
| System sleep during focus         | Pause timer; resume on wake                               |

---

## 6. Security & Permissions

- **Hosts file modification** requires elevated/admin privileges. The app should request elevation only when the blocker is first activated, not on startup.
- **API keys** for the LLM are stored locally in the settings file. The implementer should use OS-native credential storage where available.
- **No telemetry**. All data stays local unless the user explicitly opts into cloud sync (future feature, not in v1).

---

## 7. Progressive Disclosure Architecture

Features are organized into tiers:

| Tier    | Visible By Default | Features                                         |
|---------|--------------------|--------------------------------------------------|
| **T0**  | Always             | Start button, countdown, break timer              |
| **T1**  | On hover / expand  | Goal input, sprint card display, session stats    |
| **T2**  | In settings        | Custom blocklist, timer durations, notification prefs |
| **T3**  | Deep settings      | API key config, proxy mode, export data           |

The UI renders T0 by default. Users discover T1-T3 naturally through interaction.
