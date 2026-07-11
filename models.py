from chars import Player, get_character
from ortools.sat.python import cp_model

from typing import TYPE_CHECKING

from util import evil_count, outsider_count

if TYPE_CHECKING:
    from root import QuantumClocktower


def first_night_model(
    clocktower: "QuantumClocktower",
    player_making_choice: "Player | None" = None,
    chosen_player: "Player | None" = None,
):
    """Returns (model, variables)\n
    where variables = (assigned_char, target, player_learned, tokens, is_evil)"""
    model = cp_model.CpModel()

    player_count = len(clocktower.players)

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
        for c in range(len(clocktower.character_list)):
            assigned_char[p].append(model.new_bool_var(f"assigned_char_{p}_{c}"))
        for q in range(player_count):
            target[p].append(model.new_bool_var(f"target_{p}_{q}"))
            player_learned[p].append(model.new_bool_var(f"player_learned_{p}_{q}"))
        for t in range(len(clocktower.token_list)):
            tokens[p].append(model.new_bool_var(f"token_{p}_{t}"))
            current_tokens[p].append(model.new_constant(0))

    evil_alignment_token_indexes = [
        i for i, t in enumerate(clocktower.token_list) if t.name in ("goon_evil",)
    ]
    extra_evils = model.new_int_var(0, len(evil_alignment_token_indexes), "extra_evils")
    model.add(
        extra_evils
        == sum(
            tokens[p][t]
            for t in evil_alignment_token_indexes
            for p in range(player_count)
        )
    )
    is_evil = [model.new_bool_var(f"is_evil_{p}") for p in range(player_count)]
    model.add(sum(is_evil) == evil_count(player_count) + extra_evils)
    for p in range(player_count):
        p_turned_evil = model.new_bool_var(f"{p}_turned_evil")
        model.add_max_equality(
            p_turned_evil, [tokens[p][t] for t in evil_alignment_token_indexes]
        )
        p_is_evil = model.new_bool_var(f"{p}_is_evil")
        model.add_bool_or(
            p_turned_evil,
            sum(
                assigned_char[p][j]
                for j, c in enumerate(clocktower.character_list)
                if c.alignment == "evil"
            )
            == 1,
        ).only_enforce_if(p_is_evil)
        model.add_bool_and(
            p_turned_evil.Not(),
            sum(
                assigned_char[p][j]
                for j, c in enumerate(clocktower.character_list)
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
    for c in range(len(clocktower.character_list)):
        model.add(sum(assigned_char[p][c] for p in range(player_count)) <= 1)
    # apply possible characters
    for i, p in enumerate(clocktower.players):
        for j, c in enumerate(clocktower.character_list):
            if c not in p.possible_characters:
                model.add(assigned_char[i][j] == 0)
    # must have one demon
    model.add(
        sum(
            assigned_char[p][j]
            for j, c in enumerate(clocktower.character_list)
            if c.character_type == "demon"
            for p in range(player_count)
        )
        == 1
    )
    # correct number of outsiders
    balloonist_exists = model.new_bool_var("balloonist_exists")
    balloonist_index = clocktower.character_list.index(
        get_character("balloonist", clocktower.character_list)
    )
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
                for j, c in enumerate(clocktower.character_list)
                if c.character_type == "outsider"
            ),
        ],
        [
            (0, outsider_count(player_count)),
            (1, outsider_count(player_count)),
            (1, outsider_count(player_count) + 1),
        ],
    )
    # correct targeting and player learned
    for p in range(player_count):
        p_can_target = model.new_bool_var("")
        model.add(
            p_can_target
            == sum(
                assigned_char[p][j]
                for j, c in enumerate(clocktower.character_list)
                if c.can_target_night_1 == True
            )
        )
        p_learns_player = model.new_bool_var("")
        model.add(
            p_learns_player
            == sum(
                assigned_char[p][j]
                for j, c in enumerate(clocktower.character_list)
                if c.learns_player == True
            )
        )
        model.add(sum(target[p]) == p_can_target)
        model.add(sum(player_learned[p]) == p_learns_player)
    # tokens
    for token in clocktower.token_list:
        if token.conditions is not None:
            token.conditions[0](
                model,
                clocktower.players,
                clocktower.token_list,
                tokens,
                character_list=clocktower.character_list,
                assigned_char=assigned_char,
                target=target,
                current_tokens=current_tokens,
                is_evil=is_evil,
            )  # type: ignore

    # at most one alchemist
    alchemist_indexes = [
        j for j, c in enumerate(clocktower.character_list) if "alchemist" in c.name
    ]
    model.add(
        sum(assigned_char[p][c] for p in range(player_count) for c in alchemist_indexes)
        <= 1
    )

    if player_making_choice is not None:
        player_making_choice_index = clocktower.players.index(player_making_choice)
        if chosen_player is None:
            model.add(sum(target[player_making_choice_index]) == 0)
        else:
            model.add(
                target[player_making_choice_index][
                    clocktower.players.index(chosen_player)
                ]
                == 1
            )

        for (
            player,
            _,
            chosen_player,
        ) in clocktower.previous_night_choices:  # TODO: move out of if statement?
            player_index = clocktower.players.index(player)
            if chosen_player is None:
                model.add(sum(target[player_index]) == 0)
            else:
                model.add(
                    target[player_index][clocktower.players.index(chosen_player)] == 1
                )

    return model, variables
