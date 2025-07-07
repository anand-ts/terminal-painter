
import numpy as np
from PIL import Image

class Canvas:
    """
    Manages the drawing canvas, including the pixel buffer and drawing operations.
    """
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.buffer = np.zeros((height, width, 4), dtype=np.uint8)
        self.undo_stack = []
        self.redo_stack = []

    def _save_state(self):
        """Saves the current buffer state for undo."""
        self.undo_stack.append(self.buffer.copy())
        self.redo_stack.clear()

    def undo(self):
        """Restores the previous canvas state."""
        if self.undo_stack:
            self.redo_stack.append(self.buffer.copy())
            self.buffer = self.undo_stack.pop()

    def redo(self):
        """Restores a previously undone canvas state."""
        if self.redo_stack:
            self.undo_stack.append(self.buffer.copy())
            self.buffer = self.redo_stack.pop()

    def draw_brush(self, x, y, brush_size, color):
        """Draws a brush stroke on the canvas."""
        self._save_state()
        for i in range(-brush_size, brush_size + 1):
            for j in range(-brush_size, brush_size + 1):
                if i**2 + j**2 < brush_size**2:
                    px, py = x + i, y + j
                    if 0 <= px < self.width and 0 <= py < self.height:
                        self.buffer[py, px] = color

    def draw_line(self, x1, y1, x2, y2, brush_size, color):
        """Draws a line on the canvas."""
        self._save_state()
        # Bresenham's line algorithm
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy

        while True:
            self.draw_brush(x1, y1, brush_size, color)
            if x1 == x2 and y1 == y2:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x1 += sx
            if e2 < dx:
                err += dx
                y1 += sy

    def draw_rectangle(self, x1, y1, x2, y2, color):
        """Draws a rectangle on the canvas."""
        self._save_state()
        min_x, max_x = sorted((x1, x2))
        min_y, max_y = sorted((y1, y2))
        self.buffer[min_y:max_y, min_x:max_x] = color

    def fill(self, x, y, color):
        """Fills an area with the selected color."""
        self._save_state()
        target_color = tuple(self.buffer[y, x])
        if tuple(color) == target_color:
            return

        q = [(x, y)]
        while q:
            px, py = q.pop(0)
            if (
                0 <= px < self.width and
                0 <= py < self.height and
                tuple(self.buffer[py, px]) == target_color
            ):
                self.buffer[py, px] = color
                q.extend([(px + 1, py), (px - 1, py), (px, py + 1), (px, py - 1)])

    def save_to_png(self, filename="drawing.png"):
        """Saves the canvas to a PNG file."""
        img = Image.fromarray(self.buffer, 'RGBA')
        img.save(filename)
