# Terminal Painter

A simple Kitty Graphics Protocol demo that turns your terminal into a tiny paint
canvas. It speaks directly to Kitty-compatible terminals (Kitty, WezTerm,
Ghostty) and lets you draw with the mouse using an RGBA framebuffer.

## Requirements
- Python 3.9+ (standard library only)
- A terminal that implements the Kitty Graphics Protocol
  - Kitty
  - WezTerm
  - Ghostty

## Quick start
1. Launch the application inside a Kitty-compatible terminal:
   ```bash
   python3 kitty_painter.py
   ```
2. Drag with the **left mouse button** to paint.
3. Press `c` to clear the canvas.
4. Press `q` (or `Ctrl-C`) to quit.

## How it works
- The script keeps an in-memory 32-bit RGBA buffer (`640×400` by default).
- Mouse events are captured via SGR 1006 reporting (`\x1b[?1003h\x1b[?1006h`).
- Each brush stroke is rasterised into the framebuffer and re-sent through the
  Kitty Graphics Protocol using inline base64 chunks (≤4096 bytes).
- The image is scaled to fill the current terminal grid so pointer positions map
  consistently to pixels.

## Customisation
Adjust the defaults in `CanvasConfig` inside `kitty_painter.py` to tune:
- `width` / `height` of the canvas
- `background` colour (RGBA tuple)
- `brush_color` and `brush_radius`

The script is intentionally compact so you can extend it with colour palettes,
layering, dirty-rect updates, shared-memory transfers, or saving snapshots.
