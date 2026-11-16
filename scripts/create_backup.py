import os
import zipfile
from datetime import datetime

def create_backup():
    dest_dir = r"C:\Users\GOPAL\OneDrive\Desktop\Agentic AI"
    os.makedirs(dest_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_name = f"sru-chatbot-backup_{timestamp}.zip"
    zip_path = os.path.join(dest_dir, zip_name)
    
    src_dir = r"C:\Users\GOPAL\Agentic AI\sru-chatbot"
    
    # Exclude list
    exclude_dirs = {".git", "__pycache__", "venv", ".idea", ".vscode"}
    exclude_files = {".env"}
    
    print(f"Creating backup: {zip_path}...")
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
