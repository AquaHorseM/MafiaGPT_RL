# CONFIG YOUR API HERE :
RATE_LIMIT = 20  # sleeping time for openai per minute limitation
SLEEP_EVERYTIME = 1 # sleep for 1s every time, for what? I don't know!
TOKEN_LIMIT = 250  # token limit per message
TEMPERATURE = 1
MAX_RETRIES = 1
# MODEL = "gpt-4-turbo"
# MODEL = "gpt-4-turbo" #for debugging, use the cheaper api
MODEL = "gpt-4-turbo" #for debugging, use the cheaper api

import openai, os, time, yaml
import re

# this is for printing messages in terminal
DEBUG = False

def load_client(key_path="openai_config_backup.yaml"):
    openai._reset_client()
    key = yaml.safe_load(open(key_path))
    for k, v in key.items():
        setattr(openai, k, v)
    return openai._load_client()

# make content in openai wanted format
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


def send_message(
    intro, game_report, command, token_limit=TOKEN_LIMIT, time_limit_rate=RATE_LIMIT
):
    """
    Sending the request to api
    """
    messages = [
        ("system", intro),
        ("user", game_report[-(token_limit - len(intro) - 70) :]),
        ("system", command),
    ]
    context = get_context(messages)

    time.sleep(time_limit_rate)

    # connecting to Openai
    response = openai.chat.completions.create(
        model=MODEL, messages=context, temperature=TEMPERATURE,
        max_tokens=token_limit, top_p=1
    )
    # just for debugging in terminal
    if DEBUG:
        print(
            f"""
            #######################
            {intro}
            #######################
            {game_report}
            #######################
            {command}
            #######################
            -----------------------------
            {response.choices[0].message["content"]}
        """
        )
    # returning the response as a string
    return response.choices[0].message.content

def send_message_xsm(messages, agent_config = {}, client = None):
    '''
    A flexible function to send messages to openai
    Messages should be a tuple or list of tuples
    Each tuple should have two elements: role and content
    '''
    token_limit = agent_config.get("token_limit", TOKEN_LIMIT)
    rate_limit = agent_config.get("rate_limit", RATE_LIMIT)
    model_name = agent_config.get("model", MODEL)
    temperature = agent_config.get("temperature", TEMPERATURE)
    max_retries = agent_config.get("max_retries", MAX_RETRIES)
    sleep_everytime = agent_config.get("sleep_everytime", SLEEP_EVERYTIME)
    context = get_context(messages)
    
    time.sleep(sleep_everytime)
        
    # connecting to Openai
    for i in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model_name, messages=context, temperature=temperature,
                max_tokens=token_limit, top_p=1
            )
            break
        except Exception as e:
            print(f"Error: {e}")
            if i == max_retries - 1:
                raise e
            print(f"Retrying {i+1}th time")
            time.sleep(10)
            continue
    # returning the response as a string
    #! debug
    
    with open("message_input_history_backup.txt", "a") as f:
        f.write(f"{context}\n\n")
    with open("message_history_backup.txt", "a") as f:
        f.write(f"{response.choices[0].message.content}\n\n")
    return response.choices[0].message.content



