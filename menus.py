from tkinter import Menu, Toplevel, Entry, Listbox, Button
from tkinter.ttk import Combobox

from frames import NightActionFrame, DayActionFrame
from chars import Player


class SeatMenu(Menu):
    NIGHT_AND_DAY_PANEL_SIZE_AND_POSITION = "600x400+500+200"

    def __init__(self, master=None, player: Player | None = None, **kwargs):
        kwargs.setdefault("tearoff", 0)
        super().__init__(master, **kwargs)
        self.player = player

        self.add_command(
            label="Create Night Action",
            command=self.create_night_action,
        )
        self.add_command(
            label="Create Day Action",
            command=self.create_day_action,
        )
        self.add_command(
            label="View Possible Characters",
            command=lambda: print(
                f"Possible characters:\n{[character.name for character in self.player.possible_characters] if self.player else None}"
            ),
        )

    def create_night_action(self) -> None: # TODO: disable these at relevant times
        self.night_action_window = Toplevel(self.master)
        self.night_action_window.title(
            f"Set Night Action for {self.player.name if self.player else None}"
        )
        self.night_action_window.geometry(self.NIGHT_AND_DAY_PANEL_SIZE_AND_POSITION)

        self.night_action_frame = NightActionFrame(self.night_action_window)

        self.night_action_done_button = Button(
            self.night_action_window,
            text="Done",
            command=lambda: self.execute_night_action(
                *self.night_action_frame.get_action_info()
            ),
        )
        self.night_action_done_button.pack(side="bottom", anchor="e", padx=20, pady=20)
        self.night_action_window.bind(
            "<Return>",
            lambda _: self.execute_night_action(
                *self.night_action_frame.get_action_info()
            )
        )

    def execute_night_action(self, chosen_player, info_type, barber_swapped_player_names) -> None:
        if self.master.execute_night_action(  # type: ignore
            self.get_final_info(), chosen_player, info_type, barber_swapped_player_names
        ):
            self.night_action_window.destroy()

    def get_final_info(self):
        match self.night_action_frame.specific_info_box:
            case None:
                final_info = None
            case Combobox():
                final_info = self.night_action_frame.specific_info_box.get()
            case Entry():
                final_info = self.night_action_frame.specific_info_box.get()
                if final_info == "":
                    final_info = False
                else:
                    final_info = int(final_info)
            case Listbox():
                final_info = [
                    self.night_action_frame.specific_info_box.get(i)
                    for i in self.night_action_frame.specific_info_box.curselection()
                ]
                if len(final_info) != 3 or len(self.master.players) < 7:  # type: ignore
                    final_info = False
        return final_info
    
    def create_day_action(self) -> None:
        self.day_action_window = Toplevel(self.master)
        self.day_action_window.title(
            f"Set Day Action for {self.player.name if self.player else None}"
        )
        self.day_action_window.geometry(self.NIGHT_AND_DAY_PANEL_SIZE_AND_POSITION)
        
        self.day_action_frame = DayActionFrame(self.day_action_window)
        
        self.day_action_done_button = Button(
            self.day_action_window,
            text="Done",
            command=lambda: self.execute_day_action(
                *self.day_action_frame.get_action_info()
            ),
        )
        self.day_action_done_button.pack(side="bottom", anchor="e", padx=20, pady=20)
        self.day_action_window.bind(
            "<Return>",
            lambda _: self.execute_day_action(
                *self.day_action_frame.get_action_info()
            ),
        )
        
    def execute_day_action(self, puzzlemaster_guess, puzzlemaster_demon_learned, damsel_guess) -> None:
        if self.master.execute_day_action(
            puzzlemaster_guess, puzzlemaster_demon_learned, damsel_guess
        ):  # type: ignore
            self.day_action_window.destroy()
