from tkinter import Text


class GameLog(Text):
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, width=60, height=16, state="disabled", wrap="word", *args, **kwargs)
    
    def output(self, output):
        self["state"] = "normal"
        self.insert("end", output) # 🔥🔥🔥
        self["state"] = "disabled"