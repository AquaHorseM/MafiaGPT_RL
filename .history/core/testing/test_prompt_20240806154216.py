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
                
        init_werewolf_private_info = {
            "role": "werewolf",
            "werewolf_ids": werewolf_ids,
            "kill_history": [],
            "previous_advices": []  
        }
        
        init_villager_private_info = {
            "role": "villager",
        }