from tkinter import Menu

from frames import NightActionFrame
from components import SeatButton

class SeatMenu(Menu):
    def __init__(self, master=None, current_seat: SeatButton = None, tearoff = 0, **kwargs):
        super().__init__(master, **kwargs)
        self.current_seat = current_seat

        self.add_command(
            label = "Create Night Action",
            command = self.create_night_action,
        )       
        self.add_command(
            label = "View Possible Characters",
            command = lambda: print(
                f"Possible characters:\n{self.current_seat.player.possible_characters}"
            ),
        )

    def create_night_action(self) -> None:
        self.night_action_window = tk.Toplevel(self.master)
        self.night_action_window.title(f"Set Night Action for {seat.player.name}")
        self.night_action_window.geometry(NIGHT_PANEL_SIZE)
        self.night_action_frame = NightActionFrame(self.execute_night_action)
    
    def execute_night_action(self, chosen_player, info_type) -> None:
        if self.master.execute_night_action(self.get_final_info(), chosen_player, info_type):
            night_action_panel.destroy()


    def get_final_info(self):
        match self.night_action_frame.specific_info_box:
            case None:
                final_info = None
            case tk.Entry() | ttk.Combobox():
                final_info = specific_info_box.get()
                if final_info == "":
                    final_info = False
            case tk.Listbox():
                final_info = [
                    specific_info_box.get(i) for i in specific_info_box.curselection()
                ]
                if len(final_info) != 3 or len(player_list) < 7:
                    final_info = False
        return final_info

