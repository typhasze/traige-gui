import urllib.parse
import os
import subprocess
import shutil

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
        Tries the main data path, then a backup path if not found.
        """
        if extracted_remote_folder.startswith('/'):
            relative_path = extracted_remote_folder[1:]
        else:
            relative_path = extracted_remote_folder

        local_folder_path_absolute = os.path.join(self.local_base_path_absolute, relative_path)
        
        if os.path.exists(local_folder_path_absolute):
            return local_folder_path_absolute
        else:
            backup_path = os.path.expanduser('~/data')
            backup_local_folder_path_absolute = os.path.join(backup_path, relative_path)
            if os.path.exists(backup_local_folder_path_absolute):
                return backup_local_folder_path_absolute
            else:
                return local_folder_path_absolute

    def list_mcap_files(self, local_folder_path_absolute):
        """
        Lists .mcap files in the given directory. Returns (files_list, error_message).
        """
        if not local_folder_path_absolute:
            return [], "No folder path provided."
        
        if not os.path.exists(local_folder_path_absolute):
            return [], f"Directory does not exist: {local_folder_path_absolute}"
        
        if not os.path.isdir(local_folder_path_absolute):
            return [], f"Path is not a directory: {local_folder_path_absolute}"
        
        try:
            all_files = os.listdir(local_folder_path_absolute)
            mcap_files = [f for f in all_files if f.lower().endswith('.mcap')]
            mcap_files.sort()
            return mcap_files, None
        except PermissionError:
            return [], f"Permission denied: {local_folder_path_absolute}"
        except Exception as e:
            return [], f"Error listing files: {e}"

    def list_default_subfolders(self):
        """List subfolders in the default ~/data/default directory."""
        default_folder_path = os.path.join(self.local_base_path_absolute, 'default')
        return self.list_subfolders_in_path(default_folder_path)

    def list_subfolders_in_path(self, folder_path):
        """List all subdirectories in the given folder path."""
        if not folder_path or not os.path.exists(folder_path) or not os.path.isdir(folder_path):
            return []
        
        try:
            items = os.listdir(folder_path)
            subfolders = []
            for item in items:
                item_path = os.path.join(folder_path, item)
                if os.path.isdir(item_path):
                    subfolders.append(item_path)
            subfolders.sort()
            return subfolders
        except (PermissionError, OSError):
            return []

    def find_parent_default_folder(self, path):
        """Find the parent 'default' folder of the given path."""
        current_path = path
        while current_path and current_path != os.path.dirname(current_path):
            if os.path.basename(current_path) == 'default':
                return current_path
            current_path = os.path.dirname(current_path)
        return None

    def get_effective_default_folder(self, current_path=None):
        """Get the effective default folder to use for subfolder search."""
        if current_path:
            parent_default = self.find_parent_default_folder(current_path)
            if parent_default:
                return parent_default
        
        # Fall back to standard default folder
        return os.path.join(self.local_base_path_absolute, 'default')

    def launch_foxglove(self, mcap_file_path):
        """Launch Foxglove with the given MCAP file."""
        if not mcap_file_path or not os.path.isfile(mcap_file_path):
            return None, f"Invalid MCAP file path: {mcap_file_path}"
        
        try:
            # Try to launch foxglove-studio first, then fallback to other commands
            commands_to_try = [
                ['foxglove-studio', mcap_file_path],
                ['foxglove', mcap_file_path],
                ['ros2', 'bag', 'play', mcap_file_path]
            ]
            
            for cmd in commands_to_try:
                try:
                    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    self.running_processes.append(process)
                    return f"Launched Foxglove with {os.path.basename(mcap_file_path)}", None
                except FileNotFoundError:
                    continue
            
            return None, "Foxglove not found. Please install foxglove-studio."
        except Exception as e:
            return None, f"Error launching Foxglove: {e}"

    def launch_bazel_bag_gui(self, mcap_file_path):
        """Launch Bazel Bag GUI with the given MCAP file."""
        if not mcap_file_path or not os.path.isfile(mcap_file_path):
            return None, f"Invalid MCAP file path: {mcap_file_path}"
        
        try:
            cmd = ['bazel', 'run', '//tools/bag_gui:bag_gui', '--', mcap_file_path]
            process = subprocess.Popen(cmd, cwd=self.bazel_working_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.running_processes.append(process)
            return f"Launched Bazel Bag GUI with {os.path.basename(mcap_file_path)}", None
        except Exception as e:
            return None, f"Error launching Bazel Bag GUI: {e}"

    def launch_bazel_tools_viz(self):
        """Launch Bazel Tools Viz."""
        try:
            cmd = ['bazel', 'run', '//tools/viz:viz']
            process = subprocess.Popen(cmd, cwd=self.bazel_working_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.running_processes.append(process)
            return "Launched Bazel Tools Viz", None
        except Exception as e:
            return None, f"Error launching Bazel Tools Viz: {e}"

    def play_bazel_bag_gui_with_symlinks(self, mcap_file_paths):
        """Launch Bazel Bag GUI with multiple MCAP files using symlinks."""
        if not mcap_file_paths:
            return None, "No MCAP files provided.", None
        
        # Create symlink directory
        symlink_dir = '/tmp/selected_bags_symlinks'
        
        try:
            # Clean up existing symlink directory
            if os.path.exists(symlink_dir):
                shutil.rmtree(symlink_dir, ignore_errors=True)
            
            # Create new symlink directory
            os.makedirs(symlink_dir, exist_ok=True)
            
            # Create symlinks
            for mcap_file_path in mcap_file_paths:
                if os.path.isfile(mcap_file_path):
                    basename = os.path.basename(mcap_file_path)
                    symlink_path = os.path.join(symlink_dir, basename)
                    os.symlink(mcap_file_path, symlink_path)
            
            # Launch Bazel Bag GUI with the symlink directory
            cmd = ['bazel', 'run', '//tools/bag_gui:bag_gui', '--', symlink_dir]
            process = subprocess.Popen(cmd, cwd=self.bazel_working_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.running_processes.append(process)
            
            return f"Launched Bazel Bag GUI with {len(mcap_file_paths)} files via symlinks", None, symlink_dir
        except Exception as e:
            return None, f"Error launching Bazel Bag GUI with symlinks: {e}", symlink_dir

    def terminate_all_processes(self):
        """Terminate all running processes."""
        terminated_count = 0
        for process in self.running_processes:
            try:
                if process.poll() is None:  # Process is still running
                    process.terminate()
                    terminated_count += 1
            except Exception:
                pass
        
        self.running_processes.clear()
        return f"Terminated {terminated_count} process(es)."