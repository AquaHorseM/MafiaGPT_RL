import pickle
from core.event import Event
from core.data import DataTree
# Load data from file

data_path = "data/game_0_data.pkl"
with open(data_path, "rb") as f:
    data: DataTree = pickle.load(f)
data.show_info(interactive = True)