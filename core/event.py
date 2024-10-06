import copy, json
class Event:
    def __init__(self, init_dict):
        self.event = init_dict["event"]
        self.content = copy.deepcopy(init_dict["content"]) if "content" in init_dict else None
        self.visible = copy.deepcopy(init_dict["visible"]) if "visible" in init_dict else "all"
    
    def __str__(self) -> str:
        s = "Event: "
        if self.event == "set_player":
            s += f"Player {self.content['id']} is set as {self.content['role']} with player type {self.content['player_type']}"
        elif self.event == "heal":
            s += f"Player {self.content['player']} heals player {self.content['target']}. His reason is: {self.content['reason']}"
        elif self.event == "inquiry":
            s += f"Player {self.content['player']} inquires about player {self.content['target']}. The result is that the target {'is' if self.content['is_werewolf'] else 'is not'} a werewolf. His reason is: {self.content['reason']}"
        elif self.event == "advicing":
            s += f"Player {self.content['player']} advises targeting player {self.content['target']} for elimination. His reason is: {self.content['reason']}"
        elif self.event == "kill":
            s += f"System randomly chooses from the werewolves' suggestions. Player {self.content['target']} is killed."  
        elif self.event == "speak":
            s += f"Player {self.content['player']} says: '{self.content['speech']}'"  
        elif self.event == "speak_summarized":
            s += f"Player {self.content['player']} saying summarized as : '{self.content['speech_summary']}'"
        elif self.event == "vote":
            s += f"Player {self.content['player']} votes for player {self.content['target']}. His reason is: {self.content['reason']}"
        elif self.event == "vote_out":
            s += f"Player {self.content['player']} is voted out with the highest vote."
        elif self.event == "die":
            s += f"Player {self.content['player']} died."
        elif self.event == "end":
            s += f"Game ends. Winners are {self.content['winner']}."
        elif self.event == "no_death":
            s += f"Nobody died last night. A peaceful night."
        elif self.event == "day_start":
            s += "Day starts."
        elif self.event == "night_start":
            s += "Night starts."
        elif self.event == "vote_start":
            s += "Voting started."
        elif self.event == "start_speaking":
            s += f"System randomly chooses player {self.content['player']} to start speaking this round."
        elif self.event == "begin_round":
            s += f"Round {self.content['round']} begins."
        elif self.event == "start_game":
            s += "Game starts."
        else:
            raise ValueError(f'Event type {self.event} not recognized.')
        return s
        
    def log(self):
        s = str(self)
        s = s[:-1] + ", visible:" + str(self.visible) + "}"
        return s
    
    def to_dict(self):
        """Convert the Event object to a dictionary that can be serialized."""
        return {
            "event": self.event,
            "content": self.content,  # Assuming content is already serializable
            "visible": self.visible
        }

class EventBook:
    def __init__(self):
        self.events = {}
        self.tick = 0
    
    def add_event(self, events):
        if not isinstance(events, list):
            if isinstance(events, dict):
                self.events[self.tick] = [Event(events)]
            else:
                assert isinstance(events, Event), "event must be a dict or an instance of Event"
                self.events[self.tick] = [events]
        else:
            assert all(isinstance(event, Event) for event in events), "all elements of events must be instances of Event"
            self.events[self.tick] = events
        self.tick += 1
        
    def filter(self, start_tick = None, end_tick = None, id = None, labels = None, types = None):
        def match(event: Event, event_tick, start_tick, end_tick, id, labels, types):
            if start_tick is not None and event_tick < start_tick:
                return False
            if end_tick is not None and event_tick >= end_tick:
                return False
            if types is not None:
                if isinstance(types, str):
                    types = [types]
                if event.event not in types:
                    return False
            if isinstance(event.visible, int):
                if id is None or event.visible != id:
                    return False
            elif isinstance(event.visible, str):
                if labels is None or event.visible not in labels:
                    return False
            elif isinstance(event.visible, list):
                if labels is None or all(label not in event.visible for label in labels):
                    return False
            return True
        return [event for tick, events in self.events.items() for event in events if match(event, tick, start_tick, end_tick, id, labels, types)]
    
    def backtrace(self, back_steps = 1):
        for i in range(back_steps):
            self.events.pop(self.tick, None)
            self.tick -= 1
                
    def __str__(self) -> str:
        s = ""
        for tick, events in self.events.items():
            for event in events:
                s += str(event) + "\n"
        return s