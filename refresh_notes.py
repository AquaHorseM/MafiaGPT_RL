import shutil
import os
from argparse import ArgumentParser

def load_from_backup(role: str, note_type: str, version: int, from_prev = False) -> None:
    """
    Loads the initial version of a note to the current note.
    
    Parameters:
    role (str): The role of the note.
    note_type (str): The type of the note.
    """
    if from_prev:
        init_note_path = f"core/notes_fixed_version/notes_v{version-1}/{role}/{role}_reflex_note_{note_type}.txt"
    else:
        init_note_path = f"core/notes_fixed_version/notes_v{version}/{role}/{role}_reflex_note_{note_type}.txt"
    current_note_path = f"core/notes_v{version}/{role}/{role}_reflex_note_{note_type}.txt"
    
    # Ensure the initial note exists before copying
    if os.path.exists(init_note_path):
        os.makedirs(f"core/notes_v{version}/{role}", exist_ok=True)
        shutil.copyfile(init_note_path, current_note_path)
        print(f"Initial note for {role}'s {note_type} has been loaded into the current note.")
    else:
        print(f"Initial note does not exist at {init_note_path}. No changes made.")
    
parser = ArgumentParser()
parser.add_argument("--from-prev", default=False, action="store_true")
parser.add_argument("--version", type=int, default=1)

roles = ["werewolf", "medic", "seer", "villager"]
note_types = ["belief", "policy"]

if __name__ == "__main__":
    args = parser.parse_args()
    for role in roles:
        for note_type in note_types:
            load_from_backup(role, note_type, args.version, args.from_prev)