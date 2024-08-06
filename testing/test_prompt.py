from core.players.villager import VillagerPlayer

player_num = 7

init_global_info = {
    "player_num": player_num,
    "alive_players": range(player_num),
    "dead_players": [],
    "current_round": 0, #0 indicates the game hasn't started
    "roles_mapping": {
        "villager": 0,
        "werewolf": 1,
        "medic": 2,
        "seer": 3
    },
    "previous_votes": []
}

init_villager_private_info = {
    "role": "villager",
}

villagerpromptpath = "core/players/prompts/villager"

villager = VillagerPlayer(0, init_global_info, init_villager_private_info, villagerpromptpath)
print(villager.show_prompt("vote.txt"))