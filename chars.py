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
            self.possible_characters: list[Character] = character_list
        else:
            self.possible_characters: list[Character] = [
                char for char in character_list if char.alignment == alignment
            ]
        # self.tokens: list[str] = []


class Character:
    def __init__(
        self,
        name: str,
        alignment: str,
        character_type: str,
        can_target,
        learns_character: bool,
    ):
        self.name = name
        self.alignment = alignment
        self.character_type = character_type
        self.can_target = can_target
        self.learns_character = learns_character


class Token:
    def __init__(self, name: str, droisoning: bool, conditions: tuple):
        self.name = name
        self.droisoning = droisoning
        self.conditions = (
            conditions  # first night / other nights / daytime ?
        )


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
    only_if: cp_model.IntVar | None = None
):
    if n == 0:
        return
    if only_if is None:
        for p in range(len(player_list)):
            model.add(tokens[n][p][token_index] == tokens[n-1][p][token_index])
    else:
        for p in range(len(player_list)):
            model.add(tokens[n][p][token_index] == tokens[n-1][p][token_index]).only_enforce_if(only_if)


full_sized_char_list = [ # TODO: add learns_number/group of characters. or just remake this whole thing. use **kwargs instead?
    Character("clockmaker", "good", "townsfolk", lambda _: False, lambda _: False),
    Character("pixie", "good", "townsfolk", lambda _: False, lambda n: n == 0),
    Character("empath", "good", "townsfolk", lambda _: False, lambda _: False),
    Character("mathematician", "good", "townsfolk", lambda _: False, lambda _: False),
    Character("undertaker", "good", "townsfolk", lambda _: False, ...),
    Character("gambler", "good", "townsfolk", lambda n: (n > 1 and not n % 2), lambda _: False),
    # Character("monk", "good", "townsfolk",),
    # Character("lycanthrope", "good", "townsfolk",),
    # Character("NOT GOSSIP!!!!!!!", "good", "townsfolk",),
    # Character("fool", "good", "townsfolk",),
    # Character("tea lady", "good", "townsfolk",),
    # Character("cannibal", "good", "townsfolk",),
    # Character("mayor", "good", "townsfolk",),
    # Character("NOT ATHEIST!!! probably", "good", "townsfolk",),
    # Character("puzzlemaster", "good", "outsider",),
    # Character("damsel", "good", "outsider",),
    # Character("drunk", "good", "outsider",),
    # Character("barber", "good", "outsider",),
    # Character("poisoner", "evil", "minion",),
    # Character("devil's advocate", "evil", "minion",),
    # Character("baron", "evil", "minion",),
    # Character("mastermind", "evil", "minion",),
    # Character("pukka", "evil", "demon",),
    # Character("lleech", "evil", "demon",),
    # Character("vortox", "evil", "demon",),
]

teensy_char_list = [
    Character("balloonist", "good", "townsfolk", lambda _: True, lambda _: False),
    Character("lycanthrope", "good", "townsfolk", lambda n: (n > 1 and not n % 2), lambda _: False),
    Character("preacher", "good", "townsfolk", lambda _: True, lambda _: False),
    Character("princess", "good", "townsfolk", lambda _: False, lambda _: False),
    Character("monk", "good", "townsfolk", lambda n: (n > 1 and not n % 2), lambda _: False),
    Character("alchemist_poisoner", "good", "townsfolk", lambda _: True, lambda _: False),
    Character("alchemist_goblin", "good", "townsfolk", lambda _: False, lambda _: False),
    Character("goon", "good", "outsider", lambda _: False, lambda _: False),
    Character("klutz", "good", "outsider", lambda _: False, lambda _: False),
    Character("poisoner", "evil", "minion", lambda _: True, lambda _: False),
    Character("goblin", "evil", "minion", lambda _: False, lambda _: False),
    Character("pukka", "evil", "demon", lambda _: True, lambda _: False),
    Character("imp", "evil", "demon", lambda n: (n > 1 and not n % 2), lambda _: False),
]
teensy_night_order = [8, 4, 0, 5, 3, 2, 999, 999, 999, 1, 999, 7, 6]
teensy_char_list = [
    x[0] for x in sorted(zip(teensy_char_list, teensy_night_order), key=lambda x: x[1])
]


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


def add_lycanthrope_killed_token_first_night_condition(
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    tokens: list[list[cp_model.IntVar]],
    **kwargs,
):
    token_index = [t.name for t in token_list].index("lycanthrope_killed")
    for p in range(len(player_list)):
        model.add(tokens[p][token_index] == 0)


def add_lycanthrope_evil_token_first_night_condition(
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    tokens: list[list[cp_model.IntVar]],
    **kwargs,
):
    character_list: list[Character] = kwargs["character_list"]
    assigned_char: list[list[list[cp_model.IntVar]]] = kwargs["assigned_char"]
    is_evil: list[cp_model.IntVar] = kwargs["is_evil"]
    token_index = [t.name for t in token_list].index("lycanthrope_evil")
    lycanthrope_index = character_list.index(
        get_character("lycanthrope", character_list)
    )

    lycanthrope_exists = sum(
        assigned_char[p][lycanthrope_index] for p in range(len(player_list))
    )
    for p in range(len(player_list)):
        model.add(tokens[p][token_index] <= is_evil[p].Not())
    model.add(
        sum(tokens[p][token_index] for p in range(len(player_list)))
        == lycanthrope_exists
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


def add_monk_protected_token_first_night_condition(
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    tokens: list[list[cp_model.IntVar]],
    **kwargs,
):
    token_index = [t.name for t in token_list].index("monk_protected")
    for p in range(len(player_list)):
        model.add(tokens[p][token_index] == 0)


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
    is_evil: list[list[cp_model.IntVar]] = kwargs["is_evil"]
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
    lycanthrope_evil_token_index = [t.name for t in token_list].index("lycanthrope_evil")

    for p in range(len(player_list)):
        set_p_alignment = []
        for q in range(len(player_list)):
            q_registers_as_evil = model.new_bool_var(f"{q}_registers_as_evil")
            model.add_max_equality(
                q_registers_as_evil,
                [
                    is_evil[n][q],
                    tokens[n][q][lycanthrope_evil_token_index]
                ]
            )

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
                == q_registers_as_evil
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
    tokens: list[list[cp_model.IntVar]],
    **kwargs,
):
    character_list: list[Character] = kwargs["character_list"]
    assigned_char: list[list[list[cp_model.IntVar]]] = kwargs["assigned_char"]
    target: list[list[cp_model.IntVar]] = kwargs["target"]
    character_index = [c.name for c in character_list].index("poisoner")
    token_index = [t.name for t in token_list].index("poisoned")

    for p in range(len(player_list)):
        causes: list[cp_model.IntVar] = []
        for q in range(len(player_list)):
            cause = model.new_bool_var((f"poisoned_token_night_{p}_{q}_cause"))
            model.add_bool_and(
                assigned_char[q][character_index], target[q][p]
            ).only_enforce_if(cause)
            model.add_bool_or(
                [assigned_char[q][character_index].Not(), target[q][p].Not(), cause]
            )
            causes.append(cause)
        model.add_max_equality(tokens[p][token_index], causes)


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


def add_pukka_poisoned_token_night_condition(
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    tokens: list[list[cp_model.IntVar]],
    **kwargs,
):
    character_list: list[Character] = kwargs["character_list"]
    assigned_char: list[list[list[cp_model.IntVar]]] = kwargs["assigned_char"]
    target: list[list[cp_model.IntVar]] = kwargs["target"]
    character_index = [c.name for c in character_list].index("pukka")
    token_index = [t.name for t in token_list].index("pukka_poisoned")

    for p in range(len(player_list)):
        causes: list[cp_model.IntVar] = []
        for q in range(len(player_list)):
            cause = model.new_bool_var((f"pukka_poisoned_token_night_{p}_{q}_cause"))
            model.add_bool_and(
                assigned_char[q][character_index], target[q][p]
            ).only_enforce_if(cause)
            model.add_bool_or(
                [assigned_char[q][character_index].Not(), target[q][p].Not(), cause]
            )
            causes.append(cause)
        model.add_max_equality(tokens[p][token_index], causes)


def add_pukka_killed_token_first_night_condition(
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    tokens: list[list[cp_model.IntVar]],
    **kwargs,
):
    token_index = [t.name for t in token_list].index("pukka_killed")
    for p in range(len(player_list)):
        model.add(tokens[p][token_index] == 0)


def add_imp_killed_token_first_night_condition(
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    tokens: list[list[cp_model.IntVar]],
    **kwargs,
):
    token_index = [t.name for t in token_list].index("imp_killed")
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


def add_executed_token_condition(
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    tokens: list[list[cp_model.IntVar]],
    n: int,
    **kwargs
):
    ...


def add_dead_token_condition(
    model: cp_model.CpModel,
    player_list: list[Player],
    token_list: list[Token],
    tokens: list[list[cp_model.IntVar]],
    n: int,
    **kwargs
):
    executed_index = kwargs["executed_index"]
    token_index = [t.name for t in token_list].index("dead")
    killing_token_indexes = [
        i for i, t in enumerate(token_list)
        if t.name in killing_token_names
    ]
    general_protective_token_indexes = [
        i for i, t in enumerate(token_list)
        if t.name in protection_token_names
    ]
    for p in range(player_list):
        p_executed_unprotected = model.new_bool_var(f"{p}_executed_unprotected_{n}")
        p_was_executed = model.new_bool_var()
        model.add()
        model.add_max_equality(
            tokens[n][p][token_index],
            [p_executed_unprotected] +
            [
                tokens[n][p][t]
                for t in killing_token_indexes
            ]
        )


full_sized_token_list = []

teensy_token_list = [
    Token("balloonist_known", False, add_balloonist_known_token_condition),
    Token("lycanthrope_killed", False, add_lycanthrope_killed_token_first_night_condition),
    Token("lycanthrope_evil", False, add_lycanthrope_evil_token_first_night_condition),
    Token("preached", True, add_preached_token_first_night_condition),
    Token("princessed", False, add_princessed_token_first_night_condition),
    Token("monk_protected", False, add_monk_protected_token_first_night_condition),
    Token("alchemist_poisoned", True, add_alchemist_poisoned_token_night_condition),
    Token("alchemist_gobbled", False, add_alchemist_gobbled_token_first_night_condition),
    Token("goon_drunk", True, add_goon_drunk_and_evil_token_conditions),
    Token("goon_evil", False, None),
    Token("klutz_picked_evil", False, add_klutz_picked_token_night_condition),
    Token("poisoned", True, add_poisoned_token_night_condition),
    Token("gobble_gobble",False, add_gobble_gobble_token_night_condition),
    Token("pukka_poisoned",True, add_pukka_poisoned_token_night_condition),
    Token("pukka_killed", False, add_pukka_killed_token_first_night_condition),
    Token("imp_killed", False, add_imp_killed_token_first_night_condition),
    Token("starpassed", False, add_starpassed_token_first_night_condition),
    Token("executed", False, ...),
    Token("dead", True, ...)
]

scripts = {
    "Quantum Teensy Tor-ture": [
        teensy_char_list,
        teensy_token_list
    ],
    "Uncertainty Principle (modified)": [
        full_sized_char_list,
        full_sized_token_list
    ]
}

killing_token_names = ("executed", "imp_killed", "pukka_killed")
demon_safe_token_names = ()
protection_token_names = ()
execution_survival_tokens = ()
evil_alignment_token_names = ("goon_evil",)
initial_extra_demon_token_names = ()
character_change_token_names = ("starpassed",)
good_wins_token_names = ()
evil_wins_token_names = ("klutz_picked_evil",)
