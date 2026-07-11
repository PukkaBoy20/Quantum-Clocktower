from chars import Player, get_character, evil_alignment_token_names, initial_extra_demon_token_names, character_change_token_names, good_wins_token_names, evil_wins_token_names
from ortools.sat.python import cp_model

from typing import TYPE_CHECKING

from util import evil_count, outsider_count

if TYPE_CHECKING:
    from root import QuantumClocktower


def create_model(
    clocktower: "QuantumClocktower",
    night: int,
    daytime: bool,
    player_making_choice: "Player | None" = None,
    chosen_player: "Player | None" = None,
):
    """Returns (model, variables)\n
    where variables = (assigned_char, target, player_learned, tokens, is_evil, good_wins, evil_wins, game_over)"""
    model = cp_model.CpModel()

    player_count = len(clocktower.players)
    if player_making_choice is not None:
        player_making_choice_index = clocktower.players.index(player_making_choice)
    else:
        player_making_choice_index = None
    
    assigned_char: list[list[list]] = [[] for _ in range(2*(night-1) + 1)]
    target: list[list[list]] = [[] for _ in range(2*(night-1) + 1)]
    player_learned: list[list[list]] = [[] for _ in range(2*(night-1) + 1)]
    tokens: list[list[list]] = [[] for _ in range(2*(night-1) + 1)]
    is_evil: list[list] = [[] for _ in range(2*(night-1) + 1)]
    good_wins = []
    evil_wins = []
    game_ended = []
    if daytime:
        assigned_char.append([])
        target.append([])
        player_learned.append([])
        tokens.append([])
        is_evil.append([])
    
    if daytime:
        now = 2*(night-1) + 1
    else:
        now = 2*(night-1)
    # Night and Day Constraints
    for n in range(now+1):
        for p in range(player_count):
            assigned_char[n].append([])
            target[n].append([])
            player_learned[n].append([])
            tokens[n].append([])
            for c in range(len(clocktower.character_list)):
                assigned_char[n][p].append(model.new_bool_var(f"assigned_char_{n}_{p}_{c}"))
            for q in range(player_count):
                target[n][p].append(model.new_bool_var(f"target_{n}_{p}_{q}"))
                player_learned[n][p].append(model.new_bool_var(f"player_learned_{n}_{p}_{q}"))
            for t in range(len(clocktower.token_list)):
                tokens[n][p].append(model.new_bool_var(f"token_{n}_{p}_{t}"))

        set_is_evil(clocktower, model, player_count, assigned_char, tokens, is_evil, n)
        
        # one character per person, max one target, max one player learned
        for p in range(player_count):
            model.add(sum(assigned_char[n][p]) == 1)
            model.add(sum(target[n][p]) <= 1)
            model.add(sum(player_learned[n][p]) <= 1)

        # correct targeting and player learned
        for p in range(player_count):
            p_can_target = model.new_bool_var(f"{n}_{p}_can_target")
            model.add(
                p_can_target
                == sum(
                    assigned_char[n][p][j]
                    for j, c in enumerate(clocktower.character_list)
                    if c.can_target(n)
                )
            )
            p_learns_player = model.new_bool_var(f"{n}_{p}_learns_player")
            model.add(
                p_learns_player
                == sum(
                    assigned_char[n][p][j]
                    for j, c in enumerate(clocktower.character_list)
                    if c.learns_player
                )
            )
            model.add(sum(target[n][p]) == p_can_target)
            model.add(sum(player_learned[n][p]) == p_learns_player)

        #TODO: uncomment when tokens are finished
        # tokens
        # for token in clocktower.token_list:
        #     if token.conditions is not None:
        #         token.conditions[0](
        #             model,
        #             clocktower.players,
        #             clocktower.token_list,
        #             tokens,
        #             n,
        #             character_list=clocktower.character_list,
        #             assigned_char=assigned_char,
        #             target=target,
        #             is_evil=is_evil
        #         )

        keep_character_across_nights(clocktower, model, player_count, assigned_char, tokens, n)

        victory_conditions(clocktower, model, player_count, assigned_char, tokens, good_wins, evil_wins, game_ended, n)
        model.add( #TODO change?
            sum(game_ended[:-1]) == 0
        )
        
        for p, choices in enumerate(clocktower.all_night_choices[n]):
            if not choices or (n == now and p == player_making_choice_index):
                continue
            number_learned, old_chosen_player = choices
            if old_chosen_player is None:
                model.add(
                    sum(target[n][p]) == 0
                )
            else:
                model.add(
                    target[n][p][clocktower.players.index(old_chosen_player)] == 1
                )
    
    # Setup constraints:
    set_demons(clocktower, model, player_count, assigned_char, tokens)
    set_outsiders(clocktower, model, player_count, assigned_char)
    # apply possible characters (due to alignment)
    for i, p in enumerate(clocktower.players):
        for j, c in enumerate(clocktower.character_list):
            if c not in p.possible_characters:
                model.add(assigned_char[0][i][j] == 0)
    # characters used at most once
    for c in range(len(clocktower.character_list)):
        model.add(sum(assigned_char[0][p][c] for p in range(player_count)) <= 1)
    # at most one alchemist
    alchemist_indexes = [
        j for j, c in enumerate(clocktower.character_list) if "alchemist" in c.name
    ]
    model.add(
        sum(assigned_char[0][p][c] for p in range(player_count) for c in alchemist_indexes)
        <= 1
    )
    
    if player_making_choice is not None:
        if chosen_player is None:
            model.add(sum(target[now][player_making_choice_index]) == 0)
        else:
            model.add(
                target[now][player_making_choice_index][
                    clocktower.players.index(chosen_player)
                ]
                == 1
            )

    variables = assigned_char, target, player_learned, tokens, is_evil, good_wins, evil_wins, game_ended
    return model, variables



def keep_character_across_nights(
    clocktower: "QuantumClocktower",
    model: cp_model.CpModel,
    player_count: int,
    assigned_char: list[list[list]],
    tokens: list[list[list]],
    n: int
    ):
    if n > 0:
        character_change_token_indexes = [
                j for j, c in enumerate(clocktower.character_list) if c.name in character_change_token_names
        ]
        for p in range(player_count):
            p_changed_character = model.new_bool_var(f"{p}_changed_character")
            if len(character_change_token_indexes) > 0:
                model.add_max_equality(
                        p_changed_character,
                        [tokens[n][p][t] for t in character_change_token_indexes]
                )
            else:
                model.add(p_changed_character == 0)
            for a, b in zip(assigned_char[n][p], assigned_char[n-1][p]):
                model.add(a == b).only_enforce_if(p_changed_character.Not())



def victory_conditions(
    clocktower: "QuantumClocktower",
    model: cp_model.CpModel,
    player_count: int,
    assigned_char: list[list[list[cp_model.IntVar]]],
    tokens: list[list[list[cp_model.IntVar]]],
    good_wins: list,
    evil_wins: list,
    game_ended: list,
    n: int
    ):
    good_won = model.new_bool_var(f"{n}_good_won")
    good_wins.append(good_won)
    evil_won = model.new_bool_var(f"{n}_evil_won")
    evil_wins.append(evil_won)
    game_end = model.new_bool_var(f"{n}_game_end")
    game_ended.append(game_end)
    good_wins_token_indexes = [
        i for i, t in enumerate(clocktower.token_list)
        if t.name in good_wins_token_names
    ]
    evil_wins_token_indexes = [
        i for i, t in enumerate(clocktower.token_list)
        if t.name in evil_wins_token_names
    ]
    all_demons_dead = model.new_bool_var(f"{n}_all_demons_dead")
    demon_indexes = [
        j for j, c in enumerate(clocktower.character_list)
        if c.character_type == "demon"
    ]
    dead_token_index = [t.name for t in clocktower.token_list].index("dead")
    living_demons = []
    for p in range(player_count):
        for c in demon_indexes:
            p_is_living_demon_c = model.new_bool_var(f"{p}_is_living_demon_{c}")
            model.add_min_equality(
                p_is_living_demon_c,
                [
                    assigned_char[n][p][c],
                    tokens[n][p][dead_token_index].Not()
                ]
            )
            living_demons.append(p_is_living_demon_c)
    model.add_max_equality(
        all_demons_dead.Not(),
        living_demons
    )
    two_players_alive = model.new_bool_var(f"{n}_two_players_alive")
    model.add(
        sum(
            tokens[n][p][dead_token_index].Not()
            for p in range(player_count)
        ) < 3
    ).only_enforce_if(two_players_alive)
    model.add(
        sum(
            tokens[n][p][dead_token_index].Not()
            for p in range(player_count)
        ) > 2
    ).only_enforce_if(two_players_alive.Not())
    model.add_max_equality(
        good_won,
        [all_demons_dead] +
        [
            tokens[n][p][t]
            for p in range(player_count)
            for t in good_wins_token_indexes
        ]
    )
    model.add_max_equality(
        evil_won,
        [two_players_alive] +
        [
            tokens[n][p][t]
            for p in range(player_count)
            for t in evil_wins_token_indexes
        ]
    ).only_enforce_if(good_won.Not())
    model.add_implication(good_won, evil_won.Not())
    model.add_max_equality(
        game_end,
        [good_won, evil_won]
    )



def set_outsiders(
    clocktower: "QuantumClocktower",
    model: cp_model.CpModel,
    player_count: int,
    assigned_char: list[list]
    ):
    balloonist_effect = model.new_int_var(0, 1, "balloonist_effect")
    if "balloonist" in [c.name for c in clocktower.character_list]:
        balloonist_exists = model.new_bool_var("balloonist_exists")
        balloonist_index = clocktower.character_list.index(
            get_character("balloonist", clocktower.character_list)
        )
        model.add_max_equality(
            balloonist_exists,
            [assigned_char[0][p][balloonist_index] for p in range(player_count)]
        ) #TODO test
        model.add(balloonist_effect <= balloonist_exists)
    else:
        model.add(balloonist_effect == 0)
    ...
    model.add(
        sum(
            assigned_char[0][p][j]
            for p in range(player_count)
            for j, c in enumerate(clocktower.character_list)
            if c.character_type == "outsider"
        ) == outsider_count(player_count) + balloonist_effect
    )    
    


def set_demons(
    clocktower: "QuantumClocktower",
    model: cp_model.CpModel,
    player_count: int,
    assigned_char: list[list],
    tokens: list[list]
    ):
    initial_extra_demon_token_indexes = [
        i for i, t in enumerate(clocktower.token_list) if t.name in initial_extra_demon_token_names
    ]
    extra_demons = model.new_int_var(0, len(initial_extra_demon_token_indexes), "extra_demons")
    model.add(
        extra_demons
        == sum(
            tokens[0][p][t]
            for t in initial_extra_demon_token_indexes
            for p in range(player_count)
        )
    )
    model.add(
        sum(
            assigned_char[0][p][j]
            for j, c in enumerate(clocktower.character_list)
            if c.character_type == "demon"
            for p in range(player_count)
        ) == 1 + extra_demons
    )
    for p in range(player_count):
        p_is_extra_demon = model.new_bool_var(f"{p}_is_extra_demon")
        if len(initial_extra_demon_token_indexes) > 0:
            model.add_max_equality(
                p_is_extra_demon,
                [tokens[0][p][t] for t in initial_extra_demon_token_indexes]
        )
        else:
            model.add(p_is_extra_demon == 0)
        p_is_demon = model.new_bool_var(f"{p}_is_demon")
        model.add_max_equality(
            p_is_demon,
            [p_is_extra_demon] +
            [
                assigned_char[0][p][j]
                for j, c in enumerate(clocktower.character_list)
                if c.character_type == "demon"
            ]
        )



def set_is_evil(
    clocktower: "QuantumClocktower",
    model: cp_model.CpModel,
    player_count: int,
    assigned_char: list[list],
    tokens: list[list],
    is_evil: list[list],
    n: int
):
    """
    Sets is_evil and the number of evil players at setup
    """ # setup constraint is set here basically just because of Lord of Typhon and Legion
    evil_alignment_token_indexes = [
        i for i, t in enumerate(clocktower.token_list) if t.name in evil_alignment_token_names
    ]
    extra_evils = model.new_int_var(0, len(evil_alignment_token_indexes), f"extra_evils_{n}")
    model.add(
        extra_evils
        == sum(
            tokens[n][p][t]
            for t in evil_alignment_token_indexes
            for p in range(player_count)
        )
    )
    for p in range(player_count):
        p_turned_evil = model.new_bool_var(f"{p}_turned_evil_{n}")
        if len(evil_alignment_token_indexes) > 0:
            model.add_max_equality(
                p_turned_evil, [tokens[n][p][t] for t in evil_alignment_token_indexes]
            )
        else:
            model.add(p_turned_evil == 0)
        p_is_evil = model.new_bool_var(f"{p}_is_evil_{n}")
        model.add_max_equality(
            p_is_evil,
            [p_turned_evil] +
            [
                assigned_char[n][p][j]
                for j, c in enumerate(clocktower.character_list)
                if c.alignment == "evil"
            ]
        )
        is_evil[n].append(p_is_evil)
    if n == 0:
        model.add(sum(is_evil[0]) == evil_count(player_count) + extra_evils)
