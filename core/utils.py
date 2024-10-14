from core.players.reflex.player import Player
from core.event import EventBook
from core.players.reflex.werewolf import WerewolfPlayer
from core.players.reflex.medic import MedicPlayer
from core.players.reflex.seer import SeerPlayer
from core.players.reflex.villager import VillagerPlayer
import pickle, os
import inspect
switcher_players = {
    "reflex": {
        "werewolf": WerewolfPlayer,
        "medic": MedicPlayer,
        "seer": SeerPlayer,
        "villager": VillagerPlayer
    },
}

def count_adjustable_params(func):    
    # Get the signature of the function
    sig = inspect.signature(func)
    params = sig.parameters
    
    # Determine if it's a method (by checking if 'self' or 'cls' is the first parameter)
    is_method = inspect.ismethod(func) or (inspect.isfunction(func) and 'self' in params)

    count = 0
    for i, param in enumerate(params.values()):
        # print(f"param: {param}")
        # Skip 'self' or 'cls' for methods
        if is_method and i == 0 and param.name in ('self', 'cls'):
            continue
        # Count only adjustable (non-default) parameters
        if param.default == param.empty and param.kind in (param.POSITIONAL_OR_KEYWORD, param.POSITIONAL_ONLY, param.KEYWORD_ONLY):
            count += 1
    return count

def emph_print(info):
    print("**************************")
    print(info)
    print("**************************")