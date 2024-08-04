from core import game
import json

config_path = "configs/player_configs_v01.json"
player_configs = json.load(config_path)

new = game.Game()
new.set_players(player_configs)
new.run_game()
