import os
import sys

sys.path.append(os.getcwd())
from backend.video_util import VideoEngine

def test():
    engine = VideoEngine()
    input_path = r"D:\DaVinci Resolve\Podcast 2 Ravi Chhetri\Gyanesh on Product Ravi Chhetri LInkedIn version.mp4"
    output_path = "test_output.mp4"
    
    if not os.path.exists(input_path):
        print(f"Error: Could not find input file at {input_path}")
        return
        
    print(f"File found. Attempting to crop a 5 second segment...")
    try:
        engine.process_clip(input_path, output_path, 0, 5)
        print("Success! The snippet was rendered.")
    except Exception as e:
        print(f"Render failed: {e}")

if __name__ == "__main__":
    test()
