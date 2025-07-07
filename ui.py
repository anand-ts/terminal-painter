from asciimatics.widgets import Frame, Layout, Divider, Button, DropdownList
from asciimatics.screen import Screen

# NOTE: renamed to avoid clashing with Frame.palette attribute.
class ColorPalette:
    """
    A color palette widget.
    """
    def __init__(self, frame, on_color_change):
        self.frame = frame
        self.on_color_change = on_color_change
        self.colors = [
            (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0),
            (0, 255, 255), (255, 0, 255), (255, 255, 255), (0, 0, 0)
        ]

        layout = Layout([1] * 8)
        self.frame.add_layout(layout)
        for i, color in enumerate(self.colors):
            # Create a button that, when clicked, selects the corresponding colour.
            # The Button API (as of asciimatics 1.15) takes the text and an on_click
            # callback.  We use a lambda to bind the current colour value.
            button = Button(
                " ",  # Text placeholder – we will colour the button background.
                on_click=lambda c=color: self._select_color(c)
            )

            layout.add_widget(button, i)

    def _select_color(self, color):
        self.on_color_change(color)

class BrushSizeSelector:
    """
    A simple dropdown list to choose brush size (1-10).
    """

    def __init__(self, frame, on_size_change):
        self.frame = frame
        self.on_size_change = on_size_change

        layout = Layout([1])
        self.frame.add_layout(layout)

        # Create dropdown options as list of tuples (display_text, value)
        sizes = [(str(i), i) for i in range(1, 11)]

        # When the user picks a new size we invoke the callback with the new value.
        def _on_change():
            if self.on_size_change:
                self.on_size_change(self.dropdown.value)

        self.dropdown = DropdownList(sizes, label="Brush Size:", on_change=_on_change)
        layout.add_widget(self.dropdown)

class UIFrame(Frame):
    """
    The main UI frame containing the palette and slider.
    """
    def __init__(self, screen, on_color_change, on_size_change):
        super(UIFrame, self).__init__(
            screen,
            screen.height,
            screen.width // 4,
            x=screen.width - screen.width // 4,
            y=0,
            has_border=True,
            name="UI"
        )
        # Track whether the UI currently has focus (e.g., the mouse is over the UI region)
        self.has_focus: bool = False

        self.color_palette = ColorPalette(self, on_color_change)
        layout = Layout([1])
        self.add_layout(layout)
        layout.add_widget(Divider())
        self.brush_selector = BrushSizeSelector(self, on_size_change)
        self.fix()
