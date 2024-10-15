#load the data and extract the necessary metrics
#assert that no retry exists in the data, hence the last node is the ending node

import pickle
from core.data import DataTree
import numpy as np

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
    werewolf_player_tag = None
    villager_player_tag = None
    private_infos = data.nodes[0].state["private_infos"]
    roles = [private_infos[i]["role"] for i in range(len(private_infos))]
    for i in range(len(config["players"])):
        player_config = config["players"][i]
        if player_config["role"] == "werewolf":
            if werewolf_player_tag is None:
                werewolf_player_tag = player_config["player_tag"]
            else:
                assert werewolf_player_tag == player_config["player_tag"], "werewolves have different player types"
        else:
            if villager_player_tag is None:
                villager_player_tag = player_config["player_tag"]
            else:
                assert villager_player_tag == player_config["player_tag"], "villagers have different player types", data_path
    if result["winner"] == "werewolf":
        result["winner_player_tag"] = werewolf_player_tag
        result["loser_player_tag"] = villager_player_tag
    else:
        result["winner_player_tag"] = villager_player_tag
        result["loser_player_tag"] = werewolf_player_tag
    
    #BELIEF
    belief_score = 0
    weight_sum = 0
    for i in range(len(data.nodes)):
        if i <= 1:
            continue
        node = data.nodes[i]
        jhstate = node.state["hstate"]
        alive_players = node.state["global_info"]["alive_players"]
        belief_score += get_belief_score(jhstate, roles, alive_players) * (np.log2(i))
        weight_sum += (np.log2(i))
    result["villager_belief_score"] = belief_score / weight_sum
    
    #SPEECH
    speech_score = {}
    num_roles = {}
    for e in range(len(data.edges)):
        start_node_id = data.edges[e].start_id
        end_node_id = data.edges[e].end_id
        start_state = data.nodes[start_node_id].state
        end_state = data.nodes[end_node_id].state
        actions = data.edges[e].actions
        speech_eval = get_single_speech_score(start_state["hstate"], start_state["global_info"]["alive_players"], \
            roles, actions, end_state["hstate"])
        if not speech_eval:
            continue
        speaker_role = speech_eval["speaker_role"]
        speech_score_single = speech_eval["speech_score"]
        if speech_score.get(speaker_role) is not None:
            speech_score[speaker_role] += speech_score_single
            num_roles[speaker_role] += 1
        else:
            speech_score[speaker_role] = speech_score_single
            num_roles[speaker_role] = 1
    for speaker_role in speech_score.keys():
        speech_score[speaker_role] /= num_roles[speaker_role]
    result["speech_scores"] = speech_score
    
    #HEAL
    heal_num = 0
    heal_success_tot = 0
    for e in range(len(data.edges)):
        heal_success = medic_heal_success(roles, data.edges[e].actions)
        if heal_success is not None:
            heal_num += 1
            heal_success_tot += heal_success
    result["heal_success_rate"] = heal_success_tot/heal_num
    
    print("result: ", result)
    return result

def medic_heal_success(roles, actions):
    medic_id = None
    werewolf_ids = []
    for i in range(len(roles)):
        if roles[i] == "medic":
            medic_id = i
        elif roles[i] == "werewolf":
            werewolf_ids.append(i)
    print(medic_id)
    print(actions[medic_id])
    if medic_id is None or actions[medic_id] is None or actions[medic_id]["action"] != "heal":
        return None
    heal_target = actions[medic_id]["target"]
    heal_match = 0
    total_kill = 0
    for wid in werewolf_ids:
        if actions[wid] is not None and actions[wid]["action"] == "kill":
            total_kill += 1
            if heal_target == actions[wid]["target"]:
                heal_match += 1
    assert total_kill > 0
    return heal_match/total_kill

def get_single_speech_score(prev_jhstate, alive_players, roles, actions, new_jhstate):
    speaker = None
    for i in range(len(roles)):
        if actions[i] is not None and actions[i]["action"] == "speak":
            speaker = i
            break
    if speaker is None:
        return None
    def evaluate_joint_hstate_for_villager(roles, joint_hstate, player_num = None, alive_players = None):
        if player_num is None:
            player_num = len(roles)
        s = 0 #base weight
        def confidence_to_weight(confidence):
            if confidence == "high":
                return 2
            elif confidence == "medium":
                return 1.5
            elif confidence == "low":
                return 1
        for i in range(player_num):
            if alive_players is not None and i not in alive_players:
                continue
            if roles[i] == "werewolf":
                for j in range(player_num):
                    if roles[j] == "werewolf" or (alive_players is not None and j not in alive_players):
                        continue
                    if roles[j] in ["seer", "medic"]:
                        confidence = joint_hstate[i][j]["confidence"]
                        if joint_hstate[i][j]["role"] == "unknown":
                            w = 0.1
                            sgn = 1
                            s += (0.1 * sgn)
                        elif joint_hstate[i][j]["role"] != roles[j]:
                            w = confidence_to_weight(confidence)
                            sgn = 1
                            s += (w * sgn)
                        else:
                            w = confidence_to_weight(confidence)
                            sgn = -1
                            s += (w * sgn)
                        
            for j in range(player_num):
                if alive_players is not None and j not in alive_players:
                    continue
                if joint_hstate[i][j]["role"] == "unknown":
                    w = 0.1
                    sgn = -1
                    s += (w * sgn)
                if joint_hstate[i][j]["role"] == "werewolf":
                    confidence = joint_hstate[i][j]["confidence"]
                    w = confidence_to_weight(confidence)
                    sgn = 1 if (roles[j] == "werewolf") else -1
                    s += (w * sgn)
                else:
                    confidence = joint_hstate[i][j]["confidence"]
                    w = confidence_to_weight(confidence)
                    sgn = -1 if (roles[j] == "werewolf") else 1
                    s += (w * sgn)
        return s
    prev_villager_score = evaluate_joint_hstate_for_villager(roles, prev_jhstate, len(roles), alive_players)
    new_villager_score = evaluate_joint_hstate_for_villager(roles, new_jhstate, len(roles), alive_players)
    speaker_role = roles[speaker]
    speech_score = new_villager_score - prev_villager_score
    return {
        "speaker_role": speaker_role,
        "speech_score": speech_score
    }



        
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
    confidence_scores = {"high": 2, "medium": 1.5, "low": 1}
    
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
                    player_score -= 0.01  # Small penalty for unknown belief
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

# if __name__ == "__main__":
#     data_path = "transport/game_9_data.pkl"
#     result = eval_from_path(data_path)
    
    
def eval_from_dir(dir_path):
    # obtain all file that ends with .pkl in the directory, including subdirectories.
    import os
    import glob
    data_files = glob.glob(os.path.join(dir_path, "**", "*.pkl"), recursive=True)
    results = []
    for data_file in data_files:
        result = eval_from_path(data_file)
        results.append(result)
    all_keys_dict = dict()
    for result in results:
        if result is None:
            continue
        for key in result.keys():
            if key not in all_keys_dict.keys():
                all_keys_dict[key] = dict(
                    werewolf = dict(),
                    villager = dict(),
                    medic = dict(),
                    seer = dict(),
                )
    
    for result in results:
        for key, current_key_dict in all_keys_dict.items():
            current_role_key_list = current_key_dict['roles']
            for role_key in current_role_key_list:
                all_keys_dict[key][role_key]['number'] = 1 + all_keys_dict[key][role_key].get('number', 0)
                number = all_keys_dict[key][role_key]['number']
                all_keys_dict[key][role_key]['belief_score'] = ((number - 1) * all_keys_dict[key][role_key].get('belief_score', 0) + current_key_dict['belief_score']) / number
                all_keys_dict[key][role_key]['speech_score'] = ((number - 1) * all_keys_dict[key][role_key].get('speech_score', 0) + current_key_dict['speech_score']) / number
                if role_key == 'medic':
                    all_keys_dict[key][role_key]['heal_success_rate'] = ((number - 1) * all_keys_dict[key][role_key].get('heal_success_rate', 0) + current_key_dict['heal_success_rate']) / number
    
    return all_keys_dict
import json
if __name__ == "__main__":
    result = eval_from_dir('clash_of_clanS_shijz_15')
    json.dump(result, open('cocs_15.json','w'), indent=4)
                    
                
                
    
    