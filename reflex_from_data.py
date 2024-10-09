from functools import partial
from core.game_env import WerewolfGameEnv as Game
import json, sys, os
#run the game with multiple processes
import multiprocessing
from core.api import load_client
from argparse import ArgumentParser
    
parser = ArgumentParser()
parser.add_argument("--openai_config_path", type=str, default="openai_config.yaml")
parser.add_argument("--config_path", type=str, default="configs/game_config_v01.json")
parser.add_argument("--ckpt_path", type=str, default=None)
parser.add_argument("--data-path", type=str, default="data/game_1_data.pkl")
parser.add_argument("--num_processes", type=int, default=4)

def reflex_from_path(game_config, path, num_processes):
    game = Game(999, game_config)
    game.load_data(path)
    game.reflex_multi_process(num_processes)
    
if __name__ == "__main__":
    args = parser.parse_args()
    # client = load_client(args.openai_config_path)
    client = args.openai_config_path
    with open(args.config_path, "r") as f:
        game_config = json.load(f)
    reflex_from_path(game_config, args.data_path, args.num_processes)