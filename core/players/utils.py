import os
import json

def get_prompt(prompt_path, replacements):
    with open(prompt_path, 'r') as file:
        j = json.load(file)
    for role, content in j.items():
        for key, value in replacements.items():
            content = content.replace(key, value)
        j[role] = content
    return j