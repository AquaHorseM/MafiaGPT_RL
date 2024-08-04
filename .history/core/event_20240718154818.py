import copy
class Event:
    def __init__(self, init_dict):
        self.event = init_dict["event"]
        self.content = copy.deepcopy(init_dict["content"])
        self.visible = copy.deepcopy(init_dict["visible"]) if "visible" in init_dict else "all"
    
    def __str__(self) -> str:
        s = "{Event type:" + self.event
        for key, value in self.content.items():
            s += ", " + key + ":" + str(value)
        

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
        def match(event: Event, start_tick, end_tick, id, labels, types):
            if start_tick is not None and event.tick < start_tick:
                return False
            if end_tick is not None and event.tick >= end_tick:
                return False
            if id is not None and event.id != id:
                return False
            if labels is not None and event.labels not in labels:
                return False
            if types is not None and event.type not in types:
                return False
            return True