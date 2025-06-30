import tkinter as tk
from tkinter import ttk, Text, Scrollbar, VERTICAL, WORD, END, DISABLED, NORMAL

class LoggingComponent:
    """Handles logging/status display functionality"""
    
    def __init__(self, parent_frame, height=6):
        self.create_log_frame(parent_frame, height)
    
    def create_log_frame(self, parent_frame, height):
        """Create the logging frame with text widget and scrollbar"""
        # --- Status/Log Frame ---
        status_frame = ttk.LabelFrame(parent_frame, text="Log", padding="10")
        status_frame.pack(padx=5, pady=5, fill="both", expand=True)
        
        log_container = ttk.Frame(status_frame)
        log_container.pack(fill="both", expand=True)

        log_yscrollbar = Scrollbar(log_container, orient=VERTICAL)
        self.status_text = Text(
            log_container, 
            height=height, 
            wrap=WORD, 
            yscrollcommand=log_yscrollbar.set, 
            state=DISABLED
        )
        log_yscrollbar.config(command=self.status_text.yview)
        log_yscrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.status_text.pack(side=tk.LEFT, fill="both", expand=True)
        
        # Configure text tags
        self.status_text.tag_configure("error", foreground="red")
        self.status_text.tag_configure("info", foreground="black")
    
    def log_message(self, message, is_error=False, clear_first=False):
        """Log a message to the status text widget"""
        self.status_text.config(state=NORMAL)
        if clear_first:
            self.status_text.delete('1.0', END)
        
        tag = "error" if is_error else "info"
        prefix = "ERROR: " if is_error else "INFO: "
        
        # Split message by newlines to apply tags correctly if needed
        for line in message.splitlines():
            self.status_text.insert(END, f"{prefix}{line}\n", tag)
            
        self.status_text.see(END)
        self.status_text.config(state=DISABLED)
