import pickle
from core.events import Event
# Load data from file
data_path = "records/game_0_data.pkl"
with open(data_path, "rb") as f:
    data = pickle.load(f)
for i in range(len(data)):
    print(data[i])