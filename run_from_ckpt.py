#run the game with multiple processes
import multiprocessing
from core.api import load_client
from argparse import ArgumentParser
from functools import partial
from core.game_env import WerewolfGameEnv as Game
import json, sys, os
    
parser = ArgumentParser()
parser.add_argument("--openai_config_path", type=str, default="openai_config.yaml")
parser.add_argument("--config_path", type=str, default="configs/game_config_v01.json")
parser.add_argument("--start_idx", type=int, default=0)
parser.add_argument("--ckpt_path", type=str, default=None)
parser.add_argument("--data-path", type=str, default="data/game_1_data.pkl")

def load_ckpt(ipt, client, path):
    idx, player_configs = ipt
    game = Game(999, True, client, path)
    game.set_players(player_configs)
    game.load_data(path)
    game.sim_game_for_reflex_players()
    
if __name__ == "__main__":
    args = parser.parse_args()
    # client = load_client(args.openai_config_path)
    client = args.openai_config_path
    run_game = partial(load_ckpt, client=client, path = args.data_path)
    with open(args.config_path, "r") as f:
        player_configs = json.load(f)["players"]
    run_game((args.start_idx, player_configs))