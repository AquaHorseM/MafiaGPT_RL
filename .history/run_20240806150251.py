from core import game
import json
#run the game with multiple processes
import multiprocessing

config_path = "configs/player_configs_v01.json"
with open(config_path, "r") as f:
    player_configs = json.load(f)["players"]
    
num_games = 100
num_processes = 4

def run_game(idx, player_configs):
    new = game.Game(idx)
    new.set_players(player_configs)
    new.run_game()
    
with multiprocessing.Pool(num_processes) as pool:
    pool.map(game.run_game, [player_configs]*num_games)
