import random, logging
from core.api import send_message
import json, re
from prompts import render_prompts as render

class Player:
    def __init__(self, id):
        self.notes = ""
        self.is_alive = True
        self.id = id
        self.votes = []
        self.special_actions_log = []
        self.type = None

    def __str__(self):
        return f"Player {self.id}"
    
    def speak(self, Game, command):
        res = send_message(
            render.game_intro(self),
            render.game_report(Game, self),
            command
        ).replace("\n", " ") #
        return res

    def targeting(self, Game, command):
        res = send_message(
            render.game_intro(self),
            render.game_report(Game, self),
            command
            + "REMINDER: your message must include the number of player that you want to perform action on it.",
        )
        nums_in_res = re.findall(r"\d+", res)
        if nums_in_res == []:
            Game.logger.warning("No player provided in targetting.")
            return (None, res)
        target = int(nums_in_res[0])
        if target not in Game.alive_players:
            Game.logger.warning("Targeting a wrong player")
            return (None, res)
        return (target, res)

    def vote(self, Game):
        target, reason = self.targeting(
            Game,
            "Command: just send the number of the player that you want to vote for. You must not vote to yourself. if you don't want to vote anyone just send an empty response.",
        )
        self.votes.append(target)
        return (target, reason)

    '''
    To be consistent with the new version of the game, the following methods are added.
    '''
    def update_hstate(self, obs):
        return
    
    def train_obs(self, batch):
        return None
    
    def train_speech_policy(self, obs):
        return None
    
    def get_role(self):
        return self.type

class Villager(Player):
    def __init__(self, role, **kwargs):
        super().__init__(**kwargs)
        self.role = role
        self.type = "villager"


class Werewolf(Player):
    def __init__(self, role, **kwargs):
        super().__init__(**kwargs)
        self.role = role
        self.type = "werewolf"
        self.rank = "normal"  # it may change to leader
        self.werewolf_talks = []

    def killing(self, Game):
        target, reason = self.targeting(
            Game,
            f"Command : JUST send the number of player who you want to kill for tonight. also consider this advices : {Game.werewolves_talks}",
        )
        if target:
            self.special_actions_log.append(f"you attempted to kill player{target}")
        return target, reason

    def advicing(self, Game):
        target, reason = self.targeting(
            Game,
            "Command : send a short advice on which player do you suppose for eliminating at tonight from villagers.",
        )
        return target, reason
        
    def update_previous_advices(self, advices):
        self.werewolf_talks = advices


class Medic(Villager):
    def __init__(self, role, **kwargs):
        super().__init__(role, **kwargs)
        self.type = "medic"

    def healing(self, Game):
        target, reason = self.targeting(
            Game,
            "Command : send the number of player who you want to heal for tonight.",
        )
        return "heal", target, reason


class Seer(Villager):
    def __init__(self, role, **kwargs):
        super().__init__(role, **kwargs)
        self.type = "seer"

    def inquiry(self, Game):
        target, reason = self.targeting(
            Game,
            "Command : send the number of player who you want to know that is werewolf or not for tonight.",
        )
        return "see", target, reason
    
    def receive_inquiry_result(self, target, is_werewolf):
        tag = "" if is_werewolf else "not "
        self.special_actions_log.append(f" Player {target} is {tag}werewolf")