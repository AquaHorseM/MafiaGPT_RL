import pickle
import random, logging
from core.api import send_message
import json, re, os, datetime
import numpy as np
from prompts import render_prompts as render
from core.baseline_players import Villager, Werewolf, Medic, Seer
from core.event import Event, EventBook
from core.players.werewolf import WerewolfPlayer
from core.players.villager import VillagerPlayer
from core.players.medic import MedicPlayer
from core.players.seer import SeerPlayer
from core.utils import switcher_players, load_player_from_checkpoint
from core.api import load_client
import gym


class GameEnv:
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
        self.night_info = {
            "killed": None,
            "healed": None
        }
        self.data = []
        self.openai_client = openai_client if not isinstance(openai_client, str) else load_client(openai_client)
        self.data_path = data_path if data_path is not None else f"records/game_{self.id}_data.pkl"
        #clear the data file if it exists
        if os.path.exists(self.data_path):
            os.remove(self.data_path)
        self.train = train
        self.game_status = {
            "cur_stage": "night", #night, day, vote
            "cur_round": 0,
            "speaking_player": None, 
            "start_speaking_player": None,
        }
        #The action space and observation space should be set after the players are set using the 'init_env' method
        self.action_space = []
        self.observation_space = None
        self.shared_observation_space = 
        
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
            "werewolf": init_werewolf_private_info,
            "medic": init_medic_private_info,
            "seer": init_seer_private_info,
            "villager": init_villager_private_info
        }
        
        for i, num in enumerate(shuffled_nums):
            role = player_configs[num]["role"].lower()
            player_type = player_configs[num]["player_type"].lower()
            self.player_types.append(player_type)
            if player_type == "reflex":
                prompt_dir_path = os.path.join("core/players/prompts", role)
                assert os.path.exists(prompt_dir_path), "prompt directory not found"
                self.all_players.append(switcher_players[player_type][role](i, init_global_info, switcher_private_info[role], prompt_dir_path, self.openai_client))
            else:
                self.all_players.append(switcher_players[player_type][role](role=role, id=i))
                if role == "werewolf":
                    self.all_players[-1].special_actions_log.append(f"you are werewolf and this is your team (they are all werewolf) : {werewolf_ids}")
                
            self.add_event({"event": "set_player", "content": {"id": i, "role": role, "player_type": player_type}, "visible": "system"})
    
    def get_observation_space_single_player(self, player_id):
        def get_belief():
            return gym.spaces.Box(low = 0, high = 1, shape = (self.player_num * self.player_num * 4,), dtype = np.float32)
        if self.all_players[player_id].role == "werewolf":
            return gym.spaces.Dict({
                "belief": get_belief(),
                "role": gym.spaces.Discrete(1),
                "companions": gym.spaces.MultiBinary(self.player_num),
                "last_killing_target": gym.spaces.Discrete(1),
            })
        elif self.all_players[player_id].role == "seer":
            return gym.spaces.Dict({
                "belief": get_belief(),
                "role": gym.spaces.Discrete(1),
                "known_roles": gym.spaces.Discrete(self.player_num),
            })
        elif self.all_players[player_id].role == "medic":
            return gym.spaces.Dict({
                "belief": get_belief(),
                "role": gym.spaces.Discrete(1),
                "last_heal": gym.spaces.Discrete(1),
            })
        else: #villager
            return gym.spaces.Dict({
                "belief": get_belief(),
                "role": gym.spaces.Discrete(1),
            })
            
    def get_observation_single_player(self, player_id):
        if self.all_players[player_id].role == "werewolf":
            return {
                "belief": self.all_players[player_id].hidden_state.beliefs,
                "role": 1,
                "companions": np.array([1 if self.all_players[i].get_role() == "werewolf" else 0 for i in range(self.player_num)]),
                "last_killing_target": self.all_players[player_id].last_killing_target
            }
        elif self.all_players[player_id].role == "seer":
            return {
                "belief": self.all_players[player_id].hidden_state.beliefs,
                "role": 3,
                "known_roles": np.array([self.all_players[player_id].get_known_roles().get(i, 0) for i in range(self.player_num)])
            }
        elif self.all_players[player_id].role == "medic":
            return {
                "belief": self.all_players[player_id].hidden_state.beliefs,
                "role": 2,
                "last_heal": self.all_players[player_id].last_heal
            }
        else: #vilager
            return {
                "belief": self.all_players[player_id].hidden_state.beliefs,
                "role": 0
            }
    
    def get_shared_observation(self):
        return {
            "player_num": self.player_num,
            "alive_players": np.array([1 if i in self.alive_players else 0 for i in range(self.player_num)]),
            "current_round": self.current_round,
            "last_vote": self.votes[-1] if self.votes else np.zeros(self.player_num)
        }
        
    def step(self, actions):
        def get_action_target(action):
            return action - self.n_speak - self.n_vote
        def get_vote_target(action):
            return action - self.n_speak
        assert len(actions) == self.player_num, "Number of actions must be equal to the number of players"
        if self.game_status["cur_stage"] == "night":
            medic_id = self.get_alive_medics()[0]
            seer_id = self.get_alive_seers()[0]
            werewolf_ids= self.get_alive_werewolves()
            heal_target = get_action_target(actions[medic_id])
            seer_target = get_action_target(actions[seer_id])
            kill_target = get_action_target(actions[werewolf_ids[-1]])
            advice_target = get_action_target(actions[werewolf_ids[0]])
            self.night_info["killed"] = kill_target
            self.night_info["healed"] = heal_target
            #add the events separately to the event book
            self.add_event({"event": "heal", "content": {"player": medic_id, "target": heal_target, "reason": None}, "visible": "medic"})
            self.add_event({"event": "inquiry", "content": {"player": seer_id, "target": target, "is_werewolf": is_werewolf, "reason": reason}, "visible": seer_id})
            self.add_event({"event": "advicing", "content": {"player": werewolf_ids[0], "target": advice_target, "reason": None}, "visible": "werewolf"})
            self.add_event({"event": "kill", "content": {"player": werewolf_ids[-1], "target": kill_target, "reason": None}, "visible": "werewolf"})
            self.check_death_info()
            self.game_status["cur_stage"] = "day"
            
    
    def init_env(self):
        assert self.player_num != 0 and len(self.all_players) == self.player_num, "Players must be set before initializing the environment"
        self.n_speak = 6 #Temporarily set to 6 as the number of speak types
        self.n_kill = self.player_num #Werewolves can kill any player including themselves
        self.n_see = self.player_num #Seer can see any player including himself, though it is not useful
        self.n_heal = self.player_num #Medic can heal any player including himself
        self.n_vote = self.player_num #Any player can vote any player including himself
        self.action_space = []
        for i in range(self.player_num):
            if self.all_players[i].role == "werewolf":
                self.action_space.append(gym.spaces.Discrete(self.n_speak + self.n_vote + self.n_kill))
            elif self.all_players[i].role == "seer":
                self.action_space.append(gym.spaces.Discrete(self.n_speak + self.n_vote + self.n_see))
            elif self.all_players[i].role == "medic":
                self.action_space.append(gym.spaces.Discrete(self.n_speak + self.n_vote + self.n_heal))
            else: #villager
                self.action_space.append(gym.spaces.Discrete(self.n_speak + self.n_vote))
        self.observation_space = [self.get_observation_space_single_player(i) for i in range(self.player_num)]
        self.shared_observation_space = gym.spaces.Dict({
            "player_num": gym.spaces.Discrete(1),
            "alive_players": gym.spaces.MultiBinary(self.player_num),
            "current_round": gym.spaces.Discrete(1),
            "last_vote": gym.spaces.Discrete(self.player_num),
        })
    
    def get_player(self, id):
        return self.all_players[id]

    def get_alive_werewolves(self):
        ls = list(filter(lambda player: self.all_players[player].get_role() == "werewolf", self.alive_players))
        return ls

    def get_alive_medics(self):
        return list(filter(lambda player: self.all_players[player].get_role() == "medic", self.alive_players))

    def get_alive_seers(self):
        return list(filter(lambda player: self.all_players[player].get_role() == "seer", self.alive_players))

    def get_alive_villagers(self):
        return list(
            filter(lambda player: self.all_players[player].get_role() == "villager", self.alive_players)
        )
        
    def vote_out(self, player_id):
        if player_id not in self.alive_players:
            self.logger.warning("Voting out an already dead guy! Skipped!")
            return
        self.alive_players.remove(player_id)
        self.dead_players.append(player_id)
        self.add_event({"event": "vote_out", "content": {"player": player_id}, "visible": "all"})
        self.all_players[player_id].is_alive = False
        #update for all players
        for player_id in self.alive_players:
            self.all_players[player_id].global_info["alive_players"] = self.alive_players
            self.all_players[player_id].global_info["dead_players"] = self.dead_players
    
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
            return True
        if len(werewolves) == 0:
            self.add_event({"event": "end", "content": {"winner": "Villagers"}})
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
            "healed": None
        }
        
    def add_event(self, event):
        if isinstance(event, Event):
            if self.train:
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
            "current_round": self.current_round,
            "roles_mapping": {
                "villager": 0,
                "werewolf": 1,
                "medic": 2,
                "seer": 3
            },
            "previous_votes": self.votes
        }
            

    def save_game_record(self):
        json.dump(str(self.event_book), open(f"records/game_{self.id}_log.json", "w"), indent=4)
        
    def save_checkpoint(self, root_path):
        #assert all player types are reflex
        self.logger.info(f"Saving checkpoint to {root_path}")
        assert all([player_type == "reflex" for player_type in self.player_types]), "All players must be reflex players"
        os.makedirs(root_path, exist_ok=True)
        info = {
            "global_info": self.get_global_info(),
            "event_book": self.event_book,
            "night_info": self.night_info, 
            "id": self.id,
            "cur_stage": self.cur_stage,
        }
        with open(os.path.join(root_path, f"game_checkpoint.pkl"), "wb") as file:
            pickle.dump(info, file)
        for player in self.all_players:
            player.save_checkpoint(os.path.join(root_path, f"player_{player.id}_ckpt.pkl"))
        self.logger.info(f"Checkpoint saved successfully")
        return
        
    def load_checkpoint(self, root_path): #assume all players are reflex players
        self.logger.info(f"Loading checkpoint from {root_path}")
        with open(os.path.join(root_path, f"game_checkpoint.pkl"), "rb") as file:
            info = pickle.load(file)
        self.id = info["id"]
        self.event_book = info["event_book"]
        self.night_info = info["night_info"]
        self.cur_stage = info["cur_stage"]
        self.current_round = info["global_info"]["current_round"]
        self.alive_players = info["global_info"]["alive_players"]
        self.dead_players = info["global_info"]["dead_players"]
        self.votes = info["global_info"]["previous_votes"]
        for i in range(info["global_info"]["player_num"]):
            player = load_player_from_checkpoint(os.path.join(root_path, f"player_{i}_ckpt.pkl"), self, i)
            player.event_book.add_event(self.event_book.filter(
                end_tick = player.tick,
                id = player.id,
                labels = player.labels
            ))
            self.all_players.append(player)
            self.player_types.append("reflex")
        self.logger.info(f"Checkpoint loaded successfully")

    def get_gt_hstate(self):
        #A temporary version for the current hidden state definition
        hstate = []
        for i in range(self.player_num):
            hstate.append(self.all_players[i].get_gt_hiddenstate())
        hstate = np.concatenate(hstate, axis = 0)
        return hstate

    def all_players_reflex(self):
        for player_id in range(len(self.all_players)):
            player = self.all_players[player_id]
            if self.player_types[player_id] == "baseline":
                res = send_message(
                    render.game_intro(player),
                    render.game_report(self, player),
                    render.notetaking_command(),
                )
                self.add_event(
                    {
                        "event": "notetaking",
                        "content": {"player": player_id, "context": res},
                        "visible": player_id
                    }
                )
                player.notes = res
            elif self.player_types[player_id] == "reflex":
                player.reflex(self.data)
                
    def all_players_reflex_from_data_path(self, data_path):
        self.logger.info(f"Reflexing all players from data path {data_path}")
        for player_id in range(len(self.all_players)):
            self.all_players[player_id].reflex_from_data_path(data_path)
        self.logger.info("All players reflexed successfully")
        return
    
    def act(self, player_id, actions, update_hstate = True):
        return self.all_players[player_id]._act(self.event_book, 
                                                available_actions = [actions] if isinstance(actions, str) else actions,
                                                update_hstate = update_hstate)
    
    def update_all_hstates(self):
        for player in self.all_players:
            player.update_hidden_state(self.event_book)
        return
    
    def act_and_collect_hstate(self, player_id, actions):
        self.update_all_hstates()
        return self.act(player_id, actions, update_hstate=False)

    def get_hstate(self, player_id):
        return self.all_players[player_id].hidden_state
    
    def get_joint_hstate(self):
        return np.concatenate([player.hidden_state.beliefs for player in self.all_players], axis = 0)
    
    def add_all_hstate_to_data(self):
        if self.temp_events:
            self.add_events_to_data(self.temp_events)
            self.temp_events = []
        self.data.append(self.get_joint_hstate())
    
    def add_events_to_data(self, events):
        #convert events to a tuple of strings
        _events_ = [str(event) for event in events]
        #convert to a tuple and add to data as a single element
        self.data.append(tuple(_events_))

    
    def store_data(self, path):
        if not self.data:
            self.logger.warning("No data to store! Skipped!")
            return
        if os.path.exists(path):
            with open(path, "rb") as file:
                d = pickle.load(file)
            dat = d + self.data
        else:
            dat = self.data
        with open(path, "wb") as file:
            pickle.dump(dat, file)
        self.data = []
        self.logger.info(f"Data stored successfully to {path}")
        
    def end(self):
        self.save_game_record()
        if self.train:
            self.add_events_to_data(self.temp_events)
            self.temp_events = []
            self.logger.info("ALl players reflexing")
            self.all_players_reflex()
            self.store_data(f"records/game_{self.id}_data.pkl")
            
    def get_action_space_size(self, player_id):
        if self.all_players[player_id].role == "werewolf":
            return self.n_speak + self.n_vote + self.n_kill
        elif self.all_players[player_id].role == "seer":
            return self.n_speak + self.n_vote + self.n_see
        elif self.all_players[player_id].role == "medic":
            return self.n_speak + self.n_vote + self.n_heal
        else: #villager
            return self.n_speak + self.n_vote
            
    def discretify(self, actions, player_id):
        if isinstance(actions, list):
            avail = [0] * self.get_action_space_size(player_id)
        assert isinstance(actions, str), "actions must be a string or a list of strings"
        if actions == "speak":
            return [1] * self.n_speak + [0] * (self.get_action_space_size(player_id) - self.n_speak)
        elif actions == "vote":
            return [0] * self.n_speak + [1] * self.n_vote + [0] * (self.get_action_space_size(player_id) - self.n_speak - self.n_vote)
        else: #night actions
            return [0] * self.n_speak + [0] * self.n_vote + [1] * (self.get_action_space_size(player_id) - self.n_speak - self.n_vote)
        
            
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
            if player_id == self.game_status["speaking_player"]:
                return ["speak"]
            else:
                return []
        else: #vote stage
            return ["vote"]
        
    def get_available_actions(self):
        return [self.get_available_actions_single_player(player_id) for player_id in range(self.player_num)]
    
    def get_observation(self, player_id):
        return self.event_book.filter(