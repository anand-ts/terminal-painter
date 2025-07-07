import sys
from typing import Optional, Tuple
import time
from asciimatics.screen import Screen
from asciimatics.event import KeyboardEvent, MouseEvent
from asciimatics.exceptions import ResizeScreenError
from asciimatics.scene import Scene
from asciimatics.effects import Effect
from canvas import Canvas
from ui import UIFrame

# Simple 8-colour mapping from RGBA to nearest basic terminal colour index.
def _rgb_to_colour_index(r: int, g: int, b: int) -> int:
    # Threshold values chosen for basic distinction.
    if r > 200 and g > 200 and b > 200:
        return Screen.COLOUR_WHITE
    if r > 200 and g < 100 and b < 100:
        return Screen.COLOUR_RED
    if g > 200 and r < 100 and b < 100:
        return Screen.COLOUR_GREEN
    if b > 200 and r < 100 and g < 100:
        return Screen.COLOUR_BLUE
    if r > 200 and g > 200 and b < 100:
        return Screen.COLOUR_YELLOW
    if r > 200 and b > 200 and g < 100:
        return Screen.COLOUR_MAGENTA
    if g > 200 and b > 200 and r < 100:
        return Screen.COLOUR_CYAN
    return Screen.COLOUR_BLACK

def half_block_render(screen, canvas):
    """Renders the canvas to the screen using half-blocks."""
    # Iterate over character-cell rows. Each cell corresponds to two pixel rows in
    # the canvas: upper (y) and lower (y+1).
    for y in range(0, min(canvas.height - 1, screen.height * 2), 2):
        row = y // 2  # Character-cell row on the Screen.
        for x in range(min(canvas.width, screen.width)):
            upper_pixel = canvas.buffer[y, x]
            lower_pixel = canvas.buffer[y + 1, x]

            fg = _rgb_to_colour_index(int(upper_pixel[0]), int(upper_pixel[1]), int(upper_pixel[2]))
            bg = _rgb_to_colour_index(int(lower_pixel[0]), int(lower_pixel[1]), int(lower_pixel[2]))

            # If both halves share the same colour, draw a full-block for crisper output.
            if fg == bg:
                screen.print_at('█', x, row, colour=fg, bg=bg)
            else:
                screen.print_at('▀', x, row, colour=fg, bg=bg)

class CanvasEffect(Effect):
    """Asciimatics Effect that renders our pixel buffer using half-block chars."""

    def __init__(self, screen: Screen, canvas: "Canvas"):
        super().__init__(screen)
        self._canvas = canvas

    def reset(self):
        # Nothing to reset between scene restarts.
        pass

    def stop_frame(self):
        # Run indefinitely; Scene duration is -1.
        return 0

    def _update(self, frame_no):
        half_block_render(self._screen, self._canvas)

def main(screen):
    canvas_width = screen.width - screen.width // 4
    canvas_height = screen.height * 2  # Two pixel rows per character row
    canvas = Canvas(canvas_width, canvas_height)
    ui = UIFrame(screen, lambda c: setattr(app_state, 'color', c), lambda s: setattr(app_state, 'brush_size', s))

    class AppState:
        def __init__(self):
            self.color = (255, 255, 255, 255)
            self.brush_size = 1
            self.last_mouse_pos: Optional[Tuple[int, int]] = None
            self.drawing = False

    app_state = AppState()

    # Build a Scene containing both the canvas effect and the UI frame.
    canvas_effect = CanvasEffect(screen, canvas)
    screen.set_scenes([Scene([canvas_effect, ui], duration=-1)])

    while True:
        # Event handling ----------------------------------------------------
        event = screen.get_event()

        # Let the UI consume the event first (e.g., button clicks).
        event = ui.process_event(event)

        if isinstance(event, KeyboardEvent):
            if event.key_code in (ord('q'), ord('Q')):
                return
            elif event.key_code == Screen.ctrl("s"):
                canvas.save_to_png()
            elif event.key_code == Screen.ctrl("e"):
                with open("drawing.txt", "w") as f:
                    f.write(screen.get_as_text())
            elif event.key_code == Screen.ctrl("z"):
                canvas.undo()
            elif event.key_code == Screen.ctrl("y"):
                canvas.redo()
        elif isinstance(event, MouseEvent):
            # Determine if the mouse event occurred inside the UI frame. The UI occupies
            # the right-most quarter of the screen, starting at `canvas_width`.
            ui.has_focus = event.x >= canvas_width

            # Convert character coordinates to pixel coordinates for the canvas.
            pixel_x = event.x
            pixel_y = event.y * 2

            if event.buttons == MouseEvent.LEFT_CLICK:
                # Only draw on the canvas if the UI does not have focus.
                if not ui.has_focus:
                    if not app_state.drawing:
                        app_state.drawing = True
                        app_state.last_mouse_pos = (pixel_x, pixel_y)
                        canvas.draw_brush(pixel_x, pixel_y, app_state.brush_size, app_state.color)
                    else:
                        if app_state.last_mouse_pos is not None:
                            canvas.draw_line(
                                app_state.last_mouse_pos[0], app_state.last_mouse_pos[1],
                                pixel_x, pixel_y,
                                app_state.brush_size, app_state.color
                            )
                        app_state.last_mouse_pos = (pixel_x, pixel_y)
            else:
                app_state.drawing = False

        # ------------------------------------------------------------------
        # Draw the next frame for the Scene (canvas effect + UI).
        screen.draw_next_frame()

        # Cap the frame-rate to ~30 FPS to reduce flicker and CPU usage.
        time.sleep(1 / 30)

if __name__ == "__main__":
    while True:
        try:
            Screen.wrapper(main)
            sys.exit(0)
        except ResizeScreenError:
            pass
