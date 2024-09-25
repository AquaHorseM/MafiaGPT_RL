import os
import re, pickle
import numpy as np
from typing import List, Dict, Tuple

from core.api import send_message_xsm

def create_message(role, content):
    return {"role": role, "content": content}

def get_context(messages):
    if isinstance(messages, list) and isinstance(messages[0], dict):
        return messages
    context = []
    if isinstance(messages, tuple):
        messages = [messages]
    elif isinstance(messages, str):
        messages = [("user", messages)]
    for role, content in messages:
        context.append(create_message(role, content))
    return context

def events_include_player(event, player_id):
    #check if the event includes the player
    #find 'player: player_id' in the event
    #There could be multiple spaces between : and player_id
    match = re.search(r"player\s*:\s*" + str(player_id), event.lower())
    if match is not None:
        return True
    else:
        with open("debug.out", "a") as f:
            f.write(f"Event not include player {player_id}: {event}\n")
        return False

def get_prompt(prompt_path, replacements, background_path = None):
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
        print(f"joint_hstate shape: {joint_hstate.shape}")
        if len(joint_hstate.shape) == 4:
            assert joint_hstate.shape[1] == joint_hstate.shape[2], \
                f"joint_hstate shape {joint_hstate.shape} is not recognized!"
            self_hstates = [joint_hstate[i, i] for i in range(joint_hstate.shape[0])]
        elif len(joint_hstate.shape) == 3:
            assert joint_hstate.shape[0] == joint_hstate.shape[1] ** 2, \
                f"joint_hstate shape {joint_hstate.shape} is not recognized!"
            joint_hstate = np.reshape(joint_hstate, (int(joint_hstate.shape[0] ** 0.5), int(joint_hstate.shape[0] ** 0.5), joint_hstate.shape[1], joint_hstate.shape[2]))
            self_hstates = [joint_hstate[i] for i in range(joint_hstate.shape[0])]
    return np.concatenate(np.expand_dims(self_hstates, axis=0), axis=0)

def get_player_reflex_info_from_raw_data(prev_joint_hstate, merged_events, new_joint_hstate, player_id, alpha = 1):
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
            if prev_hstate_index == 0 and isinstance(data[0], tuple):
                #error data; skip
                prev_hstate_index = i
                continue
            else:
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
            values = re.findall(r"\[.*?\]", line)
            try:
                id = int(values[0][1:-1])
                rule = values[1][1:-1]
                vote = int(values[2][1:-1])
            except:
                print(f"Line in reflex note not recognized! {line}")
                continue
            res[id] = [rule, vote]
    return res

import os
import json

def load_prompts_from_folder(folder_path):
    return sorted(os.listdir(folder_path))

def load_config(config_path):
    with open(config_path, 'r') as file:
        return json.load(file)

def send_dialogue(folder_path, config_path):
    prompts = load_prompts_from_folder(folder_path)
    config = load_config(config_path)
    
    conversation_history = []
    
    for prompt_name in config['prompt_order']:
        if prompt_name in prompts:
            prompt_path = os.path.join(folder_path, prompt_name)
            with open(prompt_path, 'r') as file:
                prompt = file.read()
            
            # Send the current message to GPT
            conversation_history.append({"role": "user", "content": prompt})
            response = send_message_xsm(conversation_history)  # Assuming this function handles the request
            
            # Add the response to conversation history
            conversation_history.append({"role": "assistant", "content": response})
    
    # Return the final response from the last assistant message
    return conversation_history[-1]["content"]

# Example usage
# final_response = send_dialogue("path_to_prompts_folder", "path_to_config.json")
