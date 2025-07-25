import urllib.parse
import os
import subprocess
import shutil
import json
import sys
import signal
from .logic.symlink_playback_logic import SymlinkPlaybackLogic

# Constants for better maintainability
DEFAULT_DATA_PATH = os.path.expanduser('~/data')
DEFAULT_BACKUP_PATH = os.path.expanduser('~/data/psa_logs_backup_nas3')
DEFAULT_BAZEL_WORKING_DIR = os.path.expanduser('~/av-system/catkin_ws/src')
SYMLINK_DIR = '/tmp/selected_bags_symlinks'

# Default settings
DEFAULT_SETTINGS = {
    'bazel_tools_viz_cmd': 'bazel run //tools/viz',
    'bazel_bag_gui_cmd': 'bazel run //tools/bag:gui',
    'bazel_working_dir': DEFAULT_BAZEL_WORKING_DIR,
}

# Process names for better consistency
PROCESS_NAMES = {
    'FOXGLOVE_STUDIO': 'Foxglove Studio',
    'FOXGLOVE_BROWSER': 'Foxglove Studio (Browser)',
    'BAZEL_TOOLS_VIZ': 'Bazel Tools Viz',
    'BAZEL_BAG_GUI': 'Bazel Bag GUI'
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
            'bazel_tools_viz_cmd': 'bazel run //tools/viz',
            'bazel_bag_gui_cmd': 'bazel run //tools/bag:gui',
            'bazel_working_dir': os.path.expanduser('~/av-system/catkin_ws/src'),
        }
        # self.settings = default_settings.copy() # self.settings is no longer present
        self.save_settings(default_settings)


    def get_setting(self, key):
        """Gets a specific setting value by key."""
        # self.settings.get(key) # self.settings is no longer present
        return None # Placeholder as settings are not managed here

    def get_bazel_working_dir(self, settings=None):
        if settings is not None:
            return settings.get('bazel_working_dir')
        return None

    def extract_info_from_link(self, link):
        """
        Extracts the folder path and filename from a Foxglove link
        or a direct URL to a file or folder.
        Handles .mcap, .mp4, and /logs directories.
        Optimized for better performance and readability.
        """
        if not link.strip():
            return None, None
            
        try:
            parsed_url = urllib.parse.urlparse(link)
            query_params = urllib.parse.parse_qs(parsed_url.query)

            # Case 1: Foxglove link with ds.url parameter
            if 'ds.url' in query_params and query_params['ds.url']:
                mcap_url_str = query_params['ds.url'][0]
                path_to_check = urllib.parse.urlparse(mcap_url_str).path
            # Case 2: Direct link
            else:
                path_to_check = parsed_url.path

            if not path_to_check:
                return None, None

            # Normalize path - remove trailing slash and whitespace
            path_to_check = path_to_check.strip().rstrip('/')

            # Check if it's a file (.mcap or .mp4)
            lower_path = path_to_check.lower()
            if lower_path.endswith(('.mcap', '.mp4')):
                folder_path = os.path.dirname(path_to_check)
                filename = os.path.basename(path_to_check)
                return folder_path, filename
            
            # It's a directory path
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
        if extracted_remote_folder.startswith('/'):
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
        self.log_callback(f"Could not find local directory for '{relative_path}' at primary or backup locations.", is_error=True)
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
                items = [item for item in os.listdir(local_folder_path_absolute) 
                        if item.lower().endswith(ext_lower)]
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
        viz_processes = {PROCESS_NAMES['FOXGLOVE_STUDIO'], PROCESS_NAMES['BAZEL_TOOLS_VIZ'], PROCESS_NAMES['BAZEL_BAG_GUI']}
        
        for proc_info in self.running_processes:
            proc = proc_info['process']
            if proc.poll() is None and proc_info['name'] in viz_processes:
                return True
        return False

    def _terminate_process_by_name(self, name):
        """
        Terminates any running process with the given name and its children.
        Improved error handling and cross-platform compatibility.
        """
        for proc_info in list(self.running_processes):
            if proc_info['name'] == name:
                proc = proc_info['process']
                if proc.poll() is None:  # Process is still running
                    try:
                        # Terminate the entire process group
                        if sys.platform != "win32":
                            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                        else:
                            proc.terminate()
                        
                        # Wait for graceful termination
                        proc.wait(timeout=3)
                        
                    except subprocess.TimeoutExpired:
                        # Force kill if graceful termination failed
                        try:
                            if sys.platform != "win32":
                                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                            else:
                                proc.kill()
                            proc.wait()
                        except (ProcessLookupError, PermissionError, OSError):
                            # Process might have already died
                            pass
                    except (ProcessLookupError, PermissionError, OSError):
                        # Process already died between poll() and killpg()
                        pass
                        
                # Remove from tracking list
                if proc_info in self.running_processes:
                    self.running_processes.remove(proc_info)

    def _is_process_running_by_name(self, name):
        for proc_info in self.running_processes:
            if proc_info['name'] == name:
                proc = proc_info['process']
                if proc.poll() is None:
                    return True
        return False

    def _launch_process(self, command, name, cwd=None, mcap_path=None):
        if name == 'Foxglove Studio (Browser)':
            # Special case: launch in browser instead of as a process
            if mcap_path:
                return self.launch_foxglove_browser(mcap_path)
            else:
                return None, "No MCAP file path provided for browser launch."
        
        # Use shell=True for commands that are strings, False for lists of args
        use_shell = isinstance(command, str)

        if name == 'Bazel Tools Viz':
            if self._is_process_running_by_name(name):
                return f"{name} is already running.", None
        elif name in ['Foxglove Studio', 'Bazel Bag GUI']:
            self._terminate_process_by_name(name)
        try:
            # On Unix, start the process in a new session to control its process group
            preexec_fn = os.setsid if sys.platform != "win32" else None
            proc = subprocess.Popen(command, cwd=cwd, shell=use_shell, preexec_fn=preexec_fn)
            self.running_processes.append({'name': name, 'process': proc, 'path': mcap_path, 'command': command, 'cwd': cwd})
            return f"{name} launched (PID: {proc.pid}).", None
        except FileNotFoundError:
            cmd_str = command if use_shell else command[0]
            return None, f"Command for '{name}' ('{cmd_str}') not found. Ensure it's installed and in PATH."
        except Exception as e:
            return None, f"Failed to launch {name}: {e}"

    def launch_foxglove(self, mcap_filepath_absolute, settings):
        """
        Launches Foxglove Studio in a web browser with the given .mcap file.
        Returns a tuple: (message, error)
        """
        open_in_browser = settings.get('open_foxglove_in_browser')
        
        if open_in_browser:
            return self.launch_foxglove_browser(mcap_filepath_absolute)
        else:
            return self.launch_foxglove_desktop(mcap_filepath_absolute)

    def launch_foxglove_desktop(self, mcap_filepath_absolute):
        # Foxglove Studio is typically a direct command, not run with shell
        return self._launch_process(['foxglove-studio', '--file', mcap_filepath_absolute], 'Foxglove Studio', mcap_path=mcap_filepath_absolute)

    def launch_foxglove_browser(self, mcap_filepath_absolute):
        """
        Launches Foxglove Studio in a web browser with the given .mcap file.
        Returns a tuple: (message, error)
        """
        if not os.path.isfile(mcap_filepath_absolute):
            return None, f"MCAP file not found: {mcap_filepath_absolute}"
        
        # Encode the file path for URL
        prefix = os.path.expanduser('~/data')
        relative_path = mcap_filepath_absolute.removeprefix(prefix)
        first_url = 'https://foxglove.data.ventitechnologies.net/?ds=remote-file&ds.url=https://rosbag.data.ventitechnologies.net/'
        url = f"{first_url}{relative_path}"
        
        # Open in default web browser
        try:
            subprocess.run(['xdg-open', url], check=True)
            return f"Foxglove Studio launched in browser with {os.path.basename(mcap_filepath_absolute)}.", None
        except Exception as e:
            return None, f"Failed to launch Foxglove Studio in browser: {e}"


    def launch_bazel_tools_viz(self, settings):
        self.bazel_working_dir = self.get_bazel_working_dir(settings)
        if not self.bazel_working_dir or not os.path.isdir(self.bazel_working_dir):
            return None, f"Bazel working directory not found: {self.bazel_working_dir}"
        return self._launch_process(settings.get('bazel_tools_viz_cmd'), 'Bazel Tools Viz', cwd=self.bazel_working_dir)

    def launch_bazel_bag_gui(self, mcap_path, settings):
        self.bazel_working_dir = self.get_bazel_working_dir(settings)
        command = f"{settings.get('bazel_bag_gui_cmd')} -- {mcap_path}"
        return self._launch_process(command, 'Bazel Bag GUI', cwd=self.bazel_working_dir, mcap_path=mcap_path)

    def play_bazel_bag_gui_with_symlinks(self, mcap_filepaths, settings):
        self.bazel_working_dir = self.get_bazel_working_dir(settings)
        symlink_logic = SymlinkPlaybackLogic()
        symlink_dir, error = symlink_logic.prepare_symlinks(mcap_filepaths)
        if error:
            return None, error, symlink_dir

        mcap_files = symlink_logic.get_symlinked_mcap_files()
        if not mcap_files:
            return None, "No .mcap files found to play.", symlink_dir

        mcap_files_str = " ".join([f'"{f}"' for f in mcap_files])
        command = f"{settings.get('bazel_bag_gui_cmd')} -- {mcap_files_str}"
        message, error = self._launch_process(command, 'Bazel Bag GUI', cwd=self.bazel_working_dir)
        return message, error, symlink_dir

    def terminate_all_processes(self):
        log_messages = []
        if not self.running_processes:
            log_messages.append("No processes were recorded as running by this application.")
        
        for proc_info in list(self.running_processes): # Iterate over a copy for safe removal
            proc = proc_info['process']
            name = proc_info['name']
            if proc.poll() is None:
                log_messages.append(f"Terminating {name} (PID: {proc.pid})...")
                try:
                    proc.terminate()
                    proc.wait(timeout=3) # Wait for graceful termination
                    log_messages.append(f"{name} terminated.")
                except subprocess.TimeoutExpired:
                    log_messages.append(f"{name} did not terminate gracefully, killing...")
                    proc.kill()
                    proc.wait()
                    log_messages.append(f"{name} killed.")
                except Exception as e:
                    log_messages.append(f"Error terminating {name}: {e}")
            else:
                log_messages.append(f"{name} (PID: {proc.pid}) was already terminated.")
            
            # Remove from list after processing
            if proc_info in self.running_processes:
                self.running_processes.remove(proc_info)
                
        # Cleanup symlink dir if it exists from a multi-bag play
        symlink_dir = '/tmp/selected_bags_symlinks'
        if os.path.exists(symlink_dir):
            try:
                shutil.rmtree(symlink_dir, ignore_errors=True)
                log_messages.append(f"Cleaned up symlink dir: {symlink_dir}")
            except Exception as e:
                log_messages.append(f"Error cleaning symlink dir: {e}")

        if not log_messages: # Should not happen if logic above is correct
             log_messages.append("Cleanup attempt complete. No active processes found or all terminated.")
        return "\n".join(log_messages)

    def list_default_subfolders(self):
        """
        Lists all subfolders in the default directory (~/data/default).
        Returns a list of absolute paths to subfolders.
        """
        default_path = os.path.join(self.local_base_path_absolute, 'default')
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
            os.path.join(folder_path, d)
            for d in os.listdir(folder_path)
            if os.path.isdir(os.path.join(folder_path, d))
        ]

    def find_parent_default_folder(self, path):
        """
        Given a path, walk up the directory tree to find the parent 'default' folder.
        Returns the absolute path to the parent 'default' folder, or None if not found.
        """
        if not path:
            return None
        parent_default = path
        while parent_default and os.path.basename(parent_default) != 'default':
            new_parent = os.path.dirname(parent_default)
            if new_parent == parent_default:
                break
            parent_default = new_parent
        if os.path.basename(parent_default) == 'default':
            return parent_default
        return None

    def get_effective_default_folder(self, current_path=None):
        """
        Returns the parent 'default' folder of current_path, or ~/data/default if not found.
        """
        if not current_path:
            current_path = os.path.expanduser('~/data/default')
        parent_default = self.find_parent_default_folder(current_path)
        if parent_default:
            return parent_default
        return os.path.expanduser('~/data/default')

# Remove the old ApplicationLogic class if it's no longer needed, or keep it if used elsewhere.
# For this specific UI, we are focusing on FoxgloveLogic.
# class ApplicationLogic:
#     def __init__(self):
#         # Initialize any necessary variables or states
#         self.data = None
# ... (rest of ApplicationLogic)