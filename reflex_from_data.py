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
parser.add_argument("--data-path", type=str, default="transport") #could be a file path or a dir path
parser.add_argument("--num_processes", type=int, default=4)
parser.add_argument("--skip-error", default=False, action="store_true")

def reflex_from_file_path(game_config, path, num_processes, skip_error = False):
    game = Game(999, game_config)
    game.load_data(path)
    if not skip_error:
        game.reflex_multi_process(num_processes)
        return True
    else:
        try:
            game.reflex_multi_process(num_processes)
            return True
        except Exception as e:
            print(f"WARNING! Error encountered reflexing for {path}!")
            print(f"Error message: {e}")
            print("Skipping it.")
            return False
        
def reflex_from_path(game_config, path, num_processes, skip_error=False):
    if not os.path.isdir(path):
        reflex_from_file_path(game_config, path, num_processes)
    else:
        print(f"The data path {path} is folder. Recursively reflexing from all data files inside.")
        success_num = 0
        tot_num = 0
        for filename in os.listdir(path):
            if not filename.endswith(".pkl"):
                print(f"{filename} is not a valid data file. Skipped.")
                continue
            tot_num += 1
            filepath = os.path.join(path, filename)
            if reflex_from_file_path(game_config, filepath, num_processes, skip_error):
                success_num += 1
            print(f"Finished reflexing from {filepath}.")
        print(f"Finished reflexing from all data in {path}!")
        print(f"Altogether {tot_num} files. {success_num} successes. {tot_num - success_num} failures.")
       
    
if __name__ == "__main__":
    args = parser.parse_args()
    # client = load_client(args.openai_config_path)
    client = args.openai_config_path
    with open(args.config_path, "r") as f:
        game_config = json.load(f)
    reflex_from_path(game_config, args.data_path, args.num_processes, args.skip_error)