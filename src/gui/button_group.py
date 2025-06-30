import tkinter as tk
from tkinter import ttk
from typing import Dict, Callable, Optional

class ButtonGroup:
    """Manages a group of related buttons with state management"""
    
    def __init__(self, parent_frame, title="Actions", padding="10"):
        self.buttons = {}
        self.button_states = {}
        self.create_button_frame(parent_frame, title, padding)
    
    def create_button_frame(self, parent_frame, title, padding):
        """Create the button frame"""
        self.action_frame = ttk.LabelFrame(parent_frame, text=title, padding=padding)
        self.action_frame.pack(padx=5, pady=5, fill="x")
    
    def add_button(self, name: str, text: str, command: Callable, 
                   state: str = tk.NORMAL, expand: bool = True, **kwargs):
        """Add a button to the group"""
        button = ttk.Button(
            self.action_frame, 
            text=text, 
            command=command, 
            state=state,
            **kwargs
        )
        button.pack(side=tk.LEFT, padx=5, pady=5, expand=expand, fill="x")
        
        self.buttons[name] = button
        self.button_states[name] = state
        
        return button
    
    def set_button_state(self, name: str, state: str):
        """Set the state of a specific button"""
        if name in self.buttons:
            self.buttons[name].config(state=state)
            self.button_states[name] = state
    
    def set_all_button_states(self, states: Dict[str, str]):
        """Set states for multiple buttons at once"""
        for name, state in states.items():
            self.set_button_state(name, state)
    
    def enable_button(self, name: str):
        """Enable a specific button"""
        self.set_button_state(name, tk.NORMAL)
    
    def disable_button(self, name: str):
        """Disable a specific button"""
        self.set_button_state(name, tk.DISABLED)
    
    def enable_all_buttons(self):
        """Enable all buttons"""
        for name in self.buttons:
            self.enable_button(name)
    
    def disable_all_buttons(self):
        """Disable all buttons"""
        for name in self.buttons:
            self.disable_button(name)
    
    def get_button(self, name: str) -> Optional[ttk.Button]:
        """Get a button by name"""
        return self.buttons.get(name)
    
    def get_button_state(self, name: str) -> Optional[str]:
        """Get the current state of a button"""
        return self.button_states.get(name)
