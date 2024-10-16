from collections import defaultdict
import json

def count_integer_appearances(data):
    total_counts = defaultdict(int)
    position_counts = [defaultdict(int) for _ in range(4)]  # One defaultdict for each position

    for sublist in data:
        for i, value in enumerate(sublist):
            total_counts[value] += 1
            position_counts[i][value] += 1

    # Convert defaultdicts to regular dictionaries for clearer output
    total_counts = dict(total_counts)
    position_counts = [dict(pos_count) for pos_count in position_counts]

    return total_counts, position_counts

json_path = "/home/yifeizuo/sjz/ablation/MafiaGPT_RL/cocs_ablation_1/idx_to_version_list.json"
with open(json_path, "rb") as f:
    data = json.load(f)

total_counts, position_counts = count_integer_appearances(data)

print("Total counts:", total_counts)
print("Position counts:", position_counts)
