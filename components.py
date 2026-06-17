from tkinter import Button
from chars import Player


class ToggleAlignmentButton(Button):
    def __init__(self, master) -> None:
        super().__init__(
            master,
            text="Toggle Alignments",
            command=master.toggle_alignments,
            state="disabled",
        )
        self.pack(anchor="nw")
