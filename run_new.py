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
parser.add_argument("--openai_config_path", type=str, default="openai_config.yaml")
parser.add_argument("--config_path", type=str, default="configs/player_configs_v01.json")
parser.add_argument("--start_idx", type=int, default=0)
parser.add_argument("--ckpt_path", type=str, default=None)
parser.add_argument("--reflex-only",default=False, action="store_true")
parser.add_argument("--data-path", type=str, default=None)
parser.add_argument("--train",default=False, action="store_true")
parser.add_argument("--log_hstate",default=False, action="store_true")


def run_game_with_client(ipt, client):
    idx, player_configs, train, log_hstate = ipt
    new = Game(idx, train = train, log_hstate=log_hstate, openai_client=client)
    new.set_players(player_configs)
    # new.init_env()
    new.sim_game_for_reflex_players()
    
if __name__ == "__main__":
    args = parser.parse_args()
    # client = load_client(args.openai_config_path)
    client = args.openai_config_path
    
    run_game = partial(run_game_with_client, client=client)
    with open(args.config_path, "r") as f:
        player_configs = json.load(f)["players"]
    if args.num_processes == 1:
        for i in range(args.num_games):
            run_game((args.start_idx, player_configs, args.train, args.log_hstate))
    else:
        ipt = [(args.start_idx + i, player_configs, args.train, args.log_hstate) for i in range(args.num_games)]
        if __name__ == "__main__":
            with multiprocessing.Pool(args.num_processes) as pool:
                pool.map(run_game, ipt)