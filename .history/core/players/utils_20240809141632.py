import os
import re, pickle
from core.players.player import Player
from core.event import EventBook
from core.players.werewolf import WerewolfPlayer
from core.players.medic import MedicPlayer
from core.players.seer import SeerPlayer
from core.players.villager import VillagerPlayer
from core.game import Game

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