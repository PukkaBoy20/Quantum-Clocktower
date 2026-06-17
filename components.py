from tkinter import Button
from chars import Player

class SeatButton(Button):
    def __init__(self, master=None, player: Player = None, **kwargs):
        kwargs.setdefault("takefocus", 0)
        super().__init__(master, **kwargs)
        self.player = player

class ToggleAlignmentButton(Button):
    def __init__(self, master) -> None:
        super().__init__(master, text="Toggle Alignments", command=master.toggle_alignments, state="disabled")
        self.pack(anchor="nw")
