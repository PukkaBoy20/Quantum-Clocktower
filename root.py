from tkinter import Tk, Event, Entry
from menus import SeatMenu
from frames import NightControlFrame, ExecutionFrame, SeatFrame
from components import ToggleAlignmentButton
from chars import Player, Character, Token, scripts
from random import sample
from models import create_model
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
        self.character_list: list[Character] = list(scripts.values())[self.script_index][0]
        self.token_list: list[Token] = list(scripts.values())[self.script_index][1]

        self.night = 1
        self.show_alignments = False
        self.all_night_choices: list[list] = []
        self.all_chosen_bluff_indexes: list[tuple] = [() for _ in range(player_count)]

        evil_players = sample(range(player_count), evil_count(player_count)) #nosec

        self.seat_names: dict[SeatFrame, Entry] = {}
        self.players: list[Player] = []

        self.evils_predetermined = evils_predetermined
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
        raise RuntimeWarning

    def execute_night_action(
        self, final_info, chosen_player_name: str, info_type
    ) -> bool:
        if "" in (chosen_player_name, info_type) or (
            not final_info and final_info is not None
        ):
            return False

        if isinstance(final_info, int):
            number_learned = final_info
        else:
            number_learned = None

        if info_type == "One Character":
            character_learned_index = [c.name for c in self.character_list].index(final_info)
        else:
            character_learned_index = None
        
        if info_type == "Three Characters":
            chosen_bluff_indexes = tuple([c.name for c in self.character_list].index(bluff_name) for bluff_name in final_info)
        else:
            chosen_bluff_indexes = None

        if chosen_player_name == "None":
            chosen_player = None
        else:
            chosen_player = self.get_player(chosen_player_name)

        model, _ = create_model(self, self.night, False, self.seat_menu.player, chosen_player, character_learned_index, chosen_bluff_indexes, number_learned)
        solver = cp_model.CpSolver()
        if solver.solve(model) in (cp_model.FEASIBLE, cp_model.OPTIMAL):
            # TODO: make game end partway through night
            self.all_night_choices[-1][self.players.index(self.seat_menu.player)] = (
                chosen_player, character_learned_index, number_learned 
            )
            self.all_chosen_bluff_indexes[self.players.index(self.seat_menu.player)] = (
                chosen_bluff_indexes
            )
        else:
            print("Invalid Choice")
            return False
        
        if chosen_player is not None:
            self.seats[
                self.seat_menu.player.index if self.seat_menu.player else 0
            ].seat.config(text=f"Chose: {chosen_player.name}\nInfo: {final_info}")
        else:
            self.seats[
                self.seat_menu.player.index if self.seat_menu.player else 0
            ].seat.config(text=f"Chose: None\nInfo: {final_info}")
        return True

    def day_finished(self) -> bool:
        if self.night_control.night_phase == "Setup":
            return True
        if self.execution.executee_name != "":
            return True
        return False

    def start_night(self) -> None:
        self.all_night_choices.append([[] for _ in range(player_count)])
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

    def end_night_or_day(self) -> None:
        if min(len(i) for i in self.all_night_choices[-1]) == 0:
            return
        daytime = self.night_control.night_phase == "Day"
        if self.script_index != 0: # TODO: implement new scripts here
            raise NotImplementedError
        model, variables = create_model(self, self.night, daytime)
        
        assigned_char, target, learned_char, tokens, is_evil, good_wins, evil_wins, game_over = variables
        
        self.determine_possible_variables(model, assigned_char, is_evil)
        
        if not self.variable_is_possible(model, game_over[-1].Not()):
            print("GAME OVER")
            if daytime:
                now = 2*(self.night-1) + 1
            else:
                now = 2*(self.night-1)
            
            # final_worlds[world][player][variable][n]
            final_worlds: list[list[list[list]]] = []
            class SolutionCallback(cp_model.CpSolverSolutionCallback):
                def __init__(sol_self):
                    super().__init__()
                    sol_self.solution_count = 0
                    
                def OnSolutionCallback(sol_self):
                    final_worlds.append([])
                    for p in range(player_count):
                        final_worlds[-1].append([])
                        final_worlds[-1][-1].append([] for _ in range(5))
                        for n in range(now+1):
                            p_assigned_char = next(
                                c
                                for c, c_2 in zip(self.character_list, assigned_char[n][p])
                                if sol_self.boolean_value(c_2)
                            )
                            final_worlds[-1][-1][0].append(p_assigned_char)
                            p_target = next(
                                (
                                    q
                                    for q, q_2 in zip(self.players, target[n][p])
                                    if sol_self.boolean_value(q_2)
                                ),
                                None
                            )
                            final_worlds[-1][-1][1].append(p_target)
                            p_character_learned = next(
                                (
                                    c
                                    for c, c_2 in zip(self.character_list, learned_char[n][p])
                                    if sol_self.boolean_value(c_2)
                                ),
                                None
                            )
                            final_worlds[-1][-1][2].append(p_character_learned)
                            p_tokens = [
                                t
                                for t, t_2 in zip(self.token_list, tokens[n][p])
                                if sol_self.boolean_value(t_2)
                            ]
                            final_worlds[-1][-1][3].append(p_tokens)
                            p_is_evil = sol_self.boolean_value(is_evil[n][p])
                            final_worlds[-1][-1][4].append(p_is_evil)
                            
            callback = SolutionCallback()
            solver = cp_model.CpSolver()
            solver.parameters.enumerate_all_solutions = True
            solver.solve(model, callback)
            self.game_ended(final_worlds)

        if daytime:
            self.toggle_alignments(setToggle=True)
            self.execution.set_enabled(False)
            self.night_control.night_phase = "Night"
        else:
            self.toggle_alignments(setToggle=False)
            self.execution.set_enabled(True)
            self.night_control.night_phase = "Day"
        for seat in self.seats:
            seat.seat.config(text="")

    def determine_possible_variables(self, model, assigned_char, is_evil):
        possible_char_indexes: list[list] = [[] for _ in self.players]
        for i, p in enumerate(self.players):
            for c in range(len(self.character_list)):
                if self.variable_is_possible(model, assigned_char[-1][i][c]):
                    possible_char_indexes[i].append(1)
                else:
                    possible_char_indexes[i].append(0)
            p.possible_characters = [
                self.character_list[c]
                for c in range(len(self.character_list))
                if possible_char_indexes[i][c]
            ]
            if len(p.possible_characters) == 1:
                #TODO improve
                print(f"{p.name} is {self.character_list[c].name}")

        possible_alignment_indexes: list[list] = [[] for _ in self.players]
        for i, p in enumerate(self.players):
            if self.variable_is_possible(model, is_evil[-1][i]):
                possible_alignment_indexes[i].append(1)
            else:
                possible_alignment_indexes[i].append(0)
            if self.variable_is_possible(model, is_evil[-1][i].Not()):
                possible_alignment_indexes[i].append(1)
            else:
                possible_alignment_indexes[i].append(0)
            if sum(possible_alignment_indexes[i]) == 1:
                p.alignment = "evil" if possible_alignment_indexes[i][0] else "good"
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

    def game_ended(self, final_worlds):
        ...

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

    def variable_is_possible(self, model: cp_model.CpModel, variable) -> bool:
        solver = cp_model.CpSolver()
        model.add_assumption(variable)
        possible = bool(solver.solve(model) in (cp_model.OPTIMAL, cp_model.FEASIBLE))
        model.clear_assumptions()
        return possible


print("\nScripts:")
for i, name in enumerate(scripts, start=1):
    print(f"({i}). {name}")
script_index = int(input("Number: ")) - 1

player_count = int(input("Number of players: ") or "6")

evils_predetermined = input("Evil players predetermined? y/N: ").lower()
while evils_predetermined not in ["y", "n", ""]:
    evils_predetermined = input("Evil players predetermined? y/N: ").lower()

root = QuantumClocktower(player_count, script_index, evils_predetermined == "y")
root.mainloop()
