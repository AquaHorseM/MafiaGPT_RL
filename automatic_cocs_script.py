import os
from argparse import ArgumentParser
from automatic_coc_utils import make_battle_dir_and_run_one_battle
import multiprocessing
import json

def one_battle(current_args_list):
    make_battle_dir_and_run_one_battle(*current_args_list)


import itertools
from collections import defaultdict

def generate_version_tuples():
    # All possible 4-element combinations of numbers 0-9 without repetition
    all_tuples = list(itertools.permutations(range(10), 4))
    
    # We need exactly 50 unique tuples
    selected_tuples = []
    count_by_position = [defaultdict(int) for _ in range(4)]
    
    # Hash to index mapping to ensure reproducibility
    hash_to_index = {hash(tup): tup for tup in all_tuples}

    # Sorting hashes to keep the selection order consistent
    sorted_hashes = sorted(hash_to_index.keys())

    for h in sorted_hashes:
        tuple_candidate = hash_to_index[h]
        # Check if this tuple can be used without exceeding the position count limits
        if len(selected_tuples) < 50:
            valid = True
            for i in range(4):
                if count_by_position[i][tuple_candidate[i]] >= 5:
                    valid = False
                    break
            if valid:
                selected_tuples.append(tuple_candidate)
                for i in range(4):
                    count_by_position[i][tuple_candidate[i]] += 1

    return selected_tuples

# Precomputed tuples based on the hash approach
precomputed_tuples = generate_version_tuples()

def idx_to_version_tuple(idx):
    # Return the tuple corresponding to the given index
    if 0 <= idx < 50:
        return precomputed_tuples[idx]
    else:
        raise ValueError("Index out of allowed range (0-49).")








if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('--war_folder', type=str, default = './clash_of_clanS_shijz_14')
    parser.add_argument('--clans_notes_folder', type = str, default = './shijz_test_14/notes')
    parser.add_argument('--clans_tags', type=str, default='')
    parser.add_argument('--num_games_per_battle', type=int, default = 1)
    parser.add_argument('--num_process_per_battle', type=int, default = 1)
    parser.add_argument('--num_battle_parallel', type=int, default = 5)
    parser.add_argument('--num_battles_in_total', type=int, default = 50)
    
    args = parser.parse_args()
    if args.clans_tags == '':
        args.clans_tags = ['notes_v{}'.format(i) for i in range(10)]
    assert len(args.clans_tags) == 10
    
    assert args.num_battles_in_total == 50
    
    args_list = []
    
    idx_to_version_list = list()
    
    for idx in range(args.num_battles_in_total):
        version_tuple = idx_to_version_tuple(idx)
        idx_to_version_list.append(version_tuple)
        notes_folders = [os.path.join(args.clans_notes_folder, 'notes_v'+str(v)) for v in version_tuple]
        tags = [args.clans_tags[v] for v in version_tuple]
        args_list.append(('battle_'+str(idx), args.war_folder, *notes_folders, *tags, args.num_games_per_battle, args.num_process_per_battle))
    
    json.dump(idx_to_version_list, open(os.path.join(args.war_folder, 'idx_to_version_list.json'), 'w'), indent=4)
    # json.dump(idx_to_version_list, open('idx_to_version_list.json', 'w'), indent=4)
    
        
    with multiprocessing.Pool(args.num_battle_parallel) as p:
        p.map(one_battle, args_list)
