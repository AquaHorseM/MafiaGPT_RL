import shutil
import os

base_dir = "core/players/prompts"
backup_dir = "core/players/prompts_backup"
roles = ["werewolf", "seer", "villager", "medic"]
for role in roles:
    role_dir = os.path.join(base_dir, role)
    if os.exists(os.path.join(role_dir, "reflex_note.py")):
        shutil.copy("refresh_notes.py", role_dir)