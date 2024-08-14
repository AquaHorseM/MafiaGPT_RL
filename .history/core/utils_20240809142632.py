from core.players.player import Player
from core.event import EventBook
from core.players.werewolf import WerewolfPlayer
from core.players.medic import MedicPlayer
from core.players.seer import SeerPlayer
from core.players.villager import VillagerPlayer
from core.game import Game
import pickle
def load_player_from_checkpoint(path, game: Game):
    with open(path, 'rb') as file:
        info = pickle.load(file)
    role = info["private_info"]["role"]
    switcher = {
        "werewolf": WerewolfPlayer,
        "medic": MedicPlayer,
        "seer": SeerPlayer,
        "villager": VillagerPlayer
    }
    p = switcher[role](info["id"], game.get_global_info(), info["private_info"], info["prompt_dir_path"])
    p.hidden_state.beliefs = info["beliefs"]
    p.tick = info["tick"]
    return p