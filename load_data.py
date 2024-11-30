import pickle
from core.event import Event
from core.data import DataTree
# Load data from file

data_path = "records/game_121_data.pkl"
with open(data_path, "rb") as f:
    data: DataTree = pickle.load(f)
print(data)