from ortools.sat.python import cp_model

class Player:
    def __init__(self, name, alignment, character_list):
        self.name = name
        self.alignment = alignment
        if alignment == None:
            self.possible_characters: list[Character] = character_list
        else:
            self.possible_characters: list[Character] = [char for char in character_list if char.alignment == alignment]
        # self.tokens: list[str] = []
class Character:
    def __init__(self, name: str, alignment: str, character_type: str, can_target_night_1: bool, can_target_other_nights: bool, learns_player: bool):
        self.name = name
        self.alignment = alignment
        self.character_type = character_type
        self.can_target_night_1 = can_target_night_1
        self.can_target_other_nights = can_target_other_nights
        self.learns_player = learns_player
class Token:
    def __init__(self, name: str, droisoning: bool, conditions: tuple[tuple[cp_model.IntVar]]):
        self.name = name
        self.droisoning = droisoning
        self.conditions = conditions # first night / other nights / daytime / execution???

def get_character(name: str, character_list: list[Character]):
    for character in character_list:
        if character.name == name:
            return character
    raise RuntimeWarning

# backup list "clockmaker", "pixie", "empath", "mathematician", "undertaker", "gambler", "monk", "lycanthrope", "gossip", "fool", "tea lady", "cannibal", "mayor", "atheist", "puzzlemaster", "damsel", "drunk", "barber", "poisoner", "devil's advocate", "baron", "mastermind", "pukka", "lleech", "vortox"
# char_list = [
#     Character("clockmaker", "good", "townsfolk", rnm_clockmaker),
#     Character("pixie", "good", "townsfolk", rnm_pixie),
#     Character("empath", "good", "townsfolk", rnm_empath),
#     Character("mathematician", "good", "townsfolk", rnm_mathematician),
#     Character("undertaker", "good", "townsfolk", rnm_undertaker),
#     Character("gambler", "good", "townsfolk", rnm_undertaker),
#     Character("monk", "good", "townsfolk", rnm_monk),
#     Character("lycanthrope", "good", "townsfolk", rnm_lycanthrope),
#     Character("gossip", "good", "townsfolk", rnm_gossip),
#     Character("fool", "good", "townsfolk", rnm_fool),
#     Character("tea lady", "good", "townsfolk", rnm_tea_lady),
#     Character("cannibal", "good", "townsfolk", rnm_cannibal),
#     Character("mayor", "good", "townsfolk", rnm_mayor),
#     Character("atheist", "good", "townsfolk", rnm_atheist),
#     Character("puzzlemaster", "good", "outsider", rnm_puzzlemaster),
#     Character("damsel", "good", "outsider", rnm_damsel),
#     Character("drunk", "good", "outsider", rnm_drunk),
#     Character("barber", "good", "outsider", rnm_barber),
#     Character("poisoner", "evil", "minion", rnm_poisoner),
#     Character("devil's advocate", "minion", "evil", rnm_devils_advocate),
#     Character("baron", "evil", "minion", rnm_baron),
#     Character("mastermind", "evil", "minion", rnm_mastermind),
#     Character("pukka", "evil", "demon", rnm_pukka),
#     Character("lleech", "evil", "demon", rnm_lleech),
#     Character("vortox", "evil", "demon", rnm_vortox)
# ]
teensy_char_list = [
    Character("balloonist", "good", "townsfolk", True, True, True),
    Character("lycanthrope", "good", "townsfolk", False, True, False),
    Character("preacher", "good", "townsfolk", True, True, False),
    Character("princess", "good", "townsfolk", False, False, False),
    Character("monk", "good", "townsfolk", False, True, False),
    Character("alchemist_poisoner", "good", "townsfolk", True, True, False),
    Character("alchemist_goblin", "good", "townsfolk", False, False, False),
    Character("goon", "good", "outsider", False, False, False),
    Character("klutz", "good", "outsider", False, False, True),
    Character("poisoner", "evil", "minion", True, True, False),
    Character("goblin", "evil", "minion", False, False, True),
    Character("pukka", "evil", "demon", True, True, False),
    Character("imp", "evil", "demon", False, True, False)
]
teensy_night_order = [
    9,
    5,
    1,
    6,
    4,
    3,
    999,
    0,
    999,
    2,
    999,
    8,
    7
]
teensy_char_list = [x[0] for x in sorted(zip(teensy_char_list, teensy_night_order), key=lambda x: x[1])]


def add_balloonist_known_token_first_night_condition(model: cp_model.CpModel, player_list: list[Player], token_list: list[Token], tokens: list[list[cp_model.IntVar]], **kwargs):
    character_list: list[Character] = kwargs["character_list"]
    assigned_char: list[list[cp_model.IntVar]] = kwargs["assigned_char"]
    target: list[list[cp_model.IntVar]] = kwargs["target"]
    character_index = [c.name for c in character_list].index("balloonist")
    token_index = [t.name for t in token_list].index("balloonist_known")

    for p in range(len(player_list)):
        causes: list[cp_model.IntVar] = []
        for q in range(len(player_list)):
            cause = model.new_bool_var(f"balloonist_known_first_night_{p}_{q}_cause")
            model.add_bool_and(assigned_char[q][character_index], target[q][p]).only_enforce_if(cause)
            model.add_bool_or([
                assigned_char[q][character_index].Not(),
                target[q][p].Not(),
                cause
            ])
            causes.append(cause)
        model.add_max_equality(tokens[p][token_index], causes)
def add_lycanthrope_killed_token_first_night_condition(model: cp_model.CpModel, player_list: list[Player], token_list: list[Token], tokens: list[list[cp_model.IntVar]], **kwargs):
    token_index = [t.name for t in token_list].index("lycanthrope_killed")
    for p in range(len(player_list)):
        model.add(tokens[p][token_index] == 0)
def add_lycanthrope_evil_token_first_night_condition(model: cp_model.CpModel, player_list: list[Player], token_list: list[Token], tokens: list[list[cp_model.IntVar]], **kwargs):
    character_list: list[Character] = kwargs["character_list"]
    assigned_char: list[list[cp_model.IntVar]] = kwargs["assigned_char"]
    is_evil: list[cp_model.IntVar] = kwargs["is_evil"]
    token_index = [t.name for t in token_list].index("lycanthrope_evil")
    lycanthrope_index = character_list.index(get_character("lycanthrope", character_list))
    
    lycanthrope_exists = sum(assigned_char[p][lycanthrope_index] for p in range(len(player_list)))
    for p in range(len(player_list)):
        model.add(tokens[p][token_index] <= is_evil[p].Not())
    model.add(sum(tokens[p][token_index] for p in range(len(player_list))) == lycanthrope_exists)
def add_preached_token_first_night_condition(model: cp_model.CpModel, player_list: list[Player], token_list: list[Token], tokens: list[list[cp_model.IntVar]], **kwargs):
    character_list: list[Character] = kwargs["character_list"]
    assigned_char: list[list[cp_model.IntVar]] = kwargs["assigned_char"]
    target: list[list[cp_model.IntVar]] = kwargs["target"]
    character_index = [c.name for c in character_list].index("preacher")
    token_index = [t.name for t in token_list].index("preached")    
    for p in range(len(player_list)):
        p_is_minion = model.new_bool_var(f"preached_token_first_night_{p}_is_minion")
        model.add(p_is_minion == sum(assigned_char[p][j] for j, c in enumerate(character_list) if c.character_type == "minion"))
        causes = []
        for q in range(len(player_list)):
            cause = model.new_bool_var(f"preached_token_first_night_{p}_{q}_cause")
            model.add_bool_and(p_is_minion, assigned_char[q][character_index], target[q][p]).only_enforce_if(cause)
            model.add_bool_or([
                p_is_minion.Not(),
                assigned_char[q][character_index].Not(),
                target[q][p].Not(),
                cause
            ])
            causes.append(cause)
        model.add_max_equality(tokens[p][token_index], causes)
def add_princessed_token_first_night_condition(model: cp_model.CpModel, player_list: list[Player], token_list: list[Token], tokens: list[list[cp_model.IntVar]], **kwargs):
    token_index = [t.name for t in token_list].index("princessed")
    for p in range(len(player_list)):
        model.add(tokens[p][token_index] == 0)
def add_monk_protected_token_first_night_condition(model: cp_model.CpModel, player_list: list[Player], token_list: list[Token], tokens: list[list[cp_model.IntVar]], **kwargs):
    token_index = [t.name for t in token_list].index("monk_protected")
    for p in range(len(player_list)):
        model.add(tokens[p][token_index] == 0)
def add_alchemist_poisoned_token_night_condition(model: cp_model.CpModel, player_list: list[Player], token_list: list[Token], tokens: list[list[cp_model.IntVar]], **kwargs):
    character_list: list[Character] = kwargs["character_list"]
    assigned_char: list[list[cp_model.IntVar]] = kwargs["assigned_char"]
    target: list[list[cp_model.IntVar]] = kwargs["target"]
    character_index = [c.name for c in character_list].index("alchemist_poisoner")
    token_index = [t.name for t in token_list].index("alchemist_poisoned")
    
    for p in range(len(player_list)):
        causes: list[cp_model.IntVar] = []
        for q in range(len(player_list)):
            cause = model.new_bool_var(f"alchemist_poisoned_token_night_{p}_{q}_cause")
            model.add_bool_and(assigned_char[q][character_index], target[q][p]).only_enforce_if(cause)
            model.add_bool_or([
                assigned_char[q][character_index].Not(),
                target[q][p].Not(),
                cause
            ])
            causes.append(cause)
        model.add_max_equality(tokens[p][token_index], causes)
def add_alchemist_gobbled_token_first_night_condition(model: cp_model.CpModel, player_list: list[Player], token_list: list[Token], tokens: list[list[cp_model.IntVar]], **kwargs):
    token_index = [t.name for t in token_list].index("alchemist_gobbled")
    for p in range(len(player_list)):
        model.add(tokens[p][token_index] == 0)
def add_goon_drunk_and_evil_token_conditions(model: cp_model.CpModel, player_list: list[Player], token_list: list[Token], tokens: list[list[cp_model.IntVar]], **kwargs):
    character_list: list[Character] = kwargs["character_list"]
    assigned_char: list[list[cp_model.IntVar]] = kwargs["assigned_char"]
    target: list[list[cp_model.IntVar]] = kwargs["target"]
    is_evil: list[cp_model.IntVar] = kwargs["is_evil"]
    character_index = [c.name for c in character_list].index("goon")
    token_index = [t.name for t in token_list].index("goon_drunk")
    goon_evil_token_index = [t.name for t in token_list].index("goon_evil")

    chose_goon: list[cp_model.IntVar] = []
    for p in range(len(player_list)):
        chose_goon.append(model.new_bool_var(f"{p}_chose_goon"))
        causes: list[cp_model.IntVar] = []
        for q in range(len(player_list)):
            cause = model.new_bool_var((f"chose_goon_{p}_{q}_cause"))
            model.add_bool_and(assigned_char[q][character_index], target[p][q]).only_enforce_if(cause)
            model.add_bool_or([
                assigned_char[q][character_index].Not(),
                target[p][q].Not(),
                cause
            ])
            causes.append(cause)
        model.add(chose_goon[p] == sum(causes))
    
    assigned_char_night_order_index = []
    for p in range(len(player_list)):
        night_index = model.new_int_var(0, len(character_list)-1, f"{p}_char_index")
        model.add(night_index == sum(i * assigned_char[p][i] for i in range(len(character_list))))
        assigned_char_night_order_index.append(night_index)
    
    goon_drunk_player = model.new_int_var(-1, len(player_list)-1, "goon_drunk_player")
    for p in range(len(player_list)):
        model.add(goon_drunk_player == p).only_enforce_if(tokens[p][token_index])
        model.add(goon_drunk_player != p).only_enforce_if(tokens[p][token_index].Not())
        model.add(chose_goon[p] == 1).only_enforce_if(tokens[p][token_index])
        for q in range(len(player_list)):
            if p != q:
                p_acts_after_q = model.new_bool_var(f"goon_drunk_token_{p}_acts_after_{q}")
                model.add(assigned_char_night_order_index[q] < assigned_char_night_order_index[p]).only_enforce_if(p_acts_after_q)
                model.add(assigned_char_night_order_index[q] > assigned_char_night_order_index[p]).only_enforce_if(p_acts_after_q.Not())
                model.add(tokens[p][token_index] + chose_goon[q] <= 1).only_enforce_if(p_acts_after_q)
    
    # goon alignment change
    lycanthrope_evil_token_index = [t.name for t in token_list].index("lycanthrope_evil")
    for p in range(len(player_list)):
        for q in range(len(player_list)):
            q_registers_as_evil = model.new_bool_var(f"{q}_registers_as_evil")
            model.add_bool_or(is_evil[q], tokens[q][lycanthrope_evil_token_index]).only_enforce_if(q_registers_as_evil)
            model.add_bool_and(is_evil[q].Not(), tokens[q][lycanthrope_evil_token_index].Not()).only_enforce_if(q_registers_as_evil.Not())
            
            p_is_evil_goon = model.new_bool_var(f"{p}_is_evil_goon")
            model.add_bool_and([assigned_char[p][character_index], tokens[q][token_index], q_registers_as_evil]).only_enforce_if(p_is_evil_goon)
            model.add_implication(p_is_evil_goon, assigned_char[p][character_index])
            model.add_implication(p_is_evil_goon, tokens[q][token_index])
            model.add_implication(p_is_evil_goon, q_registers_as_evil)
            model.add(tokens[p][goon_evil_token_index] == 1).only_enforce_if(p_is_evil_goon)
            model.add(tokens[p][goon_evil_token_index] == 0).only_enforce_if(p_is_evil_goon.Not())
def add_klutz_picked_token_night_condition(model: cp_model.CpModel, player_list: list[Player], token_list: list[Token], tokens: list[list[cp_model.IntVar]], **kwargs):
    token_index = [t.name for t in token_list].index("klutz_picked")
    for p in range(len(player_list)):
        model.add(tokens[p][token_index] == 0)
def add_poisoned_token_night_condition(model: cp_model.CpModel, player_list: list[Player], token_list: list[Token], tokens: list[list[cp_model.IntVar]], **kwargs):
    character_list: list[Character] = kwargs["character_list"]
    assigned_char: list[list[cp_model.IntVar]] = kwargs["assigned_char"]
    target: list[list[cp_model.IntVar]] = kwargs["target"]
    character_index = [c.name for c in character_list].index("poisoner")
    token_index = [t.name for t in token_list].index("poisoned")

    for p in range(len(player_list)):
        causes: list[cp_model.IntVar] = []
        for q in range(len(player_list)):
            cause = model.new_bool_var((f"poisoned_token_night_{p}_{q}_cause"))
            model.add_bool_and(assigned_char[q][character_index], target[q][p]).only_enforce_if(cause)
            model.add_bool_or([
                assigned_char[q][character_index].Not(),
                target[q][p].Not(),
                cause
            ])
            causes.append(cause)
        model.add_max_equality(tokens[p][token_index], causes)
def add_gobble_gobble_token_night_condition(model: cp_model.CpModel, player_list: list[Player], token_list: list[Token], tokens: list[list[cp_model.IntVar]], **kwargs):
    token_index = [t.name for t in token_list].index("gobble_gobble")
    for p in range(len(player_list)):
        model.add(tokens[p][token_index] == 0)
def add_pukka_poisoned_token_night_condition(model: cp_model.CpModel, player_list: list[Player], token_list: list[Token], tokens: list[list[cp_model.IntVar]], **kwargs):
    character_list: list[Character] = kwargs["character_list"]
    assigned_char: list[list[cp_model.IntVar]] = kwargs["assigned_char"]
    target: list[list[cp_model.IntVar]] = kwargs["target"]
    character_index = [c.name for c in character_list].index("pukka")
    token_index = [t.name for t in token_list].index("pukka_poisoned")

    for p in range(len(player_list)):
        causes: list[cp_model.IntVar] = []
        for q in range(len(player_list)):
            cause = model.new_bool_var((f"pukka_poisoned_token_night_{p}_{q}_cause"))
            model.add_bool_and(assigned_char[q][character_index], target[q][p]).only_enforce_if(cause)
            model.add_bool_or([
                assigned_char[q][character_index].Not(),
                target[q][p].Not(),
                cause
            ])
            causes.append(cause)
        model.add_max_equality(tokens[p][token_index], causes)
def add_pukka_killed_token_first_night_condition(model: cp_model.CpModel, player_list: list[Player], token_list: list[Token], tokens: list[list[cp_model.IntVar]], **kwargs):
    token_index = [t.name for t in token_list].index("pukka_killed")
    for p in range(len(player_list)):
        model.add(tokens[p][token_index] == 0)
def add_imp_killed_token_first_night_condition(model: cp_model.CpModel, player_list: list[Player], token_list: list[Token], tokens: list[list[cp_model.IntVar]], **kwargs):
    token_index = [t.name for t in token_list].index("imp_killed")
    for p in range(len(player_list)):
        model.add(tokens[p][token_index] == 0)
def add_starpassed_token_first_night_condition(model: cp_model.CpModel, player_list: list[Player], token_list: list[Token], tokens: list[list[cp_model.IntVar]], **kwargs):
    token_index = [t.name for t in token_list].index("starpassed")
    for p in range(len(player_list)):
        model.add(tokens[p][token_index] == 0)

teensy_token_list = [
    Token("balloonist_known", False, (add_balloonist_known_token_first_night_condition,)),
    Token("lycanthrope_killed", False, (add_lycanthrope_killed_token_first_night_condition,)),
    Token("lycanthrope_evil", False, (add_lycanthrope_evil_token_first_night_condition,)),
    Token("preached", True, (add_preached_token_first_night_condition,)),
    Token("princessed", False, (add_princessed_token_first_night_condition,)),
    Token("monk_protected", False, (add_monk_protected_token_first_night_condition,)),
    Token("alchemist_poisoned", True, (add_alchemist_poisoned_token_night_condition,)),
    Token("alchemist_gobbled", False, (add_alchemist_gobbled_token_first_night_condition,)),
    Token("goon_drunk", True, (add_goon_drunk_and_evil_token_conditions, add_goon_drunk_and_evil_token_conditions,)),
    Token("goon_evil", False, None),
    Token("klutz_picked", False, (add_klutz_picked_token_night_condition, add_klutz_picked_token_night_condition,)),
    Token("poisoned", True, (add_poisoned_token_night_condition, add_poisoned_token_night_condition,)),
    Token("gobble_gobble", False, (add_gobble_gobble_token_night_condition, add_gobble_gobble_token_night_condition,)),
    Token("pukka_poisoned", True, (add_pukka_poisoned_token_night_condition, add_pukka_poisoned_token_night_condition,)),
    Token("pukka_killed", False, (add_pukka_killed_token_first_night_condition,)),
    Token("imp_killed", False, (add_imp_killed_token_first_night_condition,)),
    Token("starpassed", False, (add_starpassed_token_first_night_condition,)),
]