from functools import partial
from core.game import Game
import json
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
parser.add_argument("--data_path", type=str, default=None)
parser.add_argument("--train",default=False, action="store_true")

def run_game_with_client(ipt, client):
    idx, reflex, player_configs, train = ipt
    new = Game(idx, train = train, reflex=reflex, openai_client=client)
    new.set_players(player_configs)
    new.run_game()
    
if __name__ == "__main__":
    args = parser.parse_args()
    # client = load_client(args.openai_config_path)
    client = args.openai_config_path
    
    if args.reflex_only:
        assert args.data_path is not None, "Data path must be provided when running reflex only mode"
        player_configs = json.load(open(args.config_path, "r"))["players"]
        game = Game(args.start_idx, args.reflex, openai_client=client)
        game.set_players(player_configs)

        
    
    if args.ckpt_path is not None:
        game = Game(args.start_idx, args.reflex, openai_client=client)
        game.load_checkpoint(args.ckpt_path)
        game.run_game()
    else:
        run_game = partial(run_game_with_client, client=client)
        with open(args.config_path, "r") as f:
            player_configs = json.load(f)["players"]
        if args.num_processes == 1:
            for i in range(args.num_games):
                run_game((args.start_idx, args.reflex, player_configs, args.train))
        else:
            ipt = [(args.start_idx + i, args.reflex, player_configs, args.train) for i in range(args.num_games)]
            if __name__ == "__main__":
                with multiprocessing.Pool(args.num_processes) as pool:
                    pool.map(run_game, ipt)