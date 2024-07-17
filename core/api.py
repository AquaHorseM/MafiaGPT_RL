# CONFIG YOUR API HERE :
RATE_LIMIT = 20  # sleeping time for openai per minute limitation
TOKEN_LIMIT = 100  # token limit per message
TEMPERATURE = 1
# MODEL = "gpt-4-turbo"
MODEL = "gpt-3.5-turbo-0125" #for debugging, use the cheaper api

import openai, os, time

# this is for printing messages in terminal
DEBUG = False


# getting open ai api key from the environmental variables
client = openai.OpenAI(api_key = os.getenv("OPENAI_API_KEY"))

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

def send_message_new(messages, agent_config = {}):
    '''
    A flexible function to send messages to openai
    Messages should be a tuple or list of tuples
    Each tuple should have two elements: role and content
    '''
    token_limit = agent_config.get("token_limit", TOKEN_LIMIT)
    rate_limit = agent_config.get("rate_limit", RATE_LIMIT)
    model_name = agent_config.get("model", MODEL)
    temperature = agent_config.get("temperature", TEMPERATURE)
    context = get_context(messages)
    
    time.sleep(rate_limit)
        
    # connecting to Openai
    response = openai.chat.completions.create(
        model=model_name, messages=context, temperature=temperature,
        max_tokens=token_limit, top_p=1
    )
    # returning the response as a string
    return response.choices[0].message.content