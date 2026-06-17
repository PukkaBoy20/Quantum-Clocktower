import tkinter as tk
from tkinter import ttk
import math
import random
from copy import copy
from ortools.sat.python import cp_model
from chars import (
    teensy_char_list,
    teensy_token_list,
    Player,
    Character,
    Token,
    get_character,
)


class SeatMenu(tk.Menu):
    def __init__(self, master=None, current_seat: Seat = None, **kwargs):
        super().__init__(master, **kwargs)
        self.current_seat = current_seat


EVIL_COLOUR = "#FF7C7A"
GOOD_COLOUR = "light blue"
QUANTUM_COLOUR = "blue violet"
night_num = 1

scripts = [[teensy_char_list, teensy_token_list]]
script_index = int(input("\nScripts:\n1. Teensy\nNumber: ")) - 1
character_list: list[Character] = scripts[script_index][0]
token_list: list[Token] = scripts[script_index][1]

player_count = int(input("Number of players: "))

if player_count < 4:
    raise ValueError 
elif player_count < 10:
    evil_count = 2
elif player_count < 13:
    evil_count = 3
elif player_count < 16:
    evil_count = 4
else:
    raise ValueError

evils_predetermined = input("Evil players predetermined? y/n: ").lower()
if evils_predetermined in ["y", "n"]:
    evils_predetermined = evils_predetermined == "y"
else:
    raise ValueError

if player_count < 7:
    outsider_count = (player_count - 2) % 3
else:
    outsider_count = (player_count - 1) % 3

all_night_decisions: list[list] = []


def first_night_model(
    player_making_choice: Player = None, chosen_player: Player = None
):
    """Returns (model, variables)\n
    where variables = (assigned_char, target, player_learned, tokens, is_evil)"""
    model = cp_model.CpModel()

    assigned_char: list[list] = []
    target: list[list] = []
    player_learned: list[list] = []
    tokens: list[list] = []
    current_tokens: list[list] = []
    for p in range(player_count):
        assigned_char.append([])
        target.append([])
        player_learned.append([])
        tokens.append([])
        current_tokens.append([])
        for c in range(len(character_list)):
            assigned_char[p].append(model.new_bool_var(f"assigned_char_{p}_{c}"))
        for q in range(len(player_list)):
            target[p].append(model.new_bool_var(f"target_{p}_{q}"))
            player_learned[p].append(model.new_bool_var(f"player_learned_{p}_{q}"))
        for t in range(len(token_list)):
            tokens[p].append(model.new_bool_var(f"token_{p}_{t}"))
            current_tokens[p].append(model.new_constant(0))

    evil_alignment_token_indexes = [
        i for i, t in enumerate(token_list) if t.name in ("goon_evil",)
    ]
    extra_evils = model.new_int_var(0, len(evil_alignment_token_indexes), "extra_evils")
    model.add(
        extra_evils
        == sum(
            tokens[p][t]
            for t in evil_alignment_token_indexes
            for p in range(len(player_list))
        )
    )
    is_evil = [model.new_bool_var(f"is_evil_{p}") for p in range(len(player_list))]
    model.add(sum(is_evil) == evil_count + extra_evils)
    for p in range(len(player_list)):
        p_turned_evil = model.new_bool_var(f"{p}_turned_evil")
        model.add_max_equality(
            p_turned_evil, [tokens[p][t] for t in evil_alignment_token_indexes]
        )
        p_is_evil = model.new_bool_var(f"{p}_is_evil")
        model.add_bool_or(
            p_turned_evil,
            sum(
                assigned_char[p][j]
                for j, c in enumerate(character_list)
                if c.alignment == "evil"
            )
            == 1,
        ).only_enforce_if(p_is_evil)
        model.add_bool_and(
            p_turned_evil.Not(),
            sum(
                assigned_char[p][j]
                for j, c in enumerate(character_list)
                if c.alignment == "evil"
            )
            == 0,
        ).only_enforce_if(p_is_evil.Not())
        model.add(is_evil[p] == 1).only_enforce_if(p_is_evil)
        model.add(is_evil[p] == 0).only_enforce_if(p_is_evil.Not())

    variables = assigned_char, target, player_learned, tokens, is_evil

    # one character per person, max one target, max one player learned
    for p in range(player_count):
        model.add(sum(assigned_char[p]) == 1)
        model.add(sum(target[p]) <= 1)
        model.add(sum(player_learned[p]) <= 1)
    # characters used at most once
    for c in range(len(character_list)):
        model.add(sum(assigned_char[p][c] for p in range(len(player_list))) <= 1)
    # apply possible characters
    for i, p in enumerate(player_list):
        for j, c in enumerate(character_list):
            if c not in p.possible_characters:
                model.add(assigned_char[i][j] == 0)
    # must have one demon
    model.add(
        sum(
            assigned_char[p][j]
            for j, c in enumerate(character_list)
            if c.character_type == "demon"
            for p in range(player_count)
        )
        == 1
    )
    # correct number of outsiders
    balloonist_exists = model.new_bool_var("balloonist_exists")
    balloonist_index = character_list.index(get_character("balloonist", character_list))
    model.add(
        sum(assigned_char[p][balloonist_index] for p in range(player_count)) == 1
    ).only_enforce_if(balloonist_exists)
    model.add(
        sum(assigned_char[p][balloonist_index] for p in range(player_count)) == 0
    ).only_enforce_if(balloonist_exists.Not())
    model.add_allowed_assignments(
        [
            balloonist_exists,
            sum(
                assigned_char[p][j]
                for p in range(player_count)
                for j, c in enumerate(character_list)
                if c.character_type == "outsider"
            ),
        ],
        [(0, outsider_count), (1, outsider_count), (1, outsider_count + 1)],
    )
    # correct targeting and player learned
    for p in range(player_count):
        p_can_target = model.new_bool_var("")
        model.add(
            p_can_target
            == sum(
                assigned_char[p][j]
                for j, c in enumerate(character_list)
                if c.can_target_night_1 == True
            )
        )
        p_learns_player = model.new_bool_var("")
        model.add(
            p_learns_player
            == sum(
                assigned_char[p][j]
                for j, c in enumerate(character_list)
                if c.learns_player == True
            )
        )
        model.add(sum(target[p]) == p_can_target)
        model.add(sum(player_learned[p]) == p_learns_player)
    # tokens
    for token in token_list:
        if token.conditions is not None:
            token.conditions[0](
                model,
                player_list,
                token_list,
                tokens,
                character_list=character_list,
                assigned_char=assigned_char,
                target=target,
                current_tokens=current_tokens,
                is_evil=is_evil,
            )

    # at most one alchemist
    alchemist_indexes = [
        j for j, c in enumerate(character_list) if "alchemist" in c.name
    ]
    model.add(
        sum(
            assigned_char[p][c]
            for p in range(len(player_list))
            for c in alchemist_indexes
        )
        <= 1
    )

    if player_making_choice != None:
        player_making_choice_index = player_list.index(player_making_choice)
        if chosen_player == None:
            model.add(sum(target[player_making_choice_index]) == 0)
        else:
            model.add(
                target[player_making_choice_index][player_list.index(chosen_player)]
                == 1
            )

        for (
            player,
            _,
            chosen_player,
        ) in previous_night_decisions:  # TODO: move out of if statement?
            player_index = player_list.index(player)
            if chosen_player == None:
                model.add(sum(target[player_index]) == 0)
            else:
                model.add(target[player_index][player_list.index(chosen_player)] == 1)

    return model, variables


def end_night():
    if not night_finished():
        return

    if night_num == 1:
        if script_index != 0:
            raise NotImplementedError
        model, variables = first_night_model()

        assigned_char, target, player_learned, tokens, is_evil = variables
        possible_char_indexes: list[list] = [[] for _ in player_list]
        for i, p in enumerate(player_list):
            for c in range(len(character_list)):
                if variable_is_possible(assigned_char[i][c]):
                    possible_char_indexes[i].append(1)
                else:
                    possible_char_indexes[i].append(0)
            p.possible_characters = [
                character_list[c]
                for c in range(len(character_list))
                if possible_char_indexes[i][c]
            ]
            if len(p.possible_characters) == 1:
                ...

        possible_alignment_indexes: list[list] = [[] for _ in player_list]
        for i, p in enumerate(player_list):
            if variable_is_possible(is_evil[i]):
                possible_alignment_indexes[i].append(1)
            else:
                possible_alignment_indexes[i].append(0)
            if variable_is_possible(is_evil[i].Not()):
                possible_alignment_indexes[i].append(1)
            else:
                possible_alignment_indexes[i].append(0)
            if sum(possible_alignment_indexes[i]) == 1:
                p.alignment = "evil" if possible_alignment_indexes[0] else "good"
            else:
                p.alignment = None

        # possible_token_indexes: list[list] = [[] for _ in player_list]
        # for i, p in enumerate(player_list):
        #     for t in range(len(token_list)):
        #         if variable_is_possible(tokens[i][t]):
        #             possible_token_indexes[i].append(1)
        #         else:
        #             possible_token_indexes[i].append(0)
        #     p.tokens

    all_night_decisions.append(previous_night_decisions)

    toggle_alignments(False)
    end_night_button.config(state="disabled")
    start_night_button.config(state="normal")
    executee_selector.config(state="readonly")
    night_phase.set("Day")
    for seat in seat_list:
        seat.config(text="")


def variable_is_possible(variable):
    solver = cp_model.CpSolver()
    test_model, (_, target, _, _, _) = first_night_model()
    test_model.add(variable == 1)
    for player, _, chosen_player in previous_night_decisions:
        player_index = player_list.index(player)
        if chosen_player == None:
            test_model.add(sum(target[player_index]) == 0)
        else:
            test_model.add(target[player_index][player_list.index(chosen_player)] == 1)
    return bool(solver.solve(test_model) in (cp_model.OPTIMAL, cp_model.FEASIBLE))



def toggle_alignments(alignments_enabled="change"):
    if alignments_enabled == "change":
        if seat_list[0].cget("highlightbackground") not in [
            EVIL_COLOUR,
            GOOD_COLOUR,
            QUANTUM_COLOUR,
        ]:
            alignments_enabled = True
        else:
            alignments_enabled = False
    if alignments_enabled:
        for i, seat in enumerate(seat_list):
            if player_list[i].alignment == "evil":
                seat.config(highlightbackground=EVIL_COLOUR)
            elif player_list[i].alignment == "good":
                seat.config(highlightbackground=GOOD_COLOUR)
            else:
                seat.config(highlightbackground=QUANTUM_COLOUR)
    elif not alignments_enabled:
        for seat in seat_list:
            seat.config(highlightbackground="systemWindowBackgroundColor")
