import os
import sys
import shutil
import winshell
from win32com.client import Dispatch
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk

def create_shortcut(target, name, icon_path):
    desktop = winshell.desktop()
    path = os.path.join(desktop, f"{name}.lnk")
    shell = Dispatch('WScript.Shell')
    shortcut = shell.CreateShortCut(path)
    shortcut.Targetpath = target
    shortcut.WorkingDirectory = os.path.dirname(target)
    shortcut.IconLocation = icon_path
    shortcut.save()
    return path

def install():
    root = tk.Tk()
    root.withdraw() # Hide main window
    
    # 1. Verification
    try:
        # We assume this script is running next to the 'dist' folder when distributed
        # or bundled WITH the payload. For simplicity, we assume we bundle PodcastClipper.exe next to it.
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        
        # Check standard dist location or relative location
        payload_local = os.path.join(base_dir, "dist", "PodcastClipper.exe")
        payload_root = os.path.join(base_dir, "PodcastClipper.exe")
        
        executable_path = payload_root if os.path.exists(payload_root) else payload_local
        
        if not os.path.exists(executable_path):
            messagebox.showerror("Installation Error", f"Could not find application payload to install.\nExpected at: {executable_path}")
            return
            
        icon_path = os.path.join(base_dir, "assets", "icon.ico")
        
        # 2. Setup AppData
        app_data = os.environ.get('LOCALAPPDATA', '')
        install_dir = os.path.join(app_data, "PodcastToShorts")
        os.makedirs(install_dir, exist_ok=True)
        
        target_exe = os.path.join(install_dir, "PodcastClipper.exe")
        target_icon = os.path.join(install_dir, "icon.ico")
        
        # 3. Copy files
        shutil.copy2(executable_path, target_exe)
        if os.path.exists(icon_path):
            shutil.copy2(icon_path, target_icon)
            
        # 4. Create Desktop Shortcut
        create_shortcut(target_exe, "Podcast-to-Shorts", target_icon if os.path.exists(target_icon) else target_exe)
        
        messagebox.showinfo("Success", "Podcast-to-Shorts has been installed!\n\nA shortcut has been created on your desktop.")
    except Exception as e:
        messagebox.showerror("Installation Error", f"Failed during installation:\n{e}")

if __name__ == "__main__":
    install()
