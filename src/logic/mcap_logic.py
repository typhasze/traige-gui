import os
import urllib.parse
from typing import List, Tuple, Optional
from utils.path_utils import normalize_path

class McapLogic:
    """Handles MCAP file-specific operations"""
    
    def __init__(self, core_logic, local_base_path=None):
        self.core_logic = core_logic
        self.local_base_path_absolute = local_base_path or os.path.expanduser('~/data')
    
    def get_mcap_files_in_folder(self, folder_path: str) -> Tuple[List[str], Optional[str]]:
        """Get list of MCAP files in a folder"""
        return self.core_logic.list_mcap_files(folder_path)
    
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
        main_path = os.path.join(self.local_base_path_absolute, relative_path)
        if os.path.isdir(main_path):
            return main_path
        # Try backup path
        backup_base = os.path.expanduser('~/data/psa_logs_backup_nas3')
        backup_path = os.path.join(backup_base, relative_path)
        if os.path.isdir(backup_path):
            return backup_path
        return main_path  # Default to main path if neither exists

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

    def is_mcap_file(self, filepath):
        """Check if a file is an MCAP file based on extension"""
        return filepath.lower().endswith('.mcap')
    
    def get_selected_mcap_paths(self, listbox, current_folder: str) -> List[str]:
        """Get paths of selected MCAP files from a listbox"""
        selection_indices = listbox.curselection()
        selected_paths = []
        for idx in selection_indices:
            selected_filename = listbox.get(idx)
            if current_folder and os.path.isdir(current_folder):
                selected_paths.append(os.path.join(current_folder, selected_filename))
        return selected_paths
    
    def get_first_selected_mcap_path(self, listbox, current_folder: str) -> Optional[str]:
        """Get the first selected MCAP file path"""
        selection_indices = listbox.curselection()
        if not selection_indices:
            return None
        
        selected_filename = listbox.get(selection_indices[0])
        if current_folder and os.path.isdir(current_folder):
            return os.path.join(current_folder, selected_filename)
        return None
    
    def populate_mcap_listbox(self, listbox, mcap_files: List[str], target_filename: str = None):
        """Populate a listbox with MCAP files and highlight target if specified"""
        listbox.delete(0, 'end')
        highlight_idx = -1
        
        # Use normalized comparison for matching
        target = target_filename.strip().lower() if target_filename else None
        
        for i, filename in enumerate(mcap_files):
            listbox.insert('end', filename)
            if target and os.path.basename(filename).strip().lower() == target:
                listbox.itemconfig(i, {'bg': '#FFFF99'})  # Light yellow
                highlight_idx = i
        
        if highlight_idx != -1:
            listbox.selection_set(highlight_idx)
            listbox.see(highlight_idx)
            return True  # Found and highlighted target
        
        return False  # Target not found
    
    def launch_bazel_with_file(self, file_path: str) -> Tuple[Optional[str], Optional[str]]:
        """Launch Bazel Bag GUI with a single MCAP file"""
        return self.core_logic.launch_bazel_bag_gui(file_path)
    
    def launch_bazel_with_multiple_files(self, file_paths: List[str]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Launch Bazel Bag GUI with multiple MCAP files using symlinks"""
        return self.core_logic.play_bazel_bag_gui_with_symlinks(file_paths)
    
    def launch_bazel_viz(self) -> Tuple[Optional[str], Optional[str]]:
        """Launch Bazel Tools Viz"""
        return self.core_logic.launch_bazel_tools_viz()
