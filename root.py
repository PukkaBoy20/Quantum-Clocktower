from tkinter import Tk, Event, Entry
from menus import SeatMenu
from frames import NightControlFrame, ExecutionFrame, SeatFrame
from components import ToggleAlignmentButton
from chars import Player, Character, teensy_char_list, teensy_token_list

def only_int(value: str):
    return value.isdigit() or value == ""

class QuantumClocktower(Tk):
    INITIAL_WINDOW_SIZE: int = 800

    CIRCLE_RADIUS = 250
    CIRCLE_CENTRE = INITIAL_WINDOW_SIZE / 2

    def __init__(self, players: int, script: int, evils_predetermined: bool, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.geometry(f"{self.INITIAL_WINDOW_SIZE}x{self.INITIAL_WINDOW_SIZE}")

        self.int_vcmd = (self.register(only_int), "%P")

        self.script_index = script
        scripts = [[teensy_char_list, teensy_token_list]]
        self.character_list: list[Character] = scripts[self.script_index][0]
        
        self.night = 1
        self.alignments_shown = False

        if evils_predetermined:
            evil_players = random.sample(range(players), evil_count)
        
        self.seat_names: dict[Seat, Entry] = {}
        self.players: list[Player] = []

        for i in range(players):
            if evils_predetermined:
                if i in evil_players:
                    self.players.append(Player(None, "evil", self.character_list))
                else:
                    self.players.append(Player(None, "good", self.character_list))
            else:
                self.players.append(Player(None, None, self.character_list))
            
            seat = SeatFrame(self, self.players[-1], i / players, self.CIRCLE_CENTRE, self.CIRCLE_RADIUS)
            self.seat_names[seat] = seat.seat_name
        self.seats: list[Seat] = list(self.seat_names.keys())
        
        self.seat_menu = SeatMenu(self)
        self.night_control = NightControlFrame(self)
        self.alignment_button = ToggleAlignmentButton(self)
        self.execution = ExecutionFrame(self)

    def get_player(self, player_name:str) -> None:
        for player in player_list:
            if player.name == name:
                return player
        else:
            raise RuntimeWarning
    
    def execute_night_action(self, final_info, chosen_player_name: str, info_type) -> bool:
        if "" in (chosen_player_name, info_type) or final_info == False:
            return False
        
        if isinstance(final_info, int):  # Currently unused
            number_learned = final_info
        else:
            number_learned = False

        if chosen_player_name == "None":
            chosen_player = None
        else:
            chosen_player = self.get_player(chosen_player_name)

        if self.night == 1:
            if self.script_index != 0:
                raise NotImplementedError

            if number_learned is not False:
                return False

            model, _ = first_night_model(self_player, chosen_player)
            solver = cp_model.CpSolver()
            # solver.parameters.log_search_progress = True
            if solver.solve(model) in (cp_model.FEASIBLE, cp_model.OPTIMAL):
                previous_night_decisions.append(
                    (self_player, number_learned, chosen_player)
                )
            else:
                print("invalid choice")
                return False

        ...  # update worlds# update worlds

        seat_menu.current_seat.config(text=f"Chose: {chosen_player}\nInfo: {final_info}")
        return True

    def day_finished(self) -> None:
        if self.night_control.night_phase == "Setup":
            return True
        if self.execution.executee != "":
            return True
        return False
    
    def night_finished(self) -> None:
        for seat in self.seat_list:
            if seat.cget("text") == "":
                return False
        return True

    def start_night(self) -> None:
        self.night_decisions = []
        if not self.day_finished():
            return
        
        if self.night == 1:
            for i, (seat, name) in enumerate(self.seat_names.items()):
                self.players[i].name = name.get()
                name.config(state="disabled", takefocus=0)
                root.focus()
                seat.player = self.players[i]
            self.execution.executee_selector.config(
                values=[None] + [player.name for player in self.players]
            )
            self.alignment_button.config(state="normal")

            ...  # process day stuff

        self.toggle_alignments(setToggle=True)
        self.execution.set_enabled(False)
        self.night_control.night_phase = "Night"


    def end_night(self) -> None:
        pass

    def toggle_alignments(self, setToggle=None) -> None:
        if setToggle == None:
            setToggle = not self.alignments_shown
        self.alignments_shown = setToggle
    
    def create_seat_menu(self, event: Event, player: Player) -> None:
        self.seat_menu.player = player
        self.seat_menu.post(event.x_root, event.y_root)



root = QuantumClocktower(6, 0, False, )
root.mainloop()
