import os
import re, pickle
import numpy as np

def events_include_player(event, player_id):
    #check if the event includes the player
    #find 'player: player_id' in the event
    #There could be multiple spaces between : and player_id
    match = re.search(r"player\s*:\s*" + str(player_id), event)
    if match is not None:
        return True
    else:
        return False

def get_prompt(prompt_path, replacements):
    if not prompt_path.endswith(".txt"):
        prompt_path = prompt_path + ".txt"
    with open(prompt_path, 'r') as file:
        content = file.read()
        #allow user to comment using ''', '''
        content = content.split("'''")
        content = [content[i] if i % 2 == 0 else "" for i in range(len(content))]
        content = "".join(content)

        for key, value in replacements.items():
            content = content.replace(key, value)
    return content

def get_target_from_response(response):
    #find the first number in the response
    try:
        target = int(re.search(r"\d+", response).group())
    except:
        target = None
    return target

def get_gt_hstate_from_joint(joint_hstate):
    if isinstance(joint_hstate, tuple) or isinstance(joint_hstate, list):
        print("Warning: joint_hstate is a tuple or list, try to convert it to np array")
        self_hstates = [joint_hstate[i][i] for i in range(len(joint_hstate))]
    else:
        self_hstates = [joint_hstate[i, i] for i in range(joint_hstate.shape[0])]
    return np.concatenate(self_hstates, axis=0)

def get_player_reflex_info_from_raw_data(prev_joint_hstate, merged_events, new_joint_hstate, player_id, alpha = 1):
    #xsm debug
    with open("debug.out", "a") as f:
        f.write(f"prev_joint_hstate: {prev_joint_hstate}\n \n")
        f.write(f"merged_events: {merged_events}\n \n")
        f.write(f"new_joint_hstate: {new_joint_hstate}\n \n")
    prev_hstate = prev_joint_hstate[player_id]
    prev_gt_hstate = get_gt_hstate_from_joint(prev_joint_hstate)
    new_hstate = new_joint_hstate[player_id]
    new_gt_hstate = get_gt_hstate_from_joint(new_joint_hstate)
    #! Temp
    #Use alpha to blend the gt with the new hidden state, so that the model won't directly access the entire gt
    targ_hstate = alpha * new_gt_hstate + (1-alpha) * new_hstate
    return (prev_hstate, prev_gt_hstate, merged_events, new_hstate, targ_hstate)

def parse_data(data, player_id, alpha = 1, check_event_include_player = False):
    #data should be a list in the form of [hidden_state, tuple_of_events * n, hidden_state, tuple_of_events * n, ...]
    #return a list of tuples in the form of [(hidden_state, tuple_of_events (merged), new_hidden_state), ...]
    #hidden state should be np tensor
    res = []
    prev_hstate_index = 0
    events = []
    for i in range(1, len(data)):
        if isinstance(data[i], tuple):
            events.append(data[i])
        else:
            merged_events = sum(events, ())
            if check_event_include_player and not any(events_include_player(event, player_id) for event in merged_events):
                #skip this data
                prev_hstate_index = i
                continue
            res.append(get_player_reflex_info_from_raw_data(data[prev_hstate_index], merged_events, data[i], player_id, alpha))
            prev_hstate_index = i
    return res

    
    
    
def parse_reflex_actions(reflex_actions):
    #parse all lines in the reflex note. Each line should be in the format of "OPERATION [VALUE]"
    #return a list of tuples in the form of [(OPERATION, VALUE), ...]
    res = []
    for line in reflex_actions.split("\n"):
        try:
            line = line.strip()
            if line != "":
                operation = line.split(" ")[0]
                value = " ".join(line.split(" ")[1:]).strip()
                #find if there's another '[' in the value
                if value.count("[") > 1:
                    #represents that there are multiple values in the value, each of which should be in the format of "[...]"
                    values = re.findall(r"\[.*?\]", value)
                    if len(values) > 2:
                        print(f"Line in reflex note not recognized! {line}")
                        continue
                    id = values[0].strip()[1:-1].strip()
                    value = values[1].strip()[1:-1].strip()
                    if operation == "REPLACE":
                        #check if id is a number
                        try:
                            id = int(id)
                        except:
                            raise ValueError("ID should be an integer!")
                        res.append((operation, id, value))
                    else:
                        print(f"Operation not recognized! {line}")
                else:
                    value = value.strip()[1:-1].strip()
                    operation = operation.strip().upper()
                    if operation == "UPVOTE" or operation == "DOWNVOTE":
                        #check if value is a number
                        try:
                            value = int(value)
                        except:
                            raise ValueError("Value should be an integer!")
                        res.append((operation, value, None))
                    elif operation == "CREATE":
                        res.append((operation, value, None))
                    else:
                        print(f"Operation not recognized! {line}")
                        continue
        except:
            print(f"Line in reflex note not recognized! {line}")
    return res

def parse_reflex_note(reflex_note):
    res = dict()
    for line in reflex_note.split("\n"):
        if line != "":
            s = line.split(" ")
            try:
                id = int(s[0])
                vote = int(s[-1])
                rule = " ".join(s[1:-1])
            except:
                print(f"Line in reflex note not recognized! {line}")
                continue
            res[id] = [rule, vote]
    return res