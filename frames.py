from tkinter import Frame, Entry, Listbox, StringVar, Button, Label, Canvas
from tkinter.ttk import Combobox
from math import sin, cos, pi

from typing import TYPE_CHECKING

from chars import Player

if TYPE_CHECKING:
    from root import QuantumClocktower


SHROUD_WIDTH = 40
SHROUD_HEIGHT = SHROUD_WIDTH * 1.4


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
        
        self.barber_swap_label = Label(self, text="Barber Swapped Players")
        self.barber_swap_label.grid(row=4)
        
        self.first_barber_swapped_player_box = Combobox(
            self,
            state="readonly",
            values=["None"] + [p.name for p in self.master.master.players]
        )
        self.first_barber_swapped_player_box.set("None")
        self.first_barber_swapped_player_box.grid(row=5, column=0)
        self.second_barber_swapped_player_box = Combobox(
            self,
            state="readonly",
            values=["None"] + [p.name for p in self.master.master.players]
        )
        self.second_barber_swapped_player_box.set("None")
        self.second_barber_swapped_player_box.grid(row=5, column=1)

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
            case "One Character": # these are a bit broken with alchemist
                char_types = ["townsfolk", "outsider", "minion", "demon"]
                sorted_char_names = []
                for type in char_types:
                    sorted_char_names.extend(
                        sorted(
                            [
                                c.name
                                for c in self.master.master.character_list
                                if c.character_type == type
                            ]  # type: ignore
                        )
                    )
                self.specific_info_box = Combobox(
                    self,
                    state="readonly",
                    values=sorted_char_names,
                )
                self.specific_info_box.grid(row=3, column=1)
            case "Three Characters":
                char_types = ["townsfolk", "outsider", "minion", "demon"]
                sorted_char_names = []
                for type in char_types:
                    sorted_char_names.extend(
                        sorted(
                            [
                                c.name
                                for c in self.master.master.character_list
                                if c.character_type == type
                            ]  # type: ignore
                        )
                    )
                self.specific_info_box = Listbox(
                    self,
                    selectmode="multiple",
                    listvariable=StringVar(
                        value=sorted_char_names
                    ),
                )
                self.specific_info_box.grid(row=3, column=1)

    def clear_specific_info(self) -> None:
        if self.specific_info_box is not None:
            self.specific_info_box.destroy()
        self.specific_info_box = None

    def get_action_info(self) -> tuple:
        return (
            self.chosen_player_box.get(),
            self.info_type.get(),
            (self.first_barber_swapped_player_box.get(), self.second_barber_swapped_player_box.get())
        )


class DayActionFrame(Frame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.pack(anchor="w", padx=30, pady=15)
        
        self.puzzlemaster_guess_label = Label(self, text="Puzzlemaster Guess")
        self.puzzlemaster_guess_label.grid(row=0)
        
        self.puzzlemaster_guess_box = Combobox(
            self,
            state="readonly",
            values=["None"] + [p.name for p in self.master.master.players],  # type: ignore
        )
        self.puzzlemaster_guess_box.set("None")
        self.puzzlemaster_guess_box.grid(row=1)
        
        self.puzzlemaster_demon_learned_label = Label(self, text="Puzzlemaster - Demon Learned")
        self.puzzlemaster_demon_learned_label.grid(row=2)
        
        self.puzzlemaster_demon_learned_box = Combobox(
            self,
            state="readonly",
            values=["None"] + [p.name for p in self.master.master.players],  # type: ignore
        )
        self.puzzlemaster_demon_learned_box.set("None")
        self.puzzlemaster_demon_learned_box.grid(row=3)
        
        self.damsel_guess_label = Label(self, text="Damsel Guess")
        self.damsel_guess_label.grid(row=5)
        
        self.damsel_guess_box = Combobox(
            self,
            state="readonly",
            values=["None"] + [p.name for p in self.master.master.players],  # type: ignore
        )
        self.damsel_guess_box.set("None")
        self.damsel_guess_box.grid(row=6)
        
    def get_action_info(self) -> tuple:
        return (
            self.puzzlemaster_guess_box.get(),
            self.puzzlemaster_demon_learned_box.get(),
            self.damsel_guess_box.get()
        )


class NightControlFrame(Frame):
    def __init__(self, master, clocktower: "QuantumClocktower", *args, **kwargs) -> None:
        super().__init__(master, *args, **kwargs)
        self.grid(row=0, column=0, sticky="e")

        self.start_night_button = Button(
            self,
            text="Start Night",
            command=clocktower.end_day,
        )
        self.start_night_button.grid(row=0)

        self.end_night_button = Button(
            self,
            text="End Night",
            command=clocktower.end_night,
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
        self.grid(row=1, column=0, padx=15, pady=15, sticky="e")

        self.execution_label = Label(self, text="Player Executed")
        self.execution_label.grid(row=0)

        self.executee_selector = Combobox(self, state="disabled")
        self.executee_selector.grid(row=1)

    @property
    def executee_name(self) -> str:
        return self.executee_selector.get()

    def set_enabled(self, enabled: bool) -> None:
        if enabled:
            self.executee_selector.config(state="readonly")
            self.executee_selector.set("")
        else:
            self.executee_selector.config(state="disabled")


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
    
    def add_shroud(self):
        self._shroud = Canvas(self, width=SHROUD_WIDTH, height=SHROUD_HEIGHT, bd=0, highlightthickness=0)
        self._shroud.create_polygon(
            0, 0,
            0, SHROUD_HEIGHT,
            SHROUD_WIDTH/2, SHROUD_HEIGHT*0.75,
            SHROUD_WIDTH, SHROUD_HEIGHT,
            SHROUD_WIDTH, 0,
            fill="black",
            outline="black",
        )
        self._shroud.grid(row=0)


class UtilityButtonsFrame(Frame):
    def __init__(self, master, clocktower: "QuantumClocktower", *args, **kwargs) -> None:
        super().__init__(master, *args, **kwargs)
        self.pack(side="left", anchor="nw")
        
        self.toggle_alignment_button = Button(
            self,
            text="Toggle Alignments",
            command=clocktower.toggle_alignments,
            state="disabled"
        )
        self.toggle_alignment_button.grid(row=0)
        
        self.recalcute_possible_characters_button = Button(
            self,
            text="Recalculate Possible Characters",
            command=clocktower.determine_possible_variables,
            state="disabled",
        )
        self.recalcute_possible_characters_button.grid(row=1)
    
    def enable_buttons(self) -> None:
        self.toggle_alignment_button.config(state="normal")
        self.recalcute_possible_characters_button.config(state="normal")


class RightMainButtonsFrame(Frame):
    def __init__(self, clocktower: "QuantumClocktower", *args, **kwargs):
        super().__init__(master=clocktower, *args, **kwargs)
        self.pack(side="right", anchor="ne")
        
        self.night_control = NightControlFrame(self, clocktower)
        self.execution = ExecutionFrame(self)
