from ortools.sat.python import cp_model


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


def set_solver_parameters(solver: cp_model.CpSolver):
    # TODO: test these at different model sizes
    # solver.parameters.linearization_level = 0
    solver.parameters.symmetry_level = 0 # NOTE: ~20x faster in some cases
    solver.parameters.cp_model_probing_level = 0 # NOTE: ~1.25x faster
    solver.parameters.max_presolve_iterations = 1


EVIL_COLOUR = "#FF7C7A"
GOOD_COLOUR = "light blue"
QUANTUM_COLOUR = "blue violet"
DEFAULT_COLOUR = "#F0F0F0"
