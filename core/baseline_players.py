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
    def update_hidden_state(self, obs):
        return
    
    def train_obs(self, batch):
        return None
    
    def train_speech_policy(self, obs):
        return None

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

    def killing(self, Game):
        target, reason = self.targeting(
            Game,
            f"Command : JUST send the number of player who you want to kill for tonight. also consider this advices : {Game.werewolves_talks}",
        )
        if target:
            Game.log_submit(
                {"event": "targeted", "content": {"player": target, "reason": reason}}
            )
            player = Game.get_player(target)
            if Game.healed_guy is not player:
                Game.kill(player)
            self.special_actions_log.append(f"you attemped to kill player{target}")

    def advicing(self, Game):
        target, reason = self.targeting(
            Game,
            "Command : send a short advice on which player do you suppose for eliminating at tonight from villagers.",
        )
        Game.log_submit(
            {"event": "speech", "content": {"player": self.id, "context": reason}}
        )
        self.werewolves_talks.append(reason)


class Medic(Villager):
    def __init__(self, role, **kwargs):
        super().__init__(role, **kwargs)
        self.type = "medic"

    def healing(self, Game):
        target, reason = self.targeting(
            Game,
            "Command : send the number of player who you want to heal for tonight.",
        )
        if target:
            Game.healed_guy = Game.get_player(target)
            self.special_actions_log.append(f"You have healed Player number {target}")
            Game.log_submit(
                {"event": "healed", "content": {"player": target, "reason": reason}}
            )


class Seer(Villager):
    def __init__(self, role, **kwargs):
        super().__init__(role, **kwargs)
        self.type = "seer"

    def inquiry(self, Game):
        target, reason = self.targeting(
            Game,
            "Command : send the number of player who you want to know that is werewolf or not for tonight.",
        )
        if target:
            targeted_player = Game.get_player(target)
            is_werewolf = targeted_player.type == "werewolf"
            tag = "" if is_werewolf else "not"
            self.special_actions_log.append(f" Player {target} is {tag} werewolf")
            Game.log_submit(
                {
                    "event": "inquiried",
                    "content": {
                        "player": target,
                        "context": is_werewolf,
                        "reason": reason,
                    },
                }
            )