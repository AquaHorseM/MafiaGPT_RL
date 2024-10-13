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
    
    # SPEECH
    speech_scores = {tag: 0 for tag in player_tags}
    num_speeches = {tag: 0 for tag in player_tags}
    
    for e in range(len(data.edges)):
        start_node_id = data.edges[e].start_id
        end_node_id = data.edges[e].end_id
        start_state = data.nodes[start_node_id].state
        end_state = data.nodes[end_node_id].state
        actions = data.edges[e].actions
        speech_eval = get_single_speech_score(start_state["hstate"], start_state["global_info"]["alive_players"], \
            player_roles, actions, player_tags, end_state["hstate"])
        if not speech_eval:
            continue
        speaker_tag = speech_eval["speaker_tag"]  # Assuming this returns the correct player tag
        speech_score_single = speech_eval["speech_score"]
        speech_scores[speaker_tag] += speech_score_single
        num_speeches[speaker_tag] += 1
    
    for tag in player_tags:
        if num_speeches[tag] > 0:
            result[tag]["speech_score"] = speech_scores[tag] / num_speeches[tag]
    
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

def get_single_speech_score(prev_jhstate, alive_players, roles, actions, player_tags, new_jhstate):
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
    speaker_tag = player_tags[speaker]
    speech_score = new_villager_score - prev_villager_score
    return {
        "speaker_role": speaker_role,
        "speaker_tag": speaker_tag,
        "speech_score": speech_score
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




if __name__ == "__main__":
    data_path = "transport/v1vv9_game4.pkl"
    result = eval_from_path(data_path)