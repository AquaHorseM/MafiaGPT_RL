from core.game import Game
import json
#run the game with multiple processes
import multiprocessing
from argparse import ArgumentParser
    
parser = ArgumentParser()
parser.add_argument("--num_games", type=int, default=1)
parser.add_argument("--num_processes", type=int, default=1)
parser.add_argument("--config_path", type=str, default="configs/player_configs_v01.json")
parser.add_argument("--start_idx", type=int, default=0)
parser.add_argument("--ckpt_path", type=str, default=None)
parser.add_argument("--reflex",default=False, action="store_true")
parser.add_argument("--train",default=False, action="store_true")

def run_game(ipt):
    idx, reflex, player_configs, train = ipt
    new = Game(idx, reflex=reflex)
    new.set_players(player_configs)
    new.run_game(train=)
    
if __name__ == "__main__":
    args = parser.parse_args()
    if args.ckpt_path is not None:
        game = Game(args.start_idx, args.reflex)
        game.load_checkpoint(args.ckpt_path)
        game.run_game()
        
    with open(args.config_path, "r") as f:
        player_configs = json.load(f)["players"]
    if args.num_processes == 1:
        run_game((args.start_idx, args.reflex, player_configs))
    else:
        ipt = [(args.start_idx + i, args.reflex, player_configs) for i in range(args.num_games)]
        if __name__ == "__main__":
            with multiprocessing.Pool(args.num_processes) as pool:
                pool.map(run_game, ipt)