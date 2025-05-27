

# main.py
from viewer import LaserAreaViewer
import tkinter as tk

def main():
    root = tk.Tk()
    app = LaserAreaViewer(root)
    root.mainloop()

if __name__ == "__main__":
    main()