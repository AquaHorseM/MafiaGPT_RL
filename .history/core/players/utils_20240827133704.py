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

def get_player_reflex_info_from_raw_data(prev_joint_hstate, merged_events, new_joint_hstate, player_id):
    prev_hstate = prev_joint_hstate[player_id, player_id]

def parse_data(data):
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
            res.append((data[prev_hstate_index], merged_events, data[i]))
            prev_hstate_index = i
    return res