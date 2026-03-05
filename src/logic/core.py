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

        # Process health monitoring
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

        for proc_info in list(self.running_processes):
            proc = proc_info["process"]
            if proc.poll() is not None:  # Process has terminated
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

        for proc_info in dead_processes:
            if proc_info in self.running_processes:
                self.running_processes.remove(proc_info)

    def get_process_status(self):
        """Get current status of all tracked processes."""
        status = {"total": len(self.running_processes), "running": 0, "dead": 0, "processes": []}

        current_time = time.time()
        for proc_info in self.running_processes:
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
        """Updates the primary and backup search paths."""
        if primary_path:
            self.local_base_path_absolute = primary_path
        if backup_path:
            self.backup_base_path_absolute = backup_path

    def set_runtime_settings(self, settings: dict) -> None:
        """Update runtime settings used by launchers and playback."""
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

    def _normalize_path_to_relative(self, full_path):
        """Convert absolute path to relative from /data/ root."""
        if "/data/" in full_path:
            return "/" + full_path.split("/data/", 1)[1]
        return full_path

    def _extract_file_info_from_path(self, path):
        """Return (folder, filename) for .mcap/.mp4 paths, else (None, None)."""
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
        """Extract the URL token from an mpv command string."""
        for part in link.split():
            if part.startswith(("http://", "https://")):
                return part
        return None

    def _extract_from_bazel_command(self, link):
        """Extract (folder, filename) from a bazel run command string."""
        for part in link.split():
            if part.startswith("//") or part in ("bazel", "run"):
                continue
            if part.startswith("~/") or part.startswith("/home/") or "/data/" in part:
                return self._extract_file_info_from_path(part)
        return None, None

    def _extract_from_url(self, link):
        """Extract (folder, filename) from a Foxglove or direct URL."""
        parsed_url = urllib.parse.urlparse(link)
        query_params = urllib.parse.parse_qs(parsed_url.query)

        # Foxglove link with ds.url parameter
        if "ds.url" in query_params and query_params["ds.url"]:
            mcap_url_str = query_params["ds.url"][0]
            path_to_check = urllib.parse.urlparse(mcap_url_str).path
        # Direct link
        else:
            path_to_check = parsed_url.path

        if not path_to_check:
            return None, None

        # Normalize path - remove trailing slash and whitespace
        path_to_check = path_to_check.strip().rstrip("/")

        # Check if it's a file (.mcap or .mp4)
        if path_to_check.lower().endswith((".mcap", ".mp4")):
            folder_path = os.path.dirname(path_to_check)
            filename = os.path.basename(path_to_check)
            return folder_path, filename

        # It's a directory path (like /logs)
        return path_to_check, None

    def extract_info_from_link(self, link):
        """Parse a Foxglove URL, direct URL, bazel/mpv command, or file path.

        Returns (folder_path, filename) or (None, None) on failure.
        """
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
        """Map a remote folder path to local; tries main path then backup."""
        relative_path = extracted_remote_folder.lstrip("/")

        main_path = os.path.join(self.local_base_path_absolute, relative_path)
        if os.path.isdir(main_path):
            return main_path

        # Try backup path
        backup_path = os.path.join(self.backup_base_path_absolute, relative_path)
        if os.path.isdir(backup_path):
            return backup_path

        # If neither path exists, return the intended main path, but log that it's not found
        self.log_callback(
            f"Could not find local directory for '{relative_path}' at primary or backup locations.", is_error=True
        )
        return main_path

    def list_files_in_directory(self, local_folder_path_absolute, file_extension=None):
        """List files in a directory, optionally filtered by extension. Returns (items, error)."""
        if not os.path.isdir(local_folder_path_absolute):
            return [], f"Local folder not found or is not a directory: {local_folder_path_absolute}"
        try:
            ext_lower = file_extension.lower() if file_extension else None
            items = [
                item
                for item in os.listdir(local_folder_path_absolute)
                if ext_lower is None or item.lower().endswith(ext_lower)
            ]
            items.sort(key=str.lower)
            return items, None
        except PermissionError:
            return [], f"Permission denied to access folder: {local_folder_path_absolute}"
        except Exception as e:
            return [], f"An unexpected error occurred while listing files: {e}"

    def _is_any_viz_running(self):
        viz_processes = {
            PROCESS_NAMES["FOXGLOVE_STUDIO"],
            PROCESS_NAMES["BAZEL_TOOLS_VIZ"],
            PROCESS_NAMES["BAZEL_BAG_GUI"],
        }
        return any(p["process"].poll() is None and p["name"] in viz_processes for p in self.running_processes)

    def _terminate_process_by_name(self, name: str) -> None:
        for proc_info in list(self.running_processes):
            if proc_info["name"] == name:
                proc = proc_info["process"]
                if proc.poll() is None:
                    self._kill_proc(proc, name)
                if proc_info in self.running_processes:
                    self.running_processes.remove(proc_info)

    def _is_process_running_by_name(self, name):
        for proc_info in self.running_processes:
            if proc_info["name"] == name:
                if proc_info["process"].poll() is None:
                    return True
        return False

    def _kill_proc(self, proc, name: str) -> None:
        """Send SIGTERM then SIGKILL (if needed) to *proc*."""
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
                return f"{name} is already running.", None
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

            # Redirect output to DEVNULL to prevent pipe buffer blocking in long-running GUI processes
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
        """Launch Foxglove Studio in browser with the specified MCAP file."""
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
        """Build the bazel bag GUI shell command string."""
        if start_time is not None:
            self.log_callback(f"Starting playback at offset: {int(start_time)}s")
            return f"{base_command} -- --start-offset {int(start_time)} --rate={rate} {files_str}"
        return f"{base_command} -- --rate={rate} {files_str}"

    def launch_bazel_tools_viz(self, settings):
        self.bazel_working_dir = self.get_bazel_working_dir(settings)
        if not self.bazel_working_dir or not os.path.isdir(self.bazel_working_dir):
            return None, f"Bazel working directory not found: {self.bazel_working_dir}", None
        return self._launch_process(settings.get("bazel_tools_viz_cmd"), "Bazel Tools Viz", cwd=self.bazel_working_dir)

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
        command = self._build_bazel_bag_cmd(
            settings.get("bazel_bag_gui_cmd"), settings.get("bazel_bag_gui_rate", 1.0), mcap_path, start_time
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
        command = self._build_bazel_bag_cmd(
            settings.get("bazel_bag_gui_cmd"), settings.get("bazel_bag_gui_rate", 1.0), files_str, start_time
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
        for proc_info in self.running_processes:
            if proc_info["name"] == process_name:
                if proc_info["process"].poll() is None:
                    runtime = time.time() - proc_info["start_time"]
                    return True, f"{process_name} is running (runtime: {runtime:.1f}s, PID: {proc_info['process'].pid})"
                else:
                    return False, f"{process_name} has exited unexpectedly"
        return False, f"{process_name} not found in running processes"

    def terminate_process_by_id(self, proc_id: int) -> bool:
        """Terminate a specific process by its ID."""
        for proc_info in list(self.running_processes):
            if proc_info.get("id") == proc_id:
                proc = proc_info["process"]
                name = proc_info["name"]
                if proc.poll() is None:
                    self._kill_proc(proc, name)
                    self.log_callback(f"{name} terminated (ID: {proc_id}).")
                if proc_info in self.running_processes:
                    self.running_processes.remove(proc_info)
                return True
        return False

    def terminate_all_processes(self):
        self._stop_process_monitor()
        msgs = []
        if not self.running_processes:
            msgs.append("No processes were recorded as running by this application.")
        for proc_info in list(self.running_processes):
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
