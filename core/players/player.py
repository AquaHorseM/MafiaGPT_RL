import os
import random
import numpy as np
from copy import deepcopy
from core.event import EventBook
from core.players.utils import get_response
import re, pickle

from core.players.utils import parse_data, parse_reflex_note, parse_reflex_actions, get_target_from_response
        
class Player:
    class HiddenState:
        def __init__(self, player_num, role_mapping):
            roles_num = len(role_mapping)
            self.beliefs = np.ones((player_num, player_num, roles_num)) / roles_num
            self.player_num = player_num
            self.roles_num = roles_num
            self.role_mapping = role_mapping
            self.inverse_role_mapping = {v: k for k, v in role_mapping.items()}
        
        def prob_approx(self, prob):
            #approximate the probability to 0.05
            return round(prob * 20) / 20
        
        def __str__(self) -> str:
            s = ""
            for i in range(self.player_num):
                s += f"player {i} is {self.inverse_role_mapping[np.argmax(self.beliefs[i][i])]} with probability {self.prob_approx(np.max(self.beliefs[i][i]))}\n"
            for i in range(self.player_num):
                f = 0
                for j in range(self.player_num):
                    if j == i:
                        continue
                    k = np.argmax(self.beliefs[i][j])
                    if self.beliefs[i][j][k] >= 0.3: #! threshold
                        if f == 0:
                            s += "*********\n"
                            s += f"player {i} believes: \n"
                            f = 1
                        s += f"player {j} is {self.inverse_role_mapping[k]} with probability {self.prob_approx(self.beliefs[i][j][k])}\n"
            return s
            
        def str_to_tensor(self, belief_str, id):
            #assume the str is in the format "player i believes player j is role k with probability p \n ..."
            beliefs = np.ones((self.player_num, self.player_num, self.roles_num)) / self.roles_num
            cur_player_id = id
            for line in belief_str.split("\n"):
                if line == "":
                    continue
                belief_player_matches = re.search(r"player (\d+) believes", line)
                if belief_player_matches is not None:
                    cur_player_id = int(belief_player_matches.group(1))
                else:
                    assert cur_player_id is not None, "Invalid belief string"
                    self_role_matches = re.search(r"player (\d+) is (.*) with probability (\d+.\d+)", line)
                    if self_role_matches is not None:
                        try:
                            j = int(self_role_matches.group(1))
                            k = self.role_mapping[self_role_matches.group(2).strip()]
                            p = float(self_role_matches.group(3))
                            beliefs[cur_player_id][j][k] = p
                        except:
                            print(f"Invalid line: {line}")
                            continue
                    else:
                        print(f"Invalid line: {line}")
            return beliefs
        
        def update(self, beliefs, id, confidence = 0.2):
            if isinstance(beliefs, str):
                beliefs = self.str_to_tensor(beliefs, id)
            confidence = min(0.5, confidence) #DO NOT trust the new beliefs too much
            if beliefs is not None:
                self.beliefs = confidence * beliefs + (1 - confidence) * self.beliefs
            return
        
        def set_role(self, player_id, role): #Use it carefully.
            self.beliefs[player_id][player_id] = 0.0
            self.beliefs[player_id][player_id][role] = 1.0
            return
                
    
    def get_replacements(self):
        with open(self.reflex_note_path_belief, "r") as f:
            reflex_note_belief = f.read()
        with open(self.reflex_note_path_policy, "r") as f:
            reflex_note_policy = f.read()
        current_round = self.global_info["current_round"] if self.global_info.get("current_round") is not None else self.global_info["game_status"]["cur_round"]
        return {
            "{player_id}": str(self.id),
            "{player_num}": str(self.global_info["player_num"]),
            "{alive_players}": str(list(self.global_info["alive_players"])),
            "{dead_players}": str(self.global_info["dead_players"]) if len(self.global_info["dead_players"]) > 0 else "Nobody",
            "{current_round}": str(current_round + 1), #! notice the +1 here
            "{roles_mapping}": str(self.global_info["roles_mapping"]),
            "{role}": str(self.private_info["role"]),
            "{previous_votes}": str(self.global_info["previous_votes"]),
            "{reflex_note_belief}": str(reflex_note_belief),
            "{reflex_note_policy}": str(reflex_note_policy)
        }
            
                        
    def __init__(self, id, global_info, private_info, prompt_dir_path, common_prompt_dir = None, openai_client = None, reflex_note_path_belief=None, reflex_note_path_policy=None):
        self.is_alive = True
        self.id = id
        self.labels = ["all"]
        self.tick = 0
        self.event_book = EventBook()
        self.reflex_tuple = (None, None, None)
        self.prompt_dir_path = prompt_dir_path
        self.common_prompt_dir = common_prompt_dir
        self.openai_client = openai_client
        self.reflex_note_path_belief = reflex_note_path_belief if reflex_note_path_belief is not None else os.path.join(prompt_dir_path, "reflex_note_belief.txt")
        self.reflex_note_path_policy = reflex_note_path_policy if reflex_note_path_policy is not None else os.path.join(prompt_dir_path, "reflex_note_policy.txt")
        self.global_info = deepcopy(global_info)
        self.private_info = deepcopy(private_info)
        self.hidden_state = self.HiddenState(global_info["player_num"], global_info["roles_mapping"])

    def __str__(self):
        return f"Player {self.id}"
    
    def update_hidden_state(self, event_book: EventBook):
        if event_book.tick == self.tick:
            return
        self._update_hidden_state(self.filter_event_book(event_book))
        self.tick = event_book.tick
    
    def _act(self, available_actions = None): #return (action, target, reason)
        if len(available_actions) == 0:
            return (None, None, "No available actions.")
        else:
            action = random.choice(available_actions)
            target = random.choice(self.global_info["alive_players"])
            reason = "I am the baseline player and I do things randomly."
            return (action, target, reason)
        
    def _vote(self):
        response = self.get_response("vote")
        vote = get_target_from_response(response)
        return vote, response
    
    def _get_speak_type(self):
        response = self.get_response("speak_type")
        assert isinstance(response, str), f"response is not a string: {response}"
        #Find the [type] in the response
        s_type = re.search(r"\[(.*?)\]", response).group(1).lower()
        s_type = s_type.strip().split(",") #split the types
        s_type = [s.strip() for s in s_type]
        return s_type
    
    def speak_with_type(self, s_type):
        replacements = self.get_replacements()
        replacements.update({
            "{speech_type}": str(s_type)
        })
        response = self.get_response("speak_with_type", replacements)
        return response
    
    def _speak(self): #TODO
        s_type = self._get_speak_type()
        replacements = self.get_replacements()
        response = self.speak_with_type(s_type, replacements)
        return response
            
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
    
    def get_role(self):
        return self.private_info["role"]
    
    def get_hidden_state(self):
        return self.hidden_state
    
    def get_gt_hiddenstate(self):
        return self.hidden_state.beliefs[self.id]
    
    def _update_hidden_state(self, events):
        #TODO
        self.event_book.add_event(events)        
        event_des = ""
        for event in events:
            event_des += str(event)
            event_des += "\n"
            
        replacements = self.get_replacements()
        replacements.update({"{event_des}": event_des})
        response = self.get_response("update_hidden_state")
        #first line is the confidence, the other lines are the beliefs
        try:
            conf = float(response.split("\n")[0])/10
            beliefs = "\n".join(response.split("\n")[1:])
        except ValueError:
            conf = 0.2 
            beliefs = response

        self.hidden_state.update(beliefs, self.id, confidence = conf)
        return

    '''
    The following functions are defined to be consistent with the baseline version.
    DO NOT use them in the future.
    '''
    
    def healing(self):
        return self._act(available_actions = ["heal"])
    
    def inquiry(self):
        return self._act(available_actions = ["see"])
    
    def kill(self):
        return self._act(available_actions = ["kill"])
    
    '''
    The following functions are defined for saving and loading checkpoints.
    '''
    
    def save_checkpoint(self, path):
        info = {
            "prompt_dir_path": self.prompt_dir_path,
            "private_info": self.private_info,
        }
        if path is not None:
            with open(path, 'wb') as file:
                pickle.dump(info, file)
        return info

    def reflex_single_pair(self, prev_hstate, prev_gt_hstate, new_events, next_hstate, pred_hstate, note_type = "belief"):
        replacements = self.get_replacements()
        replacements.update({
            "{prev_hstate}": str(prev_hstate),
            "{prev_gt_hstate}": str(prev_gt_hstate),
            "{new_events}": str(new_events),
            "{next_hstate}": str(next_hstate),
            "{pred_hstate}": str(pred_hstate),
        })
        if note_type == "belief":
            prompt_name = "reflex_belief"
        elif note_type == "policy":
            prompt_name = "reflex_policy"
        else:
            raise ValueError("Note type must be either 'belief' or 'policy'")
        response = self.get_response(prompt_name)
        self.update_note_from_response(response, note_type=note_type)
        return response
    
    def reflex(self, data, sample_num = 6, alpha = 1): #! sample num defined here
        reflex_data_belief = parse_data(data, self.id, alpha)
        reflex_data_belief = random.sample(reflex_data_belief, sample_num) if len(reflex_data_belief) > sample_num else reflex_data_belief
        reflex_data_policy = parse_data(data, self.id, alpha, check_event_include_player = True)
        reflex_data_policy = random.sample(reflex_data_policy, sample_num) if len(reflex_data_policy) > sample_num else reflex_data_policy
        print(f"there are {len(reflex_data_belief)} data for belief model and {len(reflex_data_policy)} data for policy model")
        reflex_data_policy = random.sample(reflex_data_policy, sample_num) if len(reflex_data_policy) > sample_num else reflex_data_policy
        print(f"player {self.id} is reflexing")
        for d in reflex_data_belief:
            prev_hstate, prev_gt_hstate, events, pred_hstate, next_hstate = d
            response = self.reflex_single_pair(prev_hstate, prev_gt_hstate, events, next_hstate, pred_hstate, note_type = "belief")
            self.update_note_from_response(response, note_type = "belief")
        print(f"player {self.id} has reflexed for belief model, now starting policy model reflexing")
        for d in reflex_data_policy:
            prev_hstate, prev_gt_hstate, events, pred_hstate, next_hstate = d
            response = self.reflex_single_pair(prev_hstate, prev_gt_hstate, events, next_hstate, pred_hstate, note_type = "policy")
            self.update_note_from_response(response, note_type = "policy")
        print(f"player {self.id} has reflexed for policy model. Now polishing the reflex notes.")
        self.polish_reflex_notes()
        return
    
    def polish_reflex_note(self, note_type = "belief"):
        if note_type == "belief":
            reflex_note_path = self.reflex_note_path_belief
        elif note_type == "policy":
            reflex_note_path = self.reflex_note_path_policy
        else:
            raise ValueError("Note type must be either 'belief' or 'policy'")
        replacements = self.get_replacements()
        replacements.update({
            "{reflex_note}": open(reflex_note_path, "r").read(),
            "{note_type}": note_type
        })
        response = self.get_response("polish_reflex_note")
        original_note = parse_reflex_note(open(reflex_note_path, "r").read())
        with open(reflex_note_path, "w") as f:
            for line in response.split("\n"):
                print(f"line: {line}")
                if len(line.strip()) <= 5:
                    continue
                try:
                    id, rule, vote = re.search(r"\[(\d+)\] \[(.*)\] \[(\d+)\]", line).groups()
                    id = int(id)
                    vote = int(vote)
                    f.write(f"[{id}] [{rule}] [{vote}]\n")
                except:
                    print(f"Unable to process line {line}")
        return
        
    def polish_reflex_notes(self):
        self.polish_reflex_note("belief")
        self.polish_reflex_note("policy")
        return
    
    
    def update_note_from_response(self, response, note_type = "belief"): #note type: ["belief", "policy"]
        if note_type == "belief":
            reflex_note_path = self.reflex_note_path_belief
        elif note_type == "policy":
            reflex_note_path = self.reflex_note_path_policy
        else:
            raise ValueError("Note type must be either 'belief' or 'policy'")
        with open(reflex_note_path, "r") as f:
            reflex_note = f.read()
        operations = parse_reflex_actions(response)
        reflex_note = parse_reflex_note(reflex_note)
        with open("debug.out", "a") as f:
            f.write(f"player {self.id} is updating the reflex note with operations: {operations}\n")
            f.write(f"previous reflex note: {reflex_note}\n")
        max_id = max(reflex_note.keys())
        for action in operations:
            operation, value1, value2 = action
            print(f"player {self.id} is updating the reflex note with operation {operation} {value1} {value2}")
            if operation == "UPVOTE": #value1 is the id, value2 should be None
                if reflex_note.get(value1) is None:
                    pass
                else:
                    reflex_note[value1][1] = min(10, reflex_note[value1][1] + 1)
            elif operation == "DOWNVOTE": #value1 is the id, value2 should be None
                if reflex_note.get(value1) is None:
                    pass
                else:
                    reflex_note[value1][1] -= 1
                    if reflex_note[value1][1] <= 1:
                        reflex_note.pop(value1)
            elif operation == "CREATE": #value1 is the new rule, value2 should be None
                reflex_note[max_id + 1] = [value1, 4]
                max_id += 1
            elif operation == "REPLACE": #value1 is the id, value2 is the new rule
                if reflex_note.get(value1) is None:
                    reflex_note[value1] = [value2, 4]
                else:
                    reflex_note[value1][0] = value2
        
        #Sort the rules by the votes and give them new ids
        
        reflex_note = dict(sorted(reflex_note.items(), key=lambda x: x[1][1], reverse=True))
        new_reflex_note = {}
        for i, key in enumerate(reflex_note.keys()):
            new_reflex_note[i] = reflex_note[key]
        reflex_note = deepcopy(new_reflex_note)
        with open("debug.out", "a") as f:
            f.write(f"new reflex note: {reflex_note}\n")
        
        with open(reflex_note_path, "w") as f:
            for key, value in reflex_note.items():
                f.write(f"[{key}] [{value[0]}] [{value[1]}]\n")
                
    def reflex_from_data_path(self, data_path):
        data = pickle.load(open(data_path, "rb"))
        self.reflex(data)
        return
    
    def reset(self):
        self.hidden_state = self.HiddenState(self.global_info["player_num"], self.global_info["roles_mapping"])
        
    def backtrace(self, back_step = 1, hstate = None, global_info = None, private_info = None):
        self.event_book.backtrace(back_step)
        if hstate is not None:
            self.hidden_state = deepcopy(hstate)
        if global_info is not None:
            self.global_info = deepcopy(global_info)
        if private_info is not None:
            self.private_info = deepcopy(private_info)
    
    def get_response(self, prompt_name, replacements = None):
        if replacements is None:
            replacements = self.get_replacements()
        return get_response(self.prompt_dir_path, self.common_prompt_dir, prompt_name, replacements)