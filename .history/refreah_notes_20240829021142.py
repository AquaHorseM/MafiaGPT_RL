import shutil
import os

base_dir = "core/players/prompts"
backup_dir = "core/players/notes_backup"
os.makedirs(backup_dir, exist_ok=True)
roles = ["werewolf", "seer", "villager", "medic"]
for role in roles:
    role_dir = os.path.join(base_dir, role)
    if os.path.exists(os.path.join(role_dir, "reflex_note.txt")):
        shutil.copy("refresh_notes.txt", os.path.join(backup_dir, f"{role}_reflex_note.txt"))
        os.remove(os.path.join(role_dir, "reflex_note.txt"))
        shutil.copy(os.path.join(role_dir, "reflex_note_backup.txt"), os.path.join(role_dir, "reflex_note.txt"))
    