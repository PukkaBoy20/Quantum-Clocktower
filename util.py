def evil_count(player_count: int) -> int:
    if player_count < 4:
        raise ValueError
    elif player_count < 10:
        return 2
    elif player_count < 13:
        return 3
    elif player_count < 16:
        return 4
    else:
        raise ValueError


def outsider_count(player_count: int) -> int:
    if player_count < 7:
        return (player_count - 2) % 3
    else:
        return (player_count - 1) % 3


EVIL_COLOUR = "#FF7C7A"
GOOD_COLOUR = "light blue"
QUANTUM_COLOUR = "blue violet"
DEFAULT_COLOUR = "#F0F0F0"
