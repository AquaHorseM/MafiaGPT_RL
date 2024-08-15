import os
import random
import numpy as np
from copy import deepcopy
from core.api import send_message_xsm
from core.event import EventBook
import re, pickle

from core.players.utils import get_prompt
        
class Player:
    class HiddenState:
        def __init__(self, player_num, role_mapping):
            roles_num = len(role_mapping)
            self.beliefs = np.ones((player_num, player_num, roles_num)) / roles_num
            self.player_num = player_num
            self.roles_num = roles_num
            self.role_mapping = role_mapping
            self.inverse_role_mapping = {v: k for k, v in role_mapping.items()}
        
        def __str__(self) -> str:
            s = ""
            for i in range(self.player_num):
                for j in range(self.player_num):
                    s += f"player {i} believes player {j} is role {self.inverse_role_mapping[np.argmax(self.beliefs[i][j])]} with probability {np.max(self.beliefs[i][j])} \n"
            return s
                    
        def str_to_tensor(self, belief_str):
            #assume the str is in the format "player i believes player j is role k with probability p \n ..."
            def match(belief_str: str):
                # print(f"belief_str: {belief_str}")
                #Remember the probability is a float, and the role should be the name, i.e. a string
                pattern = r"player (\d+) believes player (\d+) is role (.*) with probability (\d+\.\d+)" #TODO: check the pattern
                match = re.match(pattern, belief_str)
                # print(f"match: {match}")
                if match is None:
                    return None
                return tuple(map(int, match.groups()[:-2])) + self.role_mapping[match.groups()[-2]] + float(match.groups()[-1])
            
            beliefs = np.zeros((self.player_num, self.player_num, self.roles_num))
            
            for line in belief_str.split("\n"):
                if line == "":
                    continue
                m = match(line)
                if m is None:
                    return None
                i, j, k, p = m
                beliefs[i][j][k] = p
                return beliefs
        
        def update(self, beliefs, confidence = 0.2):
            if isinstance(beliefs, str):
                beliefs = self.str_to_tensor(beliefs)
            print("##############################################")
            print(f"updating beliefs: \n {beliefs}")
            print(f"with confidence: {confidence}")
            print("##############################################")
            if beliefs is not None:
                self.beliefs = confidence * beliefs + (1 - confidence) * self.beliefs
            return
                
    
    def get_replacements(self):
        return {
            "{player_id}": str(self.id),
            "{player_num}": str(self.global_info["player_num"]),
            "{alive_players}": str(list(self.global_info["alive_players"])),
            "{dead_players}": str(self.global_info["dead_players"]) if len(self.global_info["dead_players"]) > 0 else "Nobody",
            "{current_round}": str(self.global_info["current_round"] + 1), #! notice the +1 here
            "{roles_mapping}": str(self.global_info["roles_mapping"]),
            "{role}": str(self.private_info["role"]),
            "{previous_votes}": str(self.global_info["previous_votes"]),
        }
            
                        
    def __init__(self, id, global_info, private_info):
        self.is_alive = True
        self.id = id
        self.hidden_state = self.HiddenState(global_info["player_num"], global_info["role_mapping"])
        self.global_info = deepcopy(global_info)
        self.private_info = deepcopy(private_info)
        self.labels = ["all"]
        self.tick = 0
        self.event_book = EventBook()
        
    def init_game(self, global_info, private_info):
        self.global_info = global_info
        self.private_info = private_info
        self.hidden_state = self.HiddenState(global_info["player_num"], len(global_info["roles_mapping"]))

    def __str__(self):
        return f"Player {self.id}"

    def update_hidden_state(self, event_book: EventBook):
        if event_book.tick == self.tick:
            return
        self._update_hidden_state(self.filter_event_book(event_book))
        self.tick = event_book.tick
    
    def _act(self, event_book: EventBook, available_actions = None): #return (action, target, reason)
        if len(available_actions) == 0:
            return (None, None, "No available actions.")
        else:
            action = random.choice(available_actions)
            target = random.choice(self.global_info["alive_players"])
            reason = "I am the baseline player and I do things randomly."
            return (action, target, reason)
        
    def vote(self, Game): #to be consistent with the baseline version
        return self.act(Game.event_book, available_actions = ["vote"])[1:]
    
    def _speak(self, event_book: EventBook):
        return "I am the baseline player and I don't have anything to say."
    
    def speak(self, Game, command): #to be consistent with the baseline version
        return self._speak(Game.event_book)
            
    def train_obs(self, batch):
        return None
    
    def train_speech_policy(self, obs):
        return None
    
    def previous_votes(self):
        return self.global_info["previous_votes"]

    def reset(self): #ABORTED
        self.is_alive = True
        self.hidden_state = self.HiddenState(self.global_info["player_num"], len(self.global_info["roles_mapping"]))
        self.global_info["alive_players"] = range(self.global_info["player_num"])
        self.global_info["dead_players"] = []
        self.global_info["current_round"] = 0
        self.private_info = {}
        return
    
    def filter_event_book(self, event_book: EventBook):
        return event_book.filter(start_tick=self.tick, id=self.id, labels=self.labels)
    
    def _update_hidden_state(self, events):
        return
    
    def init_game(self, global_info, private_info):
        return
    
    def get_role(self):
        return self.private_info["role"]
    
    def get_hidden_state(self):
        return self.hidden_state
    
    def get_gt_hiddenstate(self):
        return self.hidden_state.beliefs[self.id]
    
    def reflex(self, game):
        return
    
    def _update_hidden_state(self, events):
        #TODO
        self.event_book.add_event(events)        
        event_des = ""
        for event in events:
            event_des += str(event)
            event_des += "\n"
            
        replacements = self.get_replacements()
        replacements.update({"{event_des}": event_des})
        prompt_path = os.path.join(self.prompt_dir_path, "update_hidden_state")
        prompt = get_prompt(prompt_path, replacements)
        response = send_message_xsm(prompt)
        #DEBUG 
        print(f"Player {self.id} updating hidden state with response: {response}")
        #first line is the confidence, the other lines are the beliefs
        try:
            conf = float(response.split("\n")[0])
            beliefs = "\n".join(response.split("\n")[1:])
        except ValueError:
            conf = 0.2 
            beliefs = response

        self.hidden_state.update(beliefs, confidence = conf)
        return

    '''
    The following functions are defined to be consistent with the baseline version.
    DO NOT use them in the future.
    '''
    
    def healing(self, game):
        return self._act(game.event_book, available_actions = ["heal"])
    
    def inquiry(self, game):
        return self._act(game.event_book, available_actions = ["see"])
    
    def kill(self, game):
        return self._act(game.event_book, available_actions = ["kill"])
    
    '''
    The following functions are defined for saving and loading checkpoints.
    '''
    
    def save_checkpoint(self, path):
        info = {
            "beliefs": self.hidden_state.beliefs,
            "prompt_dir_path": self.prompt_dir_path,
            "private_info": self.private_info,
            "tick": self.tick
        }
        with open(path, 'wb') as file:
            pickle.dump(info, file)
