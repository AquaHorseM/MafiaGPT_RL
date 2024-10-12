#load the data and extract the necessary metrics
#assert that no retry exists in the data, hence the last node is the ending node

import pickle
from core.data import DataTree

data_path = "data.pkl"
def eval_from_path(data_path: str):
    result = {}
    with open(data_path, "rb") as f:
        data: DataTree = pickle.load(f)
    last_node = None
    last_state = None
    for node in reversed(data.nodes):
        last_state = node.state
        winner = last_state["global_info"]["game_status"]["winner"]
        if winner is None:
            continue
        else:
            result["winner"] = winner
            last_node = node
            break
    if last_node is None:
        print("Warning! This data does not have an ending node.")
        return None
    config = data.game_config
    werewolf_player_type = None
    villager_player_type = None
    for i in range(len(config["players"])):
        player_config = config["players"][i]
        if player_config["role"] == "werewolf":
            if werewolf_player_type is None:
                werewolf_player_type = player_config["player_type"]
            else:
                assert werewolf_player_type == player_config["player_type"], "werewolves have different player types"
        else:
            if villager_player_type is None:
                villager_player_type = player_config["player_type"]
            else:
                assert villager_player_type == player_config["player_type"], "villagers have different player types"
    if result["winner"] == "werewolf":
        result["winner_player_type"] = werewolf_player_type
        result["loser_player_type"] = villager_player_type
    else:
        result["winner_player_type"] = villager_player_type
        result["loser_player_type"] = werewolf_player_type
        
    
    
    def evaluate_joint_hstate(joint_hstate, player_configs, alive_players = None):
        #TODO make it more complete for other roles
        s = 0 #base weight
        def confidence_to_weight(confidence):
            if confidence == "high":
                return 3
            elif confidence == "medium":
                return 2
            elif confidence == "low":
                return 1
        if alive_players is not None:
            for i in range(len(player_configs)):
                if i in alive_players:
                    continue
                if joint_hstate[i][i]["role"] == "werewolf":
                    w = 3
                    sgn = 1 if (self.get_role() != "werewolf") else -1
                elif joint_hstate[i][i]["role"] == "villager":
                    w = 2
                    sgn = 1 if (self.get_role() == "werewolf") else -1
                elif joint_hstate[i][i]["role"] in ["medic", "seer"]:
                    w = 4
                    sgn = 1 if (self.get_role() == "werewolf") else -1
                else:
                    continue
                s += (w*sgn)
        for i in range(self.player_num):
            if alive_players is not None and i not in alive_players:
                continue
            if joint_hstate[i][i]["role"] == "werewolf":
                continue
            for j in range(self.player_num):
                if alive_players is not None and j not in alive_players:
                    continue
                if joint_hstate[i][j]["role"] == "werewolf":
                    confidence = joint_hstate[i][j]["confidence"]
                    w = confidence_to_weight(confidence)
                    sgn = 1 if (joint_hstate[j][j]["role"] == "werewolf") != (self.get_role() == "werewolf") else -1
                    s += (w * sgn)
                else:
                    confidence = joint_hstate[i][j]["confidence"]
                    w = confidence_to_weight(confidence)
                    sgn = 1 if (joint_hstate[j][j]["role"] == "werewolf") == (self.get_role() == "werewolf") else -1
                    s += (w * sgn)
        return s