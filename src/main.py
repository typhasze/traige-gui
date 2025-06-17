#!/usr/bin/env python3
# filepath: /python-gui-app/python-gui-app/src/main.py
import tkinter as tk
from gui_manager import FoxgloveAppGUIManager # Ensure this matches your class name

def main():
    root = tk.Tk()
    gui = FoxgloveAppGUIManager(root)
    root.mainloop()

if __name__ == "__main__":
    main()