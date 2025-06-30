import urllib.parse
import os
import webbrowser
from typing import Tuple, Optional, List
import subprocess
import shutil
import threading
import time

class FoxgloveLogic:
    """Handles Foxglove-specific operations like link analysis and launching"""
    
    def __init__(self, core_logic, bazel_working_dir=None):
        self.core_logic = core_logic
        self.running_processes = []
        # Default Bazel working directory
        self.bazel_working_dir = bazel_working_dir or os.path.expanduser('~/av-system/catkin_ws/src')
    
    def analyze_foxglove_link(self, link: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Analyze a Foxglove link and return extracted details.
        Returns: (extracted_remote_folder, mcap_filename, local_folder_path)
        """
        if not link:
            return None, None, None
            
        extracted_remote_folder, mcap_filename = self.core_logic.extract_mcap_details_from_foxglove_link(link)
        
        if not extracted_remote_folder or not mcap_filename:
            return None, None, None
            
        local_folder_path = self.core_logic.get_local_folder_path(extracted_remote_folder)
        
        return extracted_remote_folder, mcap_filename, local_folder_path
    
    def launch_foxglove_with_file(self, file_path: str) -> Tuple[Optional[str], Optional[str]]:
        """Launch Foxglove with a specific MCAP file"""
        return self.core_logic.launch_foxglove(file_path)
    
    def launch_foxglove_browser(self, url: str = None) -> bool:
        """Launch Foxglove in browser with optional URL"""
        if not url:
            url = "https://foxglove.data.ventitechnologies.net/?ds=remote-file&ds.url=https://rosbag.data.ventitechnologies.net/20250618/PROD/PSA8607/rosbags/default/PSA8607_2025-06-18_13-37-43/PSA8607_2025-06-18-17-27-45_46.mcap"
        
        try:
            webbrowser.open(url)
            return True
        except Exception:
            return False

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

    def play_bazel_bag_gui_with_symlinks(self, mcap_filepaths):
        symlink_dir = '/tmp/selected_bags_symlinks'
        # Cleanup if exists
        if os.path.exists(symlink_dir):
            shutil.rmtree(symlink_dir)
        os.makedirs(symlink_dir, exist_ok=True)
        # Create symlinks
        for bag in mcap_filepaths:
            if os.path.isfile(bag):
                link_name = os.path.join(symlink_dir, os.path.basename(bag))
                try:
                    os.symlink(bag, link_name)
                except FileExistsError:
                    pass
        # Find all .mcap files in the symlink dir
        mcap_files = [os.path.join(symlink_dir, f) for f in os.listdir(symlink_dir) if f.lower().endswith('.mcap')]
        if not mcap_files:
            return None, "No .mcap files found in symlink directory.", symlink_dir
        # Run bazel command with all .mcap files as arguments
        proc = subprocess.Popen(['bazel', 'run', '//tools/bag:gui', '--'] + mcap_files, cwd=self.bazel_working_dir)
        self.running_processes.append({'name': 'Bazel Bag GUI', 'process': proc, 'path': symlink_dir, 'command': ['bazel', 'run', '//tools/bag:gui', '--'] + mcap_files, 'cwd': self.bazel_working_dir})
        # Cleanup symlink dir after a delay
        def delayed_cleanup():
            time.sleep(10)
            shutil.rmtree(symlink_dir, ignore_errors=True)
        threading.Thread(target=delayed_cleanup, daemon=True).start()
        return f"Bazel Bag GUI launched with {len(mcap_files)} bag(s).", None, symlink_dir

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
