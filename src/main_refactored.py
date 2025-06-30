#!/usr/bin/env python3
# filepath: /python-gui-app/python-gui-app/src/main_refactored.py
import tkinter as tk
from gui_manager_refactored import FoxgloveAppGUIManager

def main():
    root = tk.Tk()
    gui = FoxgloveAppGUIManager(root)
    root.mainloop()

if __name__ == "__main__":
    main()
