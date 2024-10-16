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
    count = 0
    while True:
        # All possible 4-element combinations of numbers 0-5 without repetition
        all_tuples = list(itertools.permutations(range(6), 4))
        
        # We need exactly 40 unique tuples
        selected_tuples = []
        count_by_position = [defaultdict(int) for _ in range(4)]
        
        # Hash to index mapping to ensure reproducibility
        hash_to_index = {hash(tup+tuple([count])): tup for tup in all_tuples}

        # Sorting hashes to keep the selection order consistent
        sorted_hashes = sorted(hash_to_index.keys())

        for h in sorted_hashes:
            tuple_candidate = hash_to_index[h]
            # Check if this tuple can be used without exceeding the position count limits
            if len(selected_tuples) < 30:
                valid = True
                for i in range(4):
                    if count_by_position[i][tuple_candidate[i]] >= 5:
                        valid = False
                        break
                if valid:
                    selected_tuples.append(tuple_candidate)
                    for i in range(4):
                        count_by_position[i][tuple_candidate[i]] += 1
        if len(selected_tuples) == 30:
            return selected_tuples
        else:
            count += 1
            print("Failed to generate 30 unique tuples. Retrying...")


# Precomputed tuples based on the hash approach
precomputed_tuples = generate_version_tuples()
print(precomputed_tuples)
def idx_to_version_tuple(idx):
    # Return the tuple corresponding to the given index
    if 0 <= idx < 30:
        return precomputed_tuples[idx]
    else:
        raise ValueError("Index out of allowed range (0-29).")








if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('--war_folder', type=str, default = './cocs_ablation_1')
    parser.add_argument('--num_games_per_battle', type=int, default = 1)
    parser.add_argument('--num_process_per_battle', type=int, default = 1)
    parser.add_argument('--num_battle_parallel', type=int, default = 8)
    parser.add_argument('--num_battles_in_total', type=int, default = 30)
    
    # parse in a list of strings. not directly str type.
    parser.add_argument('--notes_dir_list', type = str, default = './shijz_test_14/notes/notes_v0,./shijz_test_14/notes/notes_v1,./shijz_test_14/notes/notes_v2,./shijz_test_14/notes/notes_v3,./shijz_test_14/notes/notes_v4,./shijz_test_14/notes/notes_v5,./shijz_test_14/notes/notes_v6,./shijz_test_14/notes/notes_v7,./shijz_test_14/notes/notes_v8,./shijz_test_14/notes/notes_v9')
    
    # parse in a list of strings. not directly str type.
    parser.add_argument('--clans_types',type=str, default = '')
    parser.add_argument('--clans_tags', type = str, default = 'notes_v0,notes_v1,notes_v2,notes_v3,notes_v4,notes_v5,notes_v6,notes_v7,notes_v8,notes_v9')
    
    
    args = parser.parse_args()
    
    args.notes_dir_list = args.notes_dir_list.split(',')
    args.clans_tags = args.clans_tags.split(',')
    args.clan_types = args.clans_types.split(',')
    
    
    
    assert len(args.clans_tags) == 6
    
    assert args.num_battles_in_total == 30
    
    args_list = []
    
    idx_to_version_list = list()
    
    for idx in range(args.num_battles_in_total):
        version_tuple = idx_to_version_tuple(idx)
        idx_to_version_list.append(version_tuple)
        notes_folders = [args.notes_dir_list[v] for v in version_tuple]
        player_id = ['villager', 'seer', 'medic', 'werewolf']
        notes_folders = [os.path.join(a,b) for (a,b) in zip(notes_folders, player_id)]
        tags = [args.clans_tags[v] for v in version_tuple]
        player_types = [args.clan_types[v] for v in version_tuple]
        args_list.append(('battle_'+str(idx), args.war_folder, *notes_folders, *tags, args.num_games_per_battle, args.num_process_per_battle,
                            *player_types,
        ))
    
    json.dump(idx_to_version_list, open(os.path.join(args.war_folder, 'idx_to_version_list.json'), 'w'), indent=4)
    # json.dump(idx_to_version_list, open('idx_to_version_list.json', 'w'), indent=4)
    
        
    with multiprocessing.Pool(args.num_battle_parallel) as p:
        p.map(one_battle, args_list)
