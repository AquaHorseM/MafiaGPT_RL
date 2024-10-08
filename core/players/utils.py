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
    # print(f"getting target from {response}")
    try:
        target = int(re.search(r"\d+", response).group())
    except:
        target = None
    # print(f"target is {target}")
    return target
    
def parse_reflex_actions(reflex_actions: str):
    #parse all lines in the reflex note. Each line should be in the format of "OPERATION [VALUE]"
    #return a list of tuples in the form of [(OPERATION, VALUE), ...]
    res = []
    if "My updating operations are:" in reflex_actions:
        reflex_actions = '\n'.join(reflex_actions.split("My updating operations are:")[1:])
    else:
        print("No Operation starting indication detected! Scanning the whole response now...")
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
                        print(f"Line in reflex operation not recognized! {line}")
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
            print(f"Line in reflex operation not recognized! {line}")
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

def send_dialogue(folder_path, background_path, replacements, config_path = None, client = None, return_history = False):
    prompts = load_prompts_from_folder(folder_path)
    config = load_config(config_path) if config_path is not None else load_config(os.path.join(folder_path, "config.json"))
    
    conversation_history = []
    conversation_history.append({"role": "system", "content": get_prompt(background_path, replacements)})
    
    for prompt_name in config['prompt_order']:
        if prompt_name in prompts:
            prompt_path = os.path.join(folder_path, prompt_name)
            prompt = get_prompt(prompt_path, replacements, background_path=None)
            conversation_history.append({"role": "user", "content": prompt})
            response = send_message_xsm(conversation_history, client = client) #?
            conversation_history.append({"role": "assistant", "content": response})
    if return_history:
        return [conversation_history[i]["content"] for i in range(len(conversation_history)) if conversation_history[i]["role"] == "assistant"]
    else:
        return conversation_history[-1]["content"]


def get_response(prompt_dir_path, common_dir_path, prompt_name, replacements, client) -> str:
    background_path = os.path.join(common_dir_path, "background.txt")
    common_folder = os.path.join(common_dir_path, prompt_name)
    if os.path.exists(common_folder):
        return send_dialogue(common_folder, background_path, replacements, client = client)
    common_file = os.path.join(common_dir_path, prompt_name + ".txt")
    if os.path.exists(common_file):
        prompt = get_prompt(common_file, replacements, background_path)
        return send_message_xsm(prompt, client = client)
    role_folder = os.path.join(prompt_dir_path, prompt_name)
    if os.path.exists(role_folder):
        return send_dialogue(role_folder, background_path, replacements, client = client)
    role_file = os.path.join(prompt_dir_path, prompt_name + ".txt")
    if os.path.exists(role_file):
        prompt = get_prompt(role_file, replacements, background_path)
        return send_message_xsm(prompt, client = client)
    raise ValueError(f"Prompt Not found for {prompt_name}")