import os
from moviepy.editor import VideoFileClip

class VideoEngine:
    def __init__(self):
        # We enforce NVENC for hardware acceleration on Nvidia GPUs
        self.codec = "h264_nvenc"
        
    def process_clip(self, input_path, output_path, start_time, end_time, callback=None):
        """
        Processes a single clip from a source video:
        1. Extracts the subclip.
        2. Calculates a center-weighted 9:16 crop.
        3. Renders the final output using NVENC.
        4. Closes the clip immediately to free memory.
        """
        clip = None
        try:
            if callback:
                callback(f"Loading video: {os.path.basename(input_path)}...")
                
            clip = VideoFileClip(input_path).subclip(start_time, end_time)
            
            # Calculate 9:16 vertical crop (Center-weighted)
            w, h = clip.size
            target_w = int(h * (9 / 16))
            
            # Only crop if the original isn't already narrower than our target
            if w > target_w:
                crop_x1 = int((w - target_w) / 2)
                crop_x2 = crop_x1 + target_w
                # crop signature depends somewhat on moviepy version, using x1,y1,x2,y2 is safe
                clip = clip.crop(x1=crop_x1, y1=0, x2=crop_x2, y2=h)
            
            if callback:
                callback(f"Rendering: {os.path.basename(output_path)}...")
                
            # Render using hardware encoder
            # logger=None prevents moviepy from spamming stdout
            clip.write_videofile(
                output_path,
                codec=self.codec,
                audio_codec="aac",
                logger=None,
                threads=4, # Use some CPU threads for decoding/audio
                preset="fast" # NVENC preset
            )
            
        except Exception as e:
            print(f"Video Processing Error for {output_path}: {e}")
            raise e
        finally:
            # CRITICAL: Close clip instances to prevent RAM/VRAM leak
            if clip is not None:
                clip.close()
