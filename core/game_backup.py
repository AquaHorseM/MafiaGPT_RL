import pickle
import random, logging
from core.api import send_message
import json, re, os, datetime
import numpy as np
from prompts import render_prompts as render
from core.baseline_players import Villager, Werewolf, Medic, Seer
from core.event import Event, EventBook
from core.players.player import Player
from core.players.werewolf import WerewolfPlayer
from core.players.villager import VillagerPlayer
from core.players.medic import MedicPlayer
from core.players.seer import SeerPlayer
from core.utils import switcher_players
from core.api import load_client
from core.data import DataTree


class Game:
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
        self.player_num = 0
        self.temp_events = []
        self.night_info = {
            "killed": None,
            "healed": None
        }
        self.game_status = {
            "cur_stage": "night", #night, day, vote
            "cur_round": 0,
            "speaking_player": None, 
            "start_speaking_player": None,
            "winner": None
        }
        self.data = DataTree()
        self.openai_client = openai_client if not isinstance(openai_client, str) else load_client(openai_client)
        self.data_path = data_path if data_path is not None else f"records/game_{self.id}_data.pkl"
        #clear the data file if it exists
        if os.path.exists(self.data_path):
            self.logger.warning(f"data path {self.data_path} already exists. Removing it.")
            os.remove(self.data_path)
        self.train = train
        self.hstate_updated = True


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
                common_prompt_dir_path = os.path.join("core/players/prompts", "common")
                assert os.path.exists(prompt_dir_path), "prompt directory not found"
                assert os.path.exists(common_prompt_dir_path), "common prompt directory not found"
                self.all_players.append(switcher_players[player_type][role](i, init_global_info, switcher_private_info[role], prompt_dir_path, common_prompt_dir_path, self.openai_client))
            else:
                self.all_players.append(switcher_players[player_type][role](role=role, id=i))
                if role == "werewolf":
                    self.all_players[-1].special_actions_log.append(f"you are werewolf and this is your team (they are all werewolf) : {werewolf_ids}")
                
            self.add_event({"event": "set_player", "content": {"id": i, "role": role, "player_type": player_type}, "visible": "system"})

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
            if votes_sorted.values[-1] == votes_sorted.values[-2]:
                self.add_event({
                    "event": "vote draw", "content": "No one is voted out"
                })
            else:
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
        
    def add_event(self, event, sim_only = False):
        if isinstance(event, Event):
            if self.train and not sim_only:
                self.temp_events.append(event)
            self.event_book.add_event(event)
            if not sim_only:
                self.logger.info(event)
        else:
            assert isinstance(event, dict), "event must be a dict or an instance of Event"
            if "visible" not in event:
                event["visible"] = "all"
            self.add_event(Event(event))
        if not sim_only and self.hstate_updated:
            self.hstate_updated = False

    def run_day(self, save_checkpoint = False):
        if self.cur_stage == 2:
            for player_id in self.alive_players:
                if self.player_types[player_id] == "baseline":
                    res = self.all_players[player_id].speak(self, render.speech_command()).replace("\n", " ")
                else:
                    if self.train:
                        self.update_all_hstates(add_to_data=True)
                        # res = self.all_players[player_id]._speak(self.event_book, update_hstate = False)
                        res = self.act(player_id, "speak", update_hstate=False)
                    else:
                        # res = self.all_players[player_id]._speak(self.event_book, update_hstate = True)
                        res = self.act(player_id, "speak", update_hstate=True)
                self.add_event(
                    {"event": "speech", "content": {"player": player_id, "context": res}}
                )
                if save_checkpoint:
                    self.save_checkpoint(f"checkpoints/game_{self.id}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}")
        self.cur_stage = max(3, self.cur_stage)
        if self.cur_stage == 3:
            votes = [0] * 7
            voting = {}
            self.add_event({"event": "vote_start"})
            for player_id in self.alive_players:
                if self.player_types[player_id] == "baseline":
                    target_voted, reason = self.all_players[player_id].vote(self)
                else:
                    if self.train:
                        if not self.hstate_updated:
                            self.update_all_hstates()
                            self.add_all_hstate_to_data()
                        action, target_voted, reason = self.all_players[player_id]._act(self.event_book, available_actions = ["vote"], update_hstate = False)
                    else:
                        action, target_voted, reason = self.all_players[player_id]._act(self.event_book, available_actions = ["vote"], update_hstate = True)
                voting[player_id] = (target_voted, reason)
            for player_id, (target, reason) in voting.items():
                if target is not None:
                    votes[target] += 1
                    self.add_event(
                        {"event": "vote", "content": {"player": player_id, "target": target}}
                    )
                    self.add_event(
                        {"event": "vote_reason", "content": {"player": player_id, "target": target, "reason": reason}, "visible": "system"}
                    )
                else:
                    self.logger.warning(f"Player {player_id} didn't vote.")
                    self.add_event(
                        {"event": "vote_reason", "content": {"player": player_id, "target": target, "reason": reason}, "visible": "system"}
                    )
            self.add_event({"event": "vote_results", "content": str(votes)})
            self.add_event({"event": "vote_end"})
            self.votes.append(dict(enumerate(votes)))
            self.check_votes()
            self.cur_stage = max(4, self.cur_stage)
        return
    
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
        return [self.get_available_actions_single_player(i) for i in range(self.player_num)]

    def run_night(self):
        self.werewolves_talks = []
        if self.train and not self.hstate_updated:
            self.update_all_hstates(add_to_data=True)
        update_hstate_for_actions = not self.train
        for medic_id in self.get_alive_medics():
            # action, target, reason = self.all_players[medic_id].healing(self, update_hstate = update_hstate_for_actions)
            action, target, reason = self.act(medic_id, "heal", update_hstate=update_hstate_for_actions)
            self.add_event({"event": "heal", "content": {"player": medic_id, "target": target, "reason": reason}, "visible": medic_id})
            self.night_info["healed"] = target
        for seer_id in self.get_alive_seers():
            # action, target, reason = self.all_players[seer_id].inquiry(self, update_hstate = update_hstate_for_actions)
            action, target, reason = self.act(seer_id, "see", update_hstate=update_hstate_for_actions)
            is_werewolf = self.all_players[target].get_role() == "werewolf" if target is not None else None
            self.add_event({"event": "inquiry", "content": {"player": seer_id, "target": target, "is_werewolf": is_werewolf, "reason": reason}, "visible": seer_id})
            if is_werewolf is not None: 
                self.all_players[seer_id].receive_inquiry_result(target, is_werewolf)
            
        werewolf_ids = self.get_alive_werewolves()
        for werewolf_id in werewolf_ids:
            advices = []
            if self.player_types[werewolf_id] == "baseline":
                if werewolf_id == werewolf_ids[-1]:
                    target, reason = self.all_players[werewolf_id].killing(self)
                    action = "kill"
                else:
                    target, reason = self.all_players[werewolf_id].advicing(self)
                    advices.append({"id": werewolf_id, "target": target, "reason": reason})
                    action = "advice"
            elif self.player_types[werewolf_id] == "reflex":
                self.all_players[werewolf_id].private_info["previous_advices"] = advices
                # action, target, reason = self.all_players[werewolf_id]._act(self.event_book, available_actions = ["kill"], 
                #                                                             update_hstate = update_hstate_for_actions)
                action, target, reason = self.act(werewolf_id, "kill", update_hstate=update_hstate_for_actions)
                action = "kill" if werewolf_id == werewolf_ids[-1] else "advice"
                if action == "kill":
                    self.night_info["killed"] = target
            self.add_event({"event": action, "content": {"player": werewolf_id, "target": target, "reason": reason},
                            "visible": "werewolf"})
            if action == "kill":
                for wid in werewolf_ids:
                    if self.player_types[wid] == "baseline":
                        self.all_players[wid].special_actions_log.append(f"Werewolves attempted to kill player{target}")          
        return

    def run_game(self, save_checkpoint = False):
        while True:
            if self.cur_stage == 0:
                self.add_event({"event": "cycle", "content": "night starts"})
                self.run_night()
            self.cur_stage = max(1, self.cur_stage)
            if self.cur_stage == 1:
                self.add_event({"event": "cycle", "content": "day starts"})
                self.check_death_info() #it is set here so that the death info would be revealed in the day
                if self.is_game_end():
                    self.end()
                    return
                if save_checkpoint:
                    self.save_checkpoint(f"checkpoints/game_{self.id}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}")
            if self.train:
                self.add_events_to_data(self.temp_events)
                self.temp_events = []
                self.store_data(f"records/game_{self.id}_data.pkl")
            self.cur_stage = max(2, self.cur_stage)
            self.run_day(save_checkpoint = save_checkpoint)       
            if self.is_game_end():
                self.end()
                return
            self.current_round += 1
            self.cur_stage = 0
            if self.train:
                self.add_events_to_data(self.temp_events)
                self.temp_events = []
                self.store_data(f"records/game_{self.id}_data.pkl")
            if save_checkpoint:
                self.save_checkpoint(f"checkpoints/game_{self.id}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}")
            
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
            "joint_hstate": self.get_joint_hstate(),
        }
            

    def save_game_record(self):
        json.dump(str(self.event_book), open(f"records/game_{self.id}_log.json", "w"), indent=4)
        
    def save_checkpoint(self, root_path = None):
        #set root_path=None to merely output the info without saving
        #assert all player types are reflex
        assert all([player_type == "reflex" for player_type in self.player_types]), "All players must be reflex players"
        if root_path is not None:
            self.logger.info(f"Saving checkpoint to {root_path}")
            os.makedirs(root_path, exist_ok=True)
        game_info = {
            "global_info": self.get_global_info(),
            "night_info": self.night_info, 
            "id": self.id,
            "game_status": self.game_status,
        }
        if root_path is not None:
            with open(os.path.join(root_path, f"game_checkpoint.pkl"), "wb") as file:
                pickle.dump(game_info, file)
        player_infos = []
        for player in self.all_players:
            if root_path is not None:
                player_info = player.save_checkpoint(os.path.join(root_path, f"player_{player.id}_ckpt.pkl"))
            else:
                player_info = player.save_checkpoint(path = None)
            player_infos.append(player_info)
        self.logger.info(f"Checkpoint saved successfully")
        return {
            "game_info": game_info,
            "player_infos": player_infos 
        }
                
    def parse_global_info(self, global_info: dict):
        self.current_round = global_info["current_round"]
        self.alive_players = global_info["alive_players"]
        self.dead_players = global_info["dead_players"]
        self.votes = global_info["previous_votes"]
        self.game_status = global_info["game_status"]
        self.player_num = global_info["player_num"]
    
    def load_checkpoint(self, info, events):
        game_info = info["game_info"]
        self.id = game_info["id"]
        self.night_info = game_info["night_info"]
        global_info = game_info["global_info"]
        self.parse_global_info(global_info)
        self.event_book = EventBook()
        self.event_book.add_event(events)
        self.all_players = []
        for i in range(global_info["player_num"]):
            player: Player = load_player_from_info(info["player_infos"][i], self, i)
            player.hstate = global_info["joint_hstate"][i]
            player.event_book.add_event(self.event_book.filter(
                end_tick = player.tick,
                id = player.id,
                labels = player.labels
            ))
            self.all_players.append(player)
            self.player_types.append("reflex")
        self.logger.info(f"Info loaded successfully")

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
    
    def act(self, player_id, actions):
        return self.all_players[player_id]._act(available_actions = [actions] if isinstance(actions, str) else actions)
    
    def update_all_hstates(self, add_to_data = True):
        for player in self.all_players:
            player.update_hstate(self.event_book)
        if add_to_data:
            self.update_data()
        self.hstate_updated = True
        return
    
    def update_data(self):
        info = self.save_checkpoint()
        self.data.add_edge_and_node(
            events = self.temp_events,
            info = info
        )
    
    def get_joint_hstate(self):
        return np.concatenate([np.expand_dims(player.hstate.beliefs, axis = 0) for player in self.all_players], axis = 0)
    
    def store_data(self, path):
        if not self.data:
            self.logger.warning("No data to store! Skipped!")
            return
        with open(path, "wb") as file:
            pickle.dump(self.data, file)
        self.logger.info(f"Data stored successfully to {path}")
        
    def end(self):
        self.save_game_record()
        if self.train:
            self.update_all_hstates(add_to_data=True)
            self.store_data(f"records/game_{self.id}_data.pkl")
            self.logger.info("ALl players reflexing")
            self.all_players_reflex()
            self.logger.info("All players reflexed successfully")
            
    def backtrace(self, back_steps = 1):
        node_id = self.data.get_backtrace_id(back_steps)
        recover_info = self.data.backtrace(node_id)
        info = recover_info["info"]
        events = recover_info["events"]
        self.load_checkpoint(info, events)
        
        
