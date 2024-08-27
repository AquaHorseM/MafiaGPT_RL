import os
import re, pickle

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
            #merge the events
            merged_events = []
            for event in events:
                merged_events += event