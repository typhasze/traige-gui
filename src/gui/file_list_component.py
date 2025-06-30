import tkinter as tk
from tkinter import ttk, Listbox, Scrollbar, EXTENDED, VERTICAL, HORIZONTAL, END
import os
from typing import Callable, Optional

class FileListComponent:
    """Reusable file list component with selection handling"""
    
    def __init__(self, parent_frame, title="Files", height=10, on_select: Optional[Callable] = None):
        self.on_select_callback = on_select
        self.files_list = []
        self.create_file_list_frame(parent_frame, title, height)
    
    def create_file_list_frame(self, parent_frame, title, height):
        """Create the file list frame with listbox and scrollbars"""
        file_list_frame = ttk.LabelFrame(parent_frame, text=title, padding="10")
        file_list_frame.pack(padx=5, pady=5, fill="both", expand=True)

        self.list_label = ttk.Label(file_list_frame, text="Files in folder:")
        self.list_label.pack(anchor="w", pady=(0, 5))

        list_container = ttk.Frame(file_list_frame)
        list_container.pack(fill="both", expand=True)

        yscrollbar = Scrollbar(list_container, orient=VERTICAL)
        xscrollbar = Scrollbar(list_container, orient=HORIZONTAL)
        
        self.listbox = Listbox(
            list_container, 
            selectmode=EXTENDED, 
            yscrollcommand=yscrollbar.set, 
            xscrollcommand=xscrollbar.set,
            height=height, 
            exportselection=False
        )
        
        yscrollbar.config(command=self.listbox.yview)
        xscrollbar.config(command=self.listbox.xview)
        
        yscrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        xscrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.listbox.pack(side=tk.LEFT, fill="both", expand=True)
        
        if self.on_select_callback:
            self.listbox.bind('<<ListboxSelect>>', self._on_select)
    
    def _on_select(self, event):
        """Internal selection handler"""
        if self.on_select_callback:
            self.on_select_callback(event)
    
    def populate_files(self, files, target_file=None):
        """Populate the listbox with files"""
        self.listbox.delete(0, END)
        self.files_list = files.copy()
        highlight_idx = -1
        
        # Use normalized comparison for matching
        target = target_file.strip().lower() if target_file else None
        
        for i, filename in enumerate(files):
            self.listbox.insert(END, filename)
            if target and os.path.basename(filename).strip().lower() == target:
                self.listbox.itemconfig(i, {'bg': '#FFFF99'})  # Light yellow
                highlight_idx = i
        
        if highlight_idx != -1:
            self.listbox.selection_set(highlight_idx)
            self.listbox.see(highlight_idx)
            return True  # Found and highlighted target
        
        return False  # Target not found
    
    def clear_files(self):
        """Clear the file list"""
        self.listbox.delete(0, END)
        self.files_list = []
    
    def get_selected_indices(self):
        """Get selected item indices"""
        return self.listbox.curselection()
    
    def get_selected_files(self):
        """Get selected filenames"""
        selection_indices = self.listbox.curselection()
        return [self.listbox.get(idx) for idx in selection_indices]
    
    def set_label_text(self, text):
        """Set the label text"""
        self.list_label.config(text=text)
    
    def bind_event(self, event, callback):
        """Bind an event to the listbox"""
        self.listbox.bind(event, callback)
