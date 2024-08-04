import os
import json

def get_prompt(prompt_path, replacements):
    with open(prompt_path, 'r') as file:
        j = json.load(file)
    for role, content in j.items():
        #allow user to comment using ''', '''
        #i.e. '''...''' should be ignored
        content = content.split("'''")
        content = [content[i] if i % 2 == 0 else "" for i in range(len(content))]
        content = "".join(content)
        for key, value in replacements.items():
            content = content.replace(key, value)
        j[role] = content
    return j