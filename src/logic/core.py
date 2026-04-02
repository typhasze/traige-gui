import os
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.parse
from typing import Optional

from ..utils.constants import (
    DEFAULT_BACKUP_PATH,
    DEFAULT_DATA_PATH,
    DEFAULT_SETTINGS,
    FOXGLOVE_DS_URL,
    FOXGLOVE_REMOTE_BASE_URL,
    LONG_RUNNING_PROCESS_THRESHOLD,
    PROCESS_MONITOR_INTERVAL,
    PROCESS_NAMES,
    PROCESS_SHUTDOWN_TIMEOUT,
)
from ..utils.file_operations import open_url_in_browser
from ..utils.logger import get_logger
from .symlink_playback_logic import SymlinkPlaybackLogic

logger = get_logger(__name__)


class FoxgloveAppLogic:
    def __init__(self, log_callback=None):
        self.running_processes = []
        self.local_base_path_absolute = DEFAULT_DATA_PATH
        self.backup_base_path_absolute = DEFAULT_BACKUP_PATH
        self.bazel_working_dir = None
        self.settings = DEFAULT_SETTINGS.copy()
        self._process_id_counter = 0
        self.log_callback = log_callback or (lambda *args, **kwargs: None)
        self._processes_lock = threading.RLock()
        self._process_monitor_thread = None
        self._monitor_stop_event = threading.Event()
        self._start_process_monitor()

    def _start_process_monitor(self):
        """Start background thread to monitor process health and clean up zombies."""
        if self._process_monitor_thread is None or not self._process_monitor_thread.is_alive():
            self._monitor_stop_event.clear()
            self._process_monitor_thread = threading.Thread(
                target=self._process_health_monitor, daemon=True, name="ProcessHealthMonitor"
            )
            self._process_monitor_thread.start()

    def _process_health_monitor(self):
        """
        Background process health monitor that periodically checks and cleans up
        dead processes to prevent zombies and hanging states.
        """
        while not self._monitor_stop_event.wait(PROCESS_MONITOR_INTERVAL):
            try:
                self._cleanup_dead_processes()
            except Exception as e:
                # Use module logger for background-thread errors (avoids Tkinter
                # cross-thread issues and guarantees capture in the log file)
                logger.error("Process monitor error: %s", e)

    def _cleanup_dead_processes(self):
        """Remove dead processes from tracking list to prevent zombie accumulation."""
        dead_processes = []
        current_time = time.time()

        with self._processes_lock:
            processes_snapshot = list(self.running_processes)

        for proc_info in processes_snapshot:
            proc = proc_info["process"]
            if proc.poll() is not None:
                dead_processes.append(proc_info)
            else:
                # Check for potentially hanging processes
                start_time = proc_info.get("start_time", current_time)
                runtime = current_time - start_time
                if runtime > LONG_RUNNING_PROCESS_THRESHOLD:
                    logger.warning(
                        "Long-running process detected: %s (PID: %s, runtime: %.1fh)",
                        proc_info["name"],
                        proc.pid,
                        runtime / 3600,
                    )

        if dead_processes:
            with self._processes_lock:
                for proc_info in dead_processes:
                    if proc_info in self.running_processes:
                        self.running_processes.remove(proc_info)

    def get_process_status(self):
        """Get current status of all tracked processes."""
        with self._processes_lock:
            processes_snapshot = list(self.running_processes)

        status = {"total": len(processes_snapshot), "running": 0, "dead": 0, "processes": []}

        current_time = time.time()
        for proc_info in processes_snapshot:
            proc = proc_info["process"]
            is_running = proc.poll() is None
            start_time = proc_info.get("start_time", current_time)
            runtime = current_time - start_time

            process_status = {
                "name": proc_info["name"],
                "pid": proc.pid,
                "running": is_running,
                "runtime_seconds": runtime,
                "runtime_display": (
                    f"Runtime: {int(runtime//60)}:{int(runtime%60):02d} min"
                    if runtime < 3600
                    else f"Runtime: {runtime/3600:.1f}h"
                ),
            }

            status["processes"].append(process_status)
            if is_running:
                status["running"] += 1
            else:
                status["dead"] += 1

        return status

    def _stop_process_monitor(self):
        """Stop the process health monitor."""
        if self._process_monitor_thread and self._process_monitor_thread.is_alive():
            self._monitor_stop_event.set()
            self._process_monitor_thread.join(timeout=PROCESS_SHUTDOWN_TIMEOUT)

    def update_search_paths(self, primary_path: Optional[str], backup_path: Optional[str]) -> None:
        if primary_path:
            self.local_base_path_absolute = primary_path
        if backup_path:
            self.backup_base_path_absolute = backup_path

    def set_runtime_settings(self, settings: dict) -> None:
        if isinstance(settings, dict):
            merged = DEFAULT_SETTINGS.copy()
            merged.update(settings)
            self.settings = merged
        else:
            self.settings = DEFAULT_SETTINGS.copy()

    def get_bazel_working_dir(self, settings=None):
        if settings is not None:
            return settings.get("bazel_working_dir")
        return None

    def parse_stable_status(self, working_dir: str) -> tuple:
        """Read <working_dir>/bazel-out/stable-status.txt and return (info_dict, error).

        info_dict keys: commit_hash, git_name, revision_short
        """
        path = os.path.join(os.path.expanduser(working_dir), "bazel-out", "stable-status.txt")
        if not os.path.isfile(path):
            return None, f"stable-status.txt not found: {path}"
        try:
            wanted = {
                "STABLE_BUILD_GIT_REVISION": "commit_hash",
                "STABLE_BUILD_GIT_NAME": "git_name",
                "STABLE_BUILD_GIT_REVISION_SHORT": "revision_short",
            }
            info = {}
            with open(path) as f:
                for line in f:
                    for key, field in wanted.items():
                        if line.startswith(key + " "):
                            info[field] = line.strip().split(None, 1)[1]
            if not info:
                return None, "No recognised fields in stable-status.txt"
            return info, None
        except Exception as e:
            return None, str(e)

    def parse_build_info(self, folder_path: str) -> tuple:
        """Find build_info*.txt in folder_path and return (info_dict, error).

        info_dict keys: commit_hash, git_name, revision_short
        """
        import glob as _glob

        pattern = os.path.join(os.path.expanduser(folder_path), "build_info*.txt")
        matches = _glob.glob(pattern)
        if not matches:
            return None, "No build_info*.txt found in this folder"
        try:
            wanted = {
                "STABLE_BUILD_GIT_REVISION": "commit_hash",
                "STABLE_BUILD_GIT_NAME": "git_name",
                "STABLE_BUILD_GIT_REVISION_SHORT": "revision_short",
            }
            info = {}
            with open(matches[0]) as f:
                for line in f:
                    for key, field in wanted.items():
                        if line.startswith(key + " "):
                            info[field] = line.strip().split(None, 1)[1]
            if "commit_hash" not in info:
                return None, "STABLE_BUILD_GIT_REVISION not found in build_info file"
            return info, None
        except Exception as e:
            return None, str(e)

    def get_git_branch(self, working_dir: str) -> tuple:
        """Return (branch_name, error_message) for the given directory."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=os.path.expanduser(working_dir),
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip(), None
            return None, result.stderr.strip() or "Not a git repository"
        except FileNotFoundError:
            return None, "git not found"
        except subprocess.TimeoutExpired:
            return None, "git timed out"
        except Exception as e:
            return None, str(e)

    def get_git_branches(self, working_dir: str) -> tuple:
        """Return (list_of_branches, error_message) for the given directory."""
        try:
            result = subprocess.run(
                ["git", "branch", "--sort=-committerdate"],
                cwd=os.path.expanduser(working_dir),
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                branches = [b.lstrip("* ").strip() for b in result.stdout.splitlines() if b.strip()]
                return branches, None
            return [], result.stderr.strip() or "Not a git repository"
        except FileNotFoundError:
            return [], "git not found"
        except subprocess.TimeoutExpired:
            return [], "git timed out"
        except Exception as e:
            return [], str(e)

    def git_fetch(self, working_dir: str) -> tuple:
        """Run 'git fetch --all --tags --prune --force' in *working_dir*. Returns (success, message)."""
        try:
            result = subprocess.run(
                ["git", "fetch", "--all", "--tags", "--prune", "--force"],
                cwd=os.path.expanduser(working_dir),
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0:
                return True, result.stderr.strip() or "Fetch completed."
            return False, result.stderr.strip() or "git fetch failed"
        except FileNotFoundError:
            return False, "git not found"
        except subprocess.TimeoutExpired:
            return False, "git fetch timed out"
        except Exception as e:
            return False, str(e)

    def git_checkout(self, working_dir: str, branch: str) -> tuple:
        """Checkout *branch* in *working_dir*. Returns (success, message)."""
        try:
            result = subprocess.run(
                ["git", "checkout", branch],
                cwd=os.path.expanduser(working_dir),
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode == 0:
                return True, result.stderr.strip() or f"Switched to branch '{branch}'"
            return False, result.stderr.strip() or f"Failed to checkout '{branch}'"
        except FileNotFoundError:
            return False, "git not found"
        except subprocess.TimeoutExpired:
            return False, "git checkout timed out"
        except Exception as e:
            return False, str(e)

    def _normalize_path_to_relative(self, full_path):
        if "/data/" in full_path:
            return "/" + full_path.split("/data/", 1)[1]
        return full_path

    def _extract_file_info_from_path(self, path):
        if path.startswith("~/"):
            path = os.path.expanduser(path)
        if path.lower().endswith((".mcap", ".mp4")):
            filename = os.path.basename(path)
            folder_path = os.path.dirname(path)
            if "/data/" in path:
                folder_path = os.path.dirname(self._normalize_path_to_relative(path))
            return folder_path, filename
        return None, None

    def _extract_from_mpv_command(self, link):
        for part in link.split():
            if part.startswith(("http://", "https://")):
                return part
        return None

    def _extract_from_bazel_command(self, link):
        for part in link.split():
            if part.startswith("//") or part in ("bazel", "run"):
                continue
            if part.startswith("~/") or part.startswith("/home/") or "/data/" in part:
                return self._extract_file_info_from_path(part)
        return None, None

    def _extract_from_url(self, link):
        parsed_url = urllib.parse.urlparse(link)
        query_params = urllib.parse.parse_qs(parsed_url.query)

        if "ds.url" in query_params and query_params["ds.url"]:
            mcap_url_str = query_params["ds.url"][0]
            path_to_check = urllib.parse.urlparse(mcap_url_str).path
        else:
            path_to_check = parsed_url.path

        if not path_to_check:
            return None, None

        path_to_check = path_to_check.strip().rstrip("/")

        if path_to_check.lower().endswith((".mcap", ".mp4")):
            folder_path = os.path.dirname(path_to_check)
            filename = os.path.basename(path_to_check)
            return folder_path, filename

        return path_to_check, None

    def extract_info_from_link(self, link):
        if not link.strip():
            return None, None
        try:
            link = link.strip()
            if link.startswith("mpv "):
                url = self._extract_from_mpv_command(link)
                return self._extract_from_url(url) if url else (None, None)
            if link.startswith("bazel "):
                return self._extract_from_bazel_command(link)
            if not link.startswith(("http://", "https://")):
                result = self._extract_file_info_from_path(link)
                return result if result[0] is not None else (link, None)
            return self._extract_from_url(link)
        except Exception as e:
            self.log_callback(f"Error parsing link: {e}", is_error=True)
            return None, None

    def get_local_folder_path(self, extracted_remote_folder):
        relative_path = extracted_remote_folder.lstrip("/")

        main_path = os.path.join(self.local_base_path_absolute, relative_path)
        if os.path.isdir(main_path):
            return main_path

        backup_path = os.path.join(self.backup_base_path_absolute, relative_path)
        if os.path.isdir(backup_path):
            return backup_path

        self.log_callback(
            f"Could not find local directory for '{relative_path}' at primary or backup locations.", is_error=True
        )
        return main_path

    def _is_any_viz_running(self):
        viz_processes = {
            PROCESS_NAMES["FOXGLOVE_STUDIO"],
            PROCESS_NAMES["BAZEL_TOOLS_VIZ"],
            PROCESS_NAMES["BAZEL_BAG_GUI"],
        }
        with self._processes_lock:
            return any(p["process"].poll() is None and p["name"] in viz_processes for p in self.running_processes)

    def _terminate_process_by_name(self, name: str) -> None:
        with self._processes_lock:
            targets = [proc_info for proc_info in self.running_processes if proc_info["name"] == name]

        for proc_info in targets:
            if proc_info["name"] == name:
                proc = proc_info["process"]
                if proc.poll() is None:
                    self._kill_proc(proc, name)
                with self._processes_lock:
                    if proc_info in self.running_processes:
                        self.running_processes.remove(proc_info)

    def _is_process_running_by_name(self, name):
        with self._processes_lock:
            processes_snapshot = list(self.running_processes)
        for proc_info in processes_snapshot:
            if proc_info["name"] == name:
                if proc_info["process"].poll() is None:
                    return True
        return False

    def _kill_proc(self, proc, name: str) -> None:
        try:
            if sys.platform != "win32":
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            else:
                proc.terminate()
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            try:
                if sys.platform != "win32":
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                else:
                    proc.kill()
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.log_callback(f"Process {name} (PID: {proc.pid}) is unresponsive to SIGKILL", is_error=True)
            except (ProcessLookupError, PermissionError, OSError):
                pass
        except (ProcessLookupError, PermissionError, OSError):
            pass

    def _launch_process(self, command, name, cwd=None, mcap_path=None, startup_timeout=10, single_instance=None):
        if name == "Foxglove Studio (Browser)":
            if mcap_path:
                return self.launch_foxglove_browser(mcap_path)
            else:
                return None, "No MCAP file path provided for browser launch.", None

        use_shell = isinstance(command, str)
        if name == "Bazel Tools Viz":
            if self._is_process_running_by_name(name):
                return f"{name} is already running.", None, None
        elif name == "Foxglove Studio":
            self._terminate_process_by_name(name)
        elif name in ["Bazel Bag GUI", "MPV Video"]:
            if single_instance is None:
                single_instance = True
            if single_instance:
                self._terminate_process_by_name(name)

        try:
            if isinstance(command, list) and len(command) > 10:
                self.log_callback(f"Launching {name} with {len(command)-2} files...")

            preexec_fn = os.setsid if sys.platform != "win32" else None

            proc = subprocess.Popen(
                command,
                cwd=cwd,
                shell=use_shell,
                preexec_fn=preexec_fn,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            try:
                time.sleep(0.1)
                if proc.poll() is not None:
                    return (
                        None,
                        f"Process {name} failed to start (exited immediately). Check command and working directory.",
                        None,
                    )

            except subprocess.TimeoutExpired:
                pass
            except Exception as e:
                self.log_callback(f"Warning: Could not validate startup for {name}: {e}", is_error=True)

            with self._processes_lock:
                proc_id = self._process_id_counter
                self._process_id_counter += 1
                self.running_processes.append(
                    {
                        "name": name,
                        "process": proc,
                        "path": mcap_path,
                        "command": command,
                        "cwd": cwd,
                        "start_time": time.time(),
                        "id": proc_id,
                    }
                )

            return f"{name} launched (PID: {proc.pid}).", None, proc_id

        except FileNotFoundError:
            cmd_str = command if use_shell else command[0]
            return None, f"Command for '{name}' ('{cmd_str}') not found. Ensure it's installed and in PATH.", None
        except PermissionError as e:
            return None, f"Permission denied launching {name}: {e}", None
        except OSError as e:
            if "Argument list too long" in str(e):
                return None, f"Command too long for {name}. Try selecting fewer files.", None
            elif "No such file or directory" in str(e):
                return None, f"Command not found for {name}. Check installation and PATH.", None
            else:
                return None, f"System error launching {name}: {e}", None
        except Exception as e:
            return None, f"Failed to launch {name}: {e}", None

    def launch_foxglove(self, mcap_filepath_absolute, settings):
        self._max_foxglove_files = settings.get("max_foxglove_files", 50)

        if isinstance(mcap_filepath_absolute, list):
            mcap_filepaths = mcap_filepath_absolute
        else:
            mcap_filepaths = [mcap_filepath_absolute]

        if not mcap_filepaths:
            return None, "No MCAP files provided", None

        open_in_browser = settings.get("open_foxglove_in_browser", False)

        if len(mcap_filepaths) == 1:
            single_file = mcap_filepaths[0]
            if open_in_browser:
                return self.launch_foxglove_browser(single_file)
            else:
                return self.launch_foxglove_desktop(single_file)
        else:
            if open_in_browser:
                self.log_callback(
                    "Multiple MCAP files selected. Browser version doesn't support multiple files, "
                    "using desktop version instead."
                )
            return self.launch_foxglove_desktop_multiple(mcap_filepaths)

    def launch_foxglove_desktop(self, mcap_filepath_absolute):
        if not mcap_filepath_absolute:
            return None, "No MCAP file path provided", None

        if not os.path.isfile(mcap_filepath_absolute):
            return None, f"MCAP file not found: {os.path.basename(mcap_filepath_absolute)}", None

        command = ["foxglove-studio", "--file", mcap_filepath_absolute]
        return self._launch_process(command, "Foxglove Studio", mcap_path=mcap_filepath_absolute)

    def launch_foxglove_desktop_multiple(self, mcap_filepaths):
        if not mcap_filepaths:
            return None, "No MCAP files provided", None

        valid_files = [f for f in mcap_filepaths if os.path.isfile(f)]
        missing = [f for f in mcap_filepaths if not os.path.isfile(f)]
        if missing:
            if len(missing) <= 3:
                return None, f"MCAP files not found: {', '.join(os.path.basename(f) for f in missing)}", None
            return None, f"{len(missing)} MCAP files not found", None
        if not valid_files:
            return None, "No valid MCAP files found", None

        max_files = getattr(self, "_max_foxglove_files", 50)
        if len(valid_files) > max_files:
            self.log_callback(f"Too many files selected ({len(valid_files)}). Limiting to {max_files} files.")
            valid_files = valid_files[:max_files]

        command_base = ["foxglove-studio", "open"]
        max_cmd_length = self._get_max_command_length()
        base_length = sum(len(arg) + 1 for arg in command_base)
        if base_length + sum(len(f) + 3 for f in valid_files) > max_cmd_length:
            limited = self._limit_files_by_command_length(valid_files, max_cmd_length - base_length)
            if len(limited) < len(valid_files):
                self.log_callback(f"Command too long, limiting to {len(limited)} files (system limit)")
            valid_files = limited

        return self._launch_process(command_base + valid_files, "Foxglove Studio", mcap_path=valid_files[0])

    def _get_max_command_length(self):
        try:
            result = subprocess.run(["getconf", "ARG_MAX"], capture_output=True, text=True, timeout=1)
            if result.returncode == 0:
                return int(int(result.stdout.strip()) * 0.8)
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, ValueError, OSError):
            pass
        return 32768

    def _limit_files_by_command_length(self, filepaths, max_length):
        selected, total = [], 0
        for fp in sorted(filepaths, key=len):
            cost = len(fp) + 3
            if total + cost > max_length:
                break
            selected.append(fp)
            total += cost
        return selected

    def launch_foxglove_browser(self, mcap_filepath_absolute):
        if not os.path.isfile(mcap_filepath_absolute):
            return None, f"MCAP file not found: {mcap_filepath_absolute}", None

        prefix = os.path.expanduser("~/data")
        relative_path = mcap_filepath_absolute.removeprefix(prefix)
        url = f"{FOXGLOVE_REMOTE_BASE_URL}?ds=remote-file&ds.url={FOXGLOVE_DS_URL}{relative_path}"

        success, message = open_url_in_browser(url)
        if success:
            return f"Foxglove Studio launched in browser with {os.path.basename(mcap_filepath_absolute)}.", None, None
        else:
            return None, message, None

    def _build_bazel_bag_cmd(self, base_command, rate, files_str, start_time):
        if start_time is not None:
            self.log_callback(f"Starting playback at offset: {int(start_time)}s")
            return f"{base_command} -- --start-offset {int(start_time)} --rate={rate} {files_str}"
        return f"{base_command} -- --rate={rate} {files_str}"

    def launch_bazel_tools_viz(self, settings):
        self.bazel_working_dir = self.get_bazel_working_dir(settings)
        if not self.bazel_working_dir or not os.path.isdir(self.bazel_working_dir):
            return None, f"Bazel working directory not found: {self.bazel_working_dir}", None
        command = DEFAULT_SETTINGS["bazel_tools_viz_cmd"]
        return self._launch_process(command, "Bazel Tools Viz", cwd=self.bazel_working_dir)

    def launch_bazel_tool(self, settings, command, tool_name):
        self.bazel_working_dir = self.get_bazel_working_dir(settings)
        if not self.bazel_working_dir or not os.path.isdir(self.bazel_working_dir):
            return None, f"Bazel working directory not found: {self.bazel_working_dir}", None
        return self._launch_process(command, tool_name, cwd=self.bazel_working_dir)

    def run_bazel_build(self, settings):
        self.bazel_working_dir = self.get_bazel_working_dir(settings)
        if not self.bazel_working_dir or not os.path.isdir(self.bazel_working_dir):
            return None, f"Bazel working directory not found: {self.bazel_working_dir}"

        self.log_callback("Running: bazel build //...")
        self.log_callback("=" * 60)
        try:
            process = subprocess.Popen(
                ["bazel", "build", "//..."],
                cwd=self.bazel_working_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            for line in process.stdout:
                line = line.rstrip()
                if line:
                    self.log_callback(line)

            return_code = process.wait(timeout=600)
            self.log_callback("=" * 60)

            if return_code == 0:
                return "✓ Bazel build completed successfully.", None
            else:
                return None, f"Build failed with exit code {return_code}"

        except subprocess.TimeoutExpired:
            process.kill()
            return None, "Build timed out after 10 minutes"
        except FileNotFoundError:
            return None, "Bazel command not found. Ensure bazel is installed and in PATH."
        except Exception as e:
            return None, f"Build error: {e}"

    def launch_bazel_bag_gui(self, mcap_path, settings, start_time=None):
        self.bazel_working_dir = self.get_bazel_working_dir(settings)
        base_command = DEFAULT_SETTINGS["bazel_bag_gui_cmd"]
        command = self._build_bazel_bag_cmd(
            base_command, settings.get("bazel_bag_gui_rate", 1.0), mcap_path, start_time
        )
        return self._launch_process(
            command,
            "Bazel Bag GUI",
            cwd=self.bazel_working_dir,
            mcap_path=mcap_path,
            single_instance=settings.get("single_instance_rosbag", True),
        )

    def play_bazel_bag_gui_with_symlinks(self, mcap_filepaths, settings, start_time=None):
        self.bazel_working_dir = self.get_bazel_working_dir(settings)
        symlink_logic = SymlinkPlaybackLogic(log_callback=self.log_callback)
        symlink_dir, error = symlink_logic.prepare_symlinks(mcap_filepaths)
        if error:
            return None, error, symlink_dir
        mcap_files = symlink_logic.get_symlinked_mcap_files()
        if not mcap_files:
            return None, "No .mcap files found to play.", symlink_dir
        files_str = " ".join(f'"{f}"' for f in mcap_files)
        base_command = DEFAULT_SETTINGS["bazel_bag_gui_cmd"]
        command = self._build_bazel_bag_cmd(
            base_command, settings.get("bazel_bag_gui_rate", 1.0), files_str, start_time
        )
        message, error, proc_id = self._launch_process(
            command,
            "Bazel Bag GUI",
            cwd=self.bazel_working_dir,
            mcap_path=symlink_dir,
            single_instance=settings.get("single_instance_rosbag", True),
        )
        return message, error, symlink_dir, proc_id

    def launch_mpv_video(self, video_filepath, start_offset, settings):
        if not video_filepath:
            return None, "No video file path provided", None

        if not os.path.isfile(video_filepath):
            return None, f"Video file not found: {os.path.basename(video_filepath)}", None

        single_instance = settings.get("single_instance_video", True)
        command = ["mpv", f"--start={int(start_offset)}", video_filepath]
        return self._launch_process(command, "MPV Video", mcap_path=video_filepath, single_instance=single_instance)

    def check_process_loaded(self, process_name):
        with self._processes_lock:
            processes_snapshot = list(self.running_processes)
        for proc_info in processes_snapshot:
            if proc_info["name"] == process_name:
                if proc_info["process"].poll() is None:
                    runtime = time.time() - proc_info["start_time"]
                    return True, f"{process_name} is running (runtime: {runtime:.1f}s, PID: {proc_info['process'].pid})"
                else:
                    return False, f"{process_name} has exited unexpectedly"
        return False, f"{process_name} not found in running processes"

    def terminate_process_by_id(self, proc_id: int) -> bool:
        with self._processes_lock:
            processes_snapshot = list(self.running_processes)

        for proc_info in processes_snapshot:
            if proc_info.get("id") == proc_id:
                proc = proc_info["process"]
                name = proc_info["name"]
                if proc.poll() is None:
                    self._kill_proc(proc, name)
                    self.log_callback(f"{name} terminated (ID: {proc_id}).")
                with self._processes_lock:
                    if proc_info in self.running_processes:
                        self.running_processes.remove(proc_info)
                return True
        return False

    def terminate_all_processes(self):
        self._stop_process_monitor()
        msgs = []
        with self._processes_lock:
            processes_snapshot = list(self.running_processes)

        if not processes_snapshot:
            msgs.append("No processes were recorded as running by this application.")
        for proc_info in processes_snapshot:
            proc, name = proc_info["process"], proc_info["name"]
            if proc.poll() is None:
                msgs.append(f"Terminating {name} (PID: {proc.pid})...")
                try:
                    self._kill_proc(proc, name)
                    msgs.append(f"{name} terminated.")
                except Exception as e:
                    msgs.append(f"Error terminating {name}: {e}")
            else:
                msgs.append(f"{name} (PID: {proc.pid}) was already terminated.")
            with self._processes_lock:
                if proc_info in self.running_processes:
                    self.running_processes.remove(proc_info)
        symlink_dir = "/tmp/selected_bags_symlinks"
        if os.path.exists(symlink_dir):
            try:
                shutil.rmtree(symlink_dir, ignore_errors=True)
                msgs.append(f"Cleaned up symlink dir: {symlink_dir}")
            except Exception as e:
                msgs.append(f"Error cleaning symlink dir: {e}")
        if not msgs:
            msgs.append("Cleanup complete. No active processes found.")
        final = self.get_process_status()
        msgs.append(f"Final status: {final['running']} running, {final['total']} total tracked")
        return "\n".join(msgs)

    def list_subfolders_in_path(self, folder_path):
        if not os.path.isdir(folder_path):
            return []
        return [
            os.path.join(folder_path, d) for d in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, d))
        ]

    def list_default_subfolders(self):
        return self.list_subfolders_in_path(os.path.join(self.local_base_path_absolute, "default"))

    def find_parent_default_folder(self, path):
        if not path:
            return None
        parent_default = path
        while parent_default and os.path.basename(parent_default) != "default":
            new_parent = os.path.dirname(parent_default)
            if new_parent == parent_default:
                break
            parent_default = new_parent
        if os.path.basename(parent_default) == "default":
            return parent_default
        return None

    def get_effective_default_folder(self, current_path=None):
        if not current_path:
            current_path = os.path.expanduser("~/data/default")
        parent_default = self.find_parent_default_folder(current_path)
        if parent_default:
            return parent_default
        return os.path.expanduser("~/data/default")
