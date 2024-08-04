import random
import numpy as np
from copy import deepcopy
from core.event import EventBook
        
class Player:
    class HiddenState:
        def __init__(self, player_num, roles_num):
            self.beliefs = np.ones((player_num, roles_num)) / roles_num
        
        def __str__(self) -> str:
            return str(self.beliefs)
        
        def set_role(self, player_id, role_id):
            self.beliefs[player_id] = 0
            self.beliefs[player_id, role_id] = np.inf
            
        def update_belief(self, player_id, role_id, belief):
            self.beliefs[player_id, role_id] = belief
            
        def set_beliefs(self, beliefs):
            self.beliefs = deepcopy(beliefs)
            
        def get_beliefs(self):
            return deepcopy(self.beliefs)
    
    def get_replacements(self):
        return {
            "{player_id}": str(self.id),
            "{player_num}": str(self.global_info["player_num"]),
            "{alive_players}": str(self.global_info["alive_players"]),
            "{dead_players}": str(self.global_info["dead_players"]),
            "{current_round}": str(self.global_info["current_round"]),
            "{roles_mapping}": str(self.global_info["roles_mapping"]),
            "{role}": str(self.private_info["role"]),
            "{beliefs}": str(self.hidden_state.get_beliefs()),
            "{previous_votes}": str(self.global_info["previous_votes"]),
        }
            
                        
    def __init__(self, id, global_info, private_info):
        self.is_alive = True
        self.id = id
        self.special_actions_log = []
        self.hidden_state = self.HiddenState(global_info["player_num"], len(global_info["roles_mapping"]))
        self.global_info = deepcopy(global_info)
        self.private_info = deepcopy(private_info)
        self.history = None
        self.last_update_tick = 0
        self.labels = ["all"]
        self.tick = 0
        
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

    def reset(self):
        self.is_alive = True
        self.special_actions_log = []
        self.hidden_state = self.HiddenState(self.global_info["player_num"], len(self.global_info["roles_mapping"]))
        self.global_info["alive_players"] = range(self.global_info["player_num"])
        self.global_info["dead_players"] = []
        self.global_info["current_round"] = 0
        self.private_info = {}
        self.history = None
        return
    
    def filter_event_book(self, event_book: EventBook):
        return event_book.filter(start_tick=self.tick, id=self.id, labels=self.labels)
    
    def _update_hidden_state(self, events):
        return
    
    def init_game(self, global_info, private_info):
        return
    
    def get_role(self):
        return self.private_info["role"]
    
    def reflex(self, game):
        return