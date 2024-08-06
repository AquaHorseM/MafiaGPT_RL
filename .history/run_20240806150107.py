from core import game
import json
#run the game with multiple processes
import multiprocessing

config_path = "configs/player_configs_v01.json"
with open(config_path, "r") as f:
    player_configs = json.load(f)["players"]
    
with multiprocessing.Pool(len(player_configs)) as pool:
    pool.map(game.run_game, player_configs)

# new = game.Game()
# new.set_players(player_configs)
# new.run_game()
