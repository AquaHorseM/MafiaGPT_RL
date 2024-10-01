from copy import deepcopy
from functools import partial
import pickle
import random, logging
from core.api import send_message
import json, re, os, datetime
import numpy as np
from core.players.player import Player
from prompts import render_prompts as render
from core.baseline_players import Villager, Werewolf, Medic, Seer
from core.event import Event, EventBook, EventEncoder
from core.players.werewolf import WerewolfPlayer
from core.players.villager import VillagerPlayer
from core.players.medic import MedicPlayer
from core.players.seer import SeerPlayer
from core.utils import load_player_from_info, switcher_players, load_player_from_checkpoint
from core.api import load_client
from core.data import DataTree
import gym
import inspect
from core.common import *

def count_adjustable_params(func):    
    # Get the signature of the function
    sig = inspect.signature(func)
    params = sig.parameters
    
    # Determine if it's a method (by checking if 'self' or 'cls' is the first parameter)
    is_method = inspect.ismethod(func) or (inspect.isfunction(func) and 'self' in params)

    count = 0
    for i, param in enumerate(params.values()):
        # print(f"param: {param}")
        # Skip 'self' or 'cls' for methods
        if is_method and i == 0 and param.name in ('self', 'cls'):
            continue
        # Count only adjustable (non-default) parameters
        if param.default == param.empty and param.kind in (param.POSITIONAL_OR_KEYWORD, param.POSITIONAL_ONLY, param.KEYWORD_ONLY):
            count += 1
    return count


class WerewolfGameEnv:
    def __init__(self, id=1, train = False, openai_client = None, data_path = None):
        self.id = id
        self.all_players = []
        self.alive_players = []
        self.dead_players = []
        self.votes = []
        self.player_types = []
        self.event_book = EventBook()
        self.logger = self._configure_logger()
        self.current_round = 0
        self.cur_stage = 0
        self.player_num = 0
        self.temp_events = []
        self.latest_actions = None
        self.night_info = {
            "killed": None,
            "healed": None,
            "known_roles": dict()
        }
        
        self.openai_client = openai_client if not isinstance(openai_client, str) else load_client(openai_client)
        self.data_path = data_path if data_path is not None else f"records/game_{self.id}_data.pkl"
        #clear the data file if it exists
        # if os.path.exists(self.data_path):
        #     os.remove(self.data_path)
        self.train = train
        self.game_status = {
            "cur_stage": "night", #night, day, vote
            "cur_round": 0,
            "next_speaking_player": None, 
            "start_speaking_player": None,
            "winner": None
        }
        self.data = DataTree()
        
        self.logger.info(f"Game {self.id} created successfully")


    def _configure_logger(self):
        logger = logging.getLogger(f"Game-{self.id}")
        logger.setLevel(logging.DEBUG)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        return logger

    def set_players(self, player_configs): #player_configs should be a list of dicts
        self.player_num = len(player_configs)
        shuffled_nums = list(range(self.player_num))
        random.shuffle(shuffled_nums)
        
        self.alive_players = list(range(self.player_num))
        self.dead_players = []        
        
        werewolf_ids = [] 
        for num in range(len(shuffled_nums)):
            if player_configs[shuffled_nums[num]]["role"].lower() == "werewolf":
                werewolf_ids.append(num)
                
        
        init_global_info = self.get_global_info()
                
        init_werewolf_private_info = {
            "role": "werewolf",
            "werewolf_ids": werewolf_ids,
            "kill_history": [],
            "previous_advices": []  
        }
        
        init_villager_private_info = {
            "role": "villager",
        }
        
        init_medic_private_info = {
            "role": "medic",
            "last_heal": None
        }
        
        init_seer_private_info = {
            "role": "seer",
            "known_roles": dict()
        }
        
        switcher_private_info = {
            "werewolf": deepcopy(init_werewolf_private_info),
            "medic": deepcopy(init_medic_private_info),
            "seer": deepcopy(init_seer_private_info),
            "villager": deepcopy(init_villager_private_info)
        }
        
        for i, num in enumerate(shuffled_nums):
            role = player_configs[num]["role"].lower()
            player_type = player_configs[num]["player_type"].lower()
            self.player_types.append(player_type)
            if player_type == "reflex":
                prompt_dir_path = os.path.join("core/players/prompts", role)
                common_prompt_dir_path = os.path.join("core/players/prompts", "common")
                assert os.path.exists(prompt_dir_path), "prompt directory not found"
                assert os.path.exists(common_prompt_dir_path), "common prompt directory not found"
                self.all_players.append(switcher_players[player_type][role](i, init_global_info, switcher_private_info[role], prompt_dir_path, common_prompt_dir_path, self.openai_client))
            else:
                self.all_players.append(switcher_players[player_type][role](role=role, id=i))
                if role == "werewolf":
                    self.all_players[-1].special_actions_log.append(f"you are werewolf and this is your team (they are all werewolf) : {werewolf_ids}")
                
            self.add_event({"event": "set_player", "content": {"id": i, "role": role, "player_type": player_type}, "visible": "system"})
        #restore the data
        self.data = DataTree(self.get_state())

    
    def win_or_not(self, player_id):
        if self.game_status["winner"] == None:
            return 0
        elif self.game_status["winner"] == "werewolf":
            return 1 if self.all_players[player_id].role == "werewolf" else -1
        else:
            return 1 if self.all_players[player_id].role != "werewolf" else -1
            
    def get_unique_observation_single_player(self, player_id):
        if self.all_players[player_id].role == "werewolf":
            return {
                "belief": self.all_players[player_id].hstate.beliefs,
                "role": 1,
                "companions": np.array([1 if self.all_players[i].get_role() == "werewolf" else 0 for i in range(self.player_num)]),
                "last_killing_target": self.night_info["killed"] 
            }
        elif self.all_players[player_id].role == "seer":
            return {
                "belief": self.all_players[player_id].hstate.beliefs,
                "role": 3,
                "known_roles": np.array([self.night_info["known_roles"].get(i, -1) for i in range(self.player_num)]),
            }
        elif self.all_players[player_id].role == "medic":
            return {
                "belief": self.all_players[player_id].hstate.beliefs,
                "role": 2,
                "last_heal": self.night_info["healed"],
            }
        else: #vilager
            return {
                "belief": self.all_players[player_id].hstate.beliefs,
                "role": 0,
            }
    
    def get_shared_observation(self):
        return {
            "player_num": self.player_num,
            "alive_players": np.array([1 if i in self.alive_players else 0 for i in range(self.player_num)]),
            "current_round": self.current_round,
            "last_vote": np.array(self.votes[-1]) if self.votes else np.zeros(self.player_num)
        }
    
    def get_state(self):
        hstate = self.get_joint_hstate()
        private_infos = [self.all_players[i].private_info for i in range(self.player_num)]
        return {
            "hstate": hstate,
            "global_info": self.get_global_info(),
            "private_infos": private_infos,
            "id": self.id
        }
        
    
    def get_observation_single_player(self, player_id):
        return self.get_unique_observation_single_player(player_id).update(self.get_shared_observation())
    
    def check_done(self, player_id):
        return 1 if self.game_status["winner"] or not self.all_players[player_id].is_alive else 0
        
    def step(self, actions):
        # print("xsm debug actions: " + str(actions))
        assert len(actions) == self.player_num, "Number of actions must be equal to the number of players"
        if self.game_status["cur_stage"] == "night":
            alive_medics = self.get_alive_medics()
            if len(alive_medics) != 0:
                medic_id = alive_medics[0]
                self.add_event({"event": "heal", "content": {"player": medic_id, \
                    "target": actions[medic_id]["target"], "reason": actions[medic_id]["reason"]}, "visible": "medic"})
                self.night_info["healed"] = actions[medic_id]["target"]
            else:
                self.night_info["healed"] = None
            alive_seers = self.get_alive_seers()
            if len(alive_seers) != 0:
                seer_id = alive_seers[0]
                seer_target = actions[seer_id]["target"]
                is_werewolf = self.all_players[seer_target].get_role() == "werewolf"
                self.night_info["known_roles"][seer_target] = is_werewolf  
                self.add_event({"event": "inquiry", "content": {"player": seer_id, "target": seer_target, "is_werewolf": is_werewolf, \
                    "reason": actions[seer_id]["reason"]}, "visible": seer_id})
            werewolf_ids= self.get_alive_werewolves()
            assert len(werewolf_ids) > 0, "There must be at least one werewolf alive"
            if len(werewolf_ids) > 1:
                kill_target_1 = actions[werewolf_ids[0]]["target"]
                kill_target_2 = actions[werewolf_ids[1]]["target"]
                if kill_target_1 == kill_target_2:
                    kill_target = kill_target_1
                    kill_decider = 0
                else:
                    #randomly choose
                    kill_decider = random.choice([0, 1])
                    kill_target = kill_target_1 if kill_decider == 0 else kill_target_2
                self.add_event({"event": "advicing", "content": {"player": werewolf_ids[0], "target": kill_target_1, "reason": None}, "visible": "werewolf"})
                self.add_event({"event": "advicing", "content": {"player": werewolf_ids[1], "target": kill_target_2, "reason": None}, "visible": "werewolf"})
                self.add_event({"event": "kill", "content": {"player": werewolf_ids[kill_decider], "target": kill_target, "reason": None}, "visible": "werewolf"})
                self.night_info["killed"] = kill_target
            else:
                werewolf_id = werewolf_ids[0]
                kill_target = actions[werewolf_id]["target"]
                self.add_event({"event": "kill", "content": {"player": werewolf_id, "target": kill_target, \
                    "reason": actions[werewolf_id]["reason"]}, "visible": "werewolf"})
                self.night_info["killed"] = kill_target
            
            self.check_death_info()
            self.game_status["cur_stage"] = "day"
            self.game_status["start_speaking_player"] = random.choice(self.alive_players)
            self.game_status["next_speaking_player"] = self.game_status["start_speaking_player"]
        elif self.game_status["cur_stage"] == "day":
            speaking_player = self.game_status["next_speaking_player"]
            self.add_event({"event": "speak", "content": {"player": speaking_player, "speech": actions[speaking_player]["reason"]}, "visible": "all"})
            while True: #Find the next player to speak
                speaking_player = (speaking_player + 1) % self.player_num
                if speaking_player == self.game_status["start_speaking_player"]:
                    self.game_status["cur_stage"] = "vote"
                    break
                elif speaking_player in self.alive_players:
                    self.game_status["next_speaking_player"] = speaking_player
                    break
        else: #vote stage
            assert all([actions[i]["action"] == "vote" for i in self.alive_players]), "all actions must be 'vote' in the vote stage"
            votes = {i : actions[i]["target"] for i in self.alive_players if actions[i]["target"] is not None}
            self.votes.append(votes)
            for player_id in self.alive_players:
                self.all_players[player_id].global_info["last_vote"] = votes[player_id]
                self.add_event({"event": "vote", "content": {"player": player_id, "target": votes[player_id], "reason": actions[player_id]["reason"]}, "visible": player_id})
            self.check_votes()
            self.current_round += 1
            self.game_status["cur_stage"] = "night"
            self.game_status["cur_round"] += 1
        # self.update_all_hstates(add_to_data = True)
        #return obs, state, rewards, dones, info, available_actions
        if self.is_game_end():
            rewards = [1 if self.all_players[i].get_role() == "werewolf" else 0 for i in range(self.player_num)]
            self.end()
        else:
            rewards = [0 for _ in range(self.player_num)]
        return self._repeat(self.get_observation_single_player), self.get_state(), rewards, self._repeat(self.check_done), self.game_status, self.get_available_actions()

        
    def seed(self, seed):
        random.seed(seed)
    
    def _repeat(self, a):
        #if a is a function, return a(i) for i in range(self.player_num)
        if callable(a):
            param_count = count_adjustable_params(a)
            if param_count == 1:
                return [a(i) for i in range(self.player_num)]
            else:
                return [a()] * self.player_num
        else:
            return [a for _ in range(self.player_num)]
    
    def _get_alive_players_for_role(self, role):
        return list(filter(lambda player: self.all_players[player].get_role() == role, self.alive_players))

    def get_alive_werewolves(self):
        return self._get_alive_players_for_role("werewolf")

    def get_alive_villagers(self):
        return self._get_alive_players_for_role("villager")
    
    def get_alive_medics(self):
        return self._get_alive_players_for_role("medic")
    
    def get_alive_seers(self):
        return self._get_alive_players_for_role("seer")
        
    def vote_out(self, player_id):
        if player_id not in self.alive_players:
            self.logger.warning("Voting out an already dead guy! Skipped!")
            return
        self.add_event({"event": "vote_out", "content": {"player": player_id}, "visible": "all"})
        self.die(player_id)
    
    def die(self, player_id):
        if player_id not in self.alive_players:
            self.logger.warning(f"Player {player_id} is already dead! Skipped!")
            return
        self.alive_players.remove(player_id)
        self.dead_players.append(player_id)
        self.add_event({"event": "die", "content" : {"player": player_id}, "visible": "all"})
        self.all_players[player_id].is_alive = False
        for player_id in self.alive_players:
            self.all_players[player_id].global_info["alive_players"] = self.alive_players
            self.all_players[player_id].global_info["dead_players"] = self.dead_players
        return

    def is_game_end(self):
        """
        Will check that the game is over or not.
        """
        werewolves = self.get_alive_werewolves()
        if len(werewolves) >= len(self.alive_players) / 2:
            self.add_event({"event": "end", "content": {"winner": "Werewolves"}})
            self.game_status["winner"] = "werewolf"
            return True
        if len(werewolves) == 0:
            self.add_event({"event": "end", "content": {"winner": "Villagers"}})
            self.game_status["winner"] = "villager"
            return True
        return False

    def check_votes(self):
        # [TODO] : debugging here
        votes = self.votes[-1]
        if max(votes) > 1:
            votes_sorted = dict(sorted(votes.items(), key=lambda x: x[1]))
            self.vote_out(list(votes_sorted.keys())[-1])
        return
    
    def check_death_info(self):
        '''
        To check the death info of the previous night
        '''
        f = 0
        if self.night_info["killed"] is not None:
            if self.night_info["healed"] is None or self.night_info["killed"] != self.night_info["healed"]:
                f = 1
                self.die(self.night_info["killed"])
        if f == 0:
            self.add_event({"event": "no_death", "content": "Nobody died last night", "visible": "all"})
        
        self.night_info = {
            "killed": None,
            "healed": None,
            "known_roles": self.night_info["known_roles"]
        }
        
    def add_event(self, event):
        if isinstance(event, Event):
            self.temp_events.append(event)
            self.event_book.add_event(event)
            self.logger.info(event)
        else:
            assert isinstance(event, dict), "event must be a dict or an instance of Event"
            if "visible" not in event:
                event["visible"] = "all"
            self.add_event(Event(event))

            
    def get_global_info(self):
        return {
            "player_num": self.player_num,
            "alive_players": list(self.alive_players),
            "dead_players": list(self.dead_players),
            "roles_mapping": {
                "villager": 0,
                "werewolf": 1,
                "medic": 2,
                "seer": 3
            },
            "previous_votes": self.votes,
            "game_status": self.game_status,
        }
            

    def save_game_record(self):
        events = list(self.event_book.events.values())
        json.dump(events, open(f"records/game_{self.id}_log.json", "w"), indent=4, cls=EventEncoder)
                
    
    def parse_global_info(self, global_info: dict):
        self.current_round = global_info["game_status"]["cur_round"]
        self.alive_players = global_info["alive_players"]
        self.dead_players = global_info["dead_players"]
        self.votes = global_info["previous_votes"]
        self.game_status = global_info["game_status"]
        self.player_num = global_info["player_num"]
    
    def load_state(self, state, events):
        self.id = state["id"]
        global_info = state["global_info"]
        self.parse_global_info(global_info)
        self.event_book = EventBook()
        self.event_book.add_event(events)
        self.all_players = []
        for i in range(global_info["player_num"]):
            player: Player = load_player_from_info(state["private_infos"][i], global_info, i, self.openai_client)
            player.hstate.beliefs = deepcopy(state["hstate"][i])
            player.event_book.add_event(self.event_book.filter(
                end_tick = player.tick,
                id = player.id,
                labels = player.labels
            ))
            self.all_players.append(player)
            self.player_types.append("reflex")
        self.logger.info(f"Info loaded successfully")

    def all_players_reflex(self):
        #temp debug, disable this
        return
        for player_id in range(len(self.all_players)):
            player = self.all_players[player_id]
            if self.player_types[player_id] == "reflex":
                player.reflex(self.data)
                
    def all_players_reflex_from_data_path(self, data_path):
        self.logger.info(f"Reflexing all players from data path {data_path}")
        for player_id in range(len(self.all_players)):
            self.all_players[player_id].reflex_from_data_path(data_path)
        self.logger.info("All players reflexed successfully")
        return
    
    def act(self, player_id, actions):
        return self.all_players[player_id]._act(available_actions = [actions] if isinstance(actions, str) else actions)
    
    def update_data(self):
        # print(f"debug: adding game_status {self.game_status} to data")
        self.data.add_edge_and_node(
            events = self.temp_events,
            actions = self.latest_actions,
            state = self.get_state()
        )
        self.temp_events = []
    
    def update_all_hstates(self, add_to_data = True):
        for player in self.all_players:
            player.update_hstate(self.event_book)
        self.logger.info("All hidden states updated successfully")
        if add_to_data:
            self.update_data()
        return

    def get_joint_hstate(self):
        return [self.all_players[i].hstate.beliefs for i in range(self.player_num)]
    
    
    def store_data(self, path):
        if not self.data:
            self.logger.warning("No data to store! Skipped!")
            return
        with open(path, "wb") as file:
            pickle.dump(self.data, file)
        self.logger.info(f"Data stored successfully to {path}")
        
    def load_data(self, path):
        self.data_path = path
        with open(path, "rb") as f:
            self.data: DataTree = pickle.load(f)
        
    def end(self):
        self.logger.info("Game ended")
        self.update_all_hstates(add_to_data=True)
        self.save_game_record()
        self.store_data(f"data/game_{self.id}_data.pkl")
        if self.train:
            self.logger.info("ALl players reflexing")
            self.all_players_reflex()
            
    def get_available_actions_single_player(self, player_id): #return the raw actions; if need to apply to gym, use discretify after this
        if self.game_status["cur_stage"] == "night":
            night_actions = {
                "seer": ["see"],
                "medic": ["heal"],
                "werewolf": ["kill"],
                "villager": []
            }
            return night_actions[self.all_players[player_id].get_role()]
        elif self.game_status["cur_stage"] == "day":
            if player_id == self.game_status["next_speaking_player"]:
                return ["speak"]
            else:
                return []
        else: #vote stage
            return ["vote"]
        
    def get_available_actions(self):
        return self._repeat(self.get_available_actions_single_player)
    
    def get_actions_from_reflex_player(self, player_id, available_actions):
        player_avail_actions = available_actions[player_id]
        # print(f"Player id: {player_id}, available_actions: {player_avail_actions}")
        if len(player_avail_actions) == 0:
            return None #Will not be checked, so return whatever action
        else:
            action = self.all_players[player_id]._act(player_avail_actions)
            return action

    def get_actions_reflex(self, available_actions):
        return self._repeat(partial(self.get_actions_from_reflex_player, available_actions = available_actions))

    def sim_game_for_reflex_players(self): #main simulation function
        self.logger.info("Simulating games for reflex players")
        avail_actions = self.get_available_actions()
        while True:
            actions = self.get_actions_reflex(avail_actions)
            # self.logger.info(f"actions: {actions}")
            obs, state, rewards, dones, info, avail_actions = self.step(actions)
            self.latest_actions = actions
            if info is not None:
                self.logger.info(str(info))
            if all(dones):
                break
            self.update_all_hstates(add_to_data=True)
        self.logger.info("Game simulated successfully")
        
    def reset(self):
        #reset hidden state
        for player in self.all_players:
            player.reset()
        self.event_book = EventBook()
        self.current_round = 0
        self.game_status = {
            "cur_stage": "night", #night, day, vote
            "cur_round": 0,
            "next_speaking_player": None, 
            "start_speaking_player": None,
            "winner": None
        }
        self.alive_players = list(range(self.player_num))
        self.dead_players = []
        self.votes = []
        self.temp_events = []
        self.night_info = {
            "killed": None,
            "healed": None,
            "known_roles": dict()
        }
        self.data = DataTree(self.get_state())
        self.logger.info("Game reset successfully")
        #return obs, state, available_actions
        return self._repeat(self.get_observation_single_player), self.get_state(), self.get_available_actions()
    
    def backtrace(self, back_steps = 1):
        node_id = self.data.get_backtrace_id(back_steps)
        recover_info = self.data.backtrace(node_id)
        info = recover_info["state"]
        prev_game_status = info["global_info"]["game_status"]
        events = recover_info["events"]
        print(f"current game status: {self.game_status}")
        print(f"game status to recover: {prev_game_status}")
        self.load_state(info, events)
        print(f"current game status: {self.game_status}")