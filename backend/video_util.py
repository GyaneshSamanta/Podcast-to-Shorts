import os
from moviepy.editor import VideoFileClip

class VideoEngine:
    def __init__(self):
        # We enforce NVENC for hardware acceleration on Nvidia GPUs
        self.codec = "h264_nvenc"
        
    def process_clip(self, input_path, output_path, start_time, end_time, mode="Crop (Center)", callback=None):
        """
        Processes a single clip from a source video:
        1. Extracts the subclip.
        2. Calculates 9:16 target dimensions.
        3. Applies Crop (Center) or Fit (Add Borders) depending on 'mode'.
        4. Renders the final output using NVENC.
        5. Closes the clip immediately to free memory.
        """
        clip = None
        try:
            if callback:
                callback(f"Loading video: {os.path.basename(input_path)}...")
                
            clip = VideoFileClip(input_path).subclip(start_time, end_time)
            
            w, h = clip.size
            
            # Target 9:16 ratio based on source height
            target_w = int(h * (9 / 16))
            
            if mode == "Crop (Center)":
                if w > target_w:
                    crop_x1 = int((w - target_w) / 2)
                    crop_x2 = crop_x1 + target_w
                    clip = clip.crop(x1=crop_x1, y1=0, x2=crop_x2, y2=h)
            elif mode == "Fit (Add Borders)":
                # To fit the video within a 9:16 vertical canvas without cutting edges:
                # We create a target resolution of e.g. (1080, 1920) by scaling width to target then adding padding.
                # However, a simpler MoviePy approach is resizing width to target_w, and let height scale,
                # then placing it in a black canvas of (target_w, target_h = w * 16/9 if we based it on width).
                
                # To be exact and keep quality: Base the canvas on the original width being the max bounds
                # or base on height. For standard Fit: Target canvas is (target_w, h) where target_w = h*(9/16)
                # But if original is horizontal (w > h), target_w < w. So to fit we must shrink the whole video
                # to width = target_w, which creates standard letterboxing.
                
                # Resize so width matches the narrow 9:16 width
                clip = clip.resize(width=target_w)
                
                # After resizing, place it in the center of a black 9:16 canvas
                # The canvas height is target_w * (16/9)
                canvas_h = int(target_w * (16 / 9))
                clip = clip.on_color(size=(target_w, canvas_h), color=(0, 0, 0), pos='center')
            
            if callback:
                callback(f"Rendering: {os.path.basename(output_path)}...")
                
            # Render using hardware encoder
            clip.write_videofile(
                output_path,
                codec=self.codec,
                audio_codec="aac",
                logger=None,
                threads=4,
                preset="fast" # NVENC preset
            )
            
        except Exception as e:
            print(f"Video Processing Error for {output_path}: {e}")
            raise e
        finally:
            # CRITICAL: Close clip instances to prevent RAM/VRAM leak
            if clip is not None:
                clip.close()
