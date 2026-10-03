"""
Git-based auto-backup for the SQLite database.

On startup  → clones / pulls the backup repo into data/ to restore the DB.
Every 10 s  → if the DB changed, commits & pushes to the same repo.

Required env vars:
    GITHUB_TOKEN   — Personal Access Token with repo scope
    GITHUB_REPO    — e.g. https://github.com/yourname/command-army-data.git
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
import subprocess


class GitBackup:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.repo_dir = os.path.dirname(db_path) or "data"
        self._last_hash: str | None = None
        self._enabled = False

    # ── public ──────────────────────────────────────────────────────────────

    def restore(self) -> bool:
        """Clone / pull the backup repo so the latest DB is available.
        Call once at startup, **before** aiosqlite opens the file.
        Returns True if backup is active."""
        token = os.environ.get("GITHUB_TOKEN", "").strip()
        repo  = os.environ.get("GITHUB_REPO", "").strip()
        if not token or not repo:
            print("⚠️  GITHUB_TOKEN / GITHUB_REPO not set — auto-backup disabled.")
            return False

        auth_url = repo.replace("https://", f"https://{token}@")
        os.makedirs(self.repo_dir, exist_ok=True)

        git_dir = os.path.join(self.repo_dir, ".git")
        if not os.path.isdir(git_dir):
            # Fresh start — try to clone into data/
            try:
                # Clone into a temp dir then move contents (git clone won't
                # clone into a non-empty dir)
                tmp = self.repo_dir + "_tmp"
                self._run(["git", "clone", auth_url, tmp])
                # Move .git and files into repo_dir
                for item in os.listdir(tmp):
                    src = os.path.join(tmp, item)
                    dst = os.path.join(self.repo_dir, item)
                    if not os.path.exists(dst):
                        os.rename(src, dst)
                    elif item == ".git":
                        import shutil
                        if os.path.isdir(dst):
                            shutil.rmtree(dst)
                        os.rename(src, dst)
                import shutil
                shutil.rmtree(tmp, ignore_errors=True)
                print("✅  Backup repo cloned — database restored.")
            except subprocess.CalledProcessError:
                # Repo may be empty / not exist yet — init fresh
                self._run(["git", "init"], cwd=self.repo_dir)
                self._run(["git", "remote", "add", "origin", auth_url],
                          cwd=self.repo_dir, check=False)
                print("✅  Initialised fresh backup repo.")
        else:
            # Repo exists — pull latest
            self._run(["git", "remote", "set-url", "origin", auth_url],
                      cwd=self.repo_dir, check=False)
            try:
                self._run(["git", "pull", "origin", "main", "--rebase"],
                          cwd=self.repo_dir)
                print("✅  Pulled latest database backup.")
            except subprocess.CalledProcessError:
                # Might be on master or empty — that's fine
                pass

        self._fix_permissions()

        # Configure identity
        self._run(["git", "config", "user.email", "bot@command-army.com"],
                  cwd=self.repo_dir, check=False)
        self._run(["git", "config", "user.name", "CommandArmyBot"],
                  cwd=self.repo_dir, check=False)
        self._run(["git", "config", "core.fileMode", "false"],
                  cwd=self.repo_dir, check=False)
        # Always keep local DB on merge conflicts
        self._run(["git", "config", "merge.ours.driver", "true"],
                  cwd=self.repo_dir, check=False)
        with open(os.path.join(self.repo_dir, ".gitattributes"), "a") as f:
            f.write("bot.db merge=ours\n")

        self._last_hash = self._file_hash()
        self._enabled = True
        return True

    def _fix_permissions(self):
        try:
            import stat
            os.chmod(self.repo_dir, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
            if os.path.exists(self.db_path):
                os.chmod(self.db_path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
        except Exception:
            pass

    def push_if_changed(self) -> bool:
        """Commit & push if the DB file changed since last check.
        Safe to call from a thread (no async)."""
        if not self._enabled:
            return False

        # Checkpoint WAL so git sees the latest data in the main file
        self._checkpoint()

        current = self._file_hash()
        if current == self._last_hash:
            return False
        self._last_hash = current

        try:
            self._run(["git", "add", "-A"], cwd=self.repo_dir)
            status = self._run(
                ["git", "status", "--porcelain"],
                cwd=self.repo_dir, capture=True,
            )
            if not status.stdout.strip():
                return False

            self._run(
                ["git", "commit", "-m", "Auto-backup"],
                cwd=self.repo_dir,
            )
            self._run(
                ["git", "push", "-u", "origin", "main"],
                cwd=self.repo_dir,
            )
            return True
        except subprocess.CalledProcessError as exc:
            print(f"⚠️  Git backup push failed: {exc}")
            # The remote probably contains new code (e.g. pushed by developer)
            # Try to pull --rebase and push again
            try:
                self._run(["git", "pull", "--no-rebase", "--no-edit", "origin", "main"], cwd=self.repo_dir)
                self._fix_permissions()
                self._run(["git", "push", "-u", "origin", "main"], cwd=self.repo_dir)
                print("✅  Successfully rebased and pushed backup!")
                return True
            except subprocess.CalledProcessError:
                # If it still fails, try initializing branch as a last resort
                try:
                    self._run(["git", "branch", "-M", "main"], cwd=self.repo_dir)
                    self._run(["git", "push", "-u", "origin", "main"], cwd=self.repo_dir)
                    return True
                except subprocess.CalledProcessError:
                    return False

    # ── internals ───────────────────────────────────────────────────────────

    def _file_hash(self) -> str | None:
        if not os.path.exists(self.db_path):
            return None
        h = hashlib.md5()
        with open(self.db_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def _checkpoint(self):
        """Flush WAL to the main database file."""
        if not os.path.exists(self.db_path):
            return
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            conn.close()
        except Exception:
            pass

    @staticmethod
    def _run(cmd, *, cwd=None, check=True, capture=False):
        return subprocess.run(
            cmd,
            cwd=cwd,
            check=check,
            capture_output=True,
            text=True,
        )
