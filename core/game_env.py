from copy import deepcopy
from functools import partial
import pickle
import random, logging
from core.api import send_message
import json, re, os, datetime
import numpy as np
from core.players.player import Player
from core.event import Event, EventBook
from core.utils import switcher_players, emph_print, count_adjustable_params
from core.api import load_client
import multiprocessing
from core.data import DataTree

class WerewolfGameEnv:
    def __init__(self, id=1, game_config = None):
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
        self.openai_client = load_client(game_config["openai_client_path"])
        data_folder = game_config.get("data_folder", "data")
        self.data_path = os.path.join(data_folder, f"game_{self.id}_data.pkl")
        #clear the data file if it exists
        # if os.path.exists(self.data_path):
        #     os.remove(self.data_path)
        self.train = game_config.get("reflex_after_sim", False)
        self.log_hstate = game_config.get("log_hstate_for_debug", False)
        self.game_status = {
            "cur_stage": "night", #night, day, vote
            "cur_round": 0,
            "next_speaking_player": None, 
            "start_speaking_player": None,
            "winner": None
        }
        self.retry_num = game_config.get("extra_sim_nodes", 5)
        self.set_players(game_config["players"])
        self.data = DataTree(self.get_state())
        self.latest_actions = [None] * self.player_num
        self.latest_drafts = [{
            "cur_action": None,
            "player_id": i
        } for i in range(self.player_num)]
        self.players_config = game_config["players"]
        self.logger.info(f"Game {self.id} created successfully")
        self.add_event({"event": "start_game"})

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

    def set_players(self, player_configs, roles_order = None): #player_configs should be a list of dicts
        self.all_players = []
        self.player_types = []
        self.player_num = len(player_configs)
        if roles_order is None:
            shuffled_nums = list(range(self.player_num))
            random.shuffle(shuffled_nums)
        else:
            def shuffle_roles(roles, player_configs):
                # Check if the lengths match
                if len(roles) != len(player_configs):
                    raise ValueError("The lengths of roles and player_configs must be the same.")
                role_count = {}
                for role in roles:
                    role_count[role] = role_count.get(role, 0) + 1
                player_role_count = {}
                for config in player_configs:
                    role = config.get("role")
                    player_role_count[role] = player_role_count.get(role, 0) + 1
                if role_count != player_role_count:
                    raise ValueError("Roles in 'roles' do not match roles in 'player_configs'.")
                role_to_indices = {}
                for idx, config in enumerate(player_configs):
                    role = config["role"]
                    if role not in role_to_indices:
                        role_to_indices[role] = []
                    role_to_indices[role].append(idx)
                ids = []
                for role in roles:
                    if role_to_indices[role]:
                        ids.append(role_to_indices[role].pop())
                    else:
                        raise ValueError(f"No available players for role: {role}")
                return ids
            shuffled_nums = shuffle_roles(roles_order, player_configs)
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
                prompt_dir_path = player_configs[num].get("prompt_dir_path")
                common_prompt_dir_path = player_configs[num].get("common_prompt_dir_path")
                assert os.path.exists(prompt_dir_path), f"prompt directory {prompt_dir_path} not found"
                assert os.path.exists(common_prompt_dir_path), f"common prompt directory {common_prompt_dir_path} not found"
                reflex_note_belief_path = player_configs[num].get("reflex_note_belief_path")
                reflex_note_policy_path = player_configs[num].get("reflex_note_policy_path")
                if reflex_note_belief_path is None or reflex_note_policy_path is None:
                    self.all_players.append(switcher_players[player_type][role](i, self.id, init_global_info, switcher_private_info[role], prompt_dir_path, \
                        common_prompt_dir_path, self.openai_client))
                else:
                    self.all_players.append(switcher_players[player_type][role](i, self.id, init_global_info, switcher_private_info[role], prompt_dir_path, \
                        common_prompt_dir_path, self.openai_client, reflex_note_belief_path, reflex_note_policy_path))
            else:
                self.all_players.append(switcher_players[player_type][role](role=role, id=i))
                if role == "werewolf":
                    self.all_players[-1].special_actions_log.append(f"you are werewolf and this is your team (they are all werewolf) : {werewolf_ids}")
                
            self.add_event({"event": "set_player", "content": {"id": i, "role": role, "player_type": player_type}, "visible": "system"})
        # self.update_all_hstates(add_to_data=True)

    
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
    
    def get_player_draft(self):
        pass
    
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
                self.all_players[seer_id].receive_inquiry_result(seer_target, is_werewolf)
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
                self.add_event({"event": "advicing", "content": {"player": werewolf_ids[0], "target": kill_target_1, "reason": actions[werewolf_ids[0]]["reason"]}, "visible": "werewolf"})
                self.add_event({"event": "advicing", "content": {"player": werewolf_ids[1], "target": kill_target_2, "reason": actions[werewolf_ids[1]]["reason"]}, "visible": "werewolf"})
                self.add_event({"event": "kill", "content": {"player": werewolf_ids[kill_decider], "target": kill_target, "reason": "System randomly decided from the werewolves' suggestions."}, "visible": "werewolf"})
                self.night_info["killed"] = kill_target
            else:
                werewolf_id = werewolf_ids[0]
                kill_target = actions[werewolf_id]["target"]
                self.add_event({"event": "advicing", "content": {"player": werewolf_id, "target": kill_target, \
                    "reason": actions[werewolf_id]["reason"]}, "visible": "werewolf"})
                self.add_event({"event": "kill", "content": {"player": werewolf_id, "target": kill_target, "reason": "System randomly decided from the werewolves' suggestions."}, "visible": "werewolf"})
                self.night_info["killed"] = kill_target
            
            self.check_death_info()
            self.game_status["cur_stage"] = "day"
            self.add_event({"event": "day_start"})
            self.game_status["start_speaking_player"] = random.choice(self.alive_players)
            self.add_event({"event": "start_speaking", "content": {"player": self.game_status['start_speaking_player']}})
            self.game_status["next_speaking_player"] = self.game_status["start_speaking_player"]
        elif self.game_status["cur_stage"] == "day":
            speaking_player = self.game_status["next_speaking_player"]
            speech = actions[speaking_player]["target"]
                    
            replacements = self.all_players[0].get_replacements()
            replacements.update({
                "{org_speech}": speech,
            })
            # speech_summary = self.all_players[0].get_response("summarize_speech", replacements)
            self.add_event({"event": "speak", "content": {"player": speaking_player, "speech": speech, "speech_summary": 'speech summary has been deprecated!'}, "visible": "all"})
            while True: #Find the next player to speak
                speaking_player = (speaking_player + 1) % self.player_num
                if speaking_player == self.game_status["start_speaking_player"]:
                    self.game_status["cur_stage"] = "vote"
                    self.add_event({"event": "vote_start"})
                    break
                elif speaking_player in self.alive_players:
                    self.game_status["next_speaking_player"] = speaking_player
                    break
                
        else: #vote stage
            assert all([actions[i]["action"] == "vote" for i in self.alive_players if actions[i] is not None]), "all actions must be 'vote' in the vote stage"
            votes = {i : actions[i]["target"] for i in self.alive_players if actions[i]["target"] is not None}
            self.votes.append(votes)
            for player_id in self.alive_players:
                self.all_players[player_id].global_info["last_vote"] = votes[player_id] if votes.get(player_id) is not None else None
                self.add_event({"event": "vote", "content": {"player": player_id, "target": votes[player_id] if votes.get(player_id) is not None else None, \
                    "reason": actions[player_id]["reason"]}, "visible": player_id})
            self.check_votes()
            self.current_round += 1
            self.game_status["cur_stage"] = "night"
            self.game_status["cur_round"] += 1
            self.add_event({"event": "begin_round", "content": {"round": self.game_status['cur_round']+1}})
            self.add_event({"event": "night_start"})
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
            self.logger.info(event.to_dict())
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
            "previous_votes": self.votes,
            "game_status": self.game_status,
        }
            

    def save_game_record(self):
        events = [e.to_dict() for es in self.event_book.events.values() for e in es]
        json.dump(events, open(f"records/game_{self.id}_log.json", "w"), indent=4)
                
    
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
        self.set_players(self.players_config, [state["private_infos"][i]["role"] for i in range(self.player_num)])
        for player in self.all_players:
            player.global_info = deepcopy(global_info)
            player.private_info = deepcopy(state["private_infos"][player.id])
            player.hstate.beliefs = deepcopy(state["hstate"][player.id])
            player.event_book.add_event(self.event_book.filter(
                end_tick = player.tick,
                id = player.id,
                labels = player.labels
            ))
        self.logger.info(f"Info loaded successfully")

    def all_players_reflex(self):
        #temp debug, disable this
        for player_id in range(len(self.all_players)):
            self.reflex_for_player(player_id)
    
    def reflex_for_player(self, player_id):
        if self.player_types[player_id] == "reflex":
            self.all_players[player_id].reflex(self.data)
            return True
        return False
    
    def reflex_multi_process(self, num_processes = 4):
        reflex_player_ids = []
        werewolf_ids = []
        villager_ids = []
        for i in range(self.player_num):
            if not self.player_types[i]=="reflex":
                self.logger.debug(f"Player {i} not reflexable. Skipping.")
                continue
            if self.all_players[i].get_role() in ["medic", "seer"]:
                reflex_player_ids.append(i)
            elif self.all_players[i].get_role() == "werewolf":
                werewolf_ids.append(i)
            else: #villager
                villager_ids.append(i)
        
        if len(werewolf_ids) > 0:
            reflex_player_ids.append(random.choice(werewolf_ids))
        if len(villager_ids) > 0:
            reflex_player_ids.append(random.choice(villager_ids))
        
        if len(reflex_player_ids) < 4:
            self.logger.warning(f"Only {len(reflex_player_ids)} players are reflexable.")
            if num_processes > len(reflex_player_ids):
                self.logger.warning(f"Reducing the number of processes used to {len(reflex_player_ids)}")
                num_processes = len(reflex_player_ids)
        
        if num_processes > 4:
            self.logger.warning(f"Maximum processes allowed for reflexing is 4, but {num_processes} is required.")
            self.logger.warning("Only using 4 processes for reflex.")
            num_processes = 4
        
        with multiprocessing.Pool(num_processes) as pool:
            successes = pool.map(self.reflex_for_player, reflex_player_ids)
        success_num = sum([1 if success else 0 for success in successes])
        if success_num == len(reflex_player_ids):
            self.logger.info(f"Reflex succeeded for all {success_num} players.")
        else:
            self.logger.warning(f"Reflex failed for {len(reflex_player_ids) - success_num} players!")
    
    def act(self, player_id, actions):
        return self.all_players[player_id]._act(available_actions = [actions] if isinstance(actions, str) else actions)
    
    def update_data(self):
        '''
            mqw 20241005 14:08 note:
            I have added draft to data
            player_draft_dict = self.latest_drafts
            It has at least two keys:
                "player_id": player_id
                "cur_action" The current action
            We should first recognize the 'cur_action' key. If it is None then there's nothing else. Else there are two cases:
                "cur_action": "vote": 
                    dictionary for vote drafts. it has the following items:
                    vote_proposal: list[int], list of proposals of votes. Currently len = 2.
                    proposal_and_imaginations: list[str], list of imagination. See core/player.py/Player/_vote
                    proposal_chosen_and_reasons: str, description of chosen proposal. See core/player.py/Player/_vote and core/players/prompts/common/vote_threeStage_choose.txt for format of it.
                "cur_action": "speak": 
                    dictionary for speak drafts. it has the following items:
                    speak_proposal: list[str], list of proposals of speak summary. Currently len = 2.
                    proposal_and_imaginations: list[str], list of imagination after speech. See core/player.py/Player/_speak_multiagent
                    final_speech: str, final speech.
                    proposal_id: int, final chosen proposal id
        '''
        if self.game_status["winner"] is not None:
            is_game_end = True
        else:
            is_game_end = False
        self.logger.debug(f"actions: {self.latest_actions}")
        cur_actions = [self.latest_drafts[i]['cur_action'] if self.latest_drafts[i] is not None else None for i in range(len(self.latest_drafts))]
        self.logger.debug(f"cur_actions in drafts: {cur_actions}")
        self.logger.debug(f"current game status: {self.game_status}")
        
        self.data.add_edge_and_node(
            events = self.temp_events,
            actions = self.latest_actions,
            state = self.get_state(),
            drafts = deepcopy(self.latest_drafts),
            is_game_end = is_game_end
        )
        self.temp_events = []
    
    def update_all_hstates(self, add_to_data = True):
        for player in self.all_players:
            player.update_hstate(self.event_book)
        self.logger.info("All hidden states updated successfully")
        if add_to_data:
            self.update_data()
        if self.log_hstate:
            for i in range(self.player_num):
                emph_print(f"Player {i}'s hstate is:")
                print(str(self.all_players[i].hstate))
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
        # self.data_path = path
        with open(path, "rb") as f:
            self.data: DataTree = pickle.load(f)
        print(f"loading data from {path}")
        recover_info = self.data.go_to_latest()
        info = recover_info["state"]
        prev_game_status = info["global_info"]["game_status"]
        events = recover_info["events"]
        print(f"game status to recover: {prev_game_status}")
        self.load_state(info, events)
        print(f"current game status: {self.game_status}")
        self.temp_events = []
        
    def end(self):
        self.logger.info("Game ended")
        if len(self.temp_events) != 0:
            self.update_all_hstates(add_to_data=True)
        self.store_data(self.data_path)
        try:
            self.save_game_record()
        except Exception as e:
            print("Failed to save game record.")
            print(f"Error: {e}")
        if self.train:
            #! temparirly random
            for i in range(self.retry_num):
                self.random_retry_one_node(retry_steps = 1)
                self.logger.info(f"Randomly retried {i+1} nodes for 1 step")
            self.store_data(self.data_path)
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
    
    def postprocess_step(self, actions, dones, info = None) -> bool: #return if the game ends
        self.latest_actions = deepcopy(actions)
        def get_latest_draft(draft_dict):
            for key in draft_dict.keys():
                if len(draft_dict[key]) == 0:
                    draft_dict[key] = None
                else:
                    draft_dict[key] = draft_dict[key][-1]
            return draft_dict
        for player_id in range(self.player_num):
            self.latest_drafts[player_id] = {
                "cur_action": actions[player_id].get("action") if actions[player_id] is not None else None,
                "player_id": player_id
            }
            if actions[player_id] is None or actions[player_id].get("action") is None:
                continue
            else:
                current_player_draft_dict = deepcopy(self.all_players[player_id].draft_dict)
                current_player_latest_draft_dict = get_latest_draft(current_player_draft_dict)
                if actions[player_id]["action"] == "vote":
                    self.latest_drafts[player_id].update(current_player_latest_draft_dict["vote"])
                elif actions[player_id]["action"] == "speak":
                    self.latest_drafts[player_id].update(current_player_latest_draft_dict["speak"])
                else:
                    continue
                    
        if info is not None:
            self.logger.info(str(info))
        if all(dones):
            return True
        self.update_all_hstates(add_to_data=True)
        return False

    def sim_game_for_reflex_players(self): #main simulation function
        if self.game_status["winner"] is not None:
            self.temp_events = []
            self.end()
            self.logger.info("Game simulated successfully")
            return
        if len(self.temp_events) != 0:
            #Not updated data yet.
            self.update_all_hstates(add_to_data=True)
        self.logger.info("Simulating games for reflex players")
            
        avail_actions = self.get_available_actions()
        self.add_event({"event": "begin_round", "content": {"round": self.game_status['cur_round']+1}})
        # self.update_all_hstates(add_to_data=True)
        while True:
            if self.game_status["cur_stage"] == "day" and self.game_status["next_speaking_player"] == self.game_status["start_speaking_player"]:
                os.makedirs("temp_data", exist_ok=True)
                self.store_data(f"temp_data/game_{self.id}_round_{self.game_status['cur_round']}_day_start.pkl")
            actions = self.get_actions_reflex(avail_actions)
            # self.logger.info(f"actions: {actions}")
            obs, state, rewards, dones, info, avail_actions = self.step(actions)
            if self.postprocess_step(actions, dones, info):
                break
             
        self.logger.info("Game simulated successfully")
        
    def retry_for_reflex_players(self, node_id: int, retry_steps: int = 1) -> bool: #return if it succeeds
        #TODO make it suitable for night actions?
        drafts = self.data.get_next_drafts(node_id)
        #debug
        print(self.data.nodes[node_id].state["global_info"]["game_status"])
        if drafts is None:
            return False
        for i in range(self.player_num):
            self.logger.debug(f"player: {i}, cur_action: {drafts[i]['cur_action']}")
        avail_drafts = []
        for draft in drafts:
            if draft["cur_action"] is None or draft["cur_action"] not in ["speak", "vote"]:
                continue
            else:
                self.logger.debug(f"next action is: {draft['cur_action']}")
                avail_drafts.append(draft)
        if len(avail_drafts) == 0:
            return False
        self.backtrace(targ_id=node_id)
        actions = [None] * self.player_num
        for draft in avail_drafts:
            if draft["cur_action"] == "speak":
                self.logger.debug("Speak other proposal!")
                player_id = draft["player_id"]
                speak_action = self.all_players[player_id]._speak_with_other_proposal(draft)
                actions[player_id] = speak_action
                self.logger.debug(f"player: {player_id}'s speak action: {speak_action}")
            elif draft["cur_action"] == "vote":
                self.logger.debug("Vote other proposal!")
                player_id = draft["player_id"]
                vote_action = self.all_players[player_id]._vote_with_other_proposal(draft)
                actions[player_id] = vote_action
                self.logger.debug(f"player: {player_id}'s vote action: {vote_action}")
        obs, state, rewards, dones, info, avail_actions = self.step(actions)
        self.logger.debug("Stepped!")
        if self.postprocess_step(actions, dones, info):
            return True
        if retry_steps == 1:
            self.logger.debug("Yeahhh")
            return True
        for retry_step in range(retry_steps - 1):
            actions = self.get_actions_reflex(avail_actions)
            # self.logger.info(f"actions: {actions}")
            obs, state, rewards, dones, info, avail_actions = self.step(actions)
            if self.postprocess_step(actions, dones, info):
                self.logger.info(f"Game ends after {retry_step+2} steps starting from the retry steps")
                return True
        return True
    
    def random_retry_one_node(self, retry_steps = 1):
        MAX_ATTEMPT = 10
        for i in range(MAX_ATTEMPT):
            nid = random.randint(1, len(self.data.nodes) - 2)
            try:
                if self.retry_for_reflex_players(nid, retry_steps):
                    print("Retry succeeded")
                    return
            except Exception as e:
                self.logger.warning(f"Encountered error {e} while retrying; skipped.")
        print(f"Retry failed after {MAX_ATTEMPT} attempts")
            
        
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
    
    def backtrace(self, targ_id = None, back_steps = 1):
        if targ_id is None:
            targ_id = self.data.get_backtrace_id(back_steps)
        self.logger.debug(f"target id: {targ_id}")
        recover_info = self.data.backtrace(targ_id)
        info = recover_info["state"]
        prev_game_status = info["global_info"]["game_status"]
        events = recover_info["events"]
        print(f"current game status: {self.game_status}")
        print(f"game status to recover: {prev_game_status}")
        self.load_state(info, events)
        print(f"current game status: {self.game_status}")
        

    