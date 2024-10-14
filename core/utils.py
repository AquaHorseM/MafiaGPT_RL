from core.players.reflex.player import Player
from core.event import EventBook
from core.players.reflex.werewolf import WerewolfPlayer
from core.players.reflex.medic import MedicPlayer
from core.players.reflex.seer import SeerPlayer
from core.players.reflex.villager import VillagerPlayer
import pickle, os
import inspect

import importlib

def get_player_class(player_type, player_role):
    # Construct the full module path as a string based on player_type and player_role
    module_path = f"core.players.{player_type}.{player_role}"
    
    # Class names are typically capitalized; handle that here
    class_name = f"{player_role.capitalize()}Player"
    
    # Dynamically import the module
    module = importlib.import_module(module_path)
    
    # Get the class from the module
    PlayerClass = getattr(module, class_name)
    
    return PlayerClass

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