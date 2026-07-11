from tkinter import Tk, Event, Entry
from menus import SeatMenu
from frames import NightControlFrame, ExecutionFrame, SeatFrame
from components import ToggleAlignmentButton
from chars import Player, Character, Token, teensy_char_list, teensy_token_list
from random import sample
from models import first_night_model
from util import evil_count, EVIL_COLOUR, GOOD_COLOUR, QUANTUM_COLOUR, DEFAULT_COLOUR
from ortools.sat.python import cp_model


def only_int(value: str):
    return value.isdigit() or value == ""


class QuantumClocktower(Tk):
    INITIAL_WINDOW_SIZE: int = 800

    CIRCLE_RADIUS = 250
    CIRCLE_CENTRE = INITIAL_WINDOW_SIZE / 2

    def __init__(
        self, player_count: int, script: int, evils_predetermined: bool, *args, **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)
        self.geometry(f"{self.INITIAL_WINDOW_SIZE}x{self.INITIAL_WINDOW_SIZE}")

        self.int_vcmd = (self.register(only_int), "%P")

        self.script_index = script
        scripts = [[teensy_char_list, teensy_token_list]]
        self.character_list: list[Character] = scripts[self.script_index][0]
        self.token_list: list[Token] = scripts[self.script_index][1]

        self.night = 1
        self.show_alignments = False
        self.previous_night_choices = []
        self.all_night_choices = []

        evil_players = sample(range(player_count), evil_count(player_count))

        self.seat_names: dict[SeatFrame, Entry] = {}
        self.players: list[Player] = []

        for i in range(player_count):
            if evils_predetermined:
                if i in evil_players:
                    self.players.append(Player(None, "evil", i, self.character_list))
                else:
                    self.players.append(Player(None, "good", i, self.character_list))
            else:
                self.players.append(Player(None, None, i, self.character_list))

            seat = SeatFrame(
                self,
                self.players[-1],
                i / player_count,
                self.CIRCLE_CENTRE,
                self.CIRCLE_RADIUS,
            )
            self.seat_names[seat] = seat.seat_name
        self.seats: list[SeatFrame] = list(self.seat_names.keys())

        self.seat_menu = SeatMenu(self)
        self.night_control = NightControlFrame(self)
        self.alignment_button = ToggleAlignmentButton(self)
        self.execution = ExecutionFrame(self)

    def get_player(self, player_name: str) -> Player:
        for player in self.players:
            if player.name == player_name:
                return player
        else:
            raise RuntimeWarning

    def execute_night_action(
        self, final_info, chosen_player_name: str, info_type
    ) -> bool:
        if "" in (chosen_player_name, info_type) or (
            not final_info and final_info is not None
        ):
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

            model, _ = first_night_model(self, self.seat_menu.player, chosen_player)
            solver = cp_model.CpSolver()
            # solver.parameters.log_search_progress = True
            if solver.solve(model) in (cp_model.FEASIBLE, cp_model.OPTIMAL):
                self.previous_night_choices.append(
                    (self.seat_menu.player, number_learned, chosen_player)
                )
            else:
                print("invalid choice")
                return False

        ...  # update worlds# update worlds

        self.seats[
            self.seat_menu.player.index if self.seat_menu.player else 0
        ].seat.config(text=f"Chose: {chosen_player}\nInfo: {final_info}")
        return True

    def day_finished(self) -> bool:
        if self.night_control.night_phase == "Setup":
            return True
        if self.execution.executee != "":
            return True
        return False

    def night_finished(self) -> bool:
        for seat in self.seat_names:
            if (
                seat.seat.cget("text") == ""
            ):  # Since we set descriptor text after night action
                return False
        return True

    def start_night(self) -> None:
        self.previous_night_choices = []
        if not self.day_finished():
            return

        if self.night == 1:
            for i, (seat, name) in enumerate(self.seat_names.items()):
                self.players[i].name = name.get()
                name.config(state="disabled", takefocus=0)
                root.focus()
                seat.player = self.players[i]
            self.execution.executee_selector.config(
                values=["None"] + [player.name for player in self.players]
            )
            self.alignment_button.config(state="normal")

            ...  # process day stuff

        self.toggle_alignments(setToggle=True)
        self.execution.set_enabled(False)
        self.night_control.night_phase = "Night"

    def end_night(self) -> None:
        if not self.night_finished():
            return

        if self.night == 1:
            if self.script_index != 0:
                raise NotImplementedError
            _, variables = first_night_model(self)

            assigned_char, target, player_learned, tokens, is_evil = variables
            possible_char_indexes: list[list] = [[] for _ in self.players]
            for i, p in enumerate(self.players):
                for c in range(len(self.character_list)):
                    if self.variable_is_possible(assigned_char[i][c]):
                        possible_char_indexes[i].append(1)
                    else:
                        possible_char_indexes[i].append(0)
                p.possible_characters = [
                    self.character_list[c]
                    for c in range(len(self.character_list))
                    if possible_char_indexes[i][c]
                ]
                if len(p.possible_characters) == 1:
                    ...

            possible_alignment_indexes: list[list] = [[] for _ in self.players]
            for i, p in enumerate(self.players):
                if self.variable_is_possible(is_evil[i]):
                    possible_alignment_indexes[i].append(1)
                else:
                    possible_alignment_indexes[i].append(0)
                if self.variable_is_possible(is_evil[i].Not()):
                    possible_alignment_indexes[i].append(1)
                else:
                    possible_alignment_indexes[i].append(0)
                if sum(possible_alignment_indexes[i]) == 1:
                    p.alignment = "evil" if possible_alignment_indexes[0] else "good"
                else:
                    p.alignment = None

            # possible_token_indexes: list[list] = [[] for _ in self.players]
            # for i, p in enumerate(self.players):
            #     for t in range(len(token_list)):
            #         if variable_is_possible(tokens[i][t]):
            #             possible_token_indexes[i].append(1)
            #         else:
            #             possible_token_indexes[i].append(0)
            #     p.tokens

        self.all_night_choices.append(self.previous_night_choices)

        self.toggle_alignments(setToggle=False)
        self.execution.set_enabled(True)
        self.night_control.night_phase = "Day"
        for seat in self.seats:
            seat.seat.config(text="")

    def toggle_alignments(self, setToggle=None) -> None:
        if setToggle is None:
            setToggle = not self.show_alignments
        self.show_alignments = setToggle
        if self.show_alignments:
            for i, seat in enumerate(self.seat_names):
                if self.players[i].alignment == "evil":
                    seat.config(background=EVIL_COLOUR)
                elif self.players[i].alignment == "good":
                    seat.config(background=GOOD_COLOUR)
                else:
                    seat.config(background=QUANTUM_COLOUR)
        else:
            for seat in self.seat_names:
                seat.config(background=DEFAULT_COLOUR)

    def create_seat_menu(self, event: Event, player: Player) -> None:
        self.seat_menu.player = player
        self.seat_menu.post(event.x_root, event.y_root)

    def variable_is_possible(self, variable) -> bool:
        solver = cp_model.CpSolver()
        test_model, (_, target, _, _, _) = first_night_model(self)
        test_model.add(variable == 1)
        for player, _, chosen_player in self.previous_night_choices:
            player_index = self.players.index(player)
            if chosen_player is None:
                test_model.add(sum(target[player_index]) == 0)
            else:
                test_model.add(
                    target[player_index][self.players.index(chosen_player)] == 1
                )
        return bool(solver.solve(test_model) in (cp_model.OPTIMAL, cp_model.FEASIBLE))


script_index = int(input("\nScripts:\n(1). Teensy\nNumber: ") or "1") - 1

player_count = int(input("Number of players: ") or "6")

evils_predetermined = input("Evil players predetermined? y/N: ").lower()
while evils_predetermined not in ["y", "n", ""]:
    evils_predetermined = input("Evil players predetermined? y/N: ").lower()

root = QuantumClocktower(player_count, script_index, evils_predetermined == "y")
root.mainloop()
