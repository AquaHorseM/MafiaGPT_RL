from functools import partial
from core.game_env import WerewolfGameEnv as Game
import json, sys, os
#run the game with multiple processes
import multiprocessing
from core.api import load_client
from argparse import ArgumentParser
    
parser = ArgumentParser()
parser.add_argument("--num_processes", type=int, default=1)
parser.add_argument("--openai_config_path", type=str, default="openai_config.yaml")
parser.add_argument("--config_path", type=str, default="configs/player_configs_v01.json")
parser.add_argument("--start_idx", type=int, default=0)
parser.add_argument("--ckpt_path", type=str, default=None)
parser.add_argument("--reflex-only",default=False, action="store_true")
parser.add_argument("--data-path", type=str, default="data/game_1_data.pkl")
parser.add_argument("--train",default=False, action="store_true")

def reflex_from_path(ipt, client, path):
    idx, player_configs, train = ipt
    game = Game(999, train, client, path)
    game.set_players(player_configs)
    game.load_data(path)
    game.all_players_reflex()
    
if __name__ == "__main__":
    args = parser.parse_args()
    # client = load_client(args.openai_config_path)
    client = args.openai_config_path
    run_game = partial(reflex_from_path, client=client, path = args.data_path)
    with open(args.config_path, "r") as f:
        player_configs = json.load(f)["players"]
    if args.num_processes == 1:
        for i in range(args.num_games):
            run_game((args.start_idx, player_configs, args.train))
    else:
        ipt = [(args.start_idx + i, player_configs, args.train) for i in range(args.num_games)]
        if __name__ == "__main__":
            with multiprocessing.Pool(args.num_processes) as pool:
                pool.map(run_game, ipt)