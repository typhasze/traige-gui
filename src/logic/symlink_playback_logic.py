import os
import shutil
import subprocess
import tempfile
from typing import List, Tuple, Optional

class SymlinkPlaybackLogic:
    def __init__(self, symlink_dir: str = '/tmp/selected_bags_symlinks'):
        self.symlink_dir = symlink_dir

    def prepare_symlinks(self, mcap_filepaths: List[str]) -> Tuple[Optional[str], Optional[str]]:
        """
        Creates symlinks for the given mcap files in the symlink_dir.
        Returns (symlink_dir, error_message_or_None)
        """
        if os.path.exists(self.symlink_dir):
            try:
                shutil.rmtree(self.symlink_dir)
            except Exception as e:
                return None, f"Failed to clean symlink dir: {e}"
        try:
            os.makedirs(self.symlink_dir, exist_ok=True)
        except Exception as e:
            return None, f"Failed to create symlink dir: {e}"

        for bag in mcap_filepaths:
            if os.path.isfile(bag):
                link_name = os.path.join(self.symlink_dir, os.path.basename(bag))
                try:
                    os.symlink(bag, link_name)
                except FileExistsError:
                    pass  # Symlink already exists, ignore.
                except Exception as e:
                    return None, f"Failed to create symlink for {bag}: {e}"

        return self.symlink_dir, None

    def get_symlinked_mcap_files(self) -> List[str]:
        """
        Returns a list of .mcap files in the symlink_dir.
        """
        if not os.path.isdir(self.symlink_dir):
            return []
        return [
            os.path.join(self.symlink_dir, f)
            for f in os.listdir(self.symlink_dir)
            if f.lower().endswith('.mcap')
        ]

    def cleanup_symlinks(self) -> Optional[str]:
        """
        Removes the symlink_dir and all its contents.
        Returns error message if any, else None.
        """
        if os.path.exists(self.symlink_dir):
            try:
                shutil.rmtree(self.symlink_dir)
            except Exception as e:
                return f"Failed to clean symlink dir: {e}"
        return None

    def merge_mcap_files(self, mcap_filepaths: List[str]) -> Tuple[Optional[str], Optional[str]]:
        """
        Merges multiple MCAP files into a single MCAP file using the mcap CLI tool.
        Returns (merged_file_path, error_message_or_None)
        """
        if not mcap_filepaths or len(mcap_filepaths) < 2:
            return None, "Need at least two MCAP files to merge."
        for f in mcap_filepaths:
            if not os.path.isfile(f):
                return None, f"File not found: {f}"
        try:
            temp_dir = tempfile.mkdtemp(prefix="merged_mcap_")
            merged_file = os.path.join(temp_dir, "merged.mcap")
            # Use the mcap CLI tool to merge
            cmd = ["mcap", "merge", "-o", merged_file] + mcap_filepaths
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                return None, f"MCAP merge failed: {result.stderr.strip()}"
            if not os.path.isfile(merged_file):
                return None, "Merged MCAP file was not created."
            return merged_file, None
        except Exception as e:
            return None, f"Error during MCAP merge: {e}"

    def play_merged_mcap(self, mcap_filepaths: List[str]) -> Tuple[Optional[str], Optional[str]]:
        """
        Merges the given MCAP files and returns the merged file path for playback.
        Returns (merged_file_path, error_message_or_None)
        """
        return self.merge_mcap_files(mcap_filepaths) 