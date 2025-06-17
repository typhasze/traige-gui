import urllib.parse
import os
import subprocess

def perform_operation(data):
    # Placeholder for core logic operation
    # Implement the main functionality of the application here
    return data

class FoxgloveLogic:
    def __init__(self):
        self.running_processes = []
        # Default local base path, make this configurable if needed
        self.local_base_path_absolute = os.path.expanduser('~/data')
        # Default Bazel working directory
        self.bazel_working_dir = os.path.expanduser('~/av-system/catkin_ws/src')

    def extract_mcap_details_from_foxglove_link(self, link):
        """
        Extracts the folder path and filename of the .mcap file from a Foxglove link
        or a direct URL to an .mcap file.
        """
        parsed_url = urllib.parse.urlparse(link)
        query_params = urllib.parse.parse_qs(parsed_url.query)

        if 'ds.url' in query_params and query_params['ds.url']:
            mcap_url_str = query_params['ds.url'][0]
            parsed_mcap_url = urllib.parse.urlparse(mcap_url_str)
            if parsed_mcap_url.path and os.path.basename(parsed_mcap_url.path):
                folder_path = os.path.dirname(parsed_mcap_url.path)
                filename = os.path.basename(parsed_mcap_url.path)
                if filename.lower().endswith('.mcap'):
                    return folder_path, filename
        
        if parsed_url.path and parsed_url.path.lower().endswith('.mcap'):
            folder_path = os.path.dirname(parsed_url.path)
            filename = os.path.basename(parsed_url.path)
            return folder_path, filename
            
        return None, None

    def get_local_folder_path(self, extracted_remote_folder):
        """
        Constructs the absolute local folder path from the extracted remote folder.
        """
        if extracted_remote_folder.startswith('/'):
            relative_path = extracted_remote_folder[1:]
        else:
            relative_path = extracted_remote_folder
        return os.path.join(self.local_base_path_absolute, relative_path)

    def list_mcap_files(self, local_folder_path_absolute):
        """
        Lists .mcap files in the specified local directory.
        Returns a tuple: (list_of_files, error_message_or_None)
        """
        mcap_files = []
        if not os.path.isdir(local_folder_path_absolute):
            return [], f"Local folder not found or is not a directory: {local_folder_path_absolute}"
        try:
            for item in os.listdir(local_folder_path_absolute):
                if item.lower().endswith('.mcap'):
                    mcap_files.append(item)
            mcap_files.sort()
            return mcap_files, None
        except PermissionError:
            return [], f"Permission denied to access folder: {local_folder_path_absolute}"
        except Exception as e:
            return [], f"An unexpected error occurred while listing files: {e}"

    def _is_any_viz_running(self):
        """
        Returns True if any viz process (Foxglove, Bazel Tools Viz, Bazel Bag GUI) is running.
        """
        for proc_info in self.running_processes:
            proc = proc_info['process']
            if proc.poll() is None and proc_info['name'] in [
                'Foxglove Studio', 'Bazel Tools Viz', 'Bazel Bag GUI']:
                return True
        return False

    def _terminate_process_by_name(self, name):
        """
        Terminates any running process with the given name.
        """
        for proc_info in list(self.running_processes):
            if proc_info['name'] == name:
                proc = proc_info['process']
                if proc.poll() is None:
                    try:
                        proc.terminate()
                        proc.wait(timeout=3)
                    except Exception:
                        try:
                            proc.kill()
                            proc.wait()
                        except Exception:
                            pass
                self.running_processes.remove(proc_info)

    def _is_process_running_by_name(self, name):
        for proc_info in self.running_processes:
            if proc_info['name'] == name:
                proc = proc_info['process']
                if proc.poll() is None:
                    return True
        return False

    def _launch_process(self, command, name, cwd=None, mcap_path=None):
        if name == 'Bazel Tools Viz':
            if self._is_process_running_by_name(name):
                return f"{name} is already running.", None
        elif name in ['Foxglove Studio', 'Bazel Bag GUI']:
            self._terminate_process_by_name(name)
        try:
            proc = subprocess.Popen(command, cwd=cwd)
            self.running_processes.append({'name': name, 'process': proc, 'path': mcap_path, 'command': command, 'cwd': cwd})
            return f"{name} launched (PID: {proc.pid}).", None
        except FileNotFoundError:
            return None, f"Command for '{name}' ('{command[0]}') not found. Ensure it's installed and in PATH."
        except Exception as e:
            return None, f"Failed to launch {name}: {e}"

    def launch_foxglove(self, mcap_filepath_absolute):
        return self._launch_process(['foxglove-studio', '--file', mcap_filepath_absolute], 'Foxglove Studio', mcap_path=mcap_filepath_absolute)

    def launch_bazel_tools_viz(self):
        if not os.path.isdir(self.bazel_working_dir):
            return None, f"Bazel working directory not found: {self.bazel_working_dir}"
        return self._launch_process(['bazel', 'run', '//tools/viz'], 'Bazel Tools Viz', cwd=self.bazel_working_dir)

    def launch_bazel_bag_gui(self, mcap_dir_or_file):
        # If a directory is provided, launch with all .mcap files in it
        if os.path.isdir(mcap_dir_or_file):
            mcap_glob = os.path.join(mcap_dir_or_file, '*.mcap')
            return self._launch_process(['bazel', 'run', '//tools/bag:gui', '--', mcap_glob], 'Bazel Bag GUI', cwd=self.bazel_working_dir, mcap_path=mcap_dir_or_file)
        else:
            return self._launch_process(['bazel', 'run', '//tools/bag:gui', mcap_dir_or_file], 'Bazel Bag GUI', cwd=self.bazel_working_dir, mcap_path=mcap_dir_or_file)

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
                
        if not log_messages: # Should not happen if logic above is correct
             log_messages.append("Cleanup attempt complete. No active processes found or all terminated.")
        return "\n".join(log_messages)

# Remove the old ApplicationLogic class if it's no longer needed, or keep it if used elsewhere.
# For this specific UI, we are focusing on FoxgloveLogic.
# class ApplicationLogic:
#     def __init__(self):
#         # Initialize any necessary variables or states
#         self.data = None
# ... (rest of ApplicationLogic)