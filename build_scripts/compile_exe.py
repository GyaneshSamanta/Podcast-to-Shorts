import subprocess
import os
import sys

def build_executable():
    print("Building Podcast-to-Shorts Executable...")
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    main_script = os.path.join(base_dir, 'main.py')
    icon_path = os.path.join(base_dir, 'assets', 'icon.ico')
    
    # Use the active python interpreter to call pyinstaller module safely
    python_exe = sys.executable
    
    # 1. Build Main Application
    app_command = [
        python_exe, "-m", "PyInstaller", "--noconfirm", "--onefile", "--windowed",
        "--collect-all", "whisper", "--name", "PodcastClipper",
    ]
    if os.path.exists(icon_path):
        app_command.extend(["--icon", icon_path])
    app_command.append(main_script)
    
    print(f"Compiling Payload: {' '.join(app_command)}")
    subprocess.run(app_command, check=True)
    
    # 2. Build Installer
    installer_script = os.path.join(base_dir, 'install_builder.py')
    inst_command = [
        python_exe, "-m", "PyInstaller", "--noconfirm", "--onefile", "--windowed",
        "--name", "PodcastClipper_Installer"
    ]
    if os.path.exists(icon_path):
        inst_command.extend(["--icon", icon_path])
    inst_command.append(installer_script)
    
    print(f"Compiling Installer: {' '.join(inst_command)}")
    subprocess.run(inst_command, check=True)
    
    print("Build complete! Check the 'dist' folder for PodcastClipper.exe and PodcastClipper_Installer.exe")

if __name__ == "__main__":
    build_executable()
