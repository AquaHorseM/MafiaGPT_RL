from functools import partial
from core.game_env import WerewolfGameEnv as Game
import json, sys, os
#run the game with multiple processes
import multiprocessing
from core.api import load_client
from argparse import ArgumentParser
    
parser = ArgumentParser()
parser.add_argument("--num_games", type=int, default=1)
parser.add_argument("--num_processes", type=int, default=1)
parser.add_argument("--config_path", type=str, default="configs/game_config_v01.json")
parser.add_argument("--start_idx", type=int, default=0)
parser.add_argument("--reflex-only",default=False, action="store_true")


def run_game_with_config(id, config):
    new = Game(id, game_config=config)
    new.sim_game_for_reflex_players()
    
if __name__ == "__main__":
    args = parser.parse_args()
    with open(args.config_path, "r") as f:
        game_config = json.load(f)
    run_game = partial(run_game_with_config, config=game_config)
    if args.num_processes == 1:
        for i in range(args.num_games):
            run_game(args.start_idx + i)
    else:
        ipt = [args.start_idx + i for i in range(args.num_games)]
        if __name__ == "__main__":
            with multiprocessing.Pool(args.num_processes) as pool:
                pool.map(run_game, ipt)