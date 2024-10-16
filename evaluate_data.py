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
            last_node = node
            break
    if last_node is None:
        print("Warning! This data does not have an ending node.")
        return None
    
    config = data.game_config
    private_infos = data.nodes[0].state["private_infos"]
    player_num = len(private_infos)
    
    # Initialize roles to handle multiple roles for the same player tag
    tag_roles = {}
    player_roles = []
    for i in range(len(private_infos)):
        player_roles.append(private_infos[i]["role"])
        for k in range(len(config["players"])):
            if config["players"][k]["role"] == private_infos[i]["role"]: # temp solution
                player_tag = config["players"][k].get("player_tag", "NoTag")
        if tag_roles.get(player_tag) is None:
            tag_roles[player_tag] = [private_infos[i]["role"]]
        else:
            if private_infos[i]["role"] not in tag_roles[player_tag]:
                tag_roles[player_tag].append(private_infos[i]["role"])
    
    # Initialize result structure
    player_tags = [config["players"][i]["player_tag"] for i in range(len(config["players"]))]
    result = {tag: {"roles": tag_roles[tag], "winner": None, "belief_score": None, "speech_score": None, "heal_success_rate": None} for tag in player_tags}

    # Determine winner and loser player tags
    if last_state["global_info"]["game_status"]["winner"] == "werewolf":
        for tag in player_tags:
            result[tag]["winner"] = "win" if "werewolf" in tag_roles[tag] else "lose"
    else:
        for tag in player_tags:
            result[tag]["winner"] = "win" if "werewolf" not in tag_roles[tag] else "lose"
    
    # BELIEF
    belief_scores = {tag: 0 for tag in player_tags}
    belief_weights = {tag: 0 for tag in player_tags}  # Track valid belief score counts
    for i in range(len(data.nodes)):
        if i <= 1:
            continue
        node = data.nodes[i]
        jhstate = node.state["hstate"]
        alive_players = node.state["global_info"]["alive_players"]
        belief_eval = get_belief_score(jhstate, player_roles, alive_players)  # belief_eval should return scores per player
        print("belief_eval: ", belief_eval)
        for j, tag in enumerate(player_tags):
            if belief_eval[j] is not None:  # Skip if belief score is None
                belief_scores[tag] += belief_eval[j] * (np.log2(i))
                belief_weights[tag] += np.log2(i)
    
    for tag in player_tags:
        if belief_weights[tag] > 0:
            result[tag]["belief_score"] = belief_scores[tag] / belief_weights[tag]
        else:
            result[tag]["belief_score"] = None  # No valid belief scores for this player


    count = 0
    sum_ = 0
    square_sum_ = 0
    for tag in player_tags:
        result[tag]["before_normalized_belief_score"] = result[tag]["belief_score"]
        count += 1 if result[tag]["belief_score"] is not None else 0
        sum_ += result[tag]["belief_score"] if result[tag]["belief_score"] is not None else 0
        square_sum_ += result[tag]["belief_score"] ** 2 if result[tag]["belief_score"] is not None else 0
    square_avg_ = square_sum_ / count
    avg_ = sum_ / count
    var = square_avg_ - avg_**2
    std = np.sqrt(var)
    for tag in player_tags:
        result[tag]["belief_score"] = (result[tag]["belief_score"]-avg_) / (std+1e-8)if result[tag]["belief_score"] is not None else None
    

    # SPEECH
    speech_scores = {tag: 0 for tag in player_tags}
    long_speech_scores = {tag: 0 for tag in player_tags}
    num_speeches = {tag: 0 for tag in player_tags}
    nodes = data.nodes
    
    for e in range(len(data.edges)):
        start_node_id = data.edges[e].start_id
        end_node_id = data.edges[e].end_id
        start_state = data.nodes[start_node_id].state
        end_state = data.nodes[end_node_id].state

        next_nodes = list()
        alive_players = list()
        valid = True
        current_prev_node_id = start_node_id
        while valid:
            next_node_id = data.edges[data.nodes[current_prev_node_id].edges[0]].end_id
            next_nodes.append(data.nodes[next_node_id])
            alive_players.append(data.nodes[next_node_id].state["global_info"]["alive_players"])
            current_prev_node_id = next_node_id
            if len(data.nodes[current_prev_node_id].edges) == 0:
                valid = False
        
        new_hstate_list = [node.state["hstate"] for node in next_nodes]


        actions = data.edges[e].actions
        speech_eval = get_single_speech_score(start_state["hstate"], start_state["global_info"]["alive_players"], \
            player_roles, actions, player_tags, new_hstate_list, alive_players)
        if not speech_eval:
            continue
        speaker_tag = speech_eval["speaker_tag"]  # Assuming this returns the correct player tag
        speech_score_single = speech_eval["speech_score"]
        speech_scores[speaker_tag] += speech_score_single
        long_speech_scores[speaker_tag] += speech_eval["long_speech_score"]
        num_speeches[speaker_tag] += 1
    
    for tag in player_tags:
        if num_speeches[tag] > 0:
            result[tag]["speech_score"] = speech_scores[tag] / num_speeches[tag]
            result[tag]["long_speech_score"] = long_speech_scores[tag] / num_speeches[tag]
    
    # HEAL (applies only to medic role)
    heal_num = 0
    heal_success_tot = 0
    for e in range(len(data.edges)):
        heal_success = medic_heal_success(player_roles, data.edges[e].actions)
        if heal_success is not None:
            heal_num += 1
            heal_success_tot += heal_success
    
    for tag in player_tags:
        if "medic" in tag_roles[tag]:
            result[tag]["heal_success_rate"] = heal_success_tot / heal_num if heal_num > 0 else 0
            
    # KILL SEER/MEDIC
    kill_num = 0
    kill_critical = 0
    
    f = 0
    second_night_node = None
    for n in data.nodes:
        if n.state["global_info"]["game_status"]["cur_stage"] == "night":
            if f==0:
                f=1
            else:
                second_night_node = n
                break
    if second_night_node is not None:
        alive_players = second_night_node.state["global_info"]["game_status"]["alive_players"]
        medic_id = [i for i in range(player_num) if player_roles[i]=="medic" and i in alive_players]
        seer_id = [i for i in range(player_num) if player_roles[i]=="seer" and i in alive_players]
        if medic_id or seer_id:
            medic_id = medic_id[0] if medic_id else None
            seer_id = seer_id[0] if seer_id else None
            werewolf_ids = [i for i in range(player_num) if player_roles[i] == "werewolf" and i in alive_players]
            if werewolf_ids:
                actions = data.edges[second_night_node.edges[0]].actions
                save_target = None
                if medic_id:
                    save_target = actions[medic_id].get("target")
                for wid in werewolf_ids:
                    target = actions[wid].get("target") 
                    if target is not None:
                        kill_num += 1
                        if ((seer_id and target == seer_id) or (medic_id and target == medic_id)) and (save_target and save_target != target):
                            kill_critical += 1
    
    for tag in player_tags:
        if "werewolf" in tag_roles[tag]:
            result[tag]["kill_critical_rate"] = heal_success_tot / heal_num if heal_num > 0 else 0
            break
    
    # print("result: ", result)
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

def get_single_speech_score(prev_jhstate, alive_players, roles, actions, player_tags, new_jhstate_list, new_alive_player_list, gamma=0.9):
    speaker = None
    for i in range(len(roles)):
        if actions[i] is not None and actions[i]["action"] == "speak":
            speaker = i
            break
    if speaker is None:
        return None
    
    prev_villager_score = evaluate_joint_hstate_for_villager(roles, prev_jhstate, len(roles), alive_players)


    sum_weight = 0.0
    sum_weighted_score = 0.0
    for idx,new_jhstate in enumerate(new_jhstate_list):
        new_villager_score = evaluate_joint_hstate_for_villager(roles, new_jhstate, len(roles), new_alive_player_list[idx])
        sum_weighted_score += new_villager_score * gamma ** (idx)
        sum_weight += gamma ** idx
    
    weighted_score = sum_weighted_score / sum_weight

    next_villager_score = evaluate_joint_hstate_for_villager(roles, new_jhstate_list[0], len(roles), new_alive_player_list[0])


    speaker_role = roles[speaker]
    speaker_tag = player_tags[speaker]
    speech_score = next_villager_score - prev_villager_score
    long_speech_score = weighted_score - prev_villager_score
    return {
        "speaker_role": speaker_role,
        "speaker_tag": speaker_tag,
        "speech_score": speech_score if speaker_role != 'werewolf' else - speech_score,
        "long_speech_score": long_speech_score if speaker_role != 'werewolf' else - long_speech_score,
    }

        
def get_belief_score(joint_hstate, roles, alive_players=None):
    # Initialize variables
    total_score = 0
    good_players_count = 0
    
    # Define teams
    good_roles = ["villager", "seer", "medic"]
    scores = [None] * len(roles)
    
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
        if not (player_role in good_roles and i in alive_players):
            continue
        # This player is on the good team and is alive
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
        scores[i] = player_score

        # Add this player's score to the total score
    return scores

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
        for key, current_key_dict in result.items():
            current_role_key_list = current_key_dict['roles']
            for role_key in current_role_key_list:
                if current_key_dict['belief_score'] is not None:
                    all_keys_dict[key][role_key]['number'] = 1 + all_keys_dict[key][role_key].get('number', 0)
                    number = all_keys_dict[key][role_key]['number']
                    all_keys_dict[key][role_key]['belief_score'] = ((number - 1) * all_keys_dict[key][role_key].get('belief_score', 0) + current_key_dict['belief_score']) / number
                    all_keys_dict[key][role_key]['speech_score'] = ((number - 1) * all_keys_dict[key][role_key].get('speech_score', 0) + current_key_dict['speech_score']) / number
                    all_keys_dict[key][role_key]['long_speech_score'] = ((number - 1) * all_keys_dict[key][role_key].get('long_speech_score', 0) + current_key_dict['long_speech_score']) / number
                    if role_key == 'medic':
                        all_keys_dict[key][role_key]['heal_success_rate'] = ((number - 1) * all_keys_dict[key][role_key].get('heal_success_rate', 0) + current_key_dict['heal_success_rate']) / number
                    if role_key == 'werewolf' and current_key_dict.get('kill_critical_rate') is not None:
                        all_keys_dict[key][role_key]['kill_critical_rate'] = ((number - 1) * all_keys_dict[key][role_key].get('kill_critical_rate', 0) + current_key_dict['kill_critical_rate']) / number
                    all_keys_dict[key][role_key]['wins'] = 1 + all_keys_dict[key][role_key].get('wins', 0) if current_key_dict['winner'] == 'win' else all_keys_dict[key][role_key].get('wins', 0)
    all_keys_dict['total_number_of_games'] = len(results)
    return all_keys_dict
import json
from argparse import ArgumentParser
if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('--dir', type=str, default = 'clan_war_shijz_15_v2Vv5')
    parser.add_argument('--file', type=str, default = 'clan_war_shijz_15_v2Vv5')
    args = parser.parse_args()
    result = eval_from_dir(args.dir)
    json.dump(result, open(args.file,'w'), indent=4)
                    
                
                
    
    
