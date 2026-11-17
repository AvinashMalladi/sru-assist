import os
import shutil
import zipfile
from datetime import datetime

def create_backup():
    dest_dir = r"C:\Users\GOPAL\OneDrive\Desktop\Agentic AI"
    old_dir = os.path.join(dest_dir, "old backup")
    os.makedirs(dest_dir, exist_ok=True)
    os.makedirs(old_dir, exist_ok=True)

    # Automatically archive any existing backups to 'old backup'
    for item in os.listdir(dest_dir):
        if item.startswith("sru-chatbot-backup_") and item.endswith(".zip"):
            old_path = os.path.join(dest_dir, item)
            target_path = os.path.join(old_dir, item)
            print(f"Archiving previous backup: {item} -> old backup/")
            shutil.move(old_path, target_path)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_name = f"sru-chatbot-backup_{timestamp}.zip"
    zip_path = os.path.join(dest_dir, zip_name)
    
    src_dir = r"C:\Users\GOPAL\Agentic AI\sru-chatbot"
    
    # Exclude list
    exclude_dirs = {".git", "__pycache__", "venv", ".venv", ".idea", ".vscode", ".pytest_cache"}
    exclude_files = {".env"}
    
    print(f"Creating latest backup: {zip_path}...")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(src_dir):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            for file in files:
                if file in exclude_files:
                    continue
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, src_dir)
                zipf.write(full_path, rel_path)
                
    size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    print(f"Backup created successfully: {zip_name} ({size_mb:.2f} MB)")
    return zip_path

if __name__ == "__main__":
    create_backup()
