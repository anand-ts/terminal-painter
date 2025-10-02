# Terminal Painter

Paint directly inside a Kitty-compatible terminal using your mouse. A tiny, dependency‑free pixel canvas rendered via the Kitty Graphics Protocol.


<p align="center">
  <img src="./terminalpainter.gif" alt="Terminal Painter" />
</p>

## Project Summary
Terminal Painter keeps a full RGBA framebuffer client‑side and streams it to the terminal as you draw. It supports continuous brush strokes with interpolated lines, adjustable brush radius, a small color palette, and a status bar with live feedback.

## Key Features

- Mouse painting in the terminal (Kitty protocol)
- Smooth stroke interpolation (disc + line drawing)
- Adjustable brush radius (fine to chunky)
- Cycling color palette with live preview
- Instant full‑frame redraw (double buffered image IDs)
- No external Python dependencies

## Tech Stack

- Python (standard library only)
- Kitty Graphics Protocol (inline image transfer)
- Raw terminal + mouse reporting (SGR / 1006 mode)

## Usage

### 1. Clone
```bash
git clone https://github.com/anand-ts/terminal-painter.git
cd terminal-painter
```

### 2. Run (Python 3.8+ recommended)
```bash
python kitty_painter.py
```

That’s it—there are no packages to install.

## Controls

- q / Ctrl+C  Quit
- c           Next color
- C           Previous color
- [ / ]       Decrease / Increase brush radius (±1)
- { / }       Decrease / Increase brush radius (±5)
- x           Clear canvas
- Mouse drag  Paint stroke

Status line shows current color (hex) and brush radius.

## Requirements

- A Kitty terminal (or another terminal fully supporting the Kitty Graphics Protocol + SGR mouse). Designed and tested with Kitty.
- Python 3.8 or newer.

## Terminal Compatibility

- **Supported**
  - Kitty (reference implementation, full feature set)
  - WezTerm (up-to-date releases; Kitty graphics and mouse reporting enabled)
  - Foot (Wayland builds with Kitty graphics support)
  - Contour (recent builds; Kitty-compatible placements)

- **Unsupported / No Kitty Graphics**
  - iTerm2 (uses OSC 1337 images instead; Kitty sequences ignored)
  - macOS Terminal.app, Hyper (no inline pixel protocol)
  - Alacritty, GNOME Terminal, Konsole, Windows Terminal (text/Sixel only)

> Thinking ahead: detecting Kitty support at startup lets us fall back gracefully. Future versions may add iTerm2's OSC 1337 path, Sixel rendering, or an ASCII preview so more terminals get a usable experience.

## Inspiration
Lightweight nostalgia from classic paint tools (MSPaint era).

---

Fall 2025
