import shutil
import os

def load_from_init(role: str, note_type: str) -> None:
    """
    Loads the initial version of a note to the current note.
    
    Parameters:
    role (str): The role of the note.
    note_type (str): The type of the note.
    """
    init_note_path = f"core/notes_v0/{role}/{role}_reflex_note_{note_type}.txt"
    current_note_path = f"core/notes_v1/{role}/{role}_reflex_note_{note_type}.txt"
    
    # Ensure the initial note exists before copying
    if os.path.exists(init_note_path):
        os.makedirs(f"core/notes_v1/{role}", exist_ok=True)
        shutil.copyfile(init_note_path, current_note_path)
        print(f"Initial note for {role}'s {note_type} has been loaded into the current note.")
    else:
        print(f"Initial note does not exist at {init_note_path}. No changes made.")


roles = ["werewolf", "medic", "seer", "villager"]
note_types = ["belief", "policy"]

if __name__ == "__main__":
    for role in roles:
        for note_type in note_types:
            load_from_init(role, note_type)