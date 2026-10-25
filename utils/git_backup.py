"""
Git-based auto-backup for the SQLite database.

On startup  → clones / pulls the backup repo into data/ to restore the DB.
Every 10 s  → on Render (production): if the DB changed, commits & pushes to GitHub.
            → on Local (development/admin portal): pulls & syncs latest DB from GitHub.

Required env vars:
    GITHUB_TOKEN   — Personal Access Token with repo scope
    GITHUB_REPO    — e.g. https://github.com/yourname/command-army-data.git
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
import subprocess
import tempfile
import threading
import time


class GitBackup:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.repo_dir = os.path.dirname(db_path) or "data"
        self._last_hash: str | None = None
        self._enabled = False
        self._last_sync_time: float = 0
        self._sync_lock = threading.Lock()

    @staticmethod
    def is_render() -> bool:
        """Return True if running inside Render's production cloud container."""
        return bool(
            os.environ.get("RENDER")
            or os.environ.get("IS_RENDER")
            or os.environ.get("RENDER_SERVICE_ID")
            or os.path.exists("/.dockerenv")
        )

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
                tmp = self.repo_dir + "_tmp"
                self._run(["git", "clone", auth_url, tmp])
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
                self._run(["git", "init"], cwd=self.repo_dir)
                self._run(["git", "remote", "add", "origin", auth_url],
                          cwd=self.repo_dir, check=False)
                print("✅  Initialised fresh backup repo.")
        else:
            self._run(["git", "remote", "set-url", "origin", auth_url],
                      cwd=self.repo_dir, check=False)
            # Preserve a valid local DB; an older remote snapshot must not
            # roll back live wallets during a restart.
            local_valid = False
            if os.path.exists(self.db_path) and os.path.getsize(self.db_path) > 1000:
                try:
                    conn = sqlite3.connect(self.db_path)
                    local_valid = conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
                    conn.close()
                except Exception:
                    local_valid = False
            if local_valid:
                print("✅  Preserved valid local database; skipped remote pull.")
            else:
                try:
                    self._run(["git", "pull", "origin", "main", "--rebase"],
                              cwd=self.repo_dir)
                    print("✅  Pulled latest database backup.")
                except subprocess.CalledProcessError:
                    pass

        self._fix_permissions()

        # Configure identity
        self._run(["git", "config", "user.email", "bot@command-army.com"],
                  cwd=self.repo_dir, check=False)
        self._run(["git", "config", "user.name", "CommandArmyBot"],
                  cwd=self.repo_dir, check=False)
        self._run(["git", "config", "core.fileMode", "false"],
                  cwd=self.repo_dir, check=False)
        self._run(["git", "config", "pull.rebase", "false"],
                  cwd=self.repo_dir, check=False)

        # On Render: merge=ours preserves cloud DB across code deploys
        if self.is_render():
            self._run(["git", "config", "merge.ours.driver", "true"],
                      cwd=self.repo_dir, check=False)
            gitattributes_path = os.path.join(self.repo_dir, ".gitattributes")
            if not os.path.exists(gitattributes_path):
                with open(gitattributes_path, "w") as f:
                    f.write("bot.db merge=ours\nbot.db binary\n")

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
        Safe to call from a thread (no async).
        Only the production Render bot pushes backups to GitHub.
        Local instances will instead pull/sync from remote."""
        if not self.is_render():
            # Local development / web portal:
            # DO NOT push to GitHub (would clobber production bot database),
            # and DO NOT automatically overwrite local database every 10 seconds.
            return False

        if not self._enabled:
            return False

        # Checkpoint WAL so git sees the latest data in the main file
        self._checkpoint()

        current = self._file_hash()
        if current == self._last_hash:
            return False
        self._last_hash = current

        try:
            self._run(["git", "add", "bot.db"], cwd=self.repo_dir)
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
            try:
                # Abort any in-progress merge or rebase conflict immediately
                self._run(["git", "merge", "--abort"], cwd=self.repo_dir, check=False)
                self._run(["git", "rebase", "--abort"], cwd=self.repo_dir, check=False)

                # Fetch and pull remote with -X ours to prioritize the active live cloud database
                self._run(["git", "pull", "--no-rebase", "-X", "ours", "--no-edit", "origin", "main"], cwd=self.repo_dir, check=False)
                self._run(["git", "checkout", "--ours", "bot.db"], cwd=self.repo_dir, check=False)
                self._fix_permissions()
                self._run(["git", "add", "bot.db"], cwd=self.repo_dir, check=False)
                self._run(["git", "commit", "-m", "Auto-backup resolution"], cwd=self.repo_dir, check=False)
                self._run(["git", "push", "-u", "origin", "main"], cwd=self.repo_dir)
                print("✅  Successfully resolved binary conflict and pushed backup!")
                return True
            except Exception as e:
                print(f"⚠️  Auto-backup recovery attempt: {e}")
                # Do NOT force push - allow developer code commits to take precedence
                return False

    def sync_from_remote(self, force: bool = False) -> bool:
        """Sync the local database with the latest backup on GitHub origin/main.
        Can be called periodically or on-demand when an admin views/refreshes the portal."""
        token = os.environ.get("GITHUB_TOKEN", "").strip()
        repo = os.environ.get("GITHUB_REPO", "").strip()
        if not token or not repo:
            return False

        with self._sync_lock:
            now = time.time()
            # Rate limit git fetch to at most once every 3 seconds unless forced
            if not force and (now - self._last_sync_time < 3.0):
                return False
            self._last_sync_time = now

            try:
                auth_url = repo.replace("https://", f"https://{token}@")
                self._run(["git", "fetch", auth_url, "main"], cwd=self.repo_dir, check=True)

                remote_blob = self._run(
                    ["git", "show", "FETCH_HEAD:bot.db"],
                    cwd=self.repo_dir, check=True, capture_binary=True
                )
                if not remote_blob or len(remote_blob) < 1000:
                    return False

                # Verify sqlite integrity before overwriting
                with tempfile.NamedTemporaryFile(delete=False) as tmp:
                    tmp.write(remote_blob)
                    tmp_path = tmp.name
                try:
                    conn = sqlite3.connect(tmp_path)
                    cur = conn.cursor()
                    cur.execute("PRAGMA integrity_check")
                    row = cur.fetchone()
                    valid = (row and row[0] == "ok")
                    conn.close()
                finally:
                    try:
                        os.unlink(tmp_path)
                    except Exception:
                        pass

                if not valid:
                    print("⚠️ Remote DB from GitHub failed integrity check, skipping sync.")
                    return False

                remote_hash = hashlib.md5(remote_blob).hexdigest()
                local_hash = self._file_hash()
                if remote_hash == local_hash:
                    return False  # Up to date

                # A valid live database is authoritative. The GitHub backup can
                # lag behind the bot by several seconds, so replacing the live
                # file here would silently roll back wallets, stocks, loans, and
                # country state. Restore/sync is only allowed when the local DB is
                # missing or corrupt; never clobber a healthy live database.
                print("⚠️ Remote DB differs from a valid live DB; skipped stale snapshot replacement.")
                return False

                # Flush WAL and remove WAL/SHM before updating
                self._checkpoint()
                wal_path = self.db_path + "-wal"
                shm_path = self.db_path + "-shm"
                for p in [wal_path, shm_path]:
                    if os.path.exists(p):
                        try:
                            os.remove(p)
                        except Exception:
                            pass

                # Write the new database content
                with open(self.db_path, "wb") as f:
                    f.write(remote_blob)

                # Also keep root bot.db in sync if it exists
                root_db = os.path.abspath(os.path.join(self.repo_dir, "..", "bot.db"))
                if os.path.exists(root_db) and os.path.abspath(root_db) != os.path.abspath(self.db_path):
                    try:
                        with open(root_db, "wb") as f:
                            f.write(remote_blob)
                    except Exception:
                        pass

                self._last_hash = remote_hash
                print(f"🔄 [Sync] Successfully synced database from GitHub! ({len(remote_blob):,} bytes)")
                return True
            except Exception as e:
                return False

    def push_admin_update(self, commit_msg: str = "Admin update from web portal") -> bool:
        """Explicitly commit and push an administrative change from the web portal to GitHub."""
        token = os.environ.get("GITHUB_TOKEN", "").strip()
        repo = os.environ.get("GITHUB_REPO", "").strip()
        if not token or not repo:
            return False

        self._checkpoint()
        try:
            auth_url = repo.replace("https://", f"https://{token}@")
            self._run(["git", "add", "bot.db"], cwd=self.repo_dir, check=False)
            self._run(["git", "commit", "-m", commit_msg], cwd=self.repo_dir, check=False)
            self._run(["git", "push", auth_url, "main"], cwd=self.repo_dir, check=False)
            self._last_hash = self._file_hash()
            print(f"✅ [Admin Push] Pushed DB change to GitHub: {commit_msg}")
            return True
        except Exception as e:
            print(f"⚠️ push_admin_update failed: {e}")
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
    def _run(cmd, *, cwd=None, check=True, capture=False, capture_binary=False):
        if capture_binary:
            proc = subprocess.run(cmd, cwd=cwd, check=check, capture_output=True)
            return proc.stdout
        return subprocess.run(
            cmd,
            cwd=cwd,
            check=check,
            capture_output=capture,
            text=True,
        )
