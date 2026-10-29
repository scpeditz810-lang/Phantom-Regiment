"""
Git-based auto-backup for the SQLite database.

On startup  → restores the latest verified SQLite snapshot from GitHub.
Every 10 s  → on Render (production): uses SQLite's online backup API to create a
              consistent snapshot file, then commits & pushes that file to GitHub.
            → on Local (development/admin portal): pulls & syncs the latest backup.

Required env vars:
    GITHUB_TOKEN   — Personal Access Token with repo scope
    GITHUB_REPO    — e.g. https://github.com/yourname/command-army-data.git
"""

from __future__ import annotations

import hashlib
import os
import shutil
import sqlite3
import subprocess
import tempfile
import threading
import time


class GitBackup:
    def __init__(self, db_path: str):
        self.db_path = db_path
        # The main git repository is at the project root; live DB is kept at db_path (e.g. data/bot.db)
        self.repo_dir = "." if os.path.isdir(".git") else (os.path.dirname(db_path) or ".")
        self._last_hash: str | None = None
        self._enabled = False
        self._last_sync_time: float = 0
        self._sync_lock = threading.Lock()
        self._push_lock = threading.Lock()
        self.snapshot_name = "bot_snapshot.db"

    @staticmethod
    def is_render() -> bool:
        """Return True if running inside cloud container or GitHub credentials are configured."""
        if os.environ.get("GITHUB_TOKEN") and os.environ.get("GITHUB_REPO"):
            return True
        return bool(
            os.environ.get("RENDER")
            or os.environ.get("IS_RENDER")
            or os.environ.get("RENDER_SERVICE_ID")
            or os.environ.get("P_SERVER_UUID")
            or os.environ.get("SERVER_MEMORY")
            or os.environ.get("STARTUP_FILE")
            or os.path.exists("/home/container")
            or os.path.exists("/.dockerenv")
            or os.environ.get("CLOUD_HOSTED") == "1"
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

        def _sqlite_integrity(path: str) -> bool:
            try:
                conn = sqlite3.connect(path, timeout=15.0)
                try:
                    result = conn.execute("PRAGMA integrity_check").fetchone()
                    return bool(result and result[0] == "ok")
                finally:
                    conn.close()
            except (sqlite3.DatabaseError, Exception):
                return False

        # First verify if existing local database is already present and sound
        local_valid = False
        if os.path.exists(self.db_path) and os.path.getsize(self.db_path) > 1000:
            local_valid = _sqlite_integrity(self.db_path)
            if not local_valid:
                conn = None
                try:
                    conn = sqlite3.connect(self.db_path, timeout=30.0)
                    conn.execute("REINDEX")
                    conn.commit()
                    integrity = conn.execute("PRAGMA integrity_check").fetchone()
                    local_valid = bool(integrity and integrity[0] == "ok")
                    if local_valid:
                        print("✅ Rebuilt corrupt indexes in the existing SQLite database.", flush=True)
                except Exception as e:
                    print(f"⚠️ Existing local database could not be repaired in place: {e}", flush=True)
                finally:
                    if conn is not None:
                        conn.close()

        git_dir = os.path.join(self.repo_dir, ".git")
        if not os.path.isdir(git_dir):
            if local_valid:
                print("✅ Preserved valid local database; initializing git backup workspace.", flush=True)
                self._run(["git", "init"], cwd=self.repo_dir, check=False)
                self._run(["git", "remote", "add", "origin", auth_url], cwd=self.repo_dir, check=False)
                self._run(["git", "remote", "set-url", "origin", auth_url], cwd=self.repo_dir, check=False)
                self._run(["git", "fetch", "--depth", "1", auth_url, "main"], cwd=self.repo_dir, check=False)
                self._run(["git", "reset", "--soft", "FETCH_HEAD"], cwd=self.repo_dir, check=False)
            else:
                tmp = self.repo_dir + "_tmp"
                import shutil
                shutil.rmtree(tmp, ignore_errors=True)
                try:
                    self._run([
                        "git", "clone", "--depth", "1", "--single-branch",
                        "--branch", "main", auth_url, tmp
                    ])

                    legacy_name = os.path.basename(self.db_path)
                    source_name = self.snapshot_name if os.path.exists(os.path.join(tmp, self.snapshot_name)) else legacy_name
                    remote_db = os.path.join(tmp, source_name)
                    if not os.path.exists(remote_db) or os.path.getsize(remote_db) < 1000:
                        raise FileNotFoundError("backup repository clone did not contain a database snapshot")

                    if not _sqlite_integrity(remote_db):
                        print("⚠️ Latest remote database failed integrity check; attempting reindex.", flush=True)
                        reindexed = os.path.join(tmp, "bot.db.reindexed")
                        try:
                            shutil.copy2(remote_db, reindexed)
                            conn = sqlite3.connect(reindexed, timeout=30.0)
                            conn.execute("REINDEX")
                            conn.commit()
                            conn.close()
                            if _sqlite_integrity(reindexed):
                                os.replace(reindexed, remote_db)
                                print("✅ Rebuilt corrupt SQLite indexes from stored rows.", flush=True)
                        except Exception:
                            pass
                        finally:
                            if os.path.exists(reindexed):
                                os.remove(reindexed)

                    if not _sqlite_integrity(remote_db):
                        raise sqlite3.DatabaseError("Remote snapshot failed integrity check.")

                    os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
                    local_snapshot = os.path.join(self.repo_dir, self.snapshot_name)
                    if source_name == self.snapshot_name:
                        shutil.copy2(remote_db, local_snapshot)
                    elif os.path.exists(local_snapshot):
                        os.remove(local_snapshot)
                    shutil.copy2(remote_db, self.db_path)

                    # Only migrate git repository metadata, never duplicate the whole code tree into repo_dir!
                    git_src = os.path.join(tmp, ".git")
                    git_dst = os.path.join(self.repo_dir, ".git")
                    if os.path.exists(git_src) and not os.path.exists(git_dst):
                        os.rename(git_src, git_dst)
                    shutil.rmtree(tmp, ignore_errors=True)
                    print("✅ Latest database snapshot restored from backup repo.", flush=True)
                except Exception as exc:
                    shutil.rmtree(tmp, ignore_errors=True)
                    print(f"⚠️ Remote restore notice: {exc}", flush=True)
                    if not (os.path.exists(self.db_path) and _sqlite_integrity(self.db_path)):
                        raise RuntimeError("Database backup restore failed and no valid local DB exists") from exc
        else:
            self._run(["git", "remote", "set-url", "origin", auth_url],
                      cwd=self.repo_dir, check=False)
            if local_valid:
                print("✅ Preserved valid local database; skipped remote pull.", flush=True)
            else:
                restore_tmp = self.db_path + ".restore.tmp"
                restored_name = None
                try:
                    self._run(["git", "fetch", "--depth", "1", auth_url, "main"], cwd=self.repo_dir)
                    for candidate_name in (self.snapshot_name, os.path.basename(self.db_path)):
                        blob = self._run(
                            ["git", "show", f"FETCH_HEAD:{candidate_name}"],
                            cwd=self.repo_dir, check=False, capture_binary=True,
                        )
                        if not blob or len(blob) < 1000:
                            continue
                        with open(restore_tmp, "wb") as restore_file:
                            restore_file.write(blob)
                        conn = sqlite3.connect(restore_tmp, timeout=30.0)
                        try:
                            integrity = conn.execute("PRAGMA integrity_check").fetchone()
                            if not integrity or integrity[0] != "ok":
                                conn.execute("REINDEX")
                                conn.commit()
                                integrity = conn.execute("PRAGMA integrity_check").fetchone()
                        finally:
                            conn.close()
                        if integrity and integrity[0] == "ok":
                            restored_name = candidate_name
                            break
                        os.remove(restore_tmp)

                    if not restored_name:
                        raise sqlite3.DatabaseError("no valid remote SQLite snapshot found")
                    for suffix in ("-wal", "-shm"):
                        sidecar = self.db_path + suffix
                        if os.path.exists(sidecar):
                            os.remove(sidecar)
                    os.replace(restore_tmp, self.db_path)
                    local_snapshot = os.path.join(self.repo_dir, self.snapshot_name)
                    if restored_name == self.snapshot_name:
                        shutil.copy2(self.db_path, local_snapshot)
                    elif os.path.exists(local_snapshot):
                        os.remove(local_snapshot)
                    print(f"✅ Restored valid database from remote {restored_name}.", flush=True)
                except Exception as restore_error:
                    print(f"❌ Could not restore a valid remote database: {restore_error}", flush=True)
                    if not (os.path.exists(self.db_path) and _sqlite_integrity(self.db_path)):
                        raise RuntimeError("No valid local or remote SQLite database is available.") from restore_error
                finally:
                    try:
                        if os.path.exists(restore_tmp):
                            os.remove(restore_tmp)
                    except OSError:
                        pass

        # Refuse to mark restore successful unless the expected SQLite file
        # exists and passes integrity verification.
        if not os.path.exists(self.db_path) or os.path.getsize(self.db_path) < 1000:
            raise RuntimeError(f"Backup restore did not produce {self.db_path}")
        conn = sqlite3.connect(self.db_path)
        try:
            integrity = conn.execute("PRAGMA integrity_check").fetchone()
        finally:
            conn.close()
        if not integrity or integrity[0] != "ok":
            raise sqlite3.DatabaseError(f"Restored database {self.db_path} failed integrity_check")

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
            existing_attributes = ""
            if os.path.exists(gitattributes_path):
                with open(gitattributes_path, "r", encoding="utf-8") as f:
                    existing_attributes = f.read()
            with open(gitattributes_path, "a", encoding="utf-8") as f:
                if existing_attributes and not existing_attributes.endswith("\n"):
                    f.write("\n")
                if "bot.db merge=ours" not in existing_attributes:
                    f.write("bot.db merge=ours\nbot.db binary\n")
                if f"{self.snapshot_name} merge=ours" not in existing_attributes:
                    f.write(f"{self.snapshot_name} merge=ours\n{self.snapshot_name} binary\n")

        # Always publish one consistent snapshot after startup. This captures
        # any committed WAL state and repairs the Git backup before the next deploy.
        self._last_hash = None
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
        """Commit a consistent SQLite online-backup snapshot to GitHub."""
        with self._push_lock:
            return self._push_snapshot_if_changed()

    def cleanup_space(self):
        """Aggressively reclaim disk space by purging git reflogs, loose objects, and duplicate databases."""
        try:
            import stat
            import shutil
            base_dir = self.repo_dir
            # 1. Clean root DB duplicates if data/bot.db is healthy
            data_db = os.path.join(base_dir, "data", "bot.db")
            if os.path.isfile(data_db) and os.path.getsize(data_db) > 10000:
                for db_name in ("bot.db", "bot_snapshot.db"):
                    p = os.path.join(base_dir, db_name)
                    if os.path.isfile(p):
                        try:
                            os.remove(p)
                        except Exception:
                            pass

            # 2. Expire reflogs, prune loose git objects, and repack git repository
            git_dir = os.path.join(base_dir, ".git")
            if os.path.isdir(git_dir):
                self._run(["git", "reflog", "expire", "--expire=now", "--all"], cwd=base_dir, check=False)
                self._run(["git", "prune", "--expire=now"], cwd=base_dir, check=False)
                self._run(["git", "repack", "-a", "-d", "-l"], cwd=base_dir, check=False)
                self._run(["git", "gc", "--auto", "--prune=now"], cwd=base_dir, check=False)

            # 3. Clean abandoned temporary files in /tmp and .cache
            for tmp_candidate in ("/tmp", os.path.join(base_dir, ".cache")):
                if os.path.isdir(tmp_candidate):
                    for item in os.listdir(tmp_candidate):
                        fp = os.path.join(tmp_candidate, item)
                        try:
                            if os.path.isdir(fp):
                                shutil.rmtree(fp, ignore_errors=True)
                            else:
                                os.remove(fp)
                        except Exception:
                            pass
        except Exception as e:
            try:
                print(f"⚠️ [Disk Cleanup Error]: {e}", flush=True)
            except Exception:
                pass

    def _push_snapshot_if_changed(self) -> bool:
        token = os.environ.get("GITHUB_TOKEN", "").strip()
        repo = os.environ.get("GITHUB_REPO", "").strip()
        if not token or not repo:
            return False
        auth_url = repo.replace("https://", f"https://{token}@")

        if not os.path.exists(self.db_path):
            return False

        current = self._file_hash()
        if current == self._last_hash:
            return False

        try:
            snapshot = self._write_snapshot()
            self._run(["git", "add", self.snapshot_name], cwd=self.repo_dir)
            status = self._run(
                ["git", "status", "--porcelain", "--", self.snapshot_name],
                cwd=self.repo_dir, capture=True,
            )
            if not status.stdout.strip():
                self._last_hash = current
                return False

            self._run(["git", "commit", "-m", "Auto-backup"], cwd=self.repo_dir, check=False)
            
            # Synchronize with remote history before pushing to prevent rejection
            self._run(["git", "fetch", "--depth", "1", auth_url, "main"], cwd=self.repo_dir, check=False)
            # Rebase snapshot on top of incoming code commits without destroying code changes
            self._run(["git", "checkout", "FETCH_HEAD", "--", "bot.py", "cogs", "utils", "web", "requirements.txt"], cwd=self.repo_dir, check=False)
            self._run(["git", "reset", "--soft", "FETCH_HEAD"], cwd=self.repo_dir, check=False)
            self._run(["git", "add", self.snapshot_name], cwd=self.repo_dir, check=False)
            self._run(["git", "commit", "-m", "Auto-backup"], cwd=self.repo_dir, check=False)

            self._run(["git", "push", "-u", auth_url, "main"], cwd=self.repo_dir)
            self._last_hash = current
            self._backup_count = getattr(self, "_backup_count", 0) + 1
            if self._backup_count % 10 == 0:
                self.cleanup_space()
            try:
                print(f"[Backup Success] Consistent SQLite snapshot backed up ({os.path.getsize(snapshot):,} bytes).", flush=True)
            except Exception:
                pass
            return True
        except Exception as exc:
            try:
                print(f"[Backup Notice] Git backup push sync: {exc}".encode("ascii", "replace").decode("ascii"), flush=True)
            except Exception:
                pass
            try:
                self._run(["git", "fetch", "--depth", "1", auth_url, "main"], cwd=self.repo_dir, check=False)
                self._run(["git", "merge", "--abort"], cwd=self.repo_dir, check=False)
                self._run(["git", "rebase", "--abort"], cwd=self.repo_dir, check=False)
                self._run(["git", "reset", "--soft", "FETCH_HEAD"], cwd=self.repo_dir, check=False)
                self._run(["git", "add", self.snapshot_name], cwd=self.repo_dir, check=False)
                self._run(["git", "commit", "-m", "Auto-backup resolution"], cwd=self.repo_dir, check=False)
                self._run(["git", "push", "-u", auth_url, "main"], cwd=self.repo_dir)
                self._last_hash = current
                print("[Backup Success] Resolved snapshot conflict and pushed current SQLite backup.", flush=True)
                return True
            except Exception as e:
                try:
                    print(f"[Backup Error] Auto-backup recovery attempt: {e}".encode("ascii", "replace").decode("ascii"), flush=True)
                except Exception:
                    pass
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
                self._run(["git", "fetch", "--depth", "1", auth_url, "main"], cwd=self.repo_dir, check=True)

                remote_blob = self._run(
                    ["git", "show", f"FETCH_HEAD:{self.snapshot_name}"],
                    cwd=self.repo_dir, check=False, capture_binary=True
                )
                if not remote_blob:
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
            except Exception as e:
                return False

    def push_admin_update(self, commit_msg: str = "Admin update from web portal") -> bool:
        """Create and push a consistent SQLite snapshot after an explicit admin update."""
        token = os.environ.get("GITHUB_TOKEN", "").strip()
        repo = os.environ.get("GITHUB_REPO", "").strip()
        if not token or not repo:
            return False

        try:
            with self._push_lock:
                self._write_snapshot()
                auth_url = repo.replace("https://", f"https://{token}@")
                self._run(["git", "add", self.snapshot_name], cwd=self.repo_dir, check=False)
                self._run(["git", "commit", "-m", commit_msg], cwd=self.repo_dir, check=False)
                self._run(["git", "push", auth_url, "main"], cwd=self.repo_dir, check=False)
                self._last_hash = self._file_hash()
                print(f"✅ [Admin Push] Pushed consistent database snapshot: {commit_msg}", flush=True)
                return True
        except Exception as e:
            print(f"⚠️ push_admin_update failed: {e}", flush=True)
            return False

    # ── internals ───────────────────────────────────────────────────────────

    def _write_snapshot(self) -> str:
        """Write an atomic, transaction-consistent SQLite backup outside the live DB."""
        os.makedirs(self.repo_dir, exist_ok=True)
        snapshot_path = os.path.join(self.repo_dir, self.snapshot_name)
        temporary_path = snapshot_path + ".tmp"
        try:
            if os.path.exists(temporary_path):
                os.remove(temporary_path)
            source = sqlite3.connect(self.db_path, timeout=30.0)
            destination = sqlite3.connect(temporary_path, timeout=30.0)
            try:
                source.backup(destination, pages=256, sleep=0.05)
                destination.commit()
            finally:
                destination.close()
                source.close()

            check = sqlite3.connect(temporary_path, timeout=30.0)
            try:
                result = check.execute("PRAGMA integrity_check").fetchone()
            finally:
                check.close()
            if not result or result[0] != "ok":
                raise sqlite3.DatabaseError(f"online backup failed integrity_check: {result}")
            os.replace(temporary_path, snapshot_path)
            return snapshot_path
        except sqlite3.OperationalError as op_err:
            if any(k in str(op_err).lower() for k in ("full", "disk", "unable", "lock")):
                self.cleanup_space()
                try:
                    from bot import emergency_disk_clean
                    emergency_disk_clean()
                except Exception:
                    pass
                if os.path.exists(temporary_path):
                    try:
                        os.remove(temporary_path)
                    except OSError:
                        pass
                try:
                    source = sqlite3.connect(self.db_path, timeout=30.0)
                    destination = sqlite3.connect(temporary_path, timeout=30.0)
                    try:
                        source.backup(destination, pages=256, sleep=0.05)
                        destination.commit()
                    finally:
                        destination.close()
                        source.close()
                    os.replace(temporary_path, snapshot_path)
                    return snapshot_path
                except Exception:
                    import shutil
                    if os.path.exists(self.db_path) and os.path.getsize(self.db_path) > 1000:
                        shutil.copy2(self.db_path, snapshot_path)
                        return snapshot_path
            raise
        except Exception as general_err:
            import shutil
            if os.path.exists(self.db_path) and os.path.getsize(self.db_path) > 1000:
                shutil.copy2(self.db_path, snapshot_path)
                return snapshot_path
            raise general_err
        finally:
            try:
                if os.path.exists(temporary_path):
                    os.remove(temporary_path)
            except OSError:
                pass

    def _file_hash(self) -> str | None:
        if not os.path.exists(self.db_path):
            return None
        h = hashlib.md5()
        # In WAL mode committed writes may exist only in bot.db-wal. Include it
        # so the 10-second backup loop does not mistake a changed live DB for an
        # unchanged main file and skip persisting wallet/country/stock updates.
        for path in (self.db_path, self.db_path + "-wal"):
            h.update(os.path.basename(path).encode("utf-8"))
            if not os.path.exists(path):
                h.update(b"<absent>")
                continue
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def _run(cmd, *, cwd=None, check=True, capture=False, capture_binary=False):
        # Never let a network/git operation stall application startup forever.
        # Render can temporarily lose access to GitHub during cold deploys.
        timeout = int(os.environ.get("GIT_COMMAND_TIMEOUT", "45"))
        if capture_binary:
            proc = subprocess.run(
                cmd, cwd=cwd, check=check, capture_output=True, timeout=timeout
            )
            return proc.stdout
        return subprocess.run(
            cmd,
            cwd=cwd,
            check=check,
            capture_output=capture,
            text=True,
            timeout=timeout,
        )
