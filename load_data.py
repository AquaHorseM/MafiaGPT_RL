import pickle
from core.event import Event
# Load data from file
data_path = "data/game_0_data.pkl"
with open(data_path, "rb") as f:
    data = pickle.load(f)
data.show_info()