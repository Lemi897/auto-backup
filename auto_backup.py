#!/usr/bin/env python3

import os
import shutil
import zipfile
from datetime import datetime, timedelta
import schedule
import time
from pathlib import Path

# Terminal color codes
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

# Configuration
BACKUP_DIR = os.path.expanduser("~/automation-projects/backups")
LOG_DIR = os.path.join(BACKUP_DIR, "logs")
MAX_BACKUP_AGE_DAYS = 30  # auto-delete backups older than this

os.makedirs(BACKUP_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

def log_backup(message):
    log_file = os.path.join(LOG_DIR, f"backup_log_{datetime.now().strftime('%Y-%m-%d')}.txt")
    with open(log_file, "a") as f:
        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")

def backup_folder(source_folder, file_types=None, compress=False):
    if not os.path.exists(source_folder):
        print(f"{Colors.FAIL}Source folder does not exist: {source_folder}{Colors.ENDC}")
        return

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_name = f"backup_{timestamp}"
    backup_path = os.path.join(BACKUP_DIR, backup_name)

    os.makedirs(backup_path, exist_ok=True)
    files_copied = 0

    print(f"{Colors.OKBLUE}Starting backup from {source_folder}...{Colors.ENDC}")

    for root, dirs, files in os.walk(source_folder):
        for file in files:
            if file_types and not any(file.endswith(ft) for ft in file_types):
                continue

            src_file = os.path.join(root, file)
            rel_path = os.path.relpath(root, source_folder)
            dest_folder = os.path.join(backup_path, rel_path)
            os.makedirs(dest_folder, exist_ok=True)
            shutil.copy2(src_file, os.path.join(dest_folder, file))
            files_copied += 1

    # Optional compression
    if compress:
        zip_file = backup_path + ".zip"
        with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(backup_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, backup_path)
                    zipf.write(file_path, arcname)
        shutil.rmtree(backup_path)  # remove uncompressed folder
        backup_path = zip_file

    print(f"{Colors.OKGREEN}Backup completed! {files_copied} files copied to {backup_path}{Colors.ENDC}")
    log_backup(f"Backup completed: {backup_path}, {files_copied} files")

def cleanup_old_backups():
    print(f"{Colors.WARNING}Cleaning up backups older than {MAX_BACKUP_AGE_DAYS} days...{Colors.ENDC}")
    now = datetime.now()
    deleted_files = 0
    for item in Path(BACKUP_DIR).glob("*"):
        if item.is_file() or item.is_dir():
            mtime = datetime.fromtimestamp(item.stat().st_mtime)
            if now - mtime > timedelta(days=MAX_BACKUP_AGE_DAYS):
                if item.is_file():
                    item.unlink()
                else:
                    shutil.rmtree(item)
                deleted_files += 1
    if deleted_files:
        print(f"{Colors.OKGREEN}Deleted {deleted_files} old backups.{Colors.ENDC}")
        log_backup(f"Deleted {deleted_files} old backups")
    else:
        print(f"{Colors.OKBLUE}No old backups to delete.{Colors.ENDC}")

def menu():
    while True:
        print(f"""
{Colors.HEADER}=== Auto Backup System ==={Colors.ENDC}
1. Backup a folder
2. Restore a backup (copy files back)
3. View backup logs
4. Cleanup old backups
5. Schedule daily backup
6. Exit
""")
        choice = input("Enter your choice: ").strip()
        if choice == "1":
            src = input("Enter folder to backup: ").strip()
            ft_input = input("Optional: enter file types separated by comma (e.g., .mp4,.pdf) or leave blank: ").strip()
            file_types = [ft.strip() for ft in ft_input.split(",")] if ft_input else None
            compress = input("Compress backup? (y/n): ").strip().lower() == "y"
            backup_folder(src, file_types=file_types, compress=compress)
        elif choice == "2":
            backup_name = input("Enter backup folder or zip name to restore: ").strip()
            restore_path = input("Enter destination folder: ").strip()
            full_path = os.path.join(BACKUP_DIR, backup_name)
            if os.path.exists(full_path):
                if full_path.endswith(".zip"):
                    with zipfile.ZipFile(full_path, 'r') as zipf:
                        zipf.extractall(restore_path)
                else:
                    shutil.copytree(full_path, restore_path, dirs_exist_ok=True)
                print(f"{Colors.OKGREEN}Restore completed!{Colors.ENDC}")
                log_backup(f"Restored {full_path} to {restore_path}")
            else:
                print(f"{Colors.FAIL}Backup not found: {full_path}{Colors.ENDC}")
        elif choice == "3":
            log_files = sorted(Path(LOG_DIR).glob("*.txt"))
            if not log_files:
                print(f"{Colors.WARNING}No logs found.{Colors.ENDC}")
            else:
                for lf in log_files:
                    print(lf)
        elif choice == "4":
            cleanup_old_backups()
        elif choice == "5":
            src = input("Enter folder to backup daily: ").strip()
            ft_input = input("Optional: enter file types separated by comma or leave blank: ").strip()
            file_types = [ft.strip() for ft in ft_input.split(",")] if ft_input else None
            compress = input("Compress backup? (y/n): ").strip().lower() == "y"
            time_str = input("Enter backup time daily (HH:MM, 24h format): ").strip()

            def scheduled_task():
                backup_folder(src, file_types=file_types, compress=compress)
                cleanup_old_backups()

            schedule.every().day.at(time_str).do(scheduled_task)
            print(f"{Colors.OKGREEN}Scheduled daily backup at {time_str}. Press Ctrl+C to stop.{Colors.ENDC}")
            try:
                while True:
                    schedule.run_pending()
                    time.sleep(30)
            except KeyboardInterrupt:
                print(f"{Colors.WARNING}\nScheduler stopped.{Colors.ENDC}")
        elif choice == "6":
            print(f"{Colors.OKBLUE}Exiting...{Colors.ENDC}")
            break
        else:
            print(f"{Colors.FAIL}Invalid choice!{Colors.ENDC}")

if __name__ == "__main__":
    menu()
