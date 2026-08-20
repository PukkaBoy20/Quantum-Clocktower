from ortools.sat.python import cp_model


class Player:
    def __init__(
        self,
        name: str | None,
        alignment: str | None,
        index: int,
        character_list: list["Character"],
    ):
        self.name = name if name else ""
        self.alignment = alignment
        self.index = index
        if alignment is None:
            self.possible_starting_characters: list[Character] = [
                char for char in character_list
                if char.name != "atheist"
            ]
        else:
            self.possible_starting_characters: list[Character] = [
                char for char in character_list
                if char.alignment == alignment
                and char.name != "atheist"
            ]
        self.possible_characters = self.possible_starting_characters
        self.night_or_day_start_possible_characters = self.possible_starting_characters
        self.dead = False


class Character:
    def __init__(
        self,
        name: str,
        alignment: str,
        character_type: str,
        targets,
        char_index_learned,
        number_learned,
        extra_ability_conditions = None,
    ):
        self.name = name
        self.alignment = alignment
        self.character_type = character_type
        self.targets = targets
        self.char_index_learned = char_index_learned
        self.number_learned = number_learned
        self.extra_ability_conditions = extra_ability_conditions


class Token:
    def __init__(self, name: str, droisoning: bool, conditions):
        self.name = name
        self.droisoning = droisoning
        self.conditions = conditions


def get_character(name: str, character_list: list[Character]):
    for character in character_list:
        if character.name == name:
            return character
    raise RuntimeWarning

def retain_token(
    model: cp_model.CpModel,
    player_list: list[Player],
    tokens: list[list[list[cp_model.IntVar]]],
    n: int,
    token_index: int,
    only_if: cp_model.IntVar | bool = True,
):
    if n == 0:
        return
    for p in range(len(player_list)):
        model.add(tokens[n][p][token_index] == tokens[n-1][p][token_index]).only_enforce_if(only_if)

def make_char_is_droisoned(
    model: cp_model.CpModel,
    player_list: list[Player],
    assigned_char: list[list[list[cp_model.IntVar]]],
    droisoned: list[list[cp_model.IntVar]],
    n: int,
    character_index: int,
    name: str
):
    char_is_droisoned = model.new_bool_var(name)
    matches = []
    for p in range(len(player_list)):
        m = model.new_bool_var(f"{p}_is_droisoned_char_{character_index}_{n}")
        model.add_min_equality(
            m,
            [
                assigned_char[n][p][character_index],
                droisoned[n][p]
            ]
        )
        matches.append(m)
    model.add_max_equality(
            char_is_droisoned,
            matches
        )
    return char_is_droisoned

def token_caused_by_char_existing(
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    assigned_char: list[list[list[cp_model.IntVar]]],
    tokens: list[list[list[cp_model.IntVar]]],
    droisoned: list[list[cp_model.IntVar]],
    n: int,
    character_index: int,
    token_index: int,
    affected_by_droisoning: bool,
    remembered_tokens: list[list[list[cp_model.IntVar]]] | None = None,
    keep_token_position: cp_model.IntVar | bool = True,
):
    new_instance_token_index = [t.name for t in token_list].index("new_instance")
    
    new_char_exists = model.new_bool_var(f"new_char_{character_index}_exists_{n}")
    old_char_exists = model.new_bool_var(f"old_char_{character_index}_exists_{n}")
    char_exists = model.new_bool_var(f"char_{character_index}_exists_{n}")
    new_char_matches = []
    old_char_matches = []
    for p in range(len(player_list)):
        m_new = model.new_bool_var(f"{n}_{p}_m_new")
        model.add_min_equality(
            m_new,
            [
                assigned_char[n][p][character_index],
                tokens[n][p][new_instance_token_index]
            ]
        )
        new_char_matches.append(m_new)
    
        m_old = model.new_bool_var(f"{n}_{p}_m_old")
        model.add_min_equality(
            m_old,
            [
                assigned_char[n][p][character_index],
                tokens[n][p][new_instance_token_index].Not()
            ]
        )
        old_char_matches.append(m_old)
    model.add_max_equality(
        new_char_exists,
        new_char_matches
    )
    model.add_max_equality(
        old_char_exists,
        old_char_matches
    )
    model.add_max_equality(
        char_exists,
        [
            old_char_exists,
            new_char_exists
        ]
    )
    
    if not affected_by_droisoning:
        token_is_retained = model.new_bool_var(f"token_caused_by_{character_index}_existing_is_retained_{n}")
        model.add_min_equality(
            token_is_retained,
            [
                old_char_exists,
                keep_token_position
            ]
        )
        retain_token(
            model,
            player_list,
            tokens,
            n,
            token_index,
            token_is_retained
        )
        model.add(
            sum(
                tokens[n][p][token_index]
                for p in range(len(player_list))
            ) == char_exists
        )
    else:
        char_is_droisoned = make_char_is_droisoned(
            model,
            player_list,
            assigned_char,
            droisoned,
            n,
            character_index,
            f"token_caused_by_char_existing_{character_index}_is_droisoned_{n}"
        )
                
        model.add(
            sum(
                remembered_tokens[n][p][token_index]
                for p in range(len(player_list))
            ) == char_exists
        ) # NOTE: The values are irrelevant when the char does not exist
        
        token_disabled = model.new_bool_var(f"token_{token_index}_disabled_{n}")
        model.add_max_equality(
            token_disabled,
            [
                char_exists.Not(),
                char_is_droisoned
            ]
        )
        for p in range(len(player_list)):
            model.add(
                tokens[n][p][token_index]
                == remembered_tokens[n][p][token_index]
            ).only_enforce_if(token_disabled.Not())
        model.add(
            sum(
                tokens[n][p][token_index]
                for p in range(len(player_list))
            ) == 0
        ).only_enforce_if(token_disabled)
        
        if n > 0:
            actually_keep_token_position = model.new_bool_var(
                f"actually_keep_token_{token_index}_position_{n}"
            )
            model.add_min_equality(
                actually_keep_token_position,
                [
                    old_char_exists,
                    keep_token_position
                ]
            )

            for p in range(len(player_list)):
                model.add(
                    remembered_tokens[n][p][token_index]
                    == remembered_tokens[n-1][p][token_index]
                ).only_enforce_if(actually_keep_token_position)

def attacking_other_player_token(
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    tokens: list[list[list[cp_model.IntVar]]],
    n: int,
    character_list: list[Character],
    assigned_char: list[list[list[cp_model.IntVar]]],
    target: list[list[list[cp_model.IntVar]]],
    droisoned: list[list[cp_model.IntVar]],
    character_index: int,
    token_index: int,
    old_instance_only: bool = False,
):
    mayor_index = [c.name for c in character_list].index("mayor")
    lycanthrope_protected_index = [t.name for t in token_list].index("lycanthrope_protected")
    protection_token_indexes = [
        i
        for i, t in enumerate(token_list)
        if t.name in protection_token_names
    ]
    demon_safe_token_indexes = [
        i
        for i, t in enumerate(token_list)
        if t.name in demon_safe_token_names
    ]
    
    attacked = []
    attacked_mayor = []
    for p in range(len(player_list)):
        p_attacked = model.new_bool_var(f"{p}_{token_index}_attacked_{n}")
        causes = []
        for q in range(len(player_list)):
            p_attacked_by_q = model.new_bool_var(f"{p}_{token_index}_attacked_by_{q}_{n}")
            if old_instance_only:
                new_instance_token_index = [t.name for t in token_list].index("new_instance")
                model.add_min_equality(
                    p_attacked_by_q,
                    [
                        assigned_char[n][q][character_index],
                        tokens[n][q][new_instance_token_index].Not(),
                        target[n][q][p],
                        droisoned[n][q].Not()
                    ]
                )
            else:
                model.add_min_equality(
                    p_attacked_by_q,
                    [
                        assigned_char[n][q][character_index],
                        target[n][q][p],
                        droisoned[n][q].Not()
                    ]
                )
            causes.append(p_attacked_by_q)
        model.add_max_equality(
            p_attacked,
            causes
        )
        attacked.append(p_attacked)
    
        p_is_sober_killed_mayor = model.new_bool_var(f"{p}_is_{token_index}_killed_mayor_{n}")
        demon_attacking_token_indexes = [
            i
            for i, t in enumerate(token_list)
            if t.name in demon_attacking_token_names
        ]
        if token_index in demon_attacking_token_indexes:
            model.add_min_equality(
                p_is_sober_killed_mayor,
                [
                    assigned_char[n][p][mayor_index],
                    droisoned[n][p].Not(),
                    p_attacked,
                    tokens[n][p][lycanthrope_protected_index].Not()
                ]
                + [
                    tokens[n][p][t].Not()
                    for t in protection_token_indexes
                    + demon_safe_token_indexes
                ]
            )
        else:
            model.add_min_equality(
                p_is_sober_killed_mayor,
                [
                    assigned_char[n][p][mayor_index],
                    droisoned[n][p].Not(),
                    p_attacked
                ]
                + [
                    tokens[n][p][t].Not()
                    for t in protection_token_indexes
                ]
            )
        attacked_mayor.append(p_is_sober_killed_mayor)
        
        
    mayor_was_attacked = model.new_bool_var(f"mayor_was_{token_index}_attacked_{n}")
    model.add_max_equality(
        mayor_was_attacked,
        attacked_mayor
    )
    model.add(
        sum(
            tokens[n][p][token_index]
            for p in range(len(player_list))
        ) == 1
    ).only_enforce_if(mayor_was_attacked)
    for p in range(len(player_list)):
        model.add(
            tokens[n][p][token_index]
            == attacked[p]
        ).only_enforce_if(mayor_was_attacked.Not())



def pixie_extra_ability_condition(
    model: cp_model.CpModel,
    player_count: int,
    has_ability: list[list[list[cp_model.IntVar]]],
    n: int,
    **kwargs,
):
    token_list: list[Token] = kwargs["token_list"]
    tokens: list[list[list[cp_model.IntVar]]] = kwargs["tokens"]
    pixie_ability_index_learned: list[list[cp_model.IntVar]] = kwargs["pixie_ability_index_learned"]
    pixie_has_ability_token_index = [t.name for t in token_list].index("pixie_has_ability")
    
    for p in range(player_count):
        model.add_element(
            pixie_ability_index_learned[n][p], has_ability[n][p], 1
        ).only_enforce_if(tokens[n][p][pixie_has_ability_token_index])

def cannibal_extra_ability_condition(
    model: cp_model.CpModel,
    player_count: int,
    has_ability: list[list[list[cp_model.IntVar]]],
    n: int,
    **kwargs,
):
    character_list: list[Character] = kwargs["character_list"]
    assigned_char: list[list[list[cp_model.IntVar]]] = kwargs["assigned_char"]
    droisoned: list[list[cp_model.IntVar]] = kwargs["droisoned"]
    cannibal_current_ability_index: list[cp_model.IntVar] = kwargs["cannibal_current_ability_index"]
    cannibal_character_index = [c.name for c in character_list].index("cannibal")
    
    lunch_exists = model.new_bool_var(f"cannibal_extra_ability_lunch_exists_{n}")
    model.add(cannibal_current_ability_index[n] != -1).only_enforce_if(lunch_exists)
    model.add(cannibal_current_ability_index[n] == -1).only_enforce_if(lunch_exists.Not())
    
    for p in range(player_count):
        model.add_element(
            cannibal_current_ability_index[n], has_ability[n][p], 1
        ).only_enforce_if(
            assigned_char[n][p][cannibal_character_index]
        ).only_enforce_if(
            droisoned[n][p].Not()
        ).only_enforce_if(
            lunch_exists
        )

def drunk_extra_ability_condition(
    model: cp_model.CpModel,
    player_count: int,
    has_ability: list[list[list[cp_model.IntVar]]],
    n: int,
    **kwargs,
):
    character_list: list[Character] = kwargs["character_list"]
    token_list: list[Token] = kwargs["token_list"]
    assigned_char: list[list[list[cp_model.IntVar]]] = kwargs["assigned_char"]
    tokens: list[list[list[cp_model.IntVar]]] = kwargs["tokens"]
    drunk_character_index = [c.name for c in character_list].index("drunk")
    new_instance_token_index = [t.name for t in token_list].index("new_instance")
    
    not_in_play_townsfolk_index = model.new_int_var_from_domain(
        cp_model.Domain.from_values(
            j
            for j, c in enumerate(character_list)
            if c.character_type == "townsfolk"
        ),
        f"drunk_extra_ability_not_in_play_townsfolk_index_{n}"
    )
    for c in range(len(character_list)):
        c_is_in_play = model.new_bool_var(f"drunk_extra_ability_{c}_is_in_play_{n}")
        model.add_max_equality(
            c_is_in_play,
            [
                assigned_char[n][p][c]
                for p in range(player_count)
            ]
        )
        model.add(not_in_play_townsfolk_index != c).only_enforce_if(c_is_in_play)
    
    for p in range(player_count):
        p_is_new_drunk = model.new_bool_var(f"extra_ability_{p}_is_new_drunk_{n}")
        model.add_min_equality(
            p_is_new_drunk,
            [
                assigned_char[n][p][drunk_character_index],
                tokens[n][p][new_instance_token_index]
            ]
        )
        p_is_old_drunk = model.new_bool_var(f"extra_ability_{p}_is_old_drunk_{n}")
        model.add_min_equality(
            p_is_old_drunk,
            [
                assigned_char[n][p][drunk_character_index],
                tokens[n][p][new_instance_token_index].Not()
            ]
        )
        
        model.add_element(not_in_play_townsfolk_index, has_ability[n][p], 1).only_enforce_if(p_is_new_drunk)
        if n > 0:
            for c in range(len(character_list)):
                model.add(has_ability[n][p][c] == has_ability[n-1][p][c]).only_enforce_if(p_is_old_drunk)


def clockmaker_number_learned(**kwargs):
    model: cp_model.CpModel = kwargs["model"]
    player_list: list[Player] = kwargs["player_list"]
    character_list: list[Character] = kwargs["character_list"]
    assigned_char: list[list[list[cp_model.IntVar]]] = kwargs["assigned_char"]
    tokens: list[list[list[cp_model.IntVar]]] = kwargs["tokens"]
    token_list: list[Token] = kwargs["token_list"]
    droisoned: list[list[cp_model.IntVar]] = kwargs["droisoned"]
    vortoxed: list[list[cp_model.IntVar]] = kwargs["vortoxed"]
    n: int = kwargs["n"]
    player_index: int = kwargs["player_index"]
    
    new_instance_token_index = [t.name for t in token_list].index("new_instance")
    
    demon_indexes = [
        j
        for j, c in enumerate(character_list)
        if c.character_type == "demon"
    ]
    minion_indexes = [
        j
        for j, c in enumerate(character_list)
        if c.character_type == "minion"
    ]
    
    learned_number = model.new_int_var(-1, len(player_list), f"clockmaker_learned_number_{player_index}_{n}")
    model.add(learned_number != 0)
    clockmaker_number = model.new_int_var(1, len(player_list), f"clockmaker_number_{player_index}_{n}")
    distances = []
    for p in range(len(player_list)): # TODO: should the upper bound be lowered?
        for q in range(len(player_list)):
            p_is_demon = model.new_bool_var(f"clockmaker_{p}_is_demon{q}_{n}")
            model.add_max_equality(
                p_is_demon,
                [
                    assigned_char[n][p][c]
                    for c in demon_indexes
                ]
            )
            q_is_minion = model.new_bool_var(f"clockmaker_{q}_is_minion_{p}_{n}")
            model.add_max_equality(
                q_is_minion,
                [
                    assigned_char[n][q][c]
                    for c in minion_indexes
                ]
            )
            p_demon_and_q_minion = model.new_bool_var(f"{p}_demon_{q}_minion")
            model.add_min_equality(
                p_demon_and_q_minion,
                [
                    p_is_demon,
                    q_is_minion
                ]
            )
            p_q_distance = model.new_int_var(1, len(player_list), f"clockmaker_{p}_{q}_distance_{n}")
            model.add_abs_equality(p_q_distance, p-q).only_enforce_if(p_demon_and_q_minion)
            model.add(p_q_distance == len(player_list)).only_enforce_if(p_demon_and_q_minion.Not())
            distances.append(p_q_distance)
    model.add_min_equality(
        clockmaker_number,
        distances
    )
    healthy_new_instance = model.new_bool_var(f"clockmaker_number_learned_healthy_new_instance_{player_index}_{n}")
    model.add_min_equality(
        healthy_new_instance,
        [
            droisoned[n][player_index].Not(),
            vortoxed[n][p].Not(),
            tokens[n][player_index][new_instance_token_index],
        ]
    )
    model.add(learned_number == clockmaker_number).only_enforce_if(healthy_new_instance)
    model.add(learned_number != clockmaker_number).only_enforce_if(vortoxed[n][p])
    model.add(learned_number == -1).only_enforce_if(tokens[n][player_index][new_instance_token_index].Not())
    model.add(learned_number != -1).only_enforce_if(tokens[n][player_index][new_instance_token_index])
    return learned_number

def pixie_character_index_learned(**kwargs):
    model: cp_model.CpModel = kwargs["model"]
    character_list: list[Character] = kwargs["character_list"]
    tokens: list[list[list[cp_model.IntVar]]] = kwargs["tokens"]
    token_list: list[Token] = kwargs["token_list"]
    player_index: int = kwargs["player_index"]
    n: int = kwargs["n"]
    
    # NOTE: already mostly constrained by the pixie token
    new_instance_token_index = [t.name for t in token_list].index("new_instance")
    
    possible_indexes = model.new_int_var_from_domain(
        cp_model.Domain.from_values(
            [-1]
            + [
                j
                for j, c in enumerate(character_list)
                if c.character_type == "townsfolk"
            ]
        ),
        f"pixie_character_index_{player_index}_{n}"
    )
    model.add(possible_indexes == -1).only_enforce_if(tokens[n][player_index][new_instance_token_index].Not())
    model.add(possible_indexes != -1).only_enforce_if(tokens[n][player_index][new_instance_token_index])
    
    return possible_indexes

def empath_number_learned(**kwargs):
    model: cp_model.CpModel = kwargs["model"]
    player_list: list[Player] = kwargs["player_list"]
    is_evil: list[list[cp_model.IntVar]] = kwargs["is_evil"]
    registers_as_evil: list[list[cp_model.IntVar]] = kwargs["registers_as_evil"]
    droisoned: list[list[cp_model.IntVar]] = kwargs["droisoned"]
    vortoxed: list[list[cp_model.IntVar]] = kwargs["vortoxed"]
    n: int = kwargs["n"]
    player_index: int = kwargs["player_index"]
    
    empath_number = model.new_int_var(0, len(player_list), f"empath_number_{player_index}_{n}")
    model.add(
        empath_number
        == registers_as_evil[n][player_index-1]
        + registers_as_evil[n][(player_index+1)%len(player_list)]
    )
    true_empath_number = model.new_int_var(0, len(player_list), f"true_empath_number_{player_index}_{n}")
    model.add(
        true_empath_number
        == is_evil[n][player_index-1]
        + is_evil[n][(player_index+1)%len(player_list)]
    )
    healthy = model.new_bool_var(f"empath_number_learned_healthy_{player_index}_{n}")
    model.add_min_equality(
        healthy,
        [
            droisoned[n][player_index].Not(),
            vortoxed[n][player_index].Not()
        ]
    )
    number_learned = model.new_int_var(0, len(player_list), f"empath_number_learned_{player_index}_{n}")
    model.add(number_learned == empath_number).only_enforce_if(healthy)
    model.add(number_learned != true_empath_number).only_enforce_if(vortoxed[n][player_index])
    return number_learned
    
def mathematician_number_learned(**kwargs): # TODO: double check this works after implementing abnormal_ability
    model: cp_model.CpModel = kwargs["model"]
    player_list: list[Player] = kwargs["player_list"]
    abnormal_ability: list[list[cp_model.IntVar]] = kwargs["abnormal_ability"]
    droisoned: list[list[cp_model.IntVar]] = kwargs["droisoned"]
    vortoxed: list[list[cp_model.IntVar]] = kwargs["vortoxed"]
    n: int = kwargs["n"]
    player_index: int = kwargs["player_index"]
    
    healthy = model.new_bool_var(f"mathematician_number_learned_healthy_{player_index}_{n}")
    model.add_min_equality(
        healthy,
        [
            droisoned[n][player_index].Not(),
            vortoxed[n][player_index].Not()
        ]
    )
    number_learned = model.new_int_var(0, len(player_list), f"mathematician_number_learned_{player_index}_{n}")
    model.add(number_learned == sum(abnormal_ability[n])).only_enforce_if(healthy)
    model.add(number_learned != sum(abnormal_ability[n])).only_enforce_if(vortoxed[n][player_index])
    return number_learned

def undertaker_character_index_learned(**kwargs):
    model: cp_model.CpModel = kwargs["model"]
    character_list: list[Character] = kwargs["character_list"]
    assigned_char: list[list[list[cp_model.IntVar]]] = kwargs["assigned_char"]
    executed_indexes: list[int | str | None] = kwargs["executed_indexes"]
    droisoned: list[list[cp_model.IntVar]] = kwargs["droisoned"]
    vortoxed: list[list[cp_model.IntVar]] = kwargs["vortoxed"]
    n: int = kwargs["n"]
    player_index: int = kwargs["player_index"]
    
    if n == 0 or executed_indexes[n-1] is None:
        return -1

    undertaker_char_index = model.new_int_var(0, len(character_list), f"undertaker_char_index_{player_index}_{n}")
    for i, char_bool in enumerate(assigned_char[n-1][executed_indexes[n-1]]):
        model.add(undertaker_char_index == i).only_enforce_if(char_bool)
    healthy = model.new_bool_var(f"undertaker_character_learned_healthy_{player_index}_{n}")
    model.add_min_equality(
        healthy,
        [
            droisoned[n][player_index].Not(),
            vortoxed[n][player_index].Not()
        ]
    )
    char_index_learned = model.new_int_var(0, len(character_list), f"undertaker_char_index_learned_{player_index}_{n}")
    model.add(char_index_learned == undertaker_char_index).only_enforce_if(healthy)
    model.add(char_index_learned != undertaker_char_index).only_enforce_if(vortoxed[n][player_index])
    return char_index_learned

full_sized_char_list = [ # FIXME implement monk and DA targeting rules
    Character("clockmaker", "good", "townsfolk", False, -1, clockmaker_number_learned),
    Character("pixie", "good", "townsfolk", False, pixie_character_index_learned, -1, pixie_extra_ability_condition),
    Character("empath", "good", "townsfolk", False, -1, empath_number_learned),
    Character("mathematician", "good", "townsfolk", False, -1, mathematician_number_learned),
    Character("undertaker", "good", "townsfolk", False, undertaker_character_index_learned, -1),
    Character("gambler", "good", "townsfolk", lambda **kwargs: kwargs["n"] > 0, -1, -1),
    Character("monk", "good", "townsfolk", lambda **kwargs: kwargs["n"] > 0, -1, -1),
    Character("lycanthrope", "good", "townsfolk", lambda **kwargs: kwargs["n"] > 0, -1, -1),
    Character("fool", "good", "townsfolk", False, -1, -1),
    Character("tea_lady", "good", "townsfolk", False, -1, -1),
    Character("cannibal", "good", "townsfolk", False, -1, -1, cannibal_extra_ability_condition),
    Character("mayor", "good", "townsfolk", False, -1, -1),
    Character("atheist", "good", "townsfolk", False, -1, -1),
    Character("puzzlemaster", "good", "outsider", False, -1, -1),
    Character("damsel", "good", "outsider", False, -1, -1),
    Character("drunk", "good", "outsider", False, -1, -1, drunk_extra_ability_condition),
    Character("barber", "good", "outsider", False, -1, -1),
    Character("poisoner", "evil", "minion", True, -1, -1),
    Character("devils_advocate", "evil", "minion", True, -1, -1),
    Character("baron", "evil", "minion", False, -1, -1),
    Character("mastermind", "evil", "minion", False, -1, -1),
    Character("pukka", "evil", "demon", True, -1, -1),
    Character("lleech", "evil", "demon", True, -1, -1),
    Character("vortox", "evil", "demon", lambda **kwargs: kwargs["n"] > 0, -1, -1),
]
full_sized_night_order = [] # TODO for barber?
# full_sized_char_list = [
#     x[0] for x in sorted(zip(full_sized_char_list, full_sized_night_order), key=lambda x: x[1])
# ]


teensy_char_list = [
    Character("balloonist", "good", "townsfolk", lambda _: True, lambda _: False, ...),
    Character("lycanthrope", "good", "townsfolk", lambda n: (n > 1 and not n % 2), lambda _: False, ...),
    Character("preacher", "good", "townsfolk", lambda _: True, lambda _: False, ...),
    Character("princess", "good", "townsfolk", lambda _: False, lambda _: False, ...),
    Character("monk", "good", "townsfolk", lambda n: (n > 1 and not n % 2), lambda _: False, ...),
    Character("alchemist_poisoner", "good", "townsfolk", lambda _: True, lambda _: False, ...),
    Character("alchemist_goblin", "good", "townsfolk", lambda _: False, lambda _: False, ...),
    Character("goon", "good", "outsider", lambda _: False, lambda _: False, ...),
    Character("klutz", "good", "outsider", lambda _: False, lambda _: False, ...),
    Character("poisoner", "evil", "minion", lambda _: True, lambda _: False, ...),
    Character("goblin", "evil", "minion", lambda _: False, lambda _: False, ...),
    Character("pukka", "evil", "demon", lambda _: True, lambda _: False, ...),
    Character("imp", "evil", "demon", lambda n: (n > 1 and not n % 2), lambda _: False, ...),
]
teensy_night_order = [8, 4, 0, 5, 3, 2, 999, 999, 999, 1, 999, 7, 6]
teensy_char_list = [
    x[0] for x in sorted(zip(teensy_char_list, teensy_night_order), key=lambda x: x[1])
]


def add_pixie_known_token_condition( # NOTE: also forces pixie known char to not be in play if vortoxed
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    tokens: list[list[list[cp_model.IntVar]]],
    n: int,
    **kwargs,
):
    character_list: list[Character] = kwargs["character_list"]
    assigned_char: list[list[list[cp_model.IntVar]]] = kwargs["assigned_char"]
    learned_char: list[list[list[cp_model.IntVar]]] = kwargs["learned_char"]
    droisoned: list[list[cp_model.IntVar]] = kwargs["droisoned"]
    vortoxed: list[list[cp_model.IntVar]] = kwargs["vortoxed"]
    character_index = [c.name for c in character_list].index("pixie")
    token_index = [t.name for t in token_list].index("pixie_known")
    new_instance_token_index = [t.name for t in token_list].index("new_instance")
    
    new_pixie_exists = model.new_bool_var(f"new_pixie_exists_{n}")
    old_pixie_exists = model.new_bool_var(f"old_pixie_exists_{n}")
    new_pixie_matches = []
    old_pixie_matches = []
    for p in range(len(player_list)):
        new_pixie_m = model.new_bool_var(f"{p}_is_new_pixie_{n}")
        model.add_min_equality(
            new_pixie_m,
            [
                assigned_char[n][p][character_index],
                tokens[n][p][new_instance_token_index]
            ]
        )
        old_pixie_m = model.new_bool_var(f"{p}_is_old_pixie_{n}")
        model.add_min_equality(
            old_pixie_m,
            [
                assigned_char[n][p][character_index],
                tokens[n][p][new_instance_token_index].Not()
            ]
        )
        new_pixie_matches.append(new_pixie_m)
        old_pixie_matches.append(old_pixie_m)
    model.add_max_equality(new_pixie_exists, new_pixie_matches)
    model.add_max_equality(old_pixie_exists, old_pixie_matches)
    model.add_max_equality(
        sum(
            tokens[n][p][token_index]
            for p in range(len(player_list))
        ),
        [
            new_pixie_exists,
            old_pixie_exists
        ]
    )
    retain_token(
        model,
        player_list,
        tokens,
        n,
        token_index,
        old_pixie_exists
    )
    
    for p in range(len(player_list)):
        causes = []
        for q in range(len(player_list)):
            cause = model.new_bool_var(f"{p}_given_pixie_known_token_by_{q}_{n}")
            p_has_q_learned_char = model.new_bool_var(f"{p}_has_{q}_learned_char")
            matches = []
            for i, (a, l) in enumerate(zip(assigned_char[n][p], learned_char[n][q])):
                m = model.new_bool_var(f"pixie_known_{p}_{q}_{i}_match")
                model.add_min_equality(m, [a, l])
                matches.append(m)
            model.add_max_equality(p_has_q_learned_char, matches)
            
            q_is_healthy = model.new_bool_var(f"pixie_known_{q}_is_healthy_{p}_{n}")
            model.add_min_equality(
                q_is_healthy,
                [
                    droisoned[n][q].Not(),
                    vortoxed[n][q].Not()
                ]
            )
            
            model.add_implication(
                assigned_char[n][q][character_index].Not(),
                cause.Not()
            )
            
            model.add_min_equality(
                cause,
                [
                    assigned_char[n][q][character_index],
                    p_has_q_learned_char
                ]
            ).only_enforce_if(q_is_healthy)
                
            model.add_bool_or(
                p_has_q_learned_char.Not(),
                assigned_char[n][q][character_index].Not(),
                vortoxed[n][q].Not()
            )

            causes.append(cause)
        model.add_max_equality(tokens[n][p][token_index], causes)


def add_pixie_has_ability_token_condition(
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    tokens: list[list[list[cp_model.IntVar]]],
    n: int,
    **kwargs,
):
    character_list: list[Character] = kwargs["character_list"]
    assigned_char: list[list[list[cp_model.IntVar]]] = kwargs["assigned_char"]
    learned_char: list[list[list[cp_model.IntVar]]] = kwargs["learned_char"]
    mad_char: list[list[list[cp_model.IntVar]]] = kwargs["mad_char"]
    character_index = [c.name for c in character_list].index("pixie")
    token_index = [t.name for t in token_list].index("pixie_has_ability")
    pixie_known_token_index = [t.name for t in token_list].index("pixie_known")
    dead_token_index = [t.name for t in token_list].index("dead")
    
    if n == 0:
        for p in range(len(player_list)):
            model.add(tokens[n][p][token_index] == 0)
        return

    for p in range(len(player_list)):
        p_was_mad = model.new_bool_var(f"pixie_has_ability_{p}_was_mad_as_learned_char")
        matches = []
        for i, (mad, learned) in enumerate(zip(mad_char[n-1][p], learned_char[n-1][p])): # FIXME
            m = model.new_bool_var(f"pixie_has_ability_{p}_is_mad_as_char_{i}")
            model.add_min_equality(
                m,
                [mad, learned]
            )
            matches.append(m)
        model.add_max_equality(
            p_was_mad,
            matches
        )
        
        causes = []
        for q in range(len(player_list)):
            p_gained_q_ability = model.new_bool_var(f"{p}_gained_{q}_ability_{n}")
            model.add_min_equality(
                p_gained_q_ability,
                [
                    assigned_char[n][p][character_index],
                    assigned_char[n-1][p][character_index],
                    p_was_mad,
                    tokens[n-1][q][pixie_known_token_index],
                    tokens[n-1][q][dead_token_index]
                ]
            )
            causes.append(p_gained_q_ability)
        model.add_max_equality(
            tokens[n][p][token_index],
            causes
        ) # TODO also make this retain?


def add_gambler_attacked_token_condition(
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    tokens: list[list[list[cp_model.IntVar]]],
    n: int,
    **kwargs,
):
    character_list: list[Character] = kwargs["character_list"]
    assigned_char: list[list[list[cp_model.IntVar]]] = kwargs["assigned_char"]
    target: list[list[list[cp_model.IntVar]]] = kwargs["target"]
    learned_char: list[list[list[cp_model.IntVar]]] = kwargs["learned_char"]
    droisoned: list[list[cp_model.IntVar]] = kwargs["droisoned"]
    character_index = [c.name for c in character_list].index("gambler")
    token_index = [t.name for t in token_list].index("gambler_attacked")
    
    for p in range(len(player_list)):
        healthy_incorrect_gambles = []
        for q in range(len(player_list)):
            healthy_p_gambled_q_incorrectly = model.new_bool_var(f"{p}_gambled_{q}_incorrectly_{n}")
            p_gambled_q_char = model.new_bool_var(f"{p}_gambled_{q}_char_{n}")
            matches = []
            for i, (a, l) in enumerate(zip(assigned_char[n][q], learned_char[n][p])):
                m = model.new_bool_var(f"gambler_{p}_{q}_{i}_match_{n}")
                model.add_min_equality(
                    m,
                    [a, l]
                )
                matches.append(m)
            model.add_max_equality(
                p_gambled_q_char,
                matches
            )
            model.add_min_equality(
                healthy_p_gambled_q_incorrectly,
                [
                    assigned_char[n][p][character_index],
                    target[n][p][q],
                    p_gambled_q_char.Not(),
                    droisoned[n][p].Not()
                ]
            )
            healthy_incorrect_gambles.append(healthy_p_gambled_q_incorrectly)
        model.add_max_equality(
            tokens[n][p][token_index],
            healthy_incorrect_gambles
        )


def add_fool_protected_token_condition(
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    tokens: list[list[list[cp_model.IntVar]]],
    n: int,
    **kwargs,
):
    character_list: list[Character] = kwargs["character_list"]
    assigned_char: list[list[list[cp_model.IntVar]]] = kwargs["assigned_char"]
    droisoned: list[list[cp_model.IntVar]] = kwargs["droisoned"]
    character_index = [c.name for c in character_list].index("fool")
    token_index = [t.name for t in token_list].index("fool_protected")
    fool_ability_used_token_index = [t.name for t in token_list].index("fool_ability_used")

    for p in range(len(player_list)):
        model.add_min_equality(
            tokens[n][p][token_index],
            [
                assigned_char[n][p][character_index],
                tokens[n][p][fool_ability_used_token_index].Not(),
                droisoned[n][p].Not()
            ]
        )


def add_tea_lady_protected_token_condition(
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    tokens: list[list[list[cp_model.IntVar]]],
    n: int,
    **kwargs,
):
    character_list: list[Character] = kwargs["character_list"]
    assigned_char: list[list[list[cp_model.IntVar]]] = kwargs["assigned_char"]
    registers_as_evil: list[list[cp_model.IntVar]] = kwargs["registers_as_evil"]
    droisoned: list[list[cp_model.IntVar]] = kwargs["droisoned"]
    character_index = [c.name for c in character_list].index("tea_lady")
    token_index = [t.name for t in token_list].index("tea_lady_protected")
    
    granting_tea_lady_protection = []
    for p in range(len(player_list)):
        p_is_granting_tea_lady_protection = model.new_bool_var(f"{p}_is_granting_tea_lady_protection_{n}")
        model.add_min_equality(
            p_is_granting_tea_lady_protection,
            [
                assigned_char[n][p][character_index],
                registers_as_evil[n][p-1].Not(),
                registers_as_evil[n][(p+1)%len(player_list)].Not(),
                droisoned[n][p].Not()
            ]
        )
        granting_tea_lady_protection.append(p_is_granting_tea_lady_protection)
    
    for p in range(len(player_list)):
        model.add_max_equality(
            tokens[n][p][token_index],
            [
                granting_tea_lady_protection[p-1],
                granting_tea_lady_protection[(p+1)%len(player_list)]
            ]
        )


def add_cannibal_lunch_token_condition(
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    tokens: list[list[list[cp_model.IntVar]]],
    n: int,
    **kwargs,
):
    token_index = [t.name for t in token_list].index("cannibal_lunch")
    executed_token_index = [t.name for t in token_list].index("executed")
    dead_token_index = [t.name for t in token_list].index("dead")
    
    if n == 0:
        for p in range(len(player_list)):
            model.add(tokens[n][p][token_index] == 0)
    else:
        new_player_killed_by_execution = model.new_bool_var(f"new_player_killed_by_execution_{n}")
        causes = []
        for p in range(len(player_list)):
            p_killed_by_execution = model.new_bool_var(f"{p}_killed_by_execution_{n}")
            model.add_min_equality(
                p_killed_by_execution,
                [
                    tokens[n][p][executed_token_index],
                    tokens[n][p][dead_token_index],
                    tokens[n-1][p][dead_token_index].Not()
                ]
            )
            causes.append(p_killed_by_execution)
            
            retain_token = model.new_bool_var(f"{p}_retain_cannibal_lunch_token_{n}")
            model.add_min_equality(
                retain_token,
                [
                    tokens[n-1][p][token_index],
                    new_player_killed_by_execution.Not()
                ]
            )
            model.add_max_equality(
                tokens[n][p][token_index],
                [
                    p_killed_by_execution,
                    retain_token
                ]
            )
        model.add_max_equality(
            new_player_killed_by_execution,
            causes
        )


def add_cannibal_poisoned_token_condition( # TODO might work weirdly with barber
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    tokens: list[list[list[cp_model.IntVar]]],
    n: int,
    **kwargs,
):
    character_list: list[Character] = kwargs["character_list"]
    assigned_char: list[list[list[cp_model.IntVar]]] = kwargs["assigned_char"]
    registers_as_evil: list[list[cp_model.IntVar]] = kwargs["registers_as_evil"]
    character_index = [c.name for c in character_list].index("cannibal")
    token_index = [t.name for t in token_list].index("cannibal_poisoned")
    cannibal_lunch_token_index = [t.name for t in token_list].index("cannibal_lunch")
    
    if n == 0:
        for p in range(len(player_list)):
            model.add(tokens[n][p][token_index] == 0)
    else:
        cannibal_poisoned_before = model.new_bool_var(f"cannibal_poisoned_before_{n}")
        model.add_max_equality(
            cannibal_poisoned_before,
            [
                tokens[n-1][p][token_index]
                for p in range(len(player_list))
            ]
        )
        
        evil_lunch = model.new_bool_var(f"evil_lunch_{n}")
        causes = []
        for p in range(len(player_list)):
            evil_p_eaten = model.new_bool_var(f"evil_{p}_eaten_{n}")
            evil_p_eaten_today = model.new_bool_var(f"evil_{p}_eaten_today_{n}")
            model.add_min_equality(
                evil_p_eaten_today,
                [
                    tokens[n][p][cannibal_lunch_token_index],
                    tokens[n-1][p][cannibal_lunch_token_index].Not(),
                    registers_as_evil[n][p]
                ]
            )
            # true if evil eaten today OR had token yesterday AND lunch has not changed
            # true if evil eaten today OR p is lunch AND p was lunch AND someone had the cannibal poisoned token
            evil_p_eaten_earlier = model.new_bool_var(f"evil_{p}_eaten_earlier_{n}")
            model.add_min_equality(
                evil_p_eaten_earlier,
                [
                    tokens[n][p][cannibal_lunch_token_index],
                    tokens[n-1][p][cannibal_lunch_token_index],
                    cannibal_poisoned_before
                ]
            )
            model.add_max_equality(
                evil_p_eaten,
                [
                    evil_p_eaten_today,
                    evil_p_eaten_earlier
                ]
            )
            causes.append(evil_p_eaten)
        model.add_max_equality(evil_lunch, causes)
        
        for p in range(len(player_list)):
            model.add_min_equality(
                tokens[n][p][token_index],
                [
                    assigned_char[n][p][character_index],
                    evil_lunch
                ]
            )


def add_mayor_win_token_condition(
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    tokens: list[list[list[cp_model.IntVar]]],
    n: int,
    **kwargs,
):
    character_list: list[Character] = kwargs["character_list"]
    assigned_char: list[list[list[cp_model.IntVar]]] = kwargs["assigned_char"]
    executed_indexes: list[int | str | None] = kwargs["executed_indexes"]
    droisoned: list[list[cp_model.IntVar]] = kwargs["droisoned"]
    character_index = [c.name for c in character_list].index("mayor")
    token_index = [t.name for t in token_list].index("mayor_win")
    dead_token_index = [t.name for t in token_list].index("dead")
    
    if not n % 2:
        model.add(
            sum(
                tokens[n][p][token_index]
                for p in range(len(player_list))
            ) == 0
        )
    else:
        three_players_alive = model.new_bool_var(f"mayor_win_three_players_alive_{n}")
        model.add(
            sum(
                tokens[n][p][dead_token_index].Not()
                for p in range(len(player_list))
            ) == 3
        ).only_enforce_if(three_players_alive)
        model.add(
            sum(
                tokens[n][p][dead_token_index].Not()
                for p in range(len(player_list))
            ) != 3
        ).only_enforce_if(three_players_alive.Not())
        
        if n < len(executed_indexes):
            no_execution = executed_indexes[n] is None
        else:
            no_execution = model.new_bool_var(f"mayor_win_no_execution_{n}") # NOTE: intentionally arbitrary
        for p in range(len(player_list)):
            model.add_min_equality(
                tokens[n][p][token_index],
                [
                    assigned_char[n][p][character_index],
                    three_players_alive,
                    no_execution,
                    droisoned[n][p].Not()
                ]
            )


def add_puzzledrunk_token_condition(
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    tokens: list[list[list[cp_model.IntVar]]],
    n: int,
    **kwargs,
):
    character_list: list[Character] = kwargs["character_list"]
    assigned_char: list[list[list[cp_model.IntVar]]] = kwargs["assigned_char"]
    remembered_tokens: list[list[list[cp_model.IntVar]]] = kwargs["remembered_tokens"]
    droisoned: list[list[cp_model.IntVar]] = kwargs["droisoned"]
    token_index = [t.name for t in token_list].index("puzzledrunk")
    character_index = [c.name for c in character_list].index("puzzlemaster")

    token_caused_by_char_existing(
        model,
        player_list,
        token_list,
        assigned_char,
        tokens,
        droisoned,
        n,
        character_index,
        token_index,
        True,
        remembered_tokens=remembered_tokens
    )


def add_puzzlemaster_guess_used_token_conditon(
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    tokens: list[list[list[cp_model.IntVar]]],
    n: int,
    **kwargs,
):
    character_list: list[Character] = kwargs["character_list"]
    assigned_char: list[list[list[cp_model.IntVar]]] = kwargs["assigned_char"]
    puzzlemaster_guess = kwargs["puzzlemaster_guess"]
    token_index = [t.name for t in token_list].index("puzzlemaster_guess_used")
    character_index = [c.name for c in character_list].index("puzzlemaster")
    
    if n == 0:
        for p in range(len(player_list)):
            model.add(tokens[n][p][token_index] == 0)
    else:
        for p in range(len(player_list)):
            p_puzzle_guessed_before = model.new_bool_var(f"{p}_puzzle_guessed_before_{n}")
            model.add_max_equality(
                p_puzzle_guessed_before,
                puzzlemaster_guess[n-1][p] + [tokens[n-1][p][token_index]]
            )
            model.add_min_equality(
                tokens[n][p][token_index],
                [
                    p_puzzle_guessed_before,
                    assigned_char[n][p][character_index]
                ]
            )


def add_damsel_loss_token_condition(
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    tokens: list[list[list[cp_model.IntVar]]],
    n: int,
    **kwargs,
):
    character_list: list[Character] = kwargs["character_list"]
    assigned_char: list[list[list[cp_model.IntVar]]] = kwargs["assigned_char"]
    droisoned: list[list[cp_model.IntVar]] = kwargs["droisoned"]
    damsel_guess: list[list[list[cp_model.IntVar]]] = kwargs["damsel_guess"]
    damsel_guess_order: list[list[cp_model.IntVar]] = kwargs["damsel_guess_order"]
    token_index = [t.name for t in token_list].index("damsel_loss")
    damsel_guess_used_token_index = [t.name for t in token_list].index("damsel_guess_used")
    character_index = [c.name for c in character_list].index("damsel")
    
    if not n % 2:
        for p in range(len(player_list)):
            model.add(tokens[n][p][token_index] == 0)
    else:
        for p in range(len(player_list)):
            causes = []
            for q in range(len(player_list)):
                q_successfully_damsel_guessed_p = model.new_bool_var(f"{q}_damsel_guessed_{p}_{n}")
                q_is_minion = model.new_bool_var(f"{p}_damsel_loss_token_{q}_is_minion_{n}")
                model.add_max_equality(
                    q_is_minion,
                    [
                        assigned_char[n][q][j]
                        for j, c in enumerate(character_list)
                        if c.character_type == "minion"
                    ]
                )
                q_is_first_minion_guess_today = model.new_bool_var(f"{q}_is_first_minion_damsel_guess_today_{n}")
                minion_damsel_guesses_before_q = []
                for r in range(len(player_list)):
                    if q == r:
                        continue
                    r_minion_damsel_guessed_before_q = model.new_bool_var(f"{r}_damsel_guessed_before_{q}_{p}_{n}")
                    r_guessed_before_q = model.new_bool_var(f"damsel_loss_{r}_guessed_before_{q}_{p}_{n}")
                    model.add(
                        damsel_guess_order[n][r] < damsel_guess_order[n][q]
                    ).only_enforce_if(r_guessed_before_q)
                    model.add(
                        damsel_guess_order[n][r] > damsel_guess_order[n][q]
                    ).only_enforce_if(r_guessed_before_q.Not())
                    r_is_minion = model.new_bool_var(f"{p}_{q}_damsel_loss_token_{r}_is_minion_{n}")
                    model.add_max_equality(
                        r_is_minion,
                        [
                            assigned_char[n][r][j]
                            for j, c in enumerate(character_list)
                            if c.character_type == "minion"
                        ]
                    )
                    model.add_min_equality(
                        r_minion_damsel_guessed_before_q,
                        [
                            r_guessed_before_q,
                            r_is_minion
                        ]
                    )
                    minion_damsel_guesses_before_q.append(r_minion_damsel_guessed_before_q)
                model.add_max_equality(
                    q_is_first_minion_guess_today.Not(),
                    minion_damsel_guesses_before_q
                )
                model.add_min_equality(
                    q_successfully_damsel_guessed_p,
                    [
                        q_is_minion,
                        damsel_guess[n][q][p],
                        assigned_char[n][p][character_index],
                        tokens[n-1][p][damsel_guess_used_token_index].Not(),
                        droisoned[n][p].Not(),
                        q_is_first_minion_guess_today,
                    ]
                )
                causes.append(q_successfully_damsel_guessed_p)
            model.add_max_equality(
                tokens[n][p][token_index],
                causes
            )


def add_damsel_guess_used_token_condition(
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    tokens: list[list[list[cp_model.IntVar]]],
    n: int,
    **kwargs,
):
    character_list: list[Character] = kwargs["character_list"]
    assigned_char: list[list[list[cp_model.IntVar]]] = kwargs["assigned_char"]
    damsel_guess: list[list[list[cp_model.IntVar]]] = kwargs["damsel_guess"]
    token_index = [t.name for t in token_list].index("damsel_guess_used")
    character_index = [c.name for c in character_list].index("damsel")
    
    if n == 0:
        for p in range(len(player_list)):
            model.add(tokens[n][p][token_index] == 0)
    else:
        minion_damsel_guessed_yesterday = model.new_bool_var(f"minion_damsel_guessed_yesterday_{n}")
        minion_damsel_guesses_from_yesterday = []
        for p in range(len(player_list)):
            p_minion_damsel_guessed_yesterday = model.new_bool_var(f"guess_used_{p}_minion_damsel_guessed_yesterday_{n}")
            p_damsel_guessed_yesterday = model.new_bool_var(f"damsel_guess_used_{p}_damsel_guessed_yesterday_{n}")
            model.add_max_equality(
                p_damsel_guessed_yesterday,
                damsel_guess[n-1][p]
            )
            p_was_minion = model.new_bool_var(f"damsel_guess_used_{p}_was_minion_{n}")
            model.add_max_equality(
                p_was_minion,
                [
                    assigned_char[n-1][p][j]
                    for j, c in enumerate(character_list)
                    if c.character_type == "minion"
                ]
            )
            model.add_min_equality(
                p_minion_damsel_guessed_yesterday,
                [
                    p_damsel_guessed_yesterday,
                    p_was_minion
                ]
            )
            minion_damsel_guesses_from_yesterday.append(p_minion_damsel_guessed_yesterday)
        model.add_max_equality(
            minion_damsel_guessed_yesterday,
            minion_damsel_guesses_from_yesterday
        )
        for p in range(len(player_list)):
            grant_token_if_damsel = model.new_bool_var(f"grant_{p}_damsel_guess_used_token_if_damsel_{n}")
            model.add_max_equality(
                grant_token_if_damsel,
                [
                    minion_damsel_guessed_yesterday,
                    tokens[n-1][p][token_index]
                ]
            )
            model.add_min_equality(
                tokens[n][p][token_index],
                [
                    grant_token_if_damsel,
                    assigned_char[n][p][character_index]
                ]
            )


def add_is_the_drunk_token_condition(
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    tokens: list[list[list[cp_model.IntVar]]],
    n: int,
    **kwargs,
):
    character_list: list[Character] = kwargs["character_list"]
    assigned_char: list[list[list[cp_model.IntVar]]] = kwargs["assigned_char"]
    character_index = [c.name for c in character_list].index("drunk")
    token_index = [t.name for t in token_list].index("is_the_drunk")
    
    for p in range(len(player_list)):
        model.add(tokens[n][p][token_index] == assigned_char[n][p][character_index])


def add_haircuts_tonight_token_condition(
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    tokens: list[list[list[cp_model.IntVar]]],
    n: int,
    **kwargs,
):
    character_list: list[Character] = kwargs["character_list"]
    assigned_char: list[list[list[cp_model.IntVar]]] = kwargs["assigned_char"]
    droisoned: list[list[cp_model.IntVar]] = kwargs["droisoned"]
    character_index = [c.name for c in character_list].index("barber")
    token_index = [t.name for t in token_list].index("haircuts_tonight")
    dead_token_index = [t.name for t in token_list].index("dead")

    if n % 2:
        for p in range(len(player_list)):
            model.add_min_equality(
                tokens[n][p][token_index],
                [
                    assigned_char[n][p][character_index],
                    tokens[n][p][dead_token_index],
                    tokens[n-1][p][dead_token_index].Not(),
                    droisoned[n][p].Not()
                ]
            )
    else:
        for p in range(len(player_list)):
            barber_p_died_tonight = model.new_bool_var(f"barber_{p}_died_tonight_{n}")
            barber_died_yesterday = model.new_bool_var(f"barber_{p}_died_yesterday_{n}")
            if n > 0:
                model.add_min_equality(
                    barber_p_died_tonight,
                    [
                        assigned_char[n-1][p][character_index], # NOTE: accounts for swapping the barber
                        tokens[n][p][dead_token_index],
                        tokens[n-1][p][dead_token_index].Not(),
                        droisoned[n][p].Not()
                    ]
                )
                
                model.add_min_equality(
                    barber_died_yesterday,
                    [
                        tokens[n-1][p][token_index],
                        assigned_char[n][p][token_index],
                        droisoned[n][p].Not()
                    ]
                )
            else:
                model.add(barber_p_died_tonight == 0)
                model.add(barber_died_yesterday == 0)
            model.add_max_equality(
                tokens[n][p][token_index],
                [
                    barber_p_died_tonight,
                    barber_died_yesterday,
                ]
            )


def add_barber_swapped_token_condition( # TODO: when does this happen?
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    tokens: list[list[list[cp_model.IntVar]]],
    n: int,
    **kwargs,
):
    barber_swap_indexes: list[list[tuple[cp_model.IntVar]]] = kwargs["barber_swap_indexes"]
    token_index = [t.name for t in token_list].index("barber_swapped")
    
    if n == 0:
        for p in range(len(player_list)):
            model.add(tokens[n][p][token_index] == 0)
        return
    
    all_last_n_barber_swap_indexes = [
        barber_swap_index
        for p in range(len(player_list))
        for barber_swap_index in barber_swap_indexes[n-1][p]
    ]
    
    for p in range(len(player_list)):
        causes = []
        for barber_swap_index in all_last_n_barber_swap_indexes:
            cause = model.new_bool_var(f"barber_swap_index_was_{p}_{n}")
            model.add(barber_swap_index == p).only_enforce_if(cause)
            model.add(barber_swap_index != p).only_enforce_if(cause.Not())
            causes.append(cause)
        model.add_max_equality(tokens[n][p][token_index], causes)


def add_devils_advocate_protected_token_condition(
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    tokens: list[list[list[cp_model.IntVar]]],
    n: int,
    **kwargs,
):
    character_list: list[Character] = kwargs["character_list"]
    assigned_char: list[list[list[cp_model.IntVar]]] = kwargs["assigned_char"]
    target: list[list[list[cp_model.IntVar]]] = kwargs["target"]
    droisoned: list[list[cp_model.IntVar]] = kwargs["droisoned"]
    character_index = [c.name for c in character_list].index("devils_advocate")
    token_index = [t.name for t in token_list].index("devils_advocate_protected")
    
    if n == 0:
        model.add(
            sum(
                tokens[n][p][token_index]
                for p in range(len(player_list))
            ) == 0
        )
    else:
        for p in range(len(player_list)):
            causes = []
            for q in range(len(player_list)):
                p_da_protected_by_q = model.new_bool_var(f"{p}_da_protected_by_{q}_{n}")
                model.add_min_equality(
                    p_da_protected_by_q,
                    [
                        assigned_char[n-1][q][character_index],
                        target[n-1][q][p],
                        droisoned[n-1][q].Not(),
                        droisoned[n][q].Not()
                    ]
                )
                causes.append(p_da_protected_by_q)
            model.add_max_equality(
                tokens[n][p][token_index],
                causes
            )


def add_mastermind_day_token_condition( # NOTE: does not work when multiple living demons are possible
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    tokens: list[list[list[cp_model.IntVar]]],
    n: int,
    **kwargs,
):
    character_list: list[Character] = kwargs["character_list"]
    assigned_char: list[list[list[cp_model.IntVar]]] = kwargs["assigned_char"]
    droisoned: list[list[cp_model.IntVar]] = kwargs["droisoned"]
    character_index = [c.name for c in character_list].index("mastermind")
    token_index = [t.name for t in token_list].index("mastermind_day")
    execution_token_index = [t.name for t in token_list].index("executed")
    dead_token_index = [t.name for t in token_list].index("dead")
    
    
    if n % 2:
        demon_died_by_execution = model.new_bool_var(f"demon_died_by_execution_{n}")
        causes = []
        for p in range((len(player_list))):
            p_is_demon = model.new_bool_var(f"{p}_is_demon")
            model.add_max_equality(
                p_is_demon,
                [
                    assigned_char[n][p][j]
                    for j, c in enumerate(character_list)
                    if c.character_type == "demon"
                ]
            )
            
            p_demon_died_by_execution = model.new_bool_var(f"{p}_demon_died_by_execution")
            model.add_min_equality(
                p_demon_died_by_execution,
                [
                    p_is_demon,
                    tokens[n][p][execution_token_index],
                    tokens[n][p][dead_token_index],
                    tokens[n-1][p][dead_token_index].Not()
                ]
            )
            
            causes.append(p_demon_died_by_execution)
        model.add_max_equality(
            demon_died_by_execution,
            causes
        )
        
        for p in range(len(player_list)):
            model.add_min_equality(
                tokens[n][p][token_index],
                [
                    assigned_char[n][p][character_index],
                    demon_died_by_execution,
                    droisoned[n][p].Not()
                ]
            )
    else:
        if n == 0:
            model.add(
                sum(
                    tokens[n][p][token_index]
                    for p in range(len(player_list))
                ) == 0
            )
        else:
            mastermind_activated_today = model.new_bool_var(f"mastermind_activated_today_{n}")
            model.add_max_equality(
                mastermind_activated_today,
                [
                    tokens[n-1][p][token_index]
                    for p in range(len(player_list))
                ]
            )

            for p in range(len(player_list)):
                model.add_min_equality(
                    tokens[n][p][token_index],
                    [
                        assigned_char[n][p][character_index],
                        mastermind_activated_today,
                        droisoned[n][p].Not()
                    ]
                )


def add_mastermind_loss_token_condition(
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    tokens: list[list[list[cp_model.IntVar]]],
    n: int,
    **kwargs,
):
    token_index = [t.name for t in token_list].index("mastermind_loss")
    mastermind_day_token_index = [t.name for t in token_list].index("mastermind_day")
    execution_token_index = [t.name for t in token_list].index("executed")
    
    if not n % 2:
        model.add(
            sum(
                tokens[n][p][token_index]
                for p in range(len(player_list))
            ) == 0
        )
    else:
        mastermind_day = model.new_bool_var(f"mastermind_day_{n}")
        model.add_max_equality(
            mastermind_day,
            [
                tokens[n-1][p][mastermind_day_token_index]
                for p in range(len(player_list))
            ]
        )
        for p in range(len(player_list)):
            model.add_min_equality(
                tokens[n][p][token_index],
                [
                    tokens[n][p][execution_token_index],
                    mastermind_day
                ]
            )


def add_lleech_host_token_condition( # TODO: change this?
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    tokens: list[list[list[cp_model.IntVar]]],
    n: int,
    **kwargs,
):
    character_list: list[Character] = kwargs["character_list"]
    assigned_char: list[list[list[cp_model.IntVar]]] = kwargs["assigned_char"]
    target: list[list[list[cp_model.IntVar]]] = kwargs["target"]
    character_index = [c.name for c in character_list].index("lleech")
    token_index = [t.name for t in token_list].index("lleech_host")
    new_instance_token_index = [t.name for t in token_list].index("new_instance")
    
    for p in range(len(player_list)):
        causes = []
        for q in range(len(player_list)):
            p_chosen_by_new_lleech_q = model.new_bool_var(f"{p}_chosen_by_new_lleech_{q}_{n}")
            model.add_min_equality(
                p_chosen_by_new_lleech_q,
                [
                    assigned_char[n][q][character_index],
                    tokens[n][q][new_instance_token_index],
                    target[n][q][p]
                ]
            )
            causes.append(p_chosen_by_new_lleech_q)
        model.add_max_equality(
            tokens[n][p][token_index],
            causes
        )


def add_lleech_poisoned_token_condition(
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    tokens: list[list[list[cp_model.IntVar]]],
    n: int,
    **kwargs,
):
    character_list: list[Character] = kwargs["character_list"]
    assigned_char: list[list[list[cp_model.IntVar]]] = kwargs["assigned_char"]
    droisoned: list[list[cp_model.IntVar]] = kwargs["droisoned"]
    character_index = [c.name for c in character_list].index("lleech")
    token_index = [t.name for t in token_list].index("lleech_poisoned")
    lleech_host_token_index = [t.name for t in token_list].index("lleech_host")
    
    lleech_is_droisoned = make_char_is_droisoned(
        model,
        player_list,
        assigned_char,
        droisoned,
        n,
        character_index,
        f"lleech_poisoned_lleech_is_droisoned_{n}"
    )
    demon_safe_token_indexes = [
        i
        for i, t in enumerate(token_list)
        if t.name in demon_safe_token_names
    ]
    for p in range(len(player_list)):
        model.add_min_equality(
            tokens[n][p][token_index],
            [
                tokens[n][p][lleech_host_token_index],
                lleech_is_droisoned.Not()
            ]
            + [
                tokens[n][p][t].Not()
                for t in demon_safe_token_indexes
            ]
        )


def add_lleech_unkillable_token_condition(
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    tokens: list[list[list[cp_model.IntVar]]],
    n: int,
    **kwargs,
):
    character_list: list[Character] = kwargs["character_list"]
    assigned_char: list[list[list[cp_model.IntVar]]] = kwargs["assigned_char"]
    droisoned: list[list[cp_model.IntVar]] = kwargs["droisoned"]
    character_index = [c.name for c in character_list].index("lleech")
    token_index = [t.name for t in token_list].index("lleech_unkillable")
    lleech_host_token_index = [t.name for t in token_list].index("lleech_host")
    dead_token_index = [t.name for t in token_list].index("dead")
    
    living_host_exists = model.new_bool_var(f"living_lleech_host_exists_{n}")
    living_hosts = []
    for p in range(len(player_list)):
        m = model.new_bool_var(f"{p}_is_living_lleech_host")
        model.add_min_equality(
            m,
            [
                tokens[n][p][lleech_host_token_index],
                tokens[n][p][dead_token_index].Not()
            ]
        )
        living_hosts.append(m)
    model.add_max_equality(
        living_host_exists,
        living_hosts
    )
    
    for p in range(len(player_list)):
        model.add_min_equality(
            tokens[n][p][token_index],
            [
                assigned_char[n][p][character_index],
                living_host_exists,
                droisoned[n][p].Not()
            ]
        )


def add_lleech_self_kill_token_condition( # TODO: double check mechanics here
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    tokens: list[list[list[cp_model.IntVar]]],
    n: int,
    **kwargs,
):
    character_list: list[Character] = kwargs["character_list"]
    assigned_char: list[list[list[cp_model.IntVar]]] = kwargs["assigned_char"]
    droisoned: list[list[cp_model.IntVar]] = kwargs["droisoned"]
    character_index = [c.name for c in character_list].index("lleech")
    token_index = [t.name for t in token_list].index("lleech_self_kill")
    lleech_unkillable_token_index = [t.name for t in token_list].index("lleech_unkillable")
    
    for p in range(len(player_list)):
        model.add_min_equality(
            tokens[n][p][token_index],
            [
                assigned_char[n][p][character_index],
                tokens[n][p][lleech_unkillable_token_index].Not(),
                droisoned[n][p].Not()
            ]
        )


def add_lleech_attacked_token_condition(
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    tokens: list[list[list[cp_model.IntVar]]],
    n: int,
    **kwargs,
):
    character_list: list[Character] = kwargs["character_list"]
    assigned_char: list[list[list[cp_model.IntVar]]] = kwargs["assigned_char"]
    target: list[list[list[cp_model.IntVar]]] = kwargs["target"]
    droisoned: list[list[cp_model.IntVar]] = kwargs["droisoned"]
    character_index = [c.name for c in character_list].index("lleech")
    token_index = [t.name for t in token_list].index("lleech_attacked")
    attacking_other_player_token(
        model,
        player_list,
        token_list,
        tokens,
        n,
        character_list,
        assigned_char,
        target,
        droisoned,
        character_index,
        token_index,
        True
    )


def add_lleech_mastermind_droisoned_token_condition(
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    tokens: list[list[list[cp_model.IntVar]]],
    n: int,
    **kwargs,
):
    character_list: list[Character] = kwargs["character_list"]
    assigned_char: list[list[list[cp_model.IntVar]]] = kwargs["assigned_char"]
    character_index = [c.name for c in character_list].index("lleech")
    token_index = [t.name for t in token_list].index("lleech_mastermind_droisoned")
    mastermind_day_token_index = [t.name for t in token_list].index("mastermind_day")
    
    mastermind_active = model.new_bool_var(f"lleech_mastermind_droisoned_mastermind_day_{n}")
    model.add_max_equality(
        mastermind_active,
        [
            tokens[n][p][mastermind_day_token_index]
            for p in range(len(player_list))
        ]
    )
    for p in range(len(player_list)):
        model.add_min_equality(
            tokens[n][p][token_index],
            [
                assigned_char[n][p][character_index],
                mastermind_active
            ]
        )


def add_vortox_attacked_token_condition(
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    tokens: list[list[list[cp_model.IntVar]]],
    n: int,
    **kwargs,
):
    character_list: list[Character] = kwargs["character_list"]
    assigned_char: list[list[list[cp_model.IntVar]]] = kwargs["assigned_char"]
    target: list[list[list[cp_model.IntVar]]] = kwargs["target"]
    droisoned: list[list[cp_model.IntVar]] = kwargs["droisoned"]
    character_index = [c.name for c in character_list].index("vortox")
    token_index = [t.name for t in token_list].index("vortox_attacked")
    attacking_other_player_token(
        model,
        player_list,
        token_list,
        tokens,
        n,
        character_list,
        assigned_char,
        target,
        droisoned,
        character_index,
        token_index
    )


def add_vortox_win_token_condition(
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    tokens: list[list[list[cp_model.IntVar]]],
    n: int,
    **kwargs,
):
    character_list: list[Character] = kwargs["character_list"]
    assigned_char: list[list[list[cp_model.IntVar]]] = kwargs["assigned_char"]
    executed_indexes: list[int | str | None] = kwargs["executed_indexes"]
    droisoned: list[list[cp_model.IntVar]] = kwargs["droisoned"]
    character_index = [c.name for c in character_list].index("vortox")
    token_index = [t.name for t in token_list].index("vortox_win")
    
    if not n % 2:
        model.add(
            sum(
                tokens[n][p][token_index]
                for p in range(len(player_list))
            ) == 0
        )
    else:
        if n < len(executed_indexes):
            no_execution = executed_indexes[n] is None
        else:
            no_execution = model.new_bool_var(f"vortox_win_no_execution_{n}") # NOTE: intentionally arbitrary
        for p in range(len(player_list)):
            model.add_min_equality(
                tokens[n][p][token_index],
                [
                    assigned_char[n][p][character_index],
                    no_execution,
                    droisoned[n][p].Not()
                ]
            )


def add_balloonist_known_token_condition(
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    tokens: list[list[list[cp_model.IntVar]]],
    n: int,
    **kwargs,
):
    character_list: list[Character] = kwargs["character_list"]
    assigned_char: list[list[list[cp_model.IntVar]]] = kwargs["assigned_char"]
    target: list[list[list[cp_model.IntVar]]] = kwargs["target"]
    character_index = [c.name for c in character_list].index("balloonist")
    token_index = [t.name for t in token_list].index("balloonist_known")
    
    if n % 2:
        retain_token(model, player_list, tokens, n, token_index) # Purely visual in this case
        return
    
    for p in range(len(player_list)):
        balloonists_chose_p: list[cp_model.IntVar] = []
        for q in range(len(player_list)):
            q_balloonist_chose_p = model.new_bool_var(f"{q}_balloonist_chose_{p}_{n}")
            model.add_min_equality(
                q_balloonist_chose_p,
                [
                    assigned_char[n][q][character_index],
                    target[n][q][p]
                ]
            )
            balloonists_chose_p.append(q_balloonist_chose_p)
        model.add(tokens[n][p][token_index] == sum(balloonists_chose_p))
    
    if n == 0:
        return
    token_exists = model.new_bool_var("balloonist_token_exists")
    assigned_char_list_of_previous_known = []
    for c in range(len(character_list)):
        char = model.new_bool_var(f"{p}_balloonist_known_char")
        for p in range(len(player_list)):
            model.add(char == assigned_char[n-2][p][c]).only_enforce_if(tokens[n-2][p][token_index])
        model.add(char == 0).only_enforce_if(token_exists.Not())
        assigned_char_list_of_previous_known.append(char)
    assigned_char_list_of_previous_known = []    
    
    droisoning_token_indexes = [i for i, t in enumerate(token_list) if t.droisoning]
    model.add_max_equality(
        token_exists,
        [tokens[n][p][token_index] for p in range(len(player_list))]
    )
    for p in range(len(player_list)):
        p_is_droisoned = model.new_bool_var(f"balloonist_known_{p}_is_droisoned_{n}")
        model.add_max_equality(
            p_is_droisoned,
            [tokens[n][p][t] for t in droisoning_token_indexes]
        )

        p_chose_same_char_type = model.new_bool_var(f"{p}_chose_same_char_type_{n}")
        townsfolk_indexes = [
            j for j, c in enumerate(character_list)
            if c.character_type == "townsfolk"
        ]
        outsider_indexes = [
            j for j, c in enumerate(character_list)
            if c.character_type == "outsider"
        ]
        minion_indexes = [
            j for j, c in enumerate(character_list)
            if c.character_type == "minion"
        ]
        demon_indexes = [
            j for j, c in enumerate(character_list)
            if c.character_type == "demon"
        ]
        char_type_index_groups = [
            townsfolk_indexes,
            outsider_indexes,
            minion_indexes,
            demon_indexes
        ]
        matches = []
        for char_type_indexes in char_type_index_groups:
            for i in char_type_indexes:
                for j in char_type_indexes:
                    for q in range(len(player_list)):
                        m = model.new_bool_var(f"{i}_{j}_{q}_character_type_match_{n}")
                        model.add_min_equality(
                            m,
                            [
                                target[n][p][q],
                                assigned_char[n][q][i],
                                assigned_char_list_of_previous_known[j]
                            ]
                        )
                        matches.append(m)
        model.add_max_equality(p_chose_same_char_type, matches)
        
        model.add_implication(
            assigned_char[n][p][character_index],
            p_chose_same_char_type.Not()
        ).only_enforce_if(p_is_droisoned.Not())


def add_lycanthrope_attacked_token_condition(
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    tokens: list[list[list[cp_model.IntVar]]],
    n: int,
    **kwargs,
):
    character_list: list[Character] = kwargs["character_list"]
    assigned_char: list[list[list[cp_model.IntVar]]] = kwargs["assigned_char"]
    target: list[list[list[cp_model.IntVar]]] = kwargs["target"]
    droisoned: list[list[cp_model.IntVar]] = kwargs["droisoned"]
    registers_as_evil: list[list[cp_model.IntVar]] = kwargs["registers_as_evil"]
    character_index = [c.name for c in character_list].index("lycanthrope")
    token_index = [t.name for t in token_list].index("lycanthrope_attacked")
    
    for p in range(len(player_list)):
        model.add_implication(
            registers_as_evil[n][p],
            tokens[n][p][token_index].Not()
        )
    
    attacking_other_player_token(
        model,
        player_list,
        token_list,
        tokens,
        n,
        character_list,
        assigned_char,
        target,
        droisoned,
        character_index,
        token_index
    )


def add_lycanthrope_protected_token_condition( # TODO: fix bug with fool?
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    tokens: list[list[list[cp_model.IntVar]]],
    n: int,
    **kwargs,
):
    lycanthrope_attacked_token_index = [t.name for t in token_list].index("lycanthrope_attacked")
    token_index = [t.name for t in token_list].index("lycanthrope_protected")
    
    for p in range(len(player_list)):
        model.add_max_equality(
            tokens[n][p][token_index],
            [
                tokens[n][q][lycanthrope_attacked_token_index]
                for q in range(len(player_list))
            ]
        )


def add_faux_paw_token_condition(
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    tokens: list[list[list[cp_model.IntVar]]],
    n: int,
    **kwargs,
):
    character_list: list[Character] = kwargs["character_list"]
    assigned_char: list[list[list[cp_model.IntVar]]] = kwargs["assigned_char"]
    is_evil: list[cp_model.IntVar] = kwargs["is_evil"]
    remembered_tokens: list[list[list[cp_model.IntVar]]] = kwargs["remembered_tokens"]
    droisoned: list[list[cp_model.IntVar]] = kwargs["droisoned"]
    token_index = [t.name for t in token_list].index("faux_paw")
    character_index = [c.name for c in character_list].index("lycanthrope")

    for p in range(len(player_list)):
        model.add_implication(
            is_evil[n][p],
            remembered_tokens[n][p][token_index].Not()
        )
    
    previous_faux_paw_turned_evil = model.new_bool_var(f"{n}_previous_faux_paw_turned_evil")
    if n == 0:
        model.add(previous_faux_paw_turned_evil == 0)
    else:
        matches = []
        for p in range(len(player_list)):
            p_faux_paw_turned_evil = model.new_bool_var(f"{p}_faux_paw_turned_evil_{n}")
            model.add_min_equality(
                p_faux_paw_turned_evil,
                [
                    remembered_tokens[n-1][p][token_index],
                    is_evil[n][p]
                ]
            )
            matches.append(p_faux_paw_turned_evil)
        model.add_max_equality(
            previous_faux_paw_turned_evil,
            matches
        )
    token_caused_by_char_existing(
        model,
        player_list,
        token_list,
        assigned_char,
        tokens,
        droisoned,
        n,
        character_index,
        token_index,
        True,
        remembered_tokens,
        keep_token_position=previous_faux_paw_turned_evil.Not()
    )


def add_preached_token_first_night_condition(
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    tokens: list[list[cp_model.IntVar]],
    **kwargs,
):
    character_list: list[Character] = kwargs["character_list"]
    assigned_char: list[list[list[cp_model.IntVar]]] = kwargs["assigned_char"]
    target: list[list[cp_model.IntVar]] = kwargs["target"]
    character_index = [c.name for c in character_list].index("preacher")
    token_index = [t.name for t in token_list].index("preached")
    for p in range(len(player_list)):
        p_is_minion = model.new_bool_var(f"preached_token_first_night_{p}_is_minion")
        model.add(
            p_is_minion
            == sum(
                assigned_char[p][j]
                for j, c in enumerate(character_list)
                if c.character_type == "minion"
            )
        )
        causes = []
        for q in range(len(player_list)):
            cause = model.new_bool_var(f"preached_token_first_night_{p}_{q}_cause")
            model.add_bool_and(
                p_is_minion, assigned_char[q][character_index], target[q][p]
            ).only_enforce_if(cause)
            model.add_bool_or(
                [
                    p_is_minion.Not(),
                    assigned_char[q][character_index].Not(),
                    target[q][p].Not(),
                    cause,
                ]
            )
            causes.append(cause)
        model.add_max_equality(tokens[p][token_index], causes)


def add_princessed_token_first_night_condition(
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    tokens: list[list[cp_model.IntVar]],
    **kwargs,
):
    token_index = [t.name for t in token_list].index("princessed")
    for p in range(len(player_list)):
        model.add(tokens[p][token_index] == 0)


def add_monk_protected_token_condition(
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    tokens: list[list[list[cp_model.IntVar]]],
    n: int,
    **kwargs,
):
    character_list: list[Character] = kwargs["character_list"]
    assigned_char: list[list[list[cp_model.IntVar]]] = kwargs["assigned_char"]
    target: list[list[list[cp_model.IntVar]]] = kwargs["target"]
    droisoned: list[list[cp_model.IntVar]] = kwargs["droisoned"]
    character_index = [c.name for c in character_list].index("monk")
    token_index = [t.name for t in token_list].index("monk_protected")
    
    for p in range(len(player_list)):
        causes = []
        for q in range(len(player_list)):
            p_monk_protected_by_q = model.new_bool_var(f"{p}_monk_protected_by_{q}_{n}")
            model.add_min_equality(
                p_monk_protected_by_q,
                [
                    assigned_char[n][q][character_index],
                    target[n][q][p],
                    droisoned[n][q].Not()
                ]
            )
            causes.append(p_monk_protected_by_q)
        model.add_max_equality(
            tokens[n][p][token_index],
            causes
        )


def add_alchemist_poisoned_token_night_condition(
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    tokens: list[list[cp_model.IntVar]],
    **kwargs,
):
    character_list: list[Character] = kwargs["character_list"]
    assigned_char: list[list[list[cp_model.IntVar]]] = kwargs["assigned_char"]
    target: list[list[cp_model.IntVar]] = kwargs["target"]
    character_index = [c.name for c in character_list].index("alchemist_poisoner")
    token_index = [t.name for t in token_list].index("alchemist_poisoned")

    for p in range(len(player_list)):
        causes: list[cp_model.IntVar] = []
        for q in range(len(player_list)):
            cause = model.new_bool_var(f"alchemist_poisoned_token_night_{p}_{q}_cause")
            model.add_bool_and(
                assigned_char[q][character_index], target[q][p]
            ).only_enforce_if(cause)
            model.add_bool_or(
                [assigned_char[q][character_index].Not(), target[q][p].Not(), cause]
            )
            causes.append(cause)
        model.add_max_equality(tokens[p][token_index], causes)


def add_alchemist_gobbled_token_first_night_condition(
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    tokens: list[list[cp_model.IntVar]],
    **kwargs,
):
    token_index = [t.name for t in token_list].index("alchemist_gobbled")
    for p in range(len(player_list)):
        model.add(tokens[p][token_index] == 0)


def add_goon_drunk_and_evil_token_conditions(
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    tokens: list[list[list[cp_model.IntVar]]],
    n: int,
    **kwargs,
):
    character_list: list[Character] = kwargs["character_list"]
    assigned_char: list[list[list[cp_model.IntVar]]] = kwargs["assigned_char"]
    target: list[list[cp_model.IntVar]] = kwargs["target"]
    registers_as_evil: list[list[cp_model.IntVar]] = kwargs["registers_as_evil"]
    character_index = [c.name for c in character_list].index("goon")
    token_index = [t.name for t in token_list].index("goon_drunk")
    goon_evil_token_index = [t.name for t in token_list].index("goon_evil")
    
    if n % 2:
        retain_token(model, player_list, tokens, n, goon_evil_token_index)
        return
    
    chose_goon: list[cp_model.IntVar] = []
    for p in range(len(player_list)):
        p_chose_goon = model.new_bool_var(f"{p}_chose_goon")
        causes = []
        for q in range(len(player_list)):
            p_chose_q_goon = model.new_bool_var(f"{p}_chose_{q}_goon")
            model.add_min_equality(
                p_chose_q_goon,
                [assigned_char[n][q][character_index], target[n][p][q]]
            )
            causes.append(p_chose_q_goon)
        model.add_max_equality(p_chose_goon, causes)
        chose_goon.append(p_chose_goon)

    assigned_char_night_order_index = []
    for p in range(len(player_list)):
        night_index = model.new_int_var(0, len(character_list) - 1, f"{p}_char_index")
        model.add_max_equality(
            night_index,
            [i * assigned_char[n][p][i] for i in range(len(character_list))]
        )
        assigned_char_night_order_index.append(night_index)

    someone_chose_goon = model.new_bool_var("someone_chose_goon")
    model.add_max_equality(someone_chose_goon, chose_goon)
    model.add(sum(tokens[n][p][token_index] for p in range(len(player_list))) == someone_chose_goon)
    for p in range(len(player_list)):
        model.add(tokens[n][p][token_index] <= chose_goon[p])
        for q in range(len(player_list)):
            if p != q:
                p_acts_after_q = model.new_bool_var(
                    f"goon_drunk_token_{p}_acts_after_{q}"
                )
                model.add(
                    assigned_char_night_order_index[q]
                    < assigned_char_night_order_index[p]
                ).only_enforce_if(p_acts_after_q)
                model.add(
                    assigned_char_night_order_index[q]
                    > assigned_char_night_order_index[p]
                ).only_enforce_if(p_acts_after_q.Not())
                model.add(tokens[n][p][token_index] + chose_goon[q] <= 1).only_enforce_if(
                    p_acts_after_q
                )
    

    # goon alignment change
    for p in range(len(player_list)):
        set_p_alignment = []
        for q in range(len(player_list)):
            q_set_p_alignment = model.new_bool_var(f"{q}_set_{p}_goon_alignment")
            set_p_alignment.append(q_set_p_alignment)
            model.add_min_equality(
                q_set_p_alignment,
                [
                    assigned_char[n][p][character_index],
                    tokens[n][q][token_index]
                ]
            )
            model.add(
                tokens[n][p][goon_evil_token_index]
                == registers_as_evil[n][q]
            ).only_enforce_if(q_set_p_alignment)

        p_alignment_was_set = model.new_bool_var(f"{p}_goon_alignment_was_set")
        model.add_max_equality(
            p_alignment_was_set,
            set_p_alignment
        )
        retain_token(model, player_list, tokens, n, goon_evil_token_index, p_alignment_was_set.Not())


def add_klutz_picked_token_night_condition(
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    tokens: list[list[cp_model.IntVar]],
    **kwargs,
):
    token_index = [t.name for t in token_list].index("klutz_picked_evil")
    for p in range(len(player_list)):
        model.add(tokens[p][token_index] == 0)


def add_poisoned_token_night_condition(
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    tokens: list[list[list[cp_model.IntVar]]],
    n: int,
    **kwargs,
):
    character_list: list[Character] = kwargs["character_list"]
    assigned_char: list[list[list[cp_model.IntVar]]] = kwargs["assigned_char"]
    target: list[list[cp_model.IntVar]] = kwargs["target"]
    droisoned: list[list[cp_model.IntVar]] = kwargs["droisoned"]
    character_index = [c.name for c in character_list].index("poisoner")
    token_index = [t.name for t in token_list].index("poisoned")

    if not n % 2:
        for p in range(len(player_list)):
            causes = []
            for q in range(len(player_list)):
                sober_poisoner_q_chose_p = model.new_bool_var(f"poisoner_{q}_chose_{p}_{n}")
                model.add_min_equality(
                    sober_poisoner_q_chose_p,
                    [
                        assigned_char[n][q][character_index],
                        target[n][q][p],
                        droisoned[n][q].Not()
                    ]
                )
                causes.append(sober_poisoner_q_chose_p)
            model.add_max_equality(
                tokens[n][p][token_index],
                causes
            )
    else:
        poisoner_is_droisoned = make_char_is_droisoned(
            model,
            player_list,
            assigned_char,
            droisoned,
            n,
            character_index,
            f"poisoner_is_droisoned_{n}"
        )
        for p in range(len(player_list)):
            model.add_min_equality(
                tokens[n][p][token_index],
                [
                    tokens[n-1][p][token_index],
                    poisoner_is_droisoned.Not()
                ]
            )


def add_gobble_gobble_token_night_condition(
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    tokens: list[list[cp_model.IntVar]],
    **kwargs,
):
    token_index = [t.name for t in token_list].index("gobble_gobble")
    for p in range(len(player_list)):
        model.add(tokens[p][token_index] == 0)

# TODO: check this
def add_pukka_poisoned_token_condition(
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    tokens: list[list[list[cp_model.IntVar]]],
    n: int,
    **kwargs,
):
    character_list: list[Character] = kwargs["character_list"]
    assigned_char: list[list[list[cp_model.IntVar]]] = kwargs["assigned_char"]
    target: list[list[list[cp_model.IntVar]]] = kwargs["target"]
    droisoned: list[list[cp_model.IntVar]] = kwargs["droisoned"]
    remembered_tokens: list[list[list[cp_model.IntVar]]] = kwargs["remembered_tokens"]
    character_index = [c.name for c in character_list].index("pukka")
    token_index = [t.name for t in token_list].index("pukka_poisoned")
    pukka_attacked_token_index = [t.name for t in token_list].index("pukka_attacked")
    new_instance_token_index = [t.name for t in token_list].index("new_instance")

    demon_safe_token_indexes = [
        i
        for i, t in enumerate(token_list)
        if t.name in demon_safe_token_names
    ]
    
    pukka_is_droisoned = make_char_is_droisoned(
        model,
        player_list,
        assigned_char,
        droisoned,
        n,
        character_index,
        f"pukka_is_droisoned_{n}"
    )
    new_pukka_instance = model.new_bool_var(f"pukka_poisoned_new_pukka_instance_{n}")
    causes = []
    for p in range(len(player_list)):
        p_is_new_pukka = model.new_bool_var(f"{p}_is_new_pukka_{n}")
        model.add_min_equality(
            p_is_new_pukka,
            [
                assigned_char[n][p][character_index],
                tokens[n][p][new_instance_token_index]
            ]
        )
        causes.append(p_is_new_pukka)
    model.add_max_equality(
        new_pukka_instance,
        causes
    )
    
    for p in range(len(player_list)):
        p_got_pukka_poisoned_tonight = model.new_bool_var(f"{p}_got_pukka_poisoned_{n}")
        causes = []
        for q in range(len(player_list)):
            q_pukka_poisoned_p = model.new_bool_var((f"{q}_pukka_poisoned_{p}"))
            model.add_min_equality(
                q_pukka_poisoned_p,
                [
                    assigned_char[n][q][character_index],
                    target[n][q][p],
                    droisoned[n][q].Not()
                ]
                + [
                    tokens[n][p][t].Not()
                    for t in demon_safe_token_indexes
                ]
            )
            causes.append(q_pukka_poisoned_p)
        model.add_max_equality(
            p_got_pukka_poisoned_tonight,
            causes
        )
        
        p_has_unresolved_pukka_poison = model.new_bool_var(f"{p}_has_unresolved_pukka_poison_{n}")
        if n == 0:
            model.add(p_has_unresolved_pukka_poison == 0)
        else:
            model.add_min_equality(
                p_has_unresolved_pukka_poison,
                [
                    remembered_tokens[n-1][p][token_index],
                    tokens[n-1][p][pukka_attacked_token_index].Not()
                ]
            )
        model.add_max_equality(
            remembered_tokens[n][p][token_index],
            [
                p_got_pukka_poisoned_tonight,
                p_has_unresolved_pukka_poison
            ]
        )
        model.add_min_equality(
            tokens[n][p][token_index],
            [
                remembered_tokens[n][p][token_index],
                pukka_is_droisoned.Not()
            ]
        )


def add_pukka_attacked_token_condition(
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    tokens: list[list[list[cp_model.IntVar]]],
    n: int,
    **kwargs,
):
    character_list: list[Character] = kwargs["character_list"]
    assigned_char: list[list[list[cp_model.IntVar]]] = kwargs["assigned_char"]
    remembered_tokens: list[list[list[cp_model.IntVar]]] = kwargs["remembered_tokens"]
    character_index = [c.name for c in character_list].index("pukka")
    token_index = [t.name for t in token_list].index("pukka_attacked")
    pukka_poisoned_token_index = [t.name for t in token_list].index("pukka_poisoned")
    new_instance_token_index = [t.name for t in token_list].index("new_instance")

    new_pukka_instance = model.new_bool_var(f"pukka_attacked_new_pukka_instance_{n}")
    causes = []
    for p in range(len(player_list)):
        p_is_new_pukka = model.new_bool_var(f"{p}_is_new_pukka_{n}")
        model.add_min_equality(
            p_is_new_pukka,
            [
                assigned_char[n][p][character_index],
                tokens[n][p][new_instance_token_index]
            ]
        )
        causes.append(p_is_new_pukka)
    model.add_max_equality(
        new_pukka_instance,
        causes
    )
    
    if n == 0:
        for p in range(len(player_list)):
            model.add(tokens[n][p][token_index] == 0)
    else:
        for p in range(len(player_list)):
            model.add_min_equality(
                tokens[n][p][token_index],
                [
                    tokens[n][p][pukka_poisoned_token_index],
                    remembered_tokens[n-1][p][pukka_poisoned_token_index],
                    tokens[n-1][p][token_index].Not(),
                    new_pukka_instance.Not()
                ]
            )


def add_imp_attacked_token_first_night_condition(
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    tokens: list[list[cp_model.IntVar]],
    **kwargs,
):
    token_index = [t.name for t in token_list].index("imp_attacked")
    for p in range(len(player_list)):
        model.add(tokens[p][token_index] == 0)


def add_starpassed_token_first_night_condition(
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    tokens: list[list[cp_model.IntVar]],
    **kwargs,
):
    token_index = [t.name for t in token_list].index("starpassed")
    for p in range(len(player_list)):
        model.add(tokens[p][token_index] == 0)


def add_new_instance_token_condition(
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    tokens: list[list[cp_model.IntVar]],
    n: int,
    **kwargs,
):
    token_index = [t.name for t in token_list].index("new_instance")
    if n == 0:
        for p in range(len(player_list)):
            model.add(tokens[0][p][token_index] == 1)
    else:
        character_change_token_indexes = [
            i
            for i, t in enumerate(token_list)
            if t.name in character_change_token_names
        ]
        for p in range(len(player_list)):
            model.add_max_equality(
                tokens[n][p][token_index],
                [
                    tokens[n][p][t]
                    for t in character_change_token_indexes
                ]
            )


def add_executed_token_condition(
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    tokens: list[list[cp_model.IntVar]],
    n: int,
    **kwargs,
):
    token_index = [t.name for t in token_list].index("executed")
    executed_indexes: list[int | str | None] = kwargs["executed_indexes"]
    
    if not n % 2:
        for p in range(len(player_list)):
            model.add(tokens[n][p][token_index] == 0)
    elif n == len(executed_indexes):
        model.add_at_most_one(
            tokens[n][p][token_index]
            for p in range(len(player_list))
        )
    else:
        for p in range(len(player_list)):
            if p == executed_indexes[n]:
                model.add(tokens[n][p][token_index] == 1)
            else:
                model.add(tokens[n][p][token_index] == 0)


def add_dead_token_condition( # NOTE: also constrains extra life used tokens
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    tokens: list[list[list[cp_model.IntVar]]],
    n: int,
    **kwargs,
):
    token_index = [t.name for t in token_list].index("dead")
    execution_token_index = [t.name for t in token_list].index("executed")
    fool_ability_used_token_index = [t.name for t in token_list].index("fool_ability_used")
    new_instance_token_index = [t.name for t in token_list].index("new_instance")
    non_demon_attacking_token_indexes = [
        i
        for i, t in enumerate(token_list)
        if t.name in non_demon_attacking_token_names
    ]
    demon_attacking_token_indexes = [
        i
        for i, t in enumerate(token_list)
        if t.name in demon_attacking_token_names
    ]
    general_protective_token_indexes = [
        i
        for i, t in enumerate(token_list)
        if t.name in protection_token_names
    ]
    demon_safe_token_indexes = [
        i
        for i, t in enumerate(token_list)
        if t.name in demon_safe_token_names
    ]
    execution_survival_token_indexes = [
        i
        for i, t in enumerate(token_list)
        if t.name in execution_survival_token_names
    ]
    extra_life_token_indexes = [
        i
        for i, t in enumerate(token_list)
        if t.name in extra_life_token_names
    ]
    
    if n == 0:
        for p in range(len(player_list)):
            model.add(tokens[n][p][token_index] == 0)
            model.add(tokens[n][p][fool_ability_used_token_index] == 0)
    else:
        for p in range(len(player_list)):
            p_died = model.new_bool_var(f"{p}_died_{n}")
            p_attacked_by_non_demon = model.new_bool_var(f"{p}_attacked_by_non_demon_{n}")
            model.add_max_equality(
                p_attacked_by_non_demon,
                [
                    tokens[n][p][t]
                    for t in non_demon_attacking_token_indexes
                ]
            )
            p_attacked_by_demon = model.new_bool_var(f"{p}_attacked_by_demon_{n}")
            model.add_max_equality(
                p_attacked_by_demon,
                [
                    tokens[n][p][t]
                    for t in demon_attacking_token_indexes
                ]
            )
            
            p_generally_protected = model.new_bool_var(f"{p}_generally_protected_{n}")
            model.add_max_equality(
                p_generally_protected,
                [
                    tokens[n][p][t]
                    for t in general_protective_token_indexes
                ]
            )
            
            p_fatally_attacked_by_non_demon = model.new_bool_var(f"{p}_fatally_attacked_by_non_demon_{n}")
            model.add_min_equality(
                p_fatally_attacked_by_non_demon,
                [
                    p_attacked_by_non_demon,
                    p_generally_protected.Not()
                ]
            )
            p_fatally_attacked_by_demon = model.new_bool_var(f"{p}_fatally_attacked_by_demon_{n}")
            model.add_min_equality(
                p_fatally_attacked_by_demon,
                [p_attacked_by_demon]
                + [
                    tokens[n][p][t].Not()
                    for t in demon_safe_token_indexes
                ]
            )
            
            p_fatally_executed = model.new_bool_var(f"{p}_fatally_executed_{n}")
            model.add_min_equality(
                p_fatally_executed,
                [
                    tokens[n][p][execution_token_index],
                    p_generally_protected.Not(),
                ]
                + [
                    tokens[n][p][t].Not()
                    for t in execution_survival_token_indexes
                ]
            )
            
            model.add_max_equality(
                p_died,
                [
                    p_fatally_attacked_by_non_demon,
                    p_fatally_attacked_by_demon,
                    p_fatally_executed
                ]
            )
            
            p_has_extra_life = model.new_bool_var(f"{p}_has_extra_life_{n}")
            model.add_max_equality(
                p_has_extra_life,
                [
                    tokens[n][p][t]
                    for t in extra_life_token_indexes
                ]
            )
            p_died_without_extra_life = model.new_bool_var(f"{p}_died_without_extra_life_{n}")
            model.add_min_equality(
                p_died_without_extra_life,
                [
                    p_died,
                    p_has_extra_life.Not()
                ]
            )
            
            model.add_max_equality(
                tokens[n][p][token_index],
                [
                    p_died_without_extra_life,
                    tokens[n-1][p][token_index]
                ]
            )
            
            p_died_with_extra_life = model.new_bool_var(f"{p}_died_with_extra_life_{n}")
            model.add_min_equality(
                p_died_with_extra_life,
                [
                    p_died,
                    p_has_extra_life
                ]
            )
            p_already_used_extra_life = model.new_bool_var(f"{p}_already_used_extra_life_{n}")
            model.add_min_equality(
                p_already_used_extra_life,
                [
                    tokens[n-1][p][fool_ability_used_token_index],
                    tokens[n][p][new_instance_token_index].Not()
                ]
            )

            model.add_max_equality( # NOTE: needs changing if other extra-life abilities are on the script
                tokens[n][p][fool_ability_used_token_index],
                [
                    p_died_with_extra_life,
                    p_already_used_extra_life
                ]
            )


full_sized_token_list = [
    Token("pixie_known", False, add_pixie_known_token_condition),
    Token("pixie_has_ability", False, add_pixie_has_ability_token_condition),
    Token("gambler_attacked", False, add_gambler_attacked_token_condition),
    Token("monk_protected", False, add_monk_protected_token_condition),
    Token("lycanthrope_attacked", False, add_lycanthrope_attacked_token_condition),
    Token("lycanthrope_protected", False, add_lycanthrope_protected_token_condition),
    Token("faux_paw", False, add_faux_paw_token_condition),
    Token("fool_protected", False, add_fool_protected_token_condition),
    Token("fool_ability_used", False, None),
    Token("tea_lady_protected", False, add_tea_lady_protected_token_condition),
    Token("cannibal_lunch", False, add_cannibal_lunch_token_condition),
    Token("cannibal_poisoned", True, add_cannibal_poisoned_token_condition),
    Token("mayor_win", False, add_mayor_win_token_condition),
    Token("puzzledrunk", True, add_puzzledrunk_token_condition),
    Token("puzzlemaster_guess_used", False, add_puzzlemaster_guess_used_token_conditon),
    Token("damsel_loss", False, add_damsel_loss_token_condition),
    Token("damsel_guess_used", False, add_damsel_guess_used_token_condition),
    Token("is_the_drunk", True, add_is_the_drunk_token_condition),
    Token("haircuts_tonight", False, add_haircuts_tonight_token_condition),
    Token("barber_swapped", False, add_barber_swapped_token_condition),
    Token("poisoned", True, add_poisoned_token_night_condition),
    Token("devils_advocate_protected", False, add_devils_advocate_protected_token_condition),
    Token("mastermind_day", False, add_mastermind_day_token_condition),
    Token("pukka_poisoned", True, add_pukka_poisoned_token_condition),
    Token("pukka_attacked", False, add_pukka_attacked_token_condition),
    Token("lleech_host", False, add_lleech_host_token_condition),
    Token("lleech_poisoned", True, add_lleech_poisoned_token_condition),
    Token("lleech_unkillable", False, add_lleech_unkillable_token_condition),
    Token("lleech_self_kill", False, add_lleech_self_kill_token_condition),
    Token("lleech_attacked", False, add_lleech_attacked_token_condition),
    Token("lleech_mastermind_droisoned", True, add_lleech_mastermind_droisoned_token_condition),
    Token("vortox_attacked", False, add_vortox_attacked_token_condition),
    Token("vortox_win", False, add_vortox_win_token_condition),
    Token("new_instance", False, add_new_instance_token_condition),
    Token("executed", False, add_executed_token_condition),
    Token("dead", True, add_dead_token_condition),
]

teensy_token_list = [
    Token("balloonist_known", False, add_balloonist_known_token_condition),
    Token("lycanthrope_attacked", False, add_lycanthrope_attacked_token_condition),
    Token("lycanthrope_protected", False, add_lycanthrope_protected_token_condition),
    Token("faux_paw", False, add_faux_paw_token_condition),
    Token("preached", True, add_preached_token_first_night_condition),
    Token("princessed", False, add_princessed_token_first_night_condition),
    Token("monk_protected", False, add_monk_protected_token_condition),
    Token("alchemist_poisoned", True, add_alchemist_poisoned_token_night_condition),
    Token("alchemist_gobbled", False, add_alchemist_gobbled_token_first_night_condition),
    Token("goon_drunk", True, add_goon_drunk_and_evil_token_conditions),
    Token("goon_evil", False, None),
    Token("klutz_picked_evil", False, add_klutz_picked_token_night_condition),
    Token("poisoned", True, add_poisoned_token_night_condition),
    Token("gobble_gobble",False, add_gobble_gobble_token_night_condition),
    Token("pukka_poisoned",True, add_pukka_poisoned_token_condition),
    Token("pukka_attacked", False, add_pukka_attacked_token_condition),
    Token("imp_attacked", False, add_imp_attacked_token_first_night_condition),
    Token("starpassed", False, add_starpassed_token_first_night_condition),
    Token("executed", False, ...),
    Token("dead", True, ...)
]

scripts = {
    "Uncertainty Principle (modified)": [
        full_sized_char_list,
        full_sized_token_list
    ],
    "Quantum Teensy Tor-ture [NOT IMPLEMENTED]": [
        teensy_char_list,
        teensy_token_list
    ],
}

non_demon_attacking_token_names = ("gambler_attacked", "lycanthrope_attacked")
demon_attacking_token_names = ("imp_attacked", "pukka_attacked", "lleech_attacked", "vortox_attacked")
demon_safe_token_names = ("monk_protected",)
protection_token_names = ("tea_lady_protected", "lleech_unkillable")
extra_life_token_names = ("fool_protected",)
execution_survival_token_names = ("devils_advocate_protected",)
evil_alignment_token_names = ("goon_evil",)
evil_registration_token_names = ("faux_paw",)
initial_extra_demon_token_names = ()
character_change_token_names = ("starpassed", "barber_swapped")
winning_token_names = ("mayor_win",)
losing_token_names = ("klutz_picked_evil", "damsel_loss")
evil_winning_token_names = ("vortox_win",)
