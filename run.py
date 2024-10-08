from functools import partial
from core.game_backup import Game
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
parser.add_argument("--skip-error",default=False, action="store_true")

def run_game_with_client(ipt, client, skip_error=False):
    idx, player_configs, train = ipt
    new = Game(idx, train = train, openai_client=client)
    new.set_players(player_configs)
    if skip_error:
        try:
            new.run_game()
        except Exception as e:
            print(f"Error: Game {idx} failed with error: {e}")
    else:
        new.run_game()
    
if __name__ == "__main__":
    args = parser.parse_args()
    # client = load_client(args.openai_config_path)
    client = args.openai_config_path
    
    if args.reflex_only:
        assert args.data_path is not None, "Data path must be provided when running reflex only mode"
        player_configs = json.load(open(args.config_path, "r"))["players"]
        game = Game(999, train = True, openai_client=client)
        game.set_players(player_configs)
        if os.path.isdir(args.data_path):
            data_paths = [os.path.join(args.data_path, x) for x in os.listdir(args.data_path) if x.endswith(".pkl")]
            for data_path in data_paths:
                game.all_players_reflex_from_data_path(data_path)
        elif os.path.isfile(args.data_path):
            game.all_players_reflex_from_data_path(args.data_path)
        else:
            raise ValueError("Data path must be a file or a directory")
        sys.exit(0)
        
    
    if args.ckpt_path is not None:
        game = Game(args.start_idx, args.train, openai_client=client, skip_error=args.skip_error)
        game.load_checkpoint_from_path(args.ckpt_path)
        game.run_game()
    else:
        run_game = partial(run_game_with_client, client=client, skip_error=args.skip_error)
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