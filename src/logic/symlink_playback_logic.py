import os
import shutil
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