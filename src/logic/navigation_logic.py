import os
from typing import List, Optional

class NavigationLogic:
    """Handles navigation history and path operations"""
    
    def __init__(self, initial_path: str = None):
        self.current_path = initial_path or os.path.expanduser("~/data")
        self.history: List[str] = []
        self.max_history = 10
    
    def navigate_to(self, path: str) -> bool:
        """Navigate to a new path, adding current path to history"""
        if not os.path.exists(path) or not os.path.isdir(path):
            return False
        
        if path != self.current_path:
            self.add_to_history(self.current_path)
            self.current_path = path
        
        return True
    
    def add_to_history(self, path: str):
        """Add a path to navigation history"""
        if path != self.current_path and path not in self.history[-5:]:
            self.history.append(path)
            # Keep only last entries
            self.history = self.history[-self.max_history:]
    
    def go_back(self) -> Optional[str]:
        """Go back to previous path in history"""
        if self.history:
            previous_path = self.history.pop()
            self.current_path = previous_path
            return previous_path
        return None
    
    def go_up(self) -> Optional[str]:
        """Navigate to parent directory"""
        parent_dir = os.path.dirname(self.current_path)
        if parent_dir != self.current_path:  # Not at root
            self.add_to_history(self.current_path)
            self.current_path = parent_dir
            return parent_dir
        return None
    
    def go_home(self, home_path: str = None) -> str:
        """Navigate to home directory"""
        if not home_path:
            home_path = os.path.expanduser("~/data")
        
        if self.current_path != home_path:
            self.add_to_history(self.current_path)
            self.current_path = home_path
        
        return home_path
    
    def get_current_path(self) -> str:
        """Get current path"""
        return self.current_path
    
    def can_go_back(self) -> bool:
        """Check if we can go back in history"""
        return len(self.history) > 0
    
    def can_go_up(self) -> bool:
        """Check if we can go up (not at root)"""
        parent_dir = os.path.dirname(self.current_path)
        return parent_dir != self.current_path
