from tkinter import Frame, Entry, Listbox, StringVar, Button, Label
from tkinter.ttk import Combobox

class NightActionFrame(Frame):
    def __init__(self, execute_night_action, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.specific_info_box: Combobox | Entry | Listbox | None = None
        
        self.pack(anchor="w", padx=30, pady=15)

        self.chosen_player_label = tk.Label(self, text="Chosen Player")
        self.chosen_player_label.grid(row=0)

        self.chosen_player_box = ttk.Combobox(
            self,
            state="readonly",
            values=[None] + [p.name for p in player_list],
        )
        self.chosen_player_box.grid(row=1)


        self.info_type_label = tk.Label(self, text="Info Learned")
        self.info_type_label.grid(row=2)

        self.info_type = ttk.Combobox(
            self,
            state="readonly",
            values=[None, "Number", "One Character", "Three Characters"],
        )
        self.info_type.bind(
            "<<ComboboxSelected>>",
            lambda event: show_specific_info(event.widget.get()),
        )
        self.info_type.grid(row=3, sticky="n")

        self.clear_specific_info()


        self.night_action_done_button = tk.Button(
            self,
            text="Done",
            command=lambda: execute_night_action(
                self.chosen_player_box.get(), self.info_type.get()
            ),
        )
        self.night_action_done_button.pack(side="bottom", anchor="e", padx=20, pady=20)

    def show_specific_info(self, info_type) -> None:
        if self.specific_info_box != None:
            self.specific_info_box.destroy()
        match info_type:
            case "None":
                self.specific_info_box = None
            case "Number":
                self.specific_info_box = Entry(
                    self, validate = "key", vcmd = int_vcmd
                )
                self.specific_info_box.grid(row=3, column=1)
            case "One Character":
                self.specific_info_box = Combobox(
                    self,
                    state="readonly",
                    values=[c.name for c in character_list],
                )
                self.specific_info_box.grid(row=3, column=1)
            case "Three Characters":
                self.specific_info_box = Listbox(
                    self,
                    selectmode = "multiple",
                    listvariable = tk.StringVar(value=[c.name for c in character_list]),
                )
                self.specific_info_box.grid(row=3, column=1)

    def clear_specific_info(self) -> None:
        if self.specific_info_box != None:
            self.specific_info_box.destroy()
        self.specific_info_box = None

class NightControlFrame(Frame):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.pack(anchor="ne")

        self.start_night_button = Button(
            self, text="Start Night", command = self.master.start_night
        )
        self.start_night_button.grid(row=0)

        self.end_night_button = Button(
            self, text="End Night", command = self.master.end_night, state="disabled"
        )
        self.end_night_button.grid(row=1)

        self._night_phase = StringVar(value="Setup")
        self.night_phase_label = Label(self, textvariable=self._night_phase)
        self.night_phase_label.grid(row=2)
    
    @property
    def night_phase(self) -> None:
        return self._night_phase.get()
    
    @night_phase.setter
    def night_phase(self, value: str) -> None:
        self._night_phase.set(value)
        self.end_night_button.config(state="disabled" if value == "Night" else "normal")
        self.end_night_button.config(state="normal" if value == "Night" else "disabled")

class ExecutionFrame(Frame):
    def __init__(self, master, *args, **kwargs) -> None:
        super().__init__(master, *args, **kwargs)
        self.pack(side="right", anchor="n", padx=15, pady=15)

        self.execution_label = Label(self, text="Player Executed")
        self.execution_label.grid(row=0)

        self.executee_selector = Combobox(self, state="disabled")
        self.executee_selector.grid(row=1)
    
    @property
    def executee(self) -> str:
        return self.executee_selector.get()

    def set_enabled(self, enabled: bool) -> None:
        self.executee_selector.config(state="normal" if enabled else "disabled")
        self.executee_selector.set("")
 