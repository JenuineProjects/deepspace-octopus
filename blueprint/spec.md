# DeepSpace — Focus Timer Desktop App Blueprint

## Master Intent
One-click-start focus timer desktop app. User clicks a single button and enters a distraction-free focus session.

## Core Requirements
1. **One-Click Start**: Single button launches a focus session (default 25 min Pomodoro)
2. **Timer Engine**: Countdown timer with configurable duration, pause/resume, and session completion
3. **Distraction Blocker**: Block distracting websites/apps during focus sessions (mocked for MVP)
4. **Session State Machine**: idle → focusing → paused → completed (clean transitions, no orphaned states)
5. **Desktop UI**: System tray presence, minimal always-on-top window showing time remaining
6. **Session History**: Track completed sessions with timestamps

## Technical Constraints
- Python with tkinter (cross-platform, no heavy dependencies)
- Fully self-contained and runnable with `python main.py`
- Mock any external APIs or OS-level blocking (simulate blocker behavior)
- No install steps beyond Python 3.8+

## UI Schema
- Main window: minimal, always-on-top capable
- States: idle (shows "Start Focus" button), focusing (shows countdown + pause button), paused (shows resume/stop), completed (shows stats + restart)
- System tray icon with quick actions
- Clean, dark theme

## Architecture
```
main.py          — Entry point, launches app
timer.py         — Timer engine (countdown, state machine)
blocker.py       — Distraction blocker (mocked)
ui.py            — Tkinter UI layer
session_store.py — Session history (JSON file)
```

## Quality Gates (Reviewer Checklist)
- [ ] Runs with single command: `python main.py`
- [ ] One click starts a focus session
- [ ] No memory leaks (no orphaned timers/threads)
- [ ] All state transitions handled (no invalid states)
- [ ] Blocker activates on focus start, deactivates on stop/complete
- [ ] Graceful shutdown (cleanup on window close)
