from core import game
import json
#run the game with multiple processes
import multiprocessing
from argparse import ArgumentParser

config_path = "configs/player_configs_v01.json"
with open(config_path, "r") as f:
    player_configs = json.load(f)["players"]
    
parser = ArgumentParser()
parser.add_argument("--num_games", type=int, default=1)
parser.add_argument("--num_processes", type=int, default=1)

    
    

    
num_games = 12
num_processes = 4

def run_game(ipt):
    idx, player_configs = ipt
    new = game.Game(idx)
    new.set_players(player_configs)
    new.run_game()
    
ipt = [(i, player_configs) for i in range(num_games)]

if __name__ == "__main__":
    with multiprocessing.Pool(num_processes) as pool:
        pool.map(run_game, ipt)