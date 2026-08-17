from chars import Player, get_character, evil_alignment_token_names, evil_registration_token_names, initial_extra_demon_token_names, character_change_token_names, demon_safe_token_names, winning_token_names, losing_token_names, evil_winning_token_names
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
    character_learned_index: int | None = None,
    chosen_bluff_indexes: tuple | None = None,
    number_learned: int | None = None,
    barber_swapped_player_indexes: list | None = None,
    puzzlemaster_guess_index: int | None = None,
    puzzlemaster_demon_player_learned_index: int | None = None,
    damsel_guess_index: int | None = None,
):
    """Returns (model, variables)
    
    where variables = (assigned_char, target, learned_char, tokens, is_evil, good_wins, evil_wins, game_over)
    """
    model = cp_model.CpModel()

    player_count = len(clocktower.players)
    if player_making_choice is not None:
        player_making_choice_index = clocktower.players.index(player_making_choice)
    else:
        player_making_choice_index = None
    
    if daytime:
        now = 2*(night-1) + 1
    else:
        now = 2*(night-1)
    
    assigned_char: list[list[list[cp_model.IntVar]]] = [[] for _ in range(now+1)]
    target: list[list[list[cp_model.IntVar]]] = [[] for _ in range(now+1)]
    learned_char: list[list[list[cp_model.IntVar]]] = [[] for _ in range(now+1)]
    num_learned: list[list[cp_model.IntVar]] = [[] for _ in range(now+1)]
    tokens: list[list[list[cp_model.IntVar]]] = [[] for _ in range(now+1)]
    is_evil: list[list[cp_model.IntVar]] = [[] for _ in range(now+1)]
    registers_as_evil: list[list[cp_model.IntVar]] = [[] for _ in range(now+1)]
    remembered_tokens: list[list[list[cp_model.IntVar]]] = [[] for _ in range(now+1)] # mainly used for stuff like faux paw
    mad_char: list[list[list[cp_model.IntVar]]] = [[] for _ in range(now+1)]
    abnormal_ability: list[list[cp_model.IntVar]] = [[] for _ in range(now+1)] # for mathematician
    barber_swap_indexes: list[list[tuple[cp_model.IntVar]]] = [[] for _ in range(now+1)]
    droisoned: list[list[cp_model.IntVar]] = [[] for _ in range(now+1)]
    vortoxed: list[list[cp_model.IntVar]] = [[] for _ in range(now+1)]
    puzzlemaster_guess: list[list[list[cp_model.IntVar]]] = [[] for _ in range(now+1)]
    puzzlemaster_demon_learned: list[list[list[cp_model.IntVar]]] = [[] for _ in range(now+1)]
    damsel_guess: list[list[list[cp_model.IntVar]]] = [[] for _ in range(now+1)]
    damsel_guess_order: list[list[cp_model.IntVar]] = [[] for _ in range(now+1)]
    good_wins: list[cp_model.IntVar] = []
    evil_wins: list[cp_model.IntVar] = []
    game_ended: list[cp_model.IntVar] = []
    

    for n in range(now+1):
        for p in range(player_count):
            assigned_char[n].append([])
            target[n].append([])
            learned_char[n].append([])
            tokens[n].append([])
            remembered_tokens[n].append([])
            mad_char[n].append([])
            puzzlemaster_guess[n].append([])
            puzzlemaster_demon_learned[n].append([])
            damsel_guess[n].append([])
            for c in range(len(clocktower.character_list)):
                assigned_char[n][p].append(model.new_bool_var(f"assigned_char_{n}_{p}_{c}"))
                learned_char[n][p].append(model.new_bool_var(f"character_learned_{n}_{p}_{c}"))
                mad_char[n][p].append(model.new_bool_var(f"mad_char_{n}_{p}_{c}"))
            for q in range(player_count):
                target[n][p].append(model.new_bool_var(f"target_{n}_{p}_{q}"))
                puzzlemaster_guess[n][p].append(model.new_bool_var(f"puzzlemaster_guess_{n}_{p}_{q}"))
                puzzlemaster_demon_learned[n][p].append(model.new_bool_var(f"puzzlemaster_demon_learned_{n}_{p}_{q}"))
                damsel_guess[n][p].append(model.new_bool_var(f"damsel_guess_{n}_{p}_{q}"))
            for t in range(len(clocktower.token_list)):
                tokens[n][p].append(model.new_bool_var(f"token_{n}_{p}_{t}"))
                remembered_tokens[n][p].append(model.new_bool_var(f"remembered_token_{n}_{p}_{t}"))
            num_learned[n].append(model.new_int_var(-1, player_count, f"num_learned_{n}_{p}"))
            abnormal_ability[n].append(model.new_bool_var(f"abnormal_ability_{n}_{p}"))
            droisoned[n].append(model.new_bool_var(f"{p}_is_droisoned_{n}"))
            vortoxed[n].append(model.new_bool_var(f"{p}_is_vortoxed_{n}"))
            barber_swap_indexes[n].append(
                (
                    model.new_int_var(-1, player_count-1, f"barber_swap_index_{n}_{p}_1"),
                    model.new_int_var(-1, player_count-1, f"barber_swap_index_{n}_{p}_2")
                )
            )
            damsel_guess_order[n].append(model.new_int_var(0, player_count-1, f"damsel_guess_order_{n}_{p}"))
            
        set_is_evil(clocktower, model, player_count, assigned_char, tokens, is_evil, n)
        for p in range(player_count):
            registers_as_evil[n].append(model.new_bool_var(f"{p}_registers_as_evil_{n}"))
            evil_registration_token_indexes = [
                i
                for i, t in enumerate(clocktower.token_list)
                if t.name in evil_registration_token_names
            ]
            model.add_max_equality(
                registers_as_evil[n][p],
                [is_evil[n][p]]
                + [
                    tokens[n][q][t]
                    for t in evil_registration_token_indexes
                ]
            )
        set_droisoning(clocktower, model, player_count, tokens, droisoned, n)
        set_vortoxed(clocktower, model, player_count, assigned_char, tokens, droisoned, vortoxed, n)
        set_barber_swap_indexes(clocktower, model, player_count, assigned_char, tokens, barber_swap_indexes, n)
        set_night_info_restrictions(
            clocktower,
            model,
            player_count,
            assigned_char,
            target,
            learned_char,
            num_learned,
            tokens,
            is_evil,
            registers_as_evil,
            abnormal_ability,
            droisoned,
            vortoxed,
            n,
        )
        set_damsel_guess_order(clocktower, model, player_count, damsel_guess, damsel_guess_order, n)
        set_puzzlemaster_guess_restrictions(
            clocktower,
            model,
            player_count,
            assigned_char,
            tokens,
            droisoned,
            puzzlemaster_guess,
            puzzlemaster_demon_learned,
            n,
        )
        
        
        
        for p in range(player_count):
            model.add_exactly_one(assigned_char[n][p])
            
            model.add_at_most_one(target[n][p])
            model.add_at_most_one(learned_char[n][p])
            model.add_at_most_one(puzzlemaster_guess[n][p])
            model.add_at_most_one(puzzlemaster_demon_learned[n][p])
            model.add_at_most_one(damsel_guess[n][p])

        if "atheist" in [c.name for c in clocktower.character_list]:
            atheist_index = [c.name for c in clocktower.character_list].index("atheist")
            model.add(
                sum(
                    assigned_char[n][p][atheist_index]
                    for p in range(player_count)
                ) == 0
            )
        
        for token in clocktower.token_list:
            if token.conditions is not None:
                token.conditions(
                    model,
                    clocktower.players,
                    clocktower.token_list,
                    tokens,
                    n,
                    character_list=clocktower.character_list,
                    assigned_char=assigned_char,
                    target=target,
                    learned_char=learned_char,
                    num_learned=num_learned,
                    is_evil=is_evil,
                    registers_as_evil=registers_as_evil,
                    executed_indexes=clocktower.executed_indexes,
                    remembered_tokens=remembered_tokens,
                    mad_char=mad_char,
                    abnormal_ability=abnormal_ability,
                    barber_swap_indexes=barber_swap_indexes,
                    droisoned=droisoned,
                    vortoxed=vortoxed,
                    puzzlemaster_guess=puzzlemaster_guess,
                    damsel_guess=damsel_guess,
                    damsel_guess_order=damsel_guess_order,
                )

        keep_character_across_nights(clocktower, model, player_count, assigned_char, tokens, n)

        victory_conditions(
            clocktower,
            model,
            player_count,
            assigned_char,
            tokens,
            registers_as_evil,
            good_wins,
            evil_wins,
            game_ended,
            n
        )
        
        if not n % 2:
            for p, choices in enumerate(clocktower.all_night_choices[n]):
                if not choices or (n == now and p == player_making_choice_index):
                    continue
                old_chosen_player, old_character_learned_index, old_number_learned, old_barber_swapped_player_indexes = choices
                if old_chosen_player is None:
                    model.add(
                        sum(target[n][p]) == 0
                    )
                else:
                    model.add(
                        target[n][p][clocktower.players.index(old_chosen_player)] == 1
                    )
                if old_character_learned_index is None:
                    model.add(
                        sum(learned_char[n][p]) == 0
                    )
                else:
                    model.add(
                        learned_char[n][p][old_character_learned_index] == 1
                    )
                if old_number_learned is None:
                    model.add(
                        num_learned[n][p] == -1
                    )
                else:
                    model.add(
                        num_learned[n][p] == old_number_learned
                    )
                if old_barber_swapped_player_indexes is None:
                    model.add(
                        barber_swap_indexes[n][p][0] == -1
                    )
                    model.add(
                        barber_swap_indexes[n][p][1] == -1
                    )
                else:
                    model.add(
                        barber_swap_indexes[n][p][0] == old_barber_swapped_player_indexes[0]
                    )
                    model.add(
                        barber_swap_indexes[n][p][1] == old_barber_swapped_player_indexes[1]
                    )
        else:
            for p in range(player_count):
                for q in range(player_count):
                    model.add(target[n][p][q] == 0)
                for c in range(len(clocktower.character_list)):
                    model.add(learned_char[n][p][c] == 0)
                model.add(num_learned[n][p] == -1)
                model.add(barber_swap_indexes[n][p][0] == -1)
                model.add(barber_swap_indexes[n][p][1] == -1)
        if n % 2:
            for p, choices in enumerate(clocktower.all_day_choices[n][0]): # NOTE: new day actions override previous ones
                if not choices or (n == now and p == player_making_choice_index):
                    continue
                old_puzzlemaster_guess_index, old_puzzlemaster_demon_player_learned_index, old_damsel_guess_index = choices

                if old_puzzlemaster_guess_index is None:
                    for q in range(player_count):
                        model.add(puzzlemaster_guess[n][p][q] == 0)
                else:
                    model.add(puzzlemaster_guess[n][p][old_puzzlemaster_guess_index] == 1)
                
                if old_puzzlemaster_demon_player_learned_index is None:
                    for q in range(player_count):
                        model.add(puzzlemaster_demon_learned[n][p][q] == 0)
                else:
                    model.add(puzzlemaster_demon_learned[n][p][old_puzzlemaster_demon_player_learned_index] == 1)
                
                if old_damsel_guess_index is None:
                    for q in range(player_count):
                        model.add(damsel_guess[n][p][q] == 0)
                else:
                    model.add(damsel_guess[n][p][old_damsel_guess_index] == 1)
        else:
            for p in range(player_count):
                for q in range(player_count):
                    model.add(puzzlemaster_guess[n][p][q] == 0)
                    model.add(puzzlemaster_demon_learned[n][p][q] == 0)
                    model.add(damsel_guess[n][p][q] == 0)
    
    model.add(sum(game_ended[:-1]) == 0) #TODO change?
    set_demons(clocktower, model, player_count, assigned_char, tokens)
    set_outsiders(clocktower, model, player_count, assigned_char)
    for i, p in enumerate(clocktower.players):
        for j, c in enumerate(clocktower.character_list):
            if c not in p.possible_starting_characters: # TODO would using p.possible_characters speed up solving?
                model.add(assigned_char[0][i][j] == 0)
    # characters used at most once
    for c in range(len(clocktower.character_list)):
        model.add(sum(assigned_char[0][p][c] for p in range(player_count)) <= 1)
    # at most one alchemist # NOTE: outdated
    alchemist_indexes = [
        j
        for j, c in enumerate(clocktower.character_list)
        if "alchemist" in c.name
    ]
    model.add_at_most_one(
        assigned_char[0][p][c]
        for p in range(player_count)
        for c in alchemist_indexes
    )
    
    if player_making_choice is not None:
        set_this_night_choice(
            clocktower,
            chosen_player,
            character_learned_index,
            number_learned,
            barber_swapped_player_indexes,
            model,
            player_making_choice_index,
            now,
            target,
            learned_char,
            num_learned,
            barber_swap_indexes,
        )
        set_this_day_choice(
            puzzlemaster_guess_index,
            puzzlemaster_demon_player_learned_index,
            damsel_guess_index,
            model,
            player_count,
            player_making_choice_index,
            puzzlemaster_guess,
            puzzlemaster_demon_learned,
            damsel_guess,
            now,
        )
    
    set_bluffs(clocktower, model, player_count, player_making_choice_index, chosen_bluff_indexes, assigned_char, now)

    variables = assigned_char, target, learned_char, tokens, is_evil, good_wins, evil_wins, game_ended
    return model, variables



def set_damsel_guess_order(
    clocktower: "QuantumClocktower",
    model: cp_model.CpModel,
    player_count: int,
    damsel_guess: list[list[list[cp_model.IntVar]]],
    damsel_guess_order: list[list[cp_model.IntVar]],
    n: int,
):
    if not n % 2:
        return
    for p in range(player_count):
        for i, damsel_guessing_player_index in enumerate(clocktower.all_day_choices[n][1]):
            if p == damsel_guessing_player_index:
                model.add(damsel_guess_order[n][p] == i)
                break
        else:
            p_damsel_guessed = model.new_bool_var(f"{p}_damsel_guessed_{n}")
            model.add(p_damsel_guessed == sum(damsel_guess[n][p]))
            model.add(
                damsel_guess_order[n][p]
                == len(clocktower.all_day_choices[n][1])
            ).only_enforce_if(p_damsel_guessed)
    model.add_all_different(damsel_guess_order[n])



def set_puzzlemaster_guess_restrictions(
    clocktower: "QuantumClocktower",
    model: cp_model.CpModel,
    player_count: int,
    assigned_char: list[list[list[cp_model.IntVar]]],
    tokens: list[list[list[cp_model.IntVar]]],
    droisoned: list[list[cp_model.IntVar]],
    puzzlemaster_guess: list[list[list[cp_model.IntVar]]],
    puzzlemaster_demon_learned: list[list[list[cp_model.IntVar]]],
    n: int,
):
    puzzlemaster_index = [c.name for c in clocktower.character_list].index("puzzlemaster")
    puzzledrunk_token_index = [t.name for t in clocktower.token_list].index("puzzledrunk")
    puzzlemaster_guess_used_token_index = [t.name for t in clocktower.token_list].index("puzzlemaster_guess_used")
    
    if not n % 2: # probably makes presolving faster
        for p in range(player_count):
            model.add(sum(puzzlemaster_guess[n][p]) == 0)
            model.add(sum(puzzlemaster_demon_learned[n][p]) == 0)
        return
    
    for p in range(player_count):
        model.add(sum(puzzlemaster_guess[n][p]) == sum(puzzlemaster_demon_learned[n][p]))
        model.add(sum(puzzlemaster_guess[n][p]) == 0).only_enforce_if(assigned_char[n][p][puzzlemaster_index].Not())
        model.add(sum(puzzlemaster_guess[n][p]) == 0).only_enforce_if(tokens[n][p][puzzlemaster_guess_used_token_index])
        
        p_puzzle_guessed = model.new_bool_var(f"{p}_puzzle_guessed_{n}")
        model.add(p_puzzle_guessed == sum(puzzlemaster_guess[n][p]))
        
        p_puzzle_guessed_correctly = model.new_bool_var(f"{p}_puzzle_guessed_correctly_{n}")
        guess_causes = []
        for q in range(player_count):
            p_puzzle_guessed_q_correctly = model.new_bool_var(f"{p}_puzzle_guessed_{q}_correctly_{n}")
            model.add_min_equality(
                p_puzzle_guessed_q_correctly,
                [
                    puzzlemaster_guess[n][p][q],
                    tokens[n][q][puzzledrunk_token_index]
                ]
            )
            guess_causes.append(p_puzzle_guessed_q_correctly)
        model.add_max_equality(p_puzzle_guessed_correctly, guess_causes)
        
        p_learned_demon = model.new_bool_var(f"{p}_puzzlemaster_learned_demon_{n}")
        learned_demon_causes = []
        for q in range(player_count):
            p_learned_q_demon = model.new_bool_var(f"{p}_puzzlemaster_learned_{q}_demon_{n}")
            q_is_demon = model.new_bool_var(f"puzzlemaster_guess_{q}_is_demon_{n}")
            model.add_max_equality(
                q_is_demon,
                [
                    assigned_char[n][q][j]
                    for j, c in enumerate(clocktower.character_list)
                    if c.character_type == "demon"
                ]
            )
            model.add_min_equality(
                p_learned_q_demon,
                [
                    puzzlemaster_demon_learned[n][p][q],
                    q_is_demon
                ]
            )
            learned_demon_causes.append(p_learned_q_demon)
        model.add_max_equality(p_learned_demon, learned_demon_causes)
        
        model.add(
            p_puzzle_guessed_correctly == p_learned_demon
        ).only_enforce_if(droisoned[n][p].Not()).only_enforce_if(p_puzzle_guessed)



def set_this_day_choice(
    puzzlemaster_guess_index: int | None,
    puzzlemaster_demon_player_learned_index: int | None,
    damsel_guess_index: int | None,
    model: cp_model.CpModel,
    player_count: int,
    player_making_choice_index: int,
    puzzlemaster_guess: list[list[list[cp_model.IntVar]]],
    puzzlemaster_demon_learned: list[list[list[cp_model.IntVar]]],
    damsel_guess: list[list[list[cp_model.IntVar]]],
    now: int,
):
    if puzzlemaster_guess_index is None:
        for q in range(player_count):
            model.add(puzzlemaster_guess[now][player_making_choice_index][q] == 0)
    else:
        model.add(puzzlemaster_guess[now][player_making_choice_index][puzzlemaster_guess_index] == 1)
        
    if puzzlemaster_demon_player_learned_index is None:
        for q in range(player_count):
            model.add(puzzlemaster_demon_learned[now][player_making_choice_index][q] == 0)
    else:
        model.add(puzzlemaster_demon_learned[now][player_making_choice_index][
            puzzlemaster_demon_player_learned_index
            ] == 1
        )
        
    if damsel_guess_index is None:
        for q in range(player_count):
            model.add(damsel_guess[now][player_making_choice_index][q] == 0)
    else:
        model.add(damsel_guess[now][player_making_choice_index][damsel_guess_index] == 1)



def set_this_night_choice(
    clocktower: "QuantumClocktower",
    chosen_player: Player,
    character_learned_index: int | None,
    number_learned: int | None,
    barber_swapped_player_indexes: list | None,
    model: cp_model.CpModel,
    player_making_choice_index: int | None,
    now: int,
    target: list[list[list[cp_model.IntVar]]],
    learned_char: list[list[list[cp_model.IntVar]]],
    num_learned: list[list[cp_model.IntVar]],
    barber_swap_indexes: list[list[tuple[cp_model.IntVar]]],
):
    if chosen_player is None:
        model.add(sum(target[now][player_making_choice_index]) == 0)
    else:
        model.add(
            target[now][player_making_choice_index][
                clocktower.players.index(chosen_player)
            ] == 1
        )
    if character_learned_index is None:
        model.add(sum(learned_char[now][player_making_choice_index]) == 0)
    else:
        model.add(
            learned_char[now][player_making_choice_index][
                character_learned_index
            ] == 1
        )
    if number_learned is None:
        model.add(num_learned[now][player_making_choice_index] == -1)
    else:
        model.add(num_learned[now][player_making_choice_index] == number_learned)
    if barber_swapped_player_indexes is None:
        model.add(barber_swap_indexes[now][player_making_choice_index][0] == -1)
        model.add(barber_swap_indexes[now][player_making_choice_index][1] == -1)
    else:
        model.add(barber_swap_indexes[now][player_making_choice_index][0] == barber_swapped_player_indexes[0])
        model.add(barber_swap_indexes[now][player_making_choice_index][1] == barber_swapped_player_indexes[1])


# NOTE: barber swap happens on the next day (equivalent to the end of the night).
# NOTE: Allows swapping other demons (fix if using imp, etc)
def set_barber_swap_indexes(
    clocktower: "QuantumClocktower",
    model: cp_model.CpModel,
    player_count: int,
    assigned_char: list[list[list[cp_model.IntVar]]],
    tokens: list[list[list[cp_model.IntVar]]],
    barber_swap_indexes: list[list[tuple[cp_model.IntVar]]],
    n: int,
):
    if "barber" in [c.name for c in clocktower.character_list] and not n % 2:
        haircuts_tonight_token_index = [t.name for t in clocktower.token_list].index("haircuts_tonight")
        haircuts_tonight = model.new_bool_var(f"haircuts_tonight_{n}")
        model.add_max_equality(
            haircuts_tonight,
            [
                tokens[n][p][haircuts_tonight_token_index]
                for p in range(player_count)
            ]
        )
        for p in range(player_count):
            p_is_demon_before_swap = model.new_bool_var(f"{p}_is_demon_before_barber_swap_{n}")
            model.add_max_equality(
                p_is_demon_before_swap,
                [
                    assigned_char[n][p][j]
                    for j, c in enumerate(clocktower.character_list)
                    if c.character_type == "demon"
                ]
            )
            
            p_makes_barber_swap = model.new_bool_var(f"{p}_makes_barber_swap_{n}")
            model.add_min_equality(
                p_makes_barber_swap,
                [
                    p_is_demon_before_swap,
                    haircuts_tonight
                ]
            )
            
            barber_swap_indexes_are_equal = model.new_bool_var(f"{p}_barber_swap_indexes_are_equal_{n}")
            model.add(
                barber_swap_indexes[n][p][0] == barber_swap_indexes[n][p][1]
            ).only_enforce_if(barber_swap_indexes_are_equal)
            model.add(
                barber_swap_indexes[n][p][0] != barber_swap_indexes[n][p][1]
            ).only_enforce_if(barber_swap_indexes_are_equal.Not())
            
            model.add(
                barber_swap_indexes[n][p][0] + barber_swap_indexes[n][p][1] == -2
            ).only_enforce_if(barber_swap_indexes_are_equal)
            model.add(barber_swap_indexes_are_equal == p_makes_barber_swap.Not())
    else:
        for p in range(player_count):
            model.add(barber_swap_indexes[n][p][0] == -1)
            model.add(barber_swap_indexes[n][p][1] == -1)



def set_night_info_restrictions(
    clocktower: "QuantumClocktower",
    model: cp_model.CpModel,
    player_count: int,
    assigned_char: list[list[list[cp_model.IntVar]]],
    target: list[list[list[cp_model.IntVar]]],
    learned_char: list[list[list[cp_model.IntVar]]],
    num_learned: list[list[cp_model.IntVar]],
    tokens: list[list[list[cp_model.IntVar]]],
    is_evil: list[list[cp_model.IntVar]],
    registers_as_evil: list[list[cp_model.IntVar]],
    abnormal_ability: list[list[cp_model.IntVar]],
    droisoned: list[list[cp_model.IntVar]],
    vortoxed: list[list[cp_model.IntVar]],
    n: int,
    ):
    if n % 2:
        return
    
    for p in range(player_count):
        p_targeted = model.new_bool_var(f"{p}_targeted_{n}")
        model.add_max_equality(
            p_targeted,
            target[n][p]
        )
        p_char_index_learned = model.new_int_var(-1, len(clocktower.character_list), f"{p}_character_index_learned_{n}")
        for i, learned_char_bool in enumerate(learned_char[n][p]):
            model.add(p_char_index_learned == i).only_enforce_if(learned_char_bool)
            model.add(p_char_index_learned != i).only_enforce_if(learned_char_bool.Not())
                
        for j, c in enumerate(clocktower.character_list):
            if isinstance(c.targets, bool):
                c_targets = c.targets
            else:
                c_targets: cp_model.IntVar | bool = c.targets(
                    model=model,
                    executed_indexes=clocktower.executed_indexes,
                    n=n,
                )
            model.add(p_targeted == c_targets).only_enforce_if(assigned_char[n][p][j])
            if isinstance(c.char_index_learned, int):
                c_char_index_learned = -1
            else:
                c_char_index_learned: cp_model.IntVar = c.char_index_learned(
                    model=model,
                    character_list=clocktower.character_list,
                    assigned_char=assigned_char,
                    learned_char=learned_char,
                    tokens=tokens,
                    token_list=clocktower.token_list,
                    executed_indexes=clocktower.executed_indexes,
                    droisoned=droisoned,
                    vortoxed=vortoxed,
                    n=n,
                    player_index=p,
                )
            model.add(p_char_index_learned == c_char_index_learned).only_enforce_if(assigned_char[n][p][j])
            if isinstance(c.number_learned, int):
                c_number_learned = -1
            else:
                c_number_learned: cp_model.IntVar = c.number_learned(
                    model=model,
                    player_list=clocktower.players,
                    character_list=clocktower.character_list,
                    assigned_char=assigned_char,
                    tokens=tokens,
                    token_list=clocktower.token_list,
                    is_evil=is_evil,
                    registers_as_evil=registers_as_evil,
                    abnormal_ability=abnormal_ability,
                    executed_indexes=clocktower.executed_indexes,
                    droisoned=droisoned,
                    vortoxed=vortoxed,
                    n=n,
                    player_index=p,
                )
            model.add(num_learned[n][p] == c_number_learned).only_enforce_if(assigned_char[n][p][j])



def set_vortoxed(
    clocktower: "QuantumClocktower",
    model: cp_model.CpModel,
    player_count: int,
    assigned_char: list[list[list[cp_model.IntVar]]],
    tokens: list[list[list[cp_model.IntVar]]],
    droisoned: list[list[cp_model.IntVar]],
    vortoxed: list[list[cp_model.IntVar]],
    n: int
    ):
    sober_vortox_exists = model.new_bool_var(f"sober_vortox_exists_{n}")
    if "vortox" in [c.name for c in clocktower.character_list]:
        vortox_index = [c.name for c in clocktower.character_list].index("vortox")
        matches = []
        for p in range(player_count):
            p_is_sober_vortox = model.new_bool_var(f"{p}_is_sober_vortox_{n}")
            model.add_min_equality(
                p_is_sober_vortox,
                [
                    assigned_char[n][p][vortox_index],
                    droisoned[n][p].Not()
                ]
            )
            matches.append(p_is_sober_vortox)
        model.add_max_equality(
            sober_vortox_exists,
            matches
        )
    else:
        model.add(sober_vortox_exists == 0)
    
    demon_safe_token_indexes = [
        i
        for i, t in enumerate(clocktower.token_list)
        if t.name in demon_safe_token_names
    ]
    for p in range(player_count):
        model.add_min_equality(
            vortoxed[n][p],
            [sober_vortox_exists]
            + [
                tokens[n][p][t].Not()
                for t in demon_safe_token_indexes
            ]
        )



def set_droisoning(
    clocktower: "QuantumClocktower",
    model: cp_model.CpModel,
    player_count: int,
    tokens: list[list[list]],
    droisoned: list[list],
    n: int
    ):
    for p in range(player_count):
        if not n % 2:
            model.add_max_equality(
                droisoned[n][p],
                [
                    tokens[n][p][i]
                    for i, t in enumerate(clocktower.token_list)
                    if t.droisoning
                ]
            )
        else: # NOTE: only works if players cannot die due to abilities during the day
            non_dead_droisoning_tokens = [
                i
                for i, t in enumerate(clocktower.token_list)
                if t.droisoning
                and t.name != "dead"
            ]
            dead_token_index = [t.name for t in clocktower.token_list].index("dead")
            model.add_max_equality(
                droisoned[n][p],
                [tokens[n-1][p][dead_token_index]]
                + [
                    tokens[n][p][t]
                    for t in non_dead_droisoning_tokens
                ]
            )



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
            i
            for i, t in enumerate(clocktower.token_list)
            if t.name in character_change_token_names
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



def victory_conditions( # TODO: implement a "day order" for winning tokens
    clocktower: "QuantumClocktower",
    model: cp_model.CpModel,
    player_count: int,
    assigned_char: list[list[list[cp_model.IntVar]]],
    tokens: list[list[list[cp_model.IntVar]]],
    registers_as_evil: list[list[cp_model.IntVar]],
    good_wins: list,
    evil_wins: list,
    game_ended: list,
    n: int
    ):
    dead_token_index = [t.name for t in clocktower.token_list].index("dead")
    demon_indexes = [
        j
        for j, c in enumerate(clocktower.character_list)
        if c.character_type == "demon"
    ]
    winning_token_indexes = [
        i
        for i, t in enumerate(clocktower.token_list)
        if t.name in winning_token_names
    ]
    losing_token_indexes = [
        i
        for i, t in enumerate(clocktower.token_list)
        if t.name in losing_token_names
    ]
    evil_winning_token_indexes = [
        i
        for i, t in enumerate(clocktower.token_list)
        if t.name in evil_winning_token_names
    ]
    
    good_won = model.new_bool_var(f"{n}_good_won")
    good_wins.append(good_won)
    evil_won = model.new_bool_var(f"{n}_evil_won")
    evil_wins.append(evil_won)
    game_end = model.new_bool_var(f"{n}_game_end")
    game_ended.append(game_end)

    all_demons_dead = model.new_bool_var(f"{n}_all_demons_dead")
    living_demons = []
    for p in range(player_count):
        p_is_demon = model.new_bool_var(f"{p}_demon_{n}")
        model.add_max_equality(
            p_is_demon,
            [
                assigned_char[n][p][c]
                for c in demon_indexes
            ]
        )
        p_is_living_demon = model.new_bool_var(f"{p}_is_living_demon_{n}")
        model.add_min_equality(
            p_is_living_demon,
            [
                p_is_demon,
                tokens[n][p][dead_token_index].Not()
            ]
        )
        living_demons.append(p_is_living_demon)
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
    
    good_win_from_token = model.new_bool_var(f"good_win_from_token_{n}")
    evil_win_from_token = model.new_bool_var(f"evil_win_from_token_{n}")
    good_win_causes = []
    evil_win_causes = []
    for p in range(player_count):
        good_win_cause = model.new_bool_var(f"good_win_cause_{p}_{n}")
        model.add_max_equality(
            good_win_cause,
            [
                tokens[n][p][t]
                for t in winning_token_indexes
            ]
        ).only_enforce_if(registers_as_evil[n][p].Not())
        model.add_max_equality(
            good_win_cause,
            [
                tokens[n][p][t]
                for t in losing_token_indexes
            ]
        ).only_enforce_if(registers_as_evil[n][p])
        good_win_causes.append(good_win_cause)
        
        evil_win_cause = model.new_bool_var(f"evil_win_cause_{p}_{n}")
        model.add_max_equality(
            evil_win_cause,
            [
                tokens[n][p][t]
                for t in winning_token_indexes
                + evil_winning_token_indexes
            ]
        ).only_enforce_if(registers_as_evil[n][p])
        model.add_max_equality(
            evil_win_cause,
            [
                tokens[n][p][t]
                for t in losing_token_indexes
                + evil_winning_token_indexes
            ]
        ).only_enforce_if(registers_as_evil[n][p].Not())
        evil_win_causes.append(evil_win_cause)
    model.add_max_equality(
        good_win_from_token,
        good_win_causes
    )
    model.add_max_equality(
        evil_win_from_token,
        evil_win_causes
    )
    
    
    token_win = model.new_bool_var(f"token_win_{n}")
    model.add_max_equality(
        token_win,
        [
            good_win_from_token,
            evil_win_from_token,
        ]
    )

    mastermind_active = model.new_bool_var(f"mastermind_active_{n}")
    if "mastermind" in [t.name for t in clocktower.character_list]:
        mastermind_day_token_index = [t.name for t in clocktower.token_list].index("mastermind_day")
        model.add_max_equality(
            mastermind_active,
            [
                tokens[n][p][mastermind_day_token_index]
                for p in range(player_count)
            ]
        )
    else:
        model.add(mastermind_active == 0)
    
    model.add_min_equality(
        good_won,
        [
            all_demons_dead,
            mastermind_active.Not()
        ]
    ).only_enforce_if(token_win.Not())
    model.add(
        good_won == good_win_from_token
    ).only_enforce_if(token_win)

    model.add_min_equality(
        evil_won,
        [
            two_players_alive,
            mastermind_active.Not(),
            good_won.Not()
        ]
    ).only_enforce_if(token_win.Not())
    model.add_min_equality(
        evil_won,
        [
            evil_win_from_token,
            good_won.Not()
        ]
    ).only_enforce_if(token_win)
    
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
        balloonist_index = [c.name for c in clocktower.character_list].index("balloonist")
        model.add_max_equality(
            balloonist_exists,
            [
                assigned_char[0][p][balloonist_index]
                for p in range(player_count)
            ]
        )
        model.add(balloonist_effect <= balloonist_exists)
    else:
        model.add(balloonist_effect == 0)
    
    baron_exists = model.new_bool_var("baron_exists")
    if "baron" in [c.name for c in clocktower.character_list]:
        baron_index = [c.name for c in clocktower.character_list].index("baron")
        model.add_max_equality(
            baron_exists,
            [
                assigned_char[0][p][baron_index]
                for p in range(player_count)
            ]
        )
    else:
        model.add(baron_exists == 0)
    
    model.add(
        sum(
            assigned_char[0][p][j]
            for p in range(player_count)
            for j, c in enumerate(clocktower.character_list)
            if c.character_type == "outsider"
        ) == outsider_count(player_count)
        + balloonist_effect
        + 2*baron_exists
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
    n: int,
):
    """
    Sets is_evil and the number of evil players at setup
    """ # setup constraint is set here basically just because of Lord of Typhon and Legion
    evil_alignment_token_indexes = [
        i
        for i, t in enumerate(clocktower.token_list)
        if t.name in evil_alignment_token_names
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
                p_turned_evil,
                [
                    tokens[n][p][t]
                    for t in evil_alignment_token_indexes
                ]
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



def set_bluffs(
    clocktower: "QuantumClocktower",
    model: "cp_model.CpModel",
    player_count: int,
    player_making_choice_index: int | None,
    chosen_bluff_indexes: tuple | None,
    assigned_char: list[list],
    now: int,
    ):
    
    new_all_chosen_bluff_indexes = clocktower.all_chosen_bluff_indexes.copy()
    if now == 0 and player_making_choice_index is not None:
        new_all_chosen_bluff_indexes[player_making_choice_index] = chosen_bluff_indexes
    
    learned_bluffs = [
        model.new_bool_var(f"{p}_learned_bluffs")
        for p in range(player_count)
    ]
    for p in range(player_count):
        match new_all_chosen_bluff_indexes[p]:
            case None:
                model.add(learned_bluffs[p] == 0)
            case (_, _, _):
                model.add(learned_bluffs[p] == 1)
    if player_count < 7:
        model.add(sum(learned_bluffs) == 0)
        return
    model.add(sum(learned_bluffs) > 0)
    if clocktower.evils_predetermined:
        for i, p in enumerate(clocktower.players):
            if p.alignment == "good":
                model.add(learned_bluffs[i] == 0)
    actual_bluffs = [
        model.new_int_var_from_domain(
            cp_model.Domain.from_values(
                [
                    j
                    for j, c in enumerate(clocktower.character_list)
                    if c.alignment == "good"
                ]
            ),
            f"bluff_{i}"
        )
        for i in range(3)
    ]
    model.add_all_different(actual_bluffs)
    
    for p in range(player_count):
        chosen_bluff_list = new_all_chosen_bluff_indexes[p]
        p_is_starting_demon = model.new_bool_var(f"{p}_making_choice_is_starting_demon")
        model.add_max_equality(
            p_is_starting_demon,
            [
                assigned_char[0][p][j]
                for j, c in enumerate(clocktower.character_list)
                if c.character_type == "demon"
            ]
        )
        if chosen_bluff_list is None:
            model.add(p_is_starting_demon == 0)
        elif chosen_bluff_list != ():
            for a, b in zip(actual_bluffs, chosen_bluff_list):
                model.add(a == b).only_enforce_if(p_is_starting_demon)
    
    for p in range(player_count):
        for bluff in actual_bluffs:
            model.add_element(bluff, assigned_char[0][p], 0)
