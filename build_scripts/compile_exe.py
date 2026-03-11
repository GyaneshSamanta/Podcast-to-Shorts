import subprocess
import os
import sys

def build_executable():
    print("Building Podcast-to-Shorts Executable...")
    main_script = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'main.py'))
    
    # Ensure we are running from the venv
    if not hasattr(sys, 'real_prefix') and not sys.base_prefix != sys.prefix:
        print("WARNING: You don't seem to be running this from a virtual environment.")
        print("It is highly recommended to run this within the venv created by setup_env.bat")
        
    command = [
        "pyinstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--collect-all", "whisper",
        "--name", "PodcastClipper",
        main_script
    ]
    
    print(f"Running command: {' '.join(command)}")
    subprocess.run(command, check=True)
    print("Build complete! Check the 'dist' folder for the executable.")

if __name__ == "__main__":
    build_executable()
