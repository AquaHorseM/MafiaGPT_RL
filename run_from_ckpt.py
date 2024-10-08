#run the game with multiple processes
import multiprocessing
from core.api import load_client
from argparse import ArgumentParser
from functools import partial
from core.game_env import WerewolfGameEnv as Game
import json, sys, os
    
parser = ArgumentParser()
parser.add_argument("--config_path", type=str, default="configs/game_config_v01.json")
parser.add_argument("--start_idx", type=int, default=0)
parser.add_argument("--data-path", type=str, default="data/game_2_data.pkl")

def load_ckpt(config, path):
    game = Game(999, config)
    game.load_data(path)
    game.sim_game_for_reflex_players()
    
if __name__ == "__main__":
    args = parser.parse_args()
    with open(args.config_path, "r") as f:
        game_config = json.load(f)
    load_ckpt()