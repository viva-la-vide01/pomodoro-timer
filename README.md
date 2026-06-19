# Pomodoro Timer

A beautiful desktop Pomodoro timer built with Python and tkinter. Zero external dependencies — runs on any Windows machine out of the box.

## Features

- **Three modes** — Focus (25 min) / Short Break (5 min) / Long Break (15 min)
- **Auto-switch** — Automatically cycles between focus and break sessions; every 4 focus sessions triggers a long break
- **Circular progress ring** — Visual countdown with smooth arc animation
- **Task list** — Add, complete, and delete tasks for the current focus session
- **Session counter** — Track daily pomodoro count with visual dots
- **Sound notification** — Dual-beep alert when a session ends (uses `winsound`)
- **Always-on-top** — Pin the window above other applications
- **Customizable settings** — Adjust durations, intervals, auto-start behavior, and volume
- **History** — View daily pomodoro counts (last 90 days retained)
- **Keyboard shortcuts** — Full control without touching the mouse

## Screenshots

```
   +----------------------------------+
   |   Pin                 -  □  ✕   |
   +----------------------------------+
   |    Focus  | Short Break|Long Break|
   |                                  |
   |          +----------+            |
   |         /    25:00   \           |
   |        |   Ready to   |          |
   |         \   start    /           |
   |          +----------+            |
   |                                  |
   |        o o o o   4 dots          |
   |                                  |
   |    [Reset] [▶ Start] [Skip]     |
   |                                  |
   |   Current Task                   |
   |   [Add task...            ] [+]  |
   |   o Buy groceries                |
   |   o Code review          x       |
   |                                  |
   |              [⚙] [📊]            |
   +----------------------------------+
```

## Quick Start

### Option 1: Run the EXE (No Python required)

1. Download `PomodoroTimer.exe` from the [Releases](https://github.com/viva-la-vide01/pomodoro-timer/releases) page
2. Double-click to run

### Option 2: Run from source

```bash
git clone https://github.com/viva-la-vide01/pomodoro-timer.git
cd pomodoro-timer/pomodoro-timer
python pomodoro.py
```

Requires Python 3.x (no extra packages needed).

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Space` | Start / Pause |
| `R` | Reset current session |
| `S` | Skip current session |
| `1` | Switch to Focus mode |
| `2` | Switch to Short Break mode |
| `3` | Switch to Long Break mode |

## Data Storage

All settings and history are stored as JSON files in `%USERPROFILE%\.pomodoro_timer\`:

- `settings.json` — User preferences (durations, intervals, volume, etc.)
- `history.json` — Daily pomodoro counts and task lists (90-day retention)

## Build from Source

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name PomodoroTimer --clean pomodoro.py
```

The executable will be in `dist/PomodoroTimer.exe`.

## Tech Stack

- **Language**: Python 3.9+
- **GUI**: tkinter (standard library)
- **Sound**: winsound (Windows built-in)
- **Data**: JSON files (standard library)
- **Packaging**: PyInstaller

## License

MIT
