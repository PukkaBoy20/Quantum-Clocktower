from tkinter import Frame, Entry, Listbox, StringVar, Button, Label
from tkinter.ttk import Combobox
from math import sin, cos, pi

from chars import Player


class NightActionFrame(Frame):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.specific_info_box: Combobox | Entry | Listbox | None = None

        self.pack(anchor="w", padx=30, pady=15)

        self.chosen_player_label = Label(self, text="Chosen Player")
        self.chosen_player_label.grid(row=0)

        self.chosen_player_box = Combobox(
            self,
            state="readonly",
            values=["None"] + [p.name for p in self.master.master.players],  # type: ignore
        )
        self.chosen_player_box.grid(row=1)

        self.info_type_label = Label(self, text="Info Learned")
        self.info_type_label.grid(row=2)

        self.info_type = Combobox(
            self,
            state="readonly",
            values=["None", "Number", "One Character", "Three Characters"],
        )
        self.info_type.bind(
            "<<ComboboxSelected>>",
            lambda event: self.show_specific_info(event.widget.get()),
        )
        self.info_type.grid(row=3, sticky="n")

        self.clear_specific_info()

    def show_specific_info(self, info_type) -> None:
        if self.specific_info_box is not None:
            self.specific_info_box.destroy()
        match info_type:
            case "None":
                self.specific_info_box = None
            case "Number":
                self.specific_info_box = Entry(
                    self,
                    validate="key",
                    vcmd=self.master.master.int_vcmd,  # type: ignore
                )
                self.specific_info_box.grid(row=3, column=1)
            case "One Character":
                self.specific_info_box = Combobox(
                    self,
                    state="readonly",
                    values=[c.name for c in self.master.master.character_list],  # type: ignore
                )
                self.specific_info_box.grid(row=3, column=1)
            case "Three Characters":
                self.specific_info_box = Listbox(
                    self,
                    selectmode="multiple",
                    listvariable=StringVar(
                        value=[c.name for c in self.master.master.character_list]  # type: ignore
                    ),
                )
                self.specific_info_box.grid(row=3, column=1)

    def clear_specific_info(self) -> None:
        if self.specific_info_box is not None:
            self.specific_info_box.destroy()
        self.specific_info_box = None

    def get_action_info(self) -> tuple:
        return self.chosen_player_box.get(), self.info_type.get()


class NightControlFrame(Frame):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.pack(anchor="ne")

        self.start_night_button = Button(
            self,
            text="Start Night",
            command=self.master.start_night,  # type: ignore
        )
        self.start_night_button.grid(row=0)

        self.end_night_button = Button(
            self,
            text="End Night",
            command=self.master.end_night_or_day,  # type: ignore
            state="disabled",
        )
        self.end_night_button.grid(row=1)

        self._night_phase = StringVar(value="Setup")
        self.night_phase_label = Label(self, textvariable=self._night_phase)
        self.night_phase_label.grid(row=2)

    @property
    def night_phase(self) -> str:
        return self._night_phase.get()

    @night_phase.setter
    def night_phase(self, value: str) -> None:
        self._night_phase.set(value)
        self.start_night_button.config(
            state="disabled" if value == "Night" else "normal"
        )
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


class SeatFrame(Frame):
    def __init__(
        self,
        master,
        player: Player,
        circle_pos: float,
        centre: float,
        radius: int,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(master, *args, **kwargs)

        self.player = player

        angle = 2 * pi * circle_pos
        x_point = radius * sin(angle)
        y_point = radius * cos(angle)
        self.place(x=centre + x_point, y=centre - y_point, anchor="center")

        self.seat = Button(self, width=5, height=3, takefocus=0)
        self.seat.bind(
            "<Button-1>",
            lambda event: self.master.create_seat_menu(event, self.player),  # type: ignore
        )
        self.seat.grid(row=0)

        self.seat_name = Entry(
            self,
            justify="center",
            bg="light grey",
            width=15,
            disabledforeground="black",
            disabledbackground="#E0E0E0",
        )
        self.seat_name.grid(row=1)
