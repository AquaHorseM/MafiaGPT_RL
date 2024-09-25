from core.players.player import Player
from core.event import EventBook
from core.players.werewolf import WerewolfPlayer
from core.players.medic import MedicPlayer
from core.players.seer import SeerPlayer
from core.players.villager import VillagerPlayer
from core.baseline_players import Werewolf, Medic, Seer, Villager
import pickle
def load_player_from_checkpoint(path, game, player_id):
    with open(path, 'rb') as file:
        info = pickle.load(file)
    return load_player_from_info(info, game, player_id)

def load_player_from_info(info, global_info, player_id):
    role = info["private_info"]["role"]
    switcher = {
        "werewolf": WerewolfPlayer,
        "medic": MedicPlayer,
        "seer": SeerPlayer,
        "villager": VillagerPlayer
    }
    p = switcher[role](player_id, global_info, info["private_info"], info["prompt_dir_path"])
    p.tick = info["tick"]
    return p

switcher_players = {
    "reflex": {
        "werewolf": WerewolfPlayer,
        "medic": MedicPlayer,
        "seer": SeerPlayer,
        "villager": VillagerPlayer
    },
    "baseline": {
        "werewolf": Werewolf,
        "medic": Medic,
        "seer": Seer,
        "villager": Villager   
    }
}