import os
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.parse

from .logic.symlink_playback_logic import SymlinkPlaybackLogic

# Constants for better maintainability
DEFAULT_DATA_PATH = os.path.expanduser("~/data")
DEFAULT_BACKUP_PATH = os.path.expanduser("~/data/psa_logs_backup_nas3")
DEFAULT_BAZEL_WORKING_DIR = os.path.expanduser("~/av-system/catkin_ws/src")
SYMLINK_DIR = "/tmp/selected_bags_symlinks"

# Default settings
DEFAULT_SETTINGS = {
    "bazel_tools_viz_cmd": "bazel run //tools/viz",
    "bazel_bag_gui_cmd": "bazel run //tools/bag:gui",
    "bazel_working_dir": DEFAULT_BAZEL_WORKING_DIR,
    "bazel_bag_gui_rate": 1.0,
}

# Process names for better consistency
PROCESS_NAMES = {
    "FOXGLOVE_STUDIO": "Foxglove Studio",
    "FOXGLOVE_BROWSER": "Foxglove Studio (Browser)",
    "BAZEL_TOOLS_VIZ": "Bazel Tools Viz",
    "BAZEL_BAG_GUI": "Bazel Bag GUI",
}


def perform_operation(data):
    # Placeholder for core logic operation
    # Implement the main functionality of the application here
    return data


class FoxgloveAppLogic:
    def __init__(self, log_callback=None):
        self.running_processes = []
        self.local_base_path_absolute = DEFAULT_DATA_PATH
        self.backup_base_path_absolute = DEFAULT_BACKUP_PATH
        self.bazel_working_dir = None
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
        while not self._monitor_stop_event.wait(10):  # Check every 10 seconds
            try:
                self._cleanup_dead_processes()
            except Exception as e:
                # Log errors but don't crash the monitor
                self.log_callback(f"Process monitor error: {e}", is_error=True)

    def _cleanup_dead_processes(self):
        """Remove dead processes from tracking list to prevent zombie accumulation."""
        dead_processes = []
        current_time = time.time()

        for proc_info in list(self.running_processes):
            proc = proc_info["process"]
            if proc.poll() is not None:  # Process has terminated
                dead_processes.append(proc_info)
            else:
                # Check for potentially hanging processes (running for more than 2 hours)
                start_time = proc_info.get("start_time", current_time)
                runtime = current_time - start_time
                if runtime > 7200:  # 2 hours
                    self.log_callback(
                        f"Long-running process detected: {proc_info['name']} "
                        f"(PID: {proc.pid}, runtime: {runtime/3600:.1f}h)",
                        is_error=False,
                    )

        # Remove dead processes from tracking
        for proc_info in dead_processes:
            if proc_info in self.running_processes:
                self.running_processes.remove(proc_info)
                # Optionally log cleanup (commented to avoid spam)
                # self.log_callback(f"Cleaned up terminated process: {proc_info['name']}")

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
            self._process_monitor_thread.join(timeout=2)  # Wait max 2 seconds

    def update_search_paths(self, primary_path, backup_path):
        """Updates the primary and backup search paths."""
        if primary_path:
            self.local_base_path_absolute = primary_path
        if backup_path:
            self.backup_base_path_absolute = backup_path

    def load_settings(self):
        """
        Loads settings from a JSON file, or returns defaults if not found.
        """
        # Remove any code that references self.settings_path, as settings are now managed in SettingsTab.
        return DEFAULT_SETTINGS.copy()

    def save_settings(self, settings_dict):
        """
        Saves provided settings to the JSON file.
        """
        try:
            # Update the current settings with the new values
            # self.settings.update(settings_dict) # self.settings is no longer present
            # with open(self.settings_path, 'w') as f: # self.settings_path is no longer present
            #     json.dump(self.settings, f, indent=4)
            # After saving, update any properties that depend on settings
            self.bazel_working_dir = self.get_bazel_working_dir()
            return True, None
        except Exception as e:
            return False, str(e)

    def reset_settings(self):
        """Resets settings to their default values and saves them."""
        default_settings = {
            "bazel_tools_viz_cmd": "bazel run //tools/viz",
            "bazel_bag_gui_cmd": "bazel run //tools/bag:gui",
            "bazel_working_dir": os.path.expanduser("~/av-system/catkin_ws/src"),
            "bazel_bag_gui_rate": 1.0,
        }
        # self.settings = default_settings.copy() # self.settings is no longer present
        self.save_settings(default_settings)

    def get_setting(self, key):
        """Gets a specific setting value by key."""
        # self.settings.get(key) # self.settings is no longer present
        return None  # Placeholder as settings are not managed here

    def get_bazel_working_dir(self, settings=None):
        if settings is not None:
            return settings.get("bazel_working_dir")
        return None

    def extract_info_from_link(self, link):
        """
        Extracts the folder path and filename from a Foxglove link,
        a direct URL to a file or folder, or a bazel/mpv command with file path.
        Handles .mcap, .mp4, and /logs directories.
        Supports:
        - Foxglove links with ds.url parameter
        - Direct URLs (https://...)
        - Bazel commands (bazel run //tools/bag:gui <path>)
        - mpv commands (mpv --start=<time> <url>)
        - Direct file paths (~/data/... or /home/...)
        """
        if not link.strip():
            return None, None

        try:
            link = link.strip()

            # Case 1: mpv command format - extract the URL after mpv command
            # Format: mpv --start=3649 https://...
            if link.startswith("mpv "):
                # Split by whitespace and find the URL (starts with http)
                parts = link.split()
                for part in parts:
                    if part.startswith(("http://", "https://")):
                        # Process this URL through the URL handler below
                        link = part
                        break
                else:
                    # No URL found in mpv command
                    return None, None

            # Case 2: Bazel command format - extract the file path after bazel command
            # Format: bazel run //tools/bag:gui <path>
            elif link.startswith("bazel "):
                # Split by whitespace and find the path argument (after the bazel command parts)
                parts = link.split()
                # Find the path - it's typically after "bazel run //tools/bag:gui" or similar
                # Look for the first part that looks like a path (starts with ~/ or /home/, or contains /data/)
                for part in parts:
                    # Skip bazel targets (start with //) and bazel keywords
                    if part.startswith("//") or part in ("bazel", "run"):
                        continue

                    # Look for actual file paths
                    if part.startswith("~/") or part.startswith("/home/") or "/data/" in part:
                        # Expand ~ to home directory if present
                        if part.startswith("~/"):
                            part = os.path.expanduser(part)

                        # Check if it's a file
                        if part.lower().endswith((".mcap", ".mp4")):
                            folder_path = os.path.dirname(part)
                            filename = os.path.basename(part)
                            # Convert to relative path from data directory
                            if "/data/" in part:
                                # Extract the path after /data/
                                relative_path = "/" + part.split("/data/", 1)[1]
                                folder_path = os.path.dirname(relative_path)
                            return folder_path, filename
                        return None, None
                return None, None

            # Case 3: Direct file path (not a URL or command)
            # Format: ~/data/... or /home/.../data/...
            if not link.startswith(("http://", "https://")):
                # Expand ~ to home directory if present
                if link.startswith("~/"):
                    link = os.path.expanduser(link)

                # Check if it's a file
                if link.lower().endswith((".mcap", ".mp4")):
                    folder_path = link
                    filename = os.path.basename(link)
                    # Convert to relative path from data directory
                    if "/data/" in link:
                        # Extract the path after /data/
                        relative_path = "/" + link.split("/data/", 1)[1]
                        folder_path = os.path.dirname(relative_path)
                    else:
                        folder_path = os.path.dirname(link)
                    return folder_path, filename
                return link, None

            # Case 4: URL-based (Foxglove or direct URL)
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
            lower_path = path_to_check.lower()
            if lower_path.endswith((".mcap", ".mp4")):
                folder_path = os.path.dirname(path_to_check)
                filename = os.path.basename(path_to_check)
                return folder_path, filename

            # It's a directory path (like /logs)
            return path_to_check, None

        except Exception as e:
            self.log_callback(f"Error parsing link: {e}", is_error=True)
            return None, None

    def get_local_folder_path(self, extracted_remote_folder):
        """
        Constructs the absolute local folder path from the extracted remote folder.
        It handles paths from URLs that map to a local base directory.
        Tries the main data path, then a backup path if not found.
        """
        # The extracted_remote_folder is already the path segment (e.g., /20250718/PROD/...)
        if extracted_remote_folder.startswith("/"):
            relative_path = extracted_remote_folder[1:]
        else:
            relative_path = extracted_remote_folder

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
        """
        Lists files in the specified local directory, optionally filtering by a file extension.
        If file_extension is None, it lists all files and directories.
        Returns a tuple: (list_of_items, error_message_or_None)
        Optimized for better performance.
        """
        if not os.path.isdir(local_folder_path_absolute):
            return [], f"Local folder not found or is not a directory: {local_folder_path_absolute}"

        try:
            # Use list comprehension for better performance
            if file_extension:
                # Pre-compile the extension check for better performance
                ext_lower = file_extension.lower()
                items = [item for item in os.listdir(local_folder_path_absolute) if item.lower().endswith(ext_lower)]
            else:
                items = list(os.listdir(local_folder_path_absolute))

            items.sort(key=str.lower)  # Case-insensitive sort for better UX
            return items, None

        except PermissionError:
            return [], f"Permission denied to access folder: {local_folder_path_absolute}"
        except Exception as e:
            return [], f"An unexpected error occurred while listing files: {e}"

    def _is_any_viz_running(self):
        """
        Returns True if any viz process (Foxglove, Bazel Tools Viz, Bazel Bag GUI) is running.
        """
        viz_processes = {
            PROCESS_NAMES["FOXGLOVE_STUDIO"],
            PROCESS_NAMES["BAZEL_TOOLS_VIZ"],
            PROCESS_NAMES["BAZEL_BAG_GUI"],
        }

        for proc_info in self.running_processes:
            proc = proc_info["process"]
            if proc.poll() is None and proc_info["name"] in viz_processes:
                return True
        return False

    def _terminate_process_by_name(self, name):
        """
        Terminates any running process with the given name and its children.
        Improved error handling and cross-platform compatibility with timeout protection.
        """
        for proc_info in list(self.running_processes):
            if proc_info["name"] == name:
                proc = proc_info["process"]
                if proc.poll() is None:  # Process is still running
                    try:
                        # Terminate the entire process group
                        if sys.platform != "win32":
                            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                        else:
                            proc.terminate()

                        # Wait for graceful termination with timeout
                        proc.wait(timeout=3)

                    except subprocess.TimeoutExpired:
                        # Force kill if graceful termination failed
                        try:
                            if sys.platform != "win32":
                                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                            else:
                                proc.kill()
                            # Add timeout to prevent hanging on wait after kill
                            proc.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            # Process is completely unresponsive, log and continue
                            self.log_callback(
                                f"Process {name} (PID: {proc.pid}) is unresponsive to SIGKILL", is_error=True
                            )
                        except (ProcessLookupError, PermissionError, OSError):
                            # Process might have already died or access denied
                            pass
                    except (ProcessLookupError, PermissionError, OSError):
                        # Process already died between poll() and killpg() or permission denied
                        pass

                # Remove from tracking list
                if proc_info in self.running_processes:
                    self.running_processes.remove(proc_info)

    def _is_process_running_by_name(self, name):
        for proc_info in self.running_processes:
            if proc_info["name"] == name:
                proc = proc_info["process"]
                if proc.poll() is None:
                    return True
        return False

    def _launch_process(self, command, name, cwd=None, mcap_path=None, startup_timeout=10):
        """
        Enhanced process launcher with better error handling, performance monitoring, and timeout controls.

        Args:
            command: Command to execute (string or list)
            name: Process name for tracking
            cwd: Working directory
            mcap_path: MCAP file path for tracking
            startup_timeout: Timeout in seconds for process startup validation
        """
        if name == "Foxglove Studio (Browser)":
            # Special case: launch in browser instead of as a process
            if mcap_path:
                return self.launch_foxglove_browser(mcap_path)
            else:
                return None, "No MCAP file path provided for browser launch."

        # Use shell=True for commands that are strings, False for lists of args
        use_shell = isinstance(command, str)

        # Process management optimization
        if name == "Bazel Tools Viz":
            if self._is_process_running_by_name(name):
                return f"{name} is already running.", None
        elif name in ["Foxglove Studio", "Bazel Bag GUI"]:
            self._terminate_process_by_name(name)

        try:
            # Performance monitoring for large commands
            if isinstance(command, list) and len(command) > 10:
                self.log_callback(f"Launching {name} with {len(command)-2} files...")

            # On Unix, start the process in a new session to control its process group
            preexec_fn = os.setsid if sys.platform != "win32" else None

            # Redirect all output to DEVNULL to prevent pipe buffer blocking
            # Long-running GUI processes can produce large amounts of output which would
            # fill pipe buffers and cause the process to hang waiting for reads
            # Trade-off: We lose detailed error messages, but GUI tools show their own errors anyway
            proc = subprocess.Popen(
                command,
                cwd=cwd,
                shell=use_shell,
                preexec_fn=preexec_fn,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            # Validate process startup with timeout
            try:
                # Give the process a moment to start and check if it immediately fails
                time.sleep(0.1)
                if proc.poll() is not None:
                    # Process exited immediately - since we're using DEVNULL, we can't get detailed errors
                    return (
                        None,
                        f"Process {name} failed to start (exited immediately). Check command and working directory.",
                    )

            except subprocess.TimeoutExpired:
                # Process is taking time to start, which is normal for some applications
                pass
            except Exception as e:
                self.log_callback(f"Warning: Could not validate startup for {name}: {e}", is_error=True)

            self.running_processes.append(
                {
                    "name": name,
                    "process": proc,
                    "path": mcap_path,
                    "command": command,
                    "cwd": cwd,
                    "start_time": time.time(),  # Add timestamp for monitoring
                }
            )

            return f"{name} launched (PID: {proc.pid}).", None

        except FileNotFoundError:
            cmd_str = command if use_shell else command[0]
            return None, f"Command for '{name}' ('{cmd_str}') not found. Ensure it's installed and in PATH."
        except PermissionError as e:
            return None, f"Permission denied launching {name}: {e}"
        except OSError as e:
            # Handle system-level errors (e.g., command too long)
            if "Argument list too long" in str(e):
                return None, f"Command too long for {name}. Try selecting fewer files."
            elif "No such file or directory" in str(e):
                return None, f"Command not found for {name}. Check installation and PATH."
            else:
                return None, f"System error launching {name}: {e}"
        except Exception as e:
            return None, f"Failed to launch {name}: {e}"

    def launch_foxglove(self, mcap_filepath_absolute, settings):
        """
        Launches Foxglove Studio with the given .mcap file(s).
        Can handle single file or multiple files (desktop only for multiple).
        Returns a tuple: (message, error)
        Optimized for performance with batch validation and smart routing.
        """
        # Store max files setting for use in other methods
        self._max_foxglove_files = settings.get("max_foxglove_files", 50)

        # Normalize input to list format for consistent processing
        if isinstance(mcap_filepath_absolute, list):
            mcap_filepaths = mcap_filepath_absolute
        else:
            mcap_filepaths = [mcap_filepath_absolute]

        # Early validation: empty list check
        if not mcap_filepaths:
            return None, "No MCAP files provided"

        open_in_browser = settings.get("open_foxglove_in_browser", False)

        # Optimized routing based on file count and user preference
        if len(mcap_filepaths) == 1:
            # Single file - use user's preference
            single_file = mcap_filepaths[0]
            if open_in_browser:
                return self.launch_foxglove_browser(single_file)
            else:
                return self.launch_foxglove_desktop(single_file)
        else:
            # Multiple files - force desktop version with notification
            if open_in_browser:
                self.log_callback(
                    "Multiple MCAP files selected. Browser version doesn't support multiple files, "
                    "using desktop version instead."
                )
            return self.launch_foxglove_desktop_multiple(mcap_filepaths)

    def launch_foxglove_desktop(self, mcap_filepath_absolute):
        """
        Launches Foxglove Studio desktop with a single MCAP file.
        Optimized with validation and better error handling.
        """
        # Early validation for better performance
        if not mcap_filepath_absolute:
            return None, "No MCAP file path provided"

        if not os.path.isfile(mcap_filepath_absolute):
            return None, f"MCAP file not found: {os.path.basename(mcap_filepath_absolute)}"

        # Use optimized command format
        command = ["foxglove-studio", "--file", mcap_filepath_absolute]
        return self._launch_process(command, "Foxglove Studio", mcap_path=mcap_filepath_absolute)

    def launch_foxglove_desktop_multiple(self, mcap_filepaths):
        """
        Launches Foxglove Studio desktop with multiple MCAP files.
        Uses the 'foxglove-studio open file1.mcap file2.mcap ...' command format.
        Returns a tuple: (message, error)
        Optimized for performance with batch validation and command size limits.
        """
        if not mcap_filepaths:
            return None, "No MCAP files provided"

        # Performance optimization: batch validate all files at once
        validation_results = self._batch_validate_files(mcap_filepaths)
        if validation_results["missing_files"]:
            missing_count = len(validation_results["missing_files"])
            if missing_count <= 3:
                # Show specific files if few are missing
                missing_names = [os.path.basename(f) for f in validation_results["missing_files"]]
                return None, f"MCAP files not found: {', '.join(missing_names)}"
            else:
                # Show count if many are missing
                return None, f"{missing_count} MCAP files not found"

        valid_files = validation_results["valid_files"]
        if not valid_files:
            return None, "No valid MCAP files found"

        # Apply user-configured file limit for performance
        max_files = getattr(self, "_max_foxglove_files", 50)  # Default fallback
        if len(valid_files) > max_files:
            self.log_callback(
                f"Too many files selected ({len(valid_files)}). Limiting to {max_files} files for performance."
            )
            valid_files = valid_files[:max_files]

        # Check command line length limits to prevent system errors
        max_cmd_length = self._get_max_command_length()
        command_base = ["foxglove-studio", "open"]

        # Estimate command length (conservative approach)
        base_length = sum(len(arg) + 1 for arg in command_base)  # +1 for spaces
        files_length = sum(len(f) + 3 for f in valid_files)  # +3 for quotes and space

        if base_length + files_length > max_cmd_length:
            # Fallback: use file list approach or limit files
            limited_files = self._limit_files_by_command_length(valid_files, max_cmd_length - base_length)
            if len(limited_files) < len(valid_files):
                self.log_callback(f"Command too long, limiting to {len(limited_files)} files (system limit)")
            valid_files = limited_files

        # Build optimized command
        command = command_base + valid_files

        # Use the first file path for tracking purposes
        primary_mcap_path = valid_files[0]

        return self._launch_process(command, "Foxglove Studio", mcap_path=primary_mcap_path)

    def _batch_validate_files(self, filepaths):
        """
        Efficiently validate multiple files in batch.
        Returns dict with 'valid_files' and 'missing_files' lists.
        """
        valid_files = []
        missing_files = []

        # Use os.path.isfile directly for better performance than try/catch
        for filepath in filepaths:
            if os.path.isfile(filepath):
                valid_files.append(filepath)
            else:
                missing_files.append(filepath)

        return {"valid_files": valid_files, "missing_files": missing_files}

    def _get_max_command_length(self):
        """
        Get maximum command line length for the current system.
        Returns conservative default if unable to determine.
        """
        try:
            # Try to get system limit
            import subprocess

            result = subprocess.run(["getconf", "ARG_MAX"], capture_output=True, text=True, timeout=1)
            if result.returncode == 0:
                # Use 80% of system limit as safety margin
                return int(int(result.stdout.strip()) * 0.8)
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, ValueError, OSError):
            pass

        # Conservative fallback (works on most systems)
        return 32768  # 32KB - safe for most Unix systems

    def _limit_files_by_command_length(self, filepaths, max_length):
        """
        Limit file list to fit within command length constraints.
        Prioritizes shorter paths and warns user about limitation.
        """
        if not filepaths:
            return []

        # Sort by path length (shorter paths first for efficiency)
        sorted_files = sorted(filepaths, key=len)

        selected_files = []
        current_length = 0

        for filepath in sorted_files:
            file_length = len(filepath) + 3  # +3 for quotes and space
            if current_length + file_length <= max_length:
                selected_files.append(filepath)
                current_length += file_length
            else:
                break

        return selected_files

    def launch_foxglove_browser(self, mcap_filepath_absolute):
        """
        Launches Foxglove Studio in a web browser with the given .mcap file.
        Returns a tuple: (message, error)
        """
        if not os.path.isfile(mcap_filepath_absolute):
            return None, f"MCAP file not found: {mcap_filepath_absolute}"

        # Encode the file path for URL
        prefix = os.path.expanduser("~/data")
        relative_path = mcap_filepath_absolute.removeprefix(prefix)
        first_url = (
            "https://foxglove.data.ventitechnologies.net/?ds=remote-file&"
            "ds.url=https://rosbag.data.ventitechnologies.net/"
        )
        url = f"{first_url}{relative_path}"

        # Open in default web browser with timeout
        try:
            subprocess.run(["xdg-open", url], check=True, timeout=10)
            return f"Foxglove Studio launched in browser with {os.path.basename(mcap_filepath_absolute)}.", None
        except subprocess.TimeoutExpired:
            return None, "Timeout launching browser for Foxglove Studio"
        except subprocess.CalledProcessError as e:
            return None, f"Failed to launch browser: {e}"
        except Exception as e:
            return None, f"Failed to launch Foxglove Studio in browser: {e}"

    def launch_bazel_tools_viz(self, settings):
        self.bazel_working_dir = self.get_bazel_working_dir(settings)
        if not self.bazel_working_dir or not os.path.isdir(self.bazel_working_dir):
            return None, f"Bazel working directory not found: {self.bazel_working_dir}"
        return self._launch_process(settings.get("bazel_tools_viz_cmd"), "Bazel Tools Viz", cwd=self.bazel_working_dir)

    def run_bazel_build(self, settings):
        """Run bazel build //... command in the bazel working directory."""
        self.bazel_working_dir = self.get_bazel_working_dir(settings)
        if not self.bazel_working_dir or not os.path.isdir(self.bazel_working_dir):
            return None, f"Bazel working directory not found: {self.bazel_working_dir}"

        self.log_callback("Running: bazel build //...")
        self.log_callback("=" * 60)
        try:
            # Use Popen to stream output in real-time
            process = subprocess.Popen(
                ["bazel", "build", "//..."],
                cwd=self.bazel_working_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Merge stderr into stdout
                text=True,
                bufsize=1,  # Line buffered
            )

            # Read output line by line and log it
            for line in process.stdout:
                line = line.rstrip()
                if line:  # Only log non-empty lines
                    self.log_callback(line)

            # Wait for process to complete
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
        base_command = settings.get("bazel_bag_gui_cmd")
        rate = settings.get("bazel_bag_gui_rate", 1.0)

        # Build command with start offset if provided
        if start_time is not None:
            # Add --start-offset parameter (convert to int for cleaner command)
            command = f"{base_command} -- --start-offset {int(start_time)} --rate={rate} {mcap_path}"
            self.log_callback(f"Starting playback at offset: {int(start_time)}s")
        else:
            command = f"{base_command} -- --rate={rate} {mcap_path}"

        return self._launch_process(command, "Bazel Bag GUI", cwd=self.bazel_working_dir, mcap_path=mcap_path)

    def play_bazel_bag_gui_with_symlinks(self, mcap_filepaths, settings):
        self.bazel_working_dir = self.get_bazel_working_dir(settings)
        symlink_logic = SymlinkPlaybackLogic(log_callback=self.log_callback)
        symlink_dir, error = symlink_logic.prepare_symlinks(mcap_filepaths)
        if error:
            return None, error, symlink_dir

        mcap_files = symlink_logic.get_symlinked_mcap_files()
        if not mcap_files:
            return None, "No .mcap files found to play.", symlink_dir

        mcap_files_str = " ".join([f'"{f}"' for f in mcap_files])
        base_command = settings.get("bazel_bag_gui_cmd")
        rate = settings.get("bazel_bag_gui_rate", 1.0)
        command = f"{base_command} -- --rate={rate} {mcap_files_str}"
        # Pass symlink_dir as mcap_path for verification logic
        message, error = self._launch_process(
            command, "Bazel Bag GUI", cwd=self.bazel_working_dir, mcap_path=symlink_dir
        )
        return message, error, symlink_dir

    def check_process_loaded(self, process_name):
        """
        Check if a process is still running (indication it loaded successfully).
        Returns (is_running: bool, message: str)
        """
        for proc_info in self.running_processes:
            if proc_info["name"] == process_name:
                if proc_info["process"].poll() is None:
                    runtime = time.time() - proc_info["start_time"]
                    return True, f"{process_name} is running (runtime: {runtime:.1f}s, PID: {proc_info['process'].pid})"
                else:
                    return False, f"{process_name} has exited unexpectedly"
        return False, f"{process_name} not found in running processes"

    def terminate_all_processes(self):
        # Stop the process monitor first
        self._stop_process_monitor()

        log_messages = []
        if not self.running_processes:
            log_messages.append("No processes were recorded as running by this application.")

        for proc_info in list(self.running_processes):  # Iterate over a copy for safe removal
            proc = proc_info["process"]
            name = proc_info["name"]
            if proc.poll() is None:
                log_messages.append(f"Terminating {name} (PID: {proc.pid})...")
                try:
                    proc.terminate()
                    proc.wait(timeout=3)  # Wait for graceful termination
                    log_messages.append(f"{name} terminated.")
                except subprocess.TimeoutExpired:
                    log_messages.append(f"{name} did not terminate gracefully, killing...")
                    try:
                        proc.kill()
                        proc.wait(timeout=5)  # Add timeout to prevent hanging
                        log_messages.append(f"{name} killed.")
                    except subprocess.TimeoutExpired:
                        log_messages.append(f"{name} kill timed out, process may be unresponsive (PID: {proc.pid})")
                    except (ProcessLookupError, PermissionError, OSError):
                        # Process already died or permission denied
                        log_messages.append(f"{name} process already terminated or inaccessible")
                except Exception as e:
                    log_messages.append(f"Error terminating {name}: {e}")
            else:
                log_messages.append(f"{name} (PID: {proc.pid}) was already terminated.")

            # Remove from list after processing
            if proc_info in self.running_processes:
                self.running_processes.remove(proc_info)

        # Cleanup symlink dir if it exists from a multi-bag play
        symlink_dir = "/tmp/selected_bags_symlinks"
        if os.path.exists(symlink_dir):
            try:
                shutil.rmtree(symlink_dir, ignore_errors=True)
                log_messages.append(f"Cleaned up symlink dir: {symlink_dir}")
            except Exception as e:
                log_messages.append(f"Error cleaning symlink dir: {e}")

        if not log_messages:  # Should not happen if logic above is correct
            log_messages.append("Cleanup attempt complete. No active processes found or all terminated.")

        # Add final process status summary
        final_status = self.get_process_status()
        log_messages.append(
            f"Final process status: {final_status['running']} running, {final_status['total']} total tracked"
        )

        return "\n".join(log_messages)

    def list_default_subfolders(self):
        """
        Lists all subfolders in the default directory (~/data/default).
        Returns a list of absolute paths to subfolders.
        """
        default_path = os.path.join(self.local_base_path_absolute, "default")
        if not os.path.isdir(default_path):
            return []
        return [
            os.path.join(default_path, d)
            for d in os.listdir(default_path)
            if os.path.isdir(os.path.join(default_path, d))
        ]

    def list_subfolders_in_path(self, folder_path):
        """
        Lists all subfolders in the given folder_path.
        Returns a list of absolute paths to subfolders.
        """
        if not os.path.isdir(folder_path):
            return []
        return [
            os.path.join(folder_path, d) for d in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, d))
        ]

    def find_parent_default_folder(self, path):
        """
        Given a path, walk up the directory tree to find the parent 'default' folder.
        Returns the absolute path to the parent 'default' folder, or None if not found.
        """
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
        """
        Returns the parent 'default' folder of current_path, or ~/data/default if not found.
        """
        if not current_path:
            current_path = os.path.expanduser("~/data/default")
        parent_default = self.find_parent_default_folder(current_path)
        if parent_default:
            return parent_default
        return os.path.expanduser("~/data/default")
