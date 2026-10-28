# -*- coding: utf-8 -*-
"""
Bot-Hosting / Pterodactyl Auto-Updater and Disk Cleaner.
Reclaims disk space by purging pip caches, removes duplicate data trees,
pulls latest code from GitHub origin/main, and boots bot.py.
"""
import os
import shutil
import subprocess
import sys

print("[Updater] Starting Phantom Regiment update & disk optimization...", flush=True)

base_dir = os.path.dirname(os.path.abspath(__file__))

# 1. Immediate disk reclaim: purge pip wheel cache & duplicate folders
clean_targets = [
    os.path.expanduser("~/.cache"),
    "/home/container/.cache",
    "/tmp",
    os.path.join(base_dir, ".cache"),
    os.path.join(base_dir, "data", "assets"),
    os.path.join(base_dir, "data", "cogs"),
    os.path.join(base_dir, "data", "utils"),
    os.path.join(base_dir, "data", "web"),
]

for target in clean_targets:
    if os.path.exists(target):
        try:
            if os.path.isdir(target):
                shutil.rmtree(target, ignore_errors=True)
            else:
                os.remove(target)
            print(f"[Updater] Cleaned: {target}", flush=True)
        except Exception:
            pass

# Clean orphaned tmp_pack_* files in git pack directories
for git_dir in [os.path.join(base_dir, ".git"), os.path.join(base_dir, "data", ".git")]:
    pack_dir = os.path.join(git_dir, "objects", "pack")
    if os.path.exists(pack_dir):
        for f in os.listdir(pack_dir):
            if f.startswith("tmp_pack"):
                try:
                    os.remove(os.path.join(pack_dir, f))
                    print(f"[Updater] Removed abandoned pack: {f}", flush=True)
                except Exception:
                    pass

# 2. Synchronize with GitHub remote
try:
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    repo = os.environ.get("GITHUB_REPO", "").strip()
    if token and repo:
        auth_url = repo.replace("https://", f"https://{token}@")
    else:
        auth_url = "origin"

    subprocess.run(["git", "config", "core.fileMode", "false"], cwd=base_dir, check=False)
    subprocess.run(["git", "fetch", auth_url, "main"], cwd=base_dir, check=False)
    subprocess.run(["git", "reset", "--hard", "FETCH_HEAD"], cwd=base_dir, check=False)
    print("[Updater] Code synchronized to latest GitHub origin/main commit.", flush=True)
except Exception as e:
    print(f"[Updater Notice] Git sync: {e}", flush=True)

print("[Updater] Launching bot.py...", flush=True)

# 3. Hand off execution to bot.py
import bot
