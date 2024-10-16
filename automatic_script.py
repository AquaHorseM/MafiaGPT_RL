import os
import subprocess
import time
import json
from copy import deepcopy
import re
import shutil

from argparse import ArgumentParser

def copy_directory_with_prompt(source_dir, destination_dir):
    try:
        # Check if the destination directory already exists
        if os.path.exists(destination_dir):
            print("WARNING: The directory already exists. Deleting it.")
            user_input = 'yes' # input(f"The directory '{destination_dir}' already exists. Do you want to delete it and copy the new one? (yes/no): ")
            if user_input.lower() == 'yes':
                # Remove the existing destination directory
                shutil.rmtree(destination_dir)
                print(f"Deleted existing directory: {destination_dir}")
            else:
                print("Aborting the copy operation.")
                return

        # Copy the directory
        shutil.copytree(source_dir, destination_dir)
        print(f"Successfully copied {source_dir} to {destination_dir}")

    except Exception as e:
        print(f"Error occurred: {e}")
        
        
def get_largest_file_in_directory(directory):
    try:
        # Get the list of files in the directory
        files = os.listdir(directory)
        
        # Filter to include only files (not directories)
        files = [f for f in files if os.path.isfile(os.path.join(directory, f))]
        
        # Return the file with the largest dictionary order
        if files:
            largest_file = max(files)
            return os.path.join(directory, largest_file)
        else:
            return None  # No files in the directory
    except Exception as e:
        print(f"Error occurred: {e}")
        return None
    

def int_to_str(ver_int):
    if ver_int < 10:
        return '0'+str(ver_int)
    else:
        return str(ver_int)
    

def run_game(args,ver):
    config_dir = args.config_dir
    data_dir = os.path.join(args.data_dir, 'data_v'+str(ver))
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    try:
        result = subprocess.run(['python', 'run_new.py', 
                                 '--num_games', str(args.num_game_per_iter), 
                                 '--num_processes', str(args.num_processes), 
                                 '--config_path', os.path.join(config_dir,"game_config_v"+int_to_str(ver)+".json")], check=True)
    except subprocess.CalledProcessError as e:
        print("Error occurred while running version "+int_to_str(ver)+": {e}")

def create_game_config(args, ver):
    config_dir = args.config_dir
    current_config = os.path.join(config_dir,"game_config_v"+int_to_str(ver)+".json")
    into_config = os.path.join(config_dir,"game_config_v"+int_to_str(ver+1)+".json")
    current_dict = json.load(open(current_config))
    new_dict = deepcopy(current_dict)
    new_dict['data_folder'] = os.path.join(args.data_dir,'data_'+'v'+str(ver+1))
    for i in range(len(new_dict["players"])):
        org_dict = new_dict["players"][i]
        new_dict["players"][i]["reflex_note_belief_path"] = re.sub('v'+str(ver)+r'\b', 'v'+str(ver+1), org_dict["reflex_note_belief_path"])
        new_dict["players"][i]["reflex_note_policy_path"] = re.sub('v'+str(ver)+r'\b', 'v'+str(ver+1), org_dict["reflex_note_policy_path"])
        new_dict["players"][i]['player_tag'] = re.sub('v'+str(ver)+r'\b', 'v'+str(ver+1), org_dict['player_tag'])
    new_dict['input_txt_path'] = os.path.join(args.prompt_logging_dir, 'message_input_history_backup_v'+str(ver+1)+'.txt')
    new_dict['output_txt_path'] = os.path.join(args.prompt_logging_dir, 'message_output_history_backup_v'+str(ver+1)+'.txt')
    json.dump(new_dict, open(into_config,'w'), indent=4)
    
def copy_files(args, ver):
    notes_dir = args.notes_dir
    current_dir = os.path.join(notes_dir, 'notes_v' + str(ver))
    target_dir = os.path.join(notes_dir, 'notes_v'+str(ver+1))
    copy_directory_with_prompt(current_dir, target_dir)

def run_reflex(args, ver):
    
    config_dir = args.config_dir
    
    data_dir = os.path.join(args.data_dir, 'data_v'+str(ver))
    
    
    
    
    new_config_path = os.path.join(config_dir,"game_config_v"+int_to_str(ver+1)+".json")
    try:
        result = subprocess.run(['python', 'reflex_from_data.py', '--config_path', new_config_path, '--data-path', data_dir], check=True)
    except subprocess.CalledProcessError as e:
        print("Error occurred while reflexing version "+int_to_str(ver)+": {e}")

def one_iter(args, ver=0):
    if (not args.skip_zero) or (ver > 0):
        run_game(args,ver)
    time.sleep(1)
    create_game_config(args,ver)
    copy_files(args,ver)
    for _ in range(args.reflex_per_data):
        time.sleep(1)
        run_reflex(args,ver)

def main_loop(args):
    MAX_ITER = args.max_iter
    for ver in range(0,MAX_ITER):
        one_iter(args,ver)
        




if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('--max_iter', type=int, default=10)
    parser.add_argument('--master_dir',type=str,default='./shijz_21_baseline')
    # parser.add_argument('--data_dir', type=str, default='./shijz_test_15/data')
    # parser.add_argument('--config_dir', type=str, default='./shijz_test_15/configs')
    # parser.add_argument('--notes_dir', type=str, default='./shijz_test_15/notes')
    # parser.add_argument('--prompt_logging_dir', type=str, default='./shijz_test_15/prompt_logging')
    
    
    parser.add_argument('--data_dir', type=str, default='')
    parser.add_argument('--config_dir', type=str, default='')
    parser.add_argument('--notes_dir', type=str, default='')
    parser.add_argument('--prompt_logging_dir', type=str, default='')
    
    
    
    
    parser.add_argument('--num_game_per_iter', type=int, default=5)
    parser.add_argument('--num_processes', type=int, default=5)

    parser.add_argument('--reflex_per_data',type=int,default=1)
    parser.add_argument('--skip_zero', action='store_true')
    
    args = parser.parse_args()
    
    if args.data_dir == '':
        args.data_dir = os.path.join(args.master_dir,'data')
    if args.config_dir == '':
        args.config_dir = os.path.join(args.master_dir,'configs')
    if args.notes_dir == '':
        args.notes_dir = os.path.join(args.master_dir,'notes')
    if args.prompt_logging_dir == '':
        args.prompt_logging_dir = os.path.join(args.master_dir,'prompt_logging')
    
    
    main_loop(args)