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
    roles = []
    for i in range(len(config["players"])):
        player_config = config["players"][i]
        roles.append(player_config["role"])
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

        
    
    
def get_belief_score(joint_hstate, roles, alive_players=None):
    # Initialize variables
    total_score = 0
    good_players_count = 0
    
    # Define teams
    good_roles = ["villager", "seer", "medic"]
    
    # Helper function to determine if two roles are on the same team
    def same_team(role1, role2):
        if role1 == "werewolf" and role2 == "werewolf":
            return True
        if role1 in good_roles and role2 in good_roles:
            return True
        return False
    
    # Assign score values based on confidence
    confidence_scores = {"high": 1.5, "medium": 1, "low": 0.5}
    
    # Iterate over each player
    for i, player_role in enumerate(roles):
        if player_role in good_roles and i in alive_players:
            # This player is on the good team and is alive
            good_players_count += 1
            player_score = 0
            
            # Iterate over the beliefs of this player about other players
            for j, belief in enumerate(joint_hstate[i]):
                if j == i or j not in alive_players:
                    continue  # Skip if it's the player's own belief or the target player is dead

                # Extract belief information
                belief_role = belief["role"]
                belief_confidence = belief["confidence"]

                # If role is 'unknown', apply a small penalty
                if belief_role == "unknown":
                    player_score -= 0.1  # Small penalty for unknown belief
                    continue

                # Determine if the belief was correct about the team
                if same_team(belief_role, roles[j]):
                    # Correct team guess, add score based on confidence
                    player_score += confidence_scores[belief_confidence]

                    # Bonus for guessing the exact role
                    if belief_role == roles[j]:
                        if belief_role == "villager":
                            player_score += 0.5  # Small bonus for guessing a villager
                        elif belief_role in ["seer", "medic"]:
                            player_score += 1  # Higher bonus for guessing seer or medic correctly
                else:
                    # Incorrect team guess, apply a negative score based on confidence
                    player_score -= confidence_scores[belief_confidence]

            # Add this player's score to the total score
            total_score += player_score
    
    # Return the average score for all good players
    return total_score / good_players_count if good_players_count > 0 else 0
