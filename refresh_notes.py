import os
import re
import shutil
import glob

# Define the source and destination patterns
source_pattern = r"core/notes_v1/([^/]+)/\1_reflex_note_([^/]+)_backup\.txt"
destination_pattern = r"core/notes_v1/{}/{}_reflex_note_{}.txt"
backup_folder = "note_v1_backups"

# Ensure the backup folder exists
os.makedirs(backup_folder, exist_ok=True)

# Find all backup files matching the pattern
backup_files = glob.glob("core/notes_v1/*/*_reflex_note_*_backup.txt")

# Determine the version number to use for all files
version = 1
while any(
    os.path.exists(
        os.path.join(backup_folder, f"{os.path.splitext(os.path.basename(destination_pattern.format(role, role, note_type)))[0]}_v{version}.txt")
    )
    for file_path in backup_files
    if (match := re.match(source_pattern, file_path))
    for role, note_type in [(match.group(1), match.group(2))]
):
    version += 1

# Use the determined version for all files
for file_path in backup_files:
    match = re.match(source_pattern, file_path)
    if match:
        role = match.group(1)
        note_type = match.group(2)
        destination_path = destination_pattern.format(role, role, note_type)
        
        # If the non-backup file exists, move it to the backup folder with the determined version number
        if os.path.exists(destination_path):
            base_name, ext = os.path.splitext(os.path.basename(destination_path))
            backup_name = f"{base_name}_v{version}{ext}"
            backup_path = os.path.join(backup_folder, backup_name)
            
            shutil.move(destination_path, backup_path)
            print(f"Moved existing file: {destination_path} -> {backup_path}")

        # Copy the backup file to the non-backup destination
        shutil.copy(file_path, destination_path)
        print(f"Copied: {file_path} -> {destination_path}")
