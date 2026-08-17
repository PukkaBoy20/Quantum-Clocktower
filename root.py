from tkinter import Tk, Event, Entry
from menus import SeatMenu
from frames import RightMainButtonsFrame, SeatFrame, UtilityButtonsFrame
from chars import Player, Character, Token, scripts, character_change_token_names, evil_alignment_token_names
from random import sample
from models import create_model
from util import evil_count, set_solver_parameters, EVIL_COLOUR, GOOD_COLOUR, QUANTUM_COLOUR, DEFAULT_COLOUR
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

        self.night = 0
        self.show_alignments = False
        self.all_night_choices: list[list[tuple]] | list[list] = []
        self.all_day_choices: list[tuple[list[tuple]]] | list[tuple[list]] = []
        self.executed_indexes: list[int | str | None] = []
        self.all_chosen_bluff_indexes: list[tuple | None] = [() for _ in range(player_count)]

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

        self.right_main_buttons_frame = RightMainButtonsFrame(self)
        self.night_control = self.right_main_buttons_frame.night_control
        self.execution = self.right_main_buttons_frame.execution
        self.seat_menu = SeatMenu(self)
        self.utility_buttons = UtilityButtonsFrame(self, self)

    def get_player(self, player_name: str) -> Player:
        for player in self.players:
            if player.name == player_name:
                return player
        raise RuntimeWarning

    def execute_night_action(
        self, final_info, chosen_player_name: str, info_type, barber_swapped_player_names: tuple
    ) -> bool:
        if "" in (chosen_player_name, info_type) or final_info is False:
            return False
        if (barber_swapped_player_names[0] == "None") != (barber_swapped_player_names[1] == "None"):
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
        
        if barber_swapped_player_names == ("None", "None"):
            barber_swapped_player_indexes = None
        else:
            barber_swapped_player_indexes = [self.players.index(self.get_player(b_p)) for b_p in barber_swapped_player_names]

        model, _ = create_model(self, self.night, False, self.seat_menu.player, chosen_player, character_learned_index, chosen_bluff_indexes, number_learned, barber_swapped_player_indexes)
        solver = cp_model.CpSolver()
        set_solver_parameters(solver)
        
        if solver.solve(model) in (cp_model.FEASIBLE, cp_model.OPTIMAL):
            self.all_night_choices[-1][self.players.index(self.seat_menu.player)] = (
                chosen_player, character_learned_index, number_learned, barber_swapped_player_indexes
            )
            self.all_chosen_bluff_indexes[self.players.index(self.seat_menu.player)] = (
                chosen_bluff_indexes
            )
        else:
            print("\nInvalid Choice")
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

    def execute_day_action(
        self,
        puzzlemaster_guess: str,
        puzzlemaster_demon_learned: str,
        damsel_guess: str
    ) -> bool:
        if (puzzlemaster_guess == "None") != (puzzlemaster_demon_learned == "None"):
            return False
        
        if puzzlemaster_guess == "None":
            puzzlemaster_guess_index = None
            puzzlemaster_demon_player_learned_index = None
        else:
            puzzlemaster_guess_index = [p.name for p in self.players].index(puzzlemaster_guess)
            puzzlemaster_demon_player_learned_index = [p.name for p in self.players].index(puzzlemaster_demon_learned)
        
        if damsel_guess == "None":
            damsel_guess_index = None
        else:
            damsel_guess_index = [p.name for p in self.players].index(damsel_guess)
        
        if puzzlemaster_guess_index == damsel_guess_index == None:
            return True
        
        model, _ = create_model(
            self,
            self.night,
            True,
            self.seat_menu.player,
            puzzlemaster_guess_index=puzzlemaster_guess_index,
            puzzlemaster_demon_player_learned_index=puzzlemaster_demon_player_learned_index,
            damsel_guess_index=damsel_guess_index
        )
        solver = cp_model.CpSolver()
        set_solver_parameters(solver)
        
        if solver.solve(model) in (cp_model.FEASIBLE, cp_model.OPTIMAL):
            player_index = self.players.index(self.seat_menu.player)
            self.all_day_choices[-1][0][player_index] = (
                puzzlemaster_guess_index,
                puzzlemaster_demon_player_learned_index,
                damsel_guess_index,
            )
            if damsel_guess_index is not None and player_index not in self.all_day_choices[-1][1]:
                self.all_day_choices[-1][1].append(player_index)
        else:
            print("\nInvalid Choice")
            return False
        seat_message_parts = []
        if puzzlemaster_guess_index is not None:
            seat_message_parts.append(
                f"""Puzzle Guessed: {self.players[puzzlemaster_guess_index].name}\n
                Learned: {self.players[puzzlemaster_demon_player_learned_index].name}"""
            )
        if damsel_guess_index is not None:
            seat_message_parts.append(f"Damsel Guessed: {self.players[damsel_guess_index].name}")
        seat_message = "\n".join(seat_message_parts)
        self.seats[self.seat_menu.player.index].seat.config(text=seat_message)
        return True

    def end_setup_specific_tasks(self):
        for i, (seat, name_entry) in enumerate(self.seat_names.items()):
            self.players[i].name = name_entry.get()
            name_entry.config(state="disabled", takefocus=0)
            seat.player = self.players[i]
        root.focus()
        self.execution.executee_selector.config(
            values=["None"] + [player.name for player in self.players]
        )
        self.utility_buttons.enable_buttons()

    def night_and_day_end_common_tasks(self, setup: bool, daytime: bool):
        if not setup:
            self.determine_possible_variables(daytime_override=daytime)
            for p in self.players:
                p.night_or_day_start_possible_characters = p.possible_characters
            
            model, variables = create_model(self, self.night, daytime)
            assigned_char, target, learned_char, tokens, is_evil, good_wins, evil_wins, game_over = variables
            
            if not self.variable_is_possible(model, game_over[-1].Not()):
                self.game_end_sequence(model, daytime, assigned_char, target, learned_char, tokens, is_evil)
        
        for seat in self.seats:
            seat.seat.config(text="")
            if seat.player.dead:
                seat.add_shroud()
                # TODO: make info default to None when dead (under certain conditions)
    
    def end_night(self):
        if min(len(i) for i in self.all_night_choices[-1]) == 0:
            return
        
        self.all_day_choices.append(([() for _ in range(player_count)], []))
        self.all_night_choices.append(None)
        self.toggle_alignments(set_toggle=False)
        self.execution.set_enabled(True)
        self.night_control.night_phase = "Day"
        self.night_and_day_end_common_tasks(False, False)
        self.executed_indexes.append("N/A")
    
    def end_day(self):
        setup = self.night_control.night_phase == "Setup"
        if not setup and self.execution.executee_name == "":
            return
        
        self.all_night_choices.append([[] for _ in range(player_count)])
        self.all_day_choices.append(None)
        self.toggle_alignments(set_toggle=True)
        self.execution.set_enabled(False)
        self.night_control.night_phase = "Night"
        
        if setup:
            self.end_setup_specific_tasks()
        else:
            if self.execution.executee_name == "None":
                self.executed_indexes.append(None)
            else:
                self.executed_indexes.append([p.name for p in self.players].index(self.execution.executee_name))
        
        self.night_and_day_end_common_tasks(setup, True)
        self.night += 1
    
    def determine_possible_variables(self, daytime_override: bool | None = None):
        if daytime_override is None:
            daytime = self.night_control.night_phase == "Day"
        else:
            daytime = daytime_override
        model, (assigned_char, _, _, tokens, is_evil, _, _, _) = create_model(self, self.night, daytime)
        
        if daytime:
            n = 2*(self.night-1) + 1
        else:
            n = 2*(self.night-1)
        
        self.determine_possible_characters(model, assigned_char, tokens, n)

        if not evils_predetermined or ({t.name for t in self.token_list} & set(evil_alignment_token_names)):
            self.determine_possible_alignments(model, is_evil)
        
        if n > 0:
            dead_token_index = [t.name for t in self.token_list].index("dead")
            for i, p in enumerate(self.players):
                if p.dead:
                    continue
                if not self.variable_is_possible(model, tokens[-1][i][dead_token_index].Not()):
                    p.dead = True
        
        print(f"\n[{"Day" if daytime else "Night"} {self.night}] Current Possible Characters:")
        for p in self.players:
            print(f"{p.name}: {sorted(c.name for c in p.possible_characters)}")

    def determine_possible_alignments(
        self,
        model: cp_model.CpModel,
        is_evil: list[list[cp_model.IntVar]],
    ):
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

    def determine_possible_characters(
        self,
        model: cp_model.CpModel,
        assigned_char: list[list[list[cp_model.IntVar]]],
        tokens: list[list[list[cp_model.IntVar]]],
        n: int,
    ):
        character_change_token_indexes = [
            i
            for i, t in enumerate(self.token_list)
            if t.name in character_change_token_names
        ]
        
        for i, p in enumerate(self.players):
            possible_characters: list[Character] = []
            p_can_change_character = model.new_bool_var(f"{p}_can_change_character")
            model.add_max_equality(
                p_can_change_character,
                [
                    tokens[-1][i][t]
                    for t in character_change_token_indexes
                ]
            )
            keep_previous_impossible_chars = (n == 0 or not self.variable_is_possible(model, p_can_change_character))
            chars_to_test = []
            if not n % 2 and self.all_night_choices[n][i]:
                p_info = [
                    self.all_night_choices[n][i][0] is not None,
                    self.all_night_choices[n][i][1] is not None,
                    self.all_night_choices[n][i][2] is not None
                ]
                for c in self.character_list:
                    if keep_previous_impossible_chars and c not in p.night_or_day_start_possible_characters:
                        continue
                    c_info = []
                    if isinstance(c.targets, bool):
                        c_info.append(c.targets)
                    elif c.targets.__name__ == "<lambda>":
                        c_info.append(c.targets(n=n))
                    else:
                        c_info.append("unknown")
                    if c.char_index_learned == -1:
                        c_info.append(False)
                    else:
                        c_info.append("unknown")
                    if c.number_learned == -1:
                        c_info.append(False)
                    else:
                        c_info.append("unknown")
                    for p_i, c_i in zip(p_info, c_info):
                        if isinstance(c_i, bool) and p_i != c_i:
                            break
                    else:
                        if (
                            n == 0 and player_count > 6
                            and c.character_type == "demon"
                            and self.all_chosen_bluff_indexes[i] is None
                        ):
                            continue
                        chars_to_test.append(c)
            elif n % 2 and self.all_day_choices[n][0][i] and self.all_day_choices[n][0][i][0] is not None:
                chars_to_test = [c for c in self.character_list if c.name == "puzzlemaster"]
            else:
                if keep_previous_impossible_chars:
                    chars_to_test = p.night_or_day_start_possible_characters
                else:
                    chars_to_test = self.character_list
            
            if len(chars_to_test) == 1:
                p.possible_characters = chars_to_test
            else:
                for c in chars_to_test:
                    if self.variable_is_possible(model, assigned_char[-1][i][self.character_list.index(c)]):
                        possible_characters.append(c)
                p.possible_characters = possible_characters
            if len(p.possible_characters) == 1:
                #TODO improve
                print(f"{p.name} is {p.possible_characters[0].name}")
            print(f"{i+1}/{len(self.players)}")

    def game_end_sequence(
        self,
        model: cp_model.CpModel,
        daytime: bool,
        assigned_char: list[list[list[cp_model.IntVar]]],
        target: list[list[list[cp_model.IntVar]]],
        learned_char: list[list[list[cp_model.IntVar]]],
        tokens: list[list[list[cp_model.IntVar]]],
        is_evil: list[list[cp_model.IntVar]]
        ):
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
        #TODO

    def toggle_alignments(self, set_toggle=None) -> None:
        if set_toggle is None:
            set_toggle = not self.show_alignments
        self.show_alignments = set_toggle
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
        set_solver_parameters(solver)
        model.add_assumption(variable)
        possible = bool(solver.solve(model) in (cp_model.OPTIMAL, cp_model.FEASIBLE))
        model.clear_assumptions()
        return possible


print("\nScripts:")
for i, name in enumerate(scripts, start=1):
    print(f"({i}). {name}")
script_index = int(input("Number: ")) - 1

player_count = int(input("Number of players: "))
while player_count not in range(5, 16):
    player_count = int(input("Number of players: "))

evils_predetermined = input("Evil players predetermined? Y/N: ").lower()
while evils_predetermined not in ["y", "n"]:
    evils_predetermined = input("Evil players predetermined? Y/N: ").lower()
evils_predetermined = evils_predetermined == "y"

root = QuantumClocktower(player_count, script_index, evils_predetermined)
root.mainloop()
