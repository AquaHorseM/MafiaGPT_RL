import os
import re, pickle
import numpy as np

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

def get_gt_hstate_from_joint_hstate(joint_hstate):
    #joint_hstate is a np tensor that concatenates the hidden states of all players in axis 0, which is N*N*N*R
    #Extract each player's beliefs of himself (N*R) and concatenate them in axis 0
    #return a np tensor
    N = joint_hstate.shape[0]
    for i in range(N):
        if i == 0:
            gt_hstate = joint_hstate[i, i]
        else:
            gt_hstate = np.concatenate((gt_hstate, joint_hstate[i, i]), axis=0)
    return gt_hstate

def get_player_reflex_info_from_raw_data(prev_joint_hstate, merged_events, new_joint_hstate, player_id, alpha = 0.5):
    prev_hstate = prev_joint_hstate[player_id]
    new_hstate = new_joint_hstate[player_id]
    new_gt_hstate = new_joint_hstate[player_id, player_id]
    #! Temp
    #Use alpha to blend the gt with the new hidden state, so that the model won't directly access the entire gt
    targ_hstate = alpha * new_gt_hstate + (1-alpha) * new_hstate
    return (prev_hstate, merged_events, new_hstate, targ_hstate)

def parse_data(data, player_id, alpha = 0.5):
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
            res.append(get_player_reflex_info_from_raw_data(data[prev_hstate_index], merged_events, data[i], player_id, alpha))
            prev_hstate_index = i
    return res

def parse_reflex_actions(reflex_actions):
    #parse all lines in the reflex note. Each line should be in the format of "OPERATION [VALUE]"
    #return a list of tuples in the form of [(OPERATION, VALUE), ...]
    res = []
    for line in reflex_actions.split("\n"):
        if line != "":
            operation = line.split(" ")[0]
            value = " ".join(line.split(" ")[1:]).strip()
            #find if there's another '[' in the value
            if value.count("[") > 1:
                #represents that there are multiple values in the value, each of which should be in the format of "[...]"
                values = re.findall(r"\[.*?\]", value)
                assert len(values) == 2, "Only support two values for now!"
                id = values[0].strip()
                value = values[1].strip()
            if len(s) == 1:
                operation = s
                #value should be "[...]"
                if value[0] != "[" or value[-1] != "]":
                    raise ValueError("Value should be in the format of [...]!")
                value = value[1:-1].strip()
                operation = operation.strip().upper()
                if operation == "UPVOTE" or operation == "DOWNVOTE":
                    #check if value is a number
                    if value.endswith("."):
                        value = value[:-1]
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
            elif len(s) == 3:
                operation, id, value = s
                if operation == "REPLACE":
                    if value.endswith("."):
                        value = value[:-1]
                    #check if id is a number
                    try:
                        id = int(id)
                    except:
                        raise ValueError("ID should be an integer!")
                    res.append((operation, id, value))
                else:
                    print(f"Operation not recognized! {line}")
            else:
                print(f"Operation not recognized! {line}")
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
            res[id] = (rule, vote)
    return res