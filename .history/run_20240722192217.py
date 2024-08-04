from core import game
import json

config_path = "configs/player_configs_v01.json"
with open(config_path, "r") as f:
    player_configs = json.load(f)

new = game.Game()
new.set_players(player_configs)
new.run_game()
