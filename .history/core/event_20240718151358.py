import copy
class Event:
    def __init__(self, init_dict):
        self.event = init_dict["event"]
        self.content = copy.deepcopy(init_dict["content"])
    
    def __str__(self) -> str:
        s = "{Event type:" + self.event
        for key, value in self.content.items():
            s += ", " + key + ":" + str(value)
        

class EventBook:
    def __init__(self):
        self.events = []
    
    def add_event(self, event):
        if isinstance(event, dict):
            self.events.append(Event(event))
        else:
            assert isinstance(event, Event), "event must be a dict or an instance of Event"
            self.events.append(event)