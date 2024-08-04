import copy
class Event:
    def __init__(self, init_dict):
        self.event = init_dict["event"]
        self.content = copy.deepcopy(init_dict["content"])
    
    def __str__(self) -> str:
        s = "{Event type:" + self.event
        for key, value in self.content.items():
            s += ", " + key + ":" + str(value)
        

class