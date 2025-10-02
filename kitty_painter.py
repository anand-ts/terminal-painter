#!/usr/bin/env python3
"""Terminal pixel painter for Kitty-compatible terminals.

This script uses the Kitty Graphics Protocol to maintain a simple RGBA canvas
and lets the user paint with the mouse directly inside the terminal window.
"""
import base64
import os
import re
import select
import sys
import termios
import time
import tty
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Union

ESC = "\x1b"
CHUNK = 4096
MOUSE_RE = re.compile(r"^\x1b\[<(\d+);(\d+);(\d+)([mM])")
CSI_RE = re.compile(r"^\x1b\[([0-9;?]*)([@-~])")


Attr = List[Union[int, List[Union[int, bytes]]]]


class RawTerminal:
    """Context manager that switches stdin into raw mode."""

    def __init__(self) -> None:
        self.fd = sys.stdin.fileno()
        self.old_attrs: Optional[Attr] = None

    def __enter__(self) -> "RawTerminal":
        self.old_attrs = termios.tcgetattr(self.fd)
        tty.setraw(self.fd)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.old_attrs is not None:
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old_attrs)


def kitty_send(payload: bytes, control: str) -> None:
    """Send RGBA payload to Kitty using the provided control parameters."""
    data = base64.b64encode(payload).decode("ascii")
    first = True
    idx = 0
    length = len(data)
    while idx < length:
        chunk = data[idx : idx + CHUNK]
        idx += len(chunk)
        more = 1 if idx < length else 0
        if first:
            sys.stdout.write(f"{ESC}_G{control},m={more};{chunk}{ESC}\\")
            first = False
        else:
            sys.stdout.write(f"{ESC}_Gm={more};{chunk}{ESC}\\")
    sys.stdout.flush()


def kitty_delete(image_id: int, placement_id: Optional[int] = None, delete_data: bool = False) -> None:
    delete_key = "I" if delete_data else "i"
    parts = ["a=d", f"d={delete_key}", f"i={image_id}"]
    if placement_id is not None:
        parts.append(f"p={placement_id}")
    sys.stdout.write(f"{ESC}_G{','.join(parts)}{ESC}\\")
    sys.stdout.flush()


def enable_mouse() -> None:
    sys.stdout.write("\x1b[?1003h\x1b[?1006h")
    sys.stdout.flush()


def disable_mouse() -> None:
    sys.stdout.write("\x1b[?1003l\x1b[?1006l")
    sys.stdout.flush()


def hide_cursor() -> None:
    sys.stdout.write("\x1b[?25l")
    sys.stdout.flush()


def show_cursor() -> None:
    sys.stdout.write("\x1b[?25h")
    sys.stdout.flush()


def clear_screen() -> None:
    sys.stdout.write("\x1b[2J\x1b[H")
    sys.stdout.flush()


class EventParser:
    """Incremental parser for raw terminal input."""

    def __init__(self) -> None:
        self.buffer = ""

    def feed(self, data: str) -> List[Tuple[str, Tuple]]:
        self.buffer += data
        events: List[Tuple[str, Tuple]] = []
        while self.buffer:
            head = self.buffer[0]
            if head == "\x1b":
                if self.buffer.startswith("\x1b[<"):
                    match = MOUSE_RE.match(self.buffer)
                    if match is None:
                        break
                    b, x, y, kind = match.groups()
                    self.buffer = self.buffer[match.end() :]
                    events.append(("mouse", (int(b), int(x), int(y), kind)))
                    continue
                csi_match = CSI_RE.match(self.buffer)
                if csi_match is None:
                    break
                seq = csi_match.group(0)
                self.buffer = self.buffer[len(seq) :]
                events.append(("csi", (seq,)))
                continue
            else:
                self.buffer = self.buffer[1:]
                events.append(("char", (head,)))
                continue
        return events


@dataclass
class CanvasConfig:
    width: int = 640
    height: int = 400
    background: Tuple[int, int, int, int] = (12, 12, 12, 255)
    brush_color: Tuple[int, int, int, int] = (255, 102, 0, 255)
    brush_radius: int = 10
    palette: List[Tuple[str, Tuple[int, int, int, int]]] = field(
        default_factory=lambda: [
            ("Orange", (255, 102, 0, 255)),
            ("Sky", (0, 170, 255, 255)),
            ("Lime", (120, 220, 50, 255)),
            ("Magenta", (200, 64, 220, 255)),
            ("White", (240, 240, 240, 255)),
        ]
    )


class RGBAFramebuffer:
    def __init__(self, config: CanvasConfig) -> None:
        self.config = config
        self.width = config.width
        self.height = config.height
        self.data = bytearray(self.width * self.height * 4)
        self.clear()

    def clear(self) -> None:
        fill = bytes(self.config.background)
        self.data[:] = fill * (self.width * self.height)

    def paint_disc(self, cx: int, cy: int, radius: int, color: Tuple[int, int, int, int]) -> None:
        r2 = radius * radius
        x0 = max(cx - radius, 0)
        x1 = min(cx + radius, self.width - 1)
        y0 = max(cy - radius, 0)
        y1 = min(cy + radius, self.height - 1)
        cr = color[0]
        cg = color[1]
        cb = color[2]
        ca = color[3]
        buf = self.data
        w = self.width
        for y in range(y0, y1 + 1):
            dy = y - cy
            dy2 = dy * dy
            row_base = y * w * 4
            for x in range(x0, x1 + 1):
                dx = x - cx
                if dx * dx + dy2 > r2:
                    continue
                idx = row_base + x * 4
                buf[idx] = cr
                buf[idx + 1] = cg
                buf[idx + 2] = cb
                buf[idx + 3] = ca

    def paint_line(self, x0: int, y0: int, x1: int, y1: int, radius: int, color: Tuple[int, int, int, int]) -> None:
        dx = x1 - x0
        dy = y1 - y0
        steps = max(abs(dx), abs(dy))
        if steps == 0:
            self.paint_disc(x0, y0, radius, color)
            return
        for i in range(steps + 1):
            t = i / steps
            x = int(round(x0 + t * dx))
            y = int(round(y0 + t * dy))
            self.paint_disc(x, y, radius, color)


class KittyPainter:
    def __init__(self, config: CanvasConfig) -> None:
        self.config = config
        self.buffer = RGBAFramebuffer(config)
        self.image_ids = (4242, 4243)
        self.active_image_index = -1
        self.placement_id = 1
        self.rows = 24
        self.cols = 80
        self.status_rows = 1
        self.canvas_rows = max(self.rows - self.status_rows, 1)
        self.pending = ""
        self.prev_point: Optional[Tuple[int, int]] = None
        self.palette = list(self.config.palette)
        if not self.palette:
            self.palette.append(("Default", self.config.brush_color))
        self.color_index = 0
        for idx, (name, color) in enumerate(self.palette):
            if color == self.config.brush_color:
                self.color_index = idx
                break
        else:
            self.palette.insert(0, ("Current", self.config.brush_color))
            self.color_index = 0
        self.config.brush_color = self.palette[self.color_index][1]
        self.status_message = ""

    def run(self) -> None:
        fd = sys.stdin.fileno()
        parser = EventParser()
        with RawTerminal():
            hide_cursor()
            clear_screen()
            self.query_dimensions(fd)
            enable_mouse()
            try:
                self.render_canvas()
                if self.pending:
                    events = parser.feed(self.pending)
                    self.pending = ""
                    if not self.process_events(events):
                        return
                while True:
                    ready, _, _ = select.select([fd], [], [], 0.05)
                    if fd in ready:
                        chunk = os.read(fd, 1024)
                        if not chunk:
                            break
                        events = parser.feed(chunk.decode("ascii", errors="ignore"))
                        if not self.process_events(events):
                            return
            finally:
                disable_mouse()
                for image_id in self.image_ids:
                    kitty_delete(image_id, delete_data=True)
                show_cursor()

    def query_dimensions(self, fd: int) -> None:
        rows, cols = self.request_csi(fd, "\x1b[18t", r"\x1b\[8;(\d+);(\d+)t", default=(24, 80))
        self.rows = rows
        self.cols = cols
        self.canvas_rows = max(self.rows - self.status_rows, 1)
        _ = self.request_csi(fd, "\x1b[14t", r"\x1b\[4;(\d+);(\d+)t", default=None)

    def request_csi(
        self,
        fd: int,
        request: str,
        pattern: str,
        default: Optional[Tuple[int, int]] = None,
        timeout: float = 0.5,
    ) -> Tuple[int, int]:
        sys.stdout.write(request)
        sys.stdout.flush()
        deadline = time.time() + timeout
        buf = ""
        compiled = re.compile(pattern)
        while time.time() < deadline:
            ready, _, _ = select.select([fd], [], [], 0.05)
            if not ready:
                continue
            chunk = os.read(fd, 1024)
            if not chunk:
                break
            buf += chunk.decode("ascii", errors="ignore")
            match = compiled.search(buf)
            if match:
                end = match.end()
                tail = buf[end:]
                self.pending = tail + self.pending
                groups = match.groups()
                if len(groups) >= 2:
                    return int(groups[0]), int(groups[1])
                break
        if default is None:
            return 0, 0
        return default

    def render_canvas(self) -> None:
        next_index = (self.active_image_index + 1) % len(self.image_ids)
        image_id = self.image_ids[next_index]
        control = (
            "a=T,"
            f"f=32,"
            f"s={self.buffer.width},"
            f"v={self.buffer.height},"
            f"i={image_id},"
            "q=2,"
            f"c={self.cols},"
            f"r={self.canvas_rows},"
            f"p={self.placement_id},"
            "C=1"
        )
        kitty_send(bytes(self.buffer.data), control)
        if self.active_image_index != -1:
            old_image_id = self.image_ids[self.active_image_index]
            kitty_delete(old_image_id, placement_id=self.placement_id, delete_data=True)
        self.active_image_index = next_index
        self.render_status_line()

    def render_status_line(self) -> None:
        if self.cols <= 0 or self.rows <= 0:
            return
        row = self.canvas_rows + 1
        if row > self.rows:
            row = self.rows
        name, color = self.palette[self.color_index]
        rgb_hex = f"#{color[0]:02X}{color[1]:02X}{color[2]:02X}"
        status = (
            "[Q]uit  "
            "[C]olor  "
            "[ [ / ] ] Radius  "
            "[X]Clear"
        )
        details = f"Color: {name} {rgb_hex}  Radius: {self.config.brush_radius}"
        message = self.status_message
        line = f"{status}  {details}"
        if message:
            line = f"{line}  | {message}"
        trimmed = line[: self.cols]
        padded = trimmed.ljust(self.cols)
        sys.stdout.write(f"{ESC}[{row};1H{padded}{ESC}[H")
        sys.stdout.flush()
        if message:
            self.status_message = ""

    def cycle_color(self, step: int) -> None:
        if not self.palette:
            return
        self.color_index = (self.color_index + step) % len(self.palette)
        _, color = self.palette[self.color_index]
        self.config.brush_color = color
        name = self.palette[self.color_index][0]
        self.status_message = f"Color -> {name}"
        self.render_status_line()

    def change_brush_radius(self, delta: int) -> None:
        min_radius = 1
        max_radius = 64
        new_radius = max(min_radius, min(max_radius, self.config.brush_radius + delta))
        if new_radius != self.config.brush_radius:
            self.config.brush_radius = new_radius
            self.status_message = f"Radius -> {new_radius}"
        else:
            if delta < 0:
                self.status_message = "Radius at minimum"
            elif delta > 0:
                self.status_message = "Radius at maximum"
        self.render_status_line()

    def clear_canvas(self) -> None:
        self.buffer.clear()
        self.prev_point = None
        self.status_message = "Canvas cleared"
        self.render_canvas()

    def process_events(self, events: List[Tuple[str, Tuple]]) -> bool:
        for kind, payload in events:
            if kind == "char":
                ch = payload[0]
                if ch in ("q", "Q", "\u0003"):
                    return False
                if ch == "c":
                    self.cycle_color(1)
                elif ch == "C":
                    self.cycle_color(-1)
                elif ch == "[":
                    self.change_brush_radius(-1)
                elif ch == "]":
                    self.change_brush_radius(1)
                elif ch == "{":
                    self.change_brush_radius(-5)
                elif ch == "}":
                    self.change_brush_radius(5)
                elif ch in ("x", "X"):
                    self.clear_canvas()
            elif kind == "mouse":
                self.handle_mouse(payload)
        return True

    def handle_mouse(self, payload: Tuple[int, int, int, str]) -> None:
        b, x_cell, y_cell, kind = payload
        button = b & 3
        is_motion = (b & 32) == 32
        if kind == "m":
            self.prev_point = None
            return
        if button != 0:
            return
        if not (is_motion or kind == "M"):
            return
        if y_cell > self.canvas_rows:
            self.prev_point = None
            return
        px, py = self.cell_to_canvas(x_cell, y_cell)
        if self.prev_point is not None:
            self.buffer.paint_line(self.prev_point[0], self.prev_point[1], px, py, self.config.brush_radius, self.config.brush_color)
        else:
            self.buffer.paint_disc(px, py, self.config.brush_radius, self.config.brush_color)
        self.prev_point = (px, py)
        self.render_canvas()

    def cell_to_canvas(self, col: int, row: int) -> Tuple[int, int]:
        fx = (col - 0.5) / max(self.cols, 1)
        fy = (row - 0.5) / max(self.canvas_rows, 1)
        x = int(max(0, min(self.buffer.width - 1, round(fx * self.buffer.width))))
        y = int(max(0, min(self.buffer.height - 1, round(fy * self.buffer.height))))
        return x, y


def main() -> None:
    config = CanvasConfig()
    painter = KittyPainter(config)
    try:
        painter.run()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
