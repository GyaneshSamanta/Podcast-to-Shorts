"""
Video Processing Engine
- Multi-aspect ratio (9:16 Crop, 9:16 Fit, 1:1 Square, 16:9 Original)
- Subtitle burn-in via ffmpeg ASS filter
- Optional enhanced audio remux
- NVENC / libx264 auto-detection
"""
import os
import subprocess
import tempfile
from PIL import Image

# ── Pillow 10+ compatibility ──────────────────────────────────────────────
if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.LANCZOS

from moviepy.editor import VideoFileClip


class VideoEngine:
    def __init__(self):
        self.codec = self._choose_codec()

    @staticmethod
    def _choose_codec():
        """Pick the best available H.264 encoder."""
        try:
            r = subprocess.run(
                ["ffmpeg", "-hide_banner", "-encoders"],
                capture_output=True, text=True, timeout=5,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if "h264_nvenc" in r.stdout:
                return "h264_nvenc"
        except Exception:
            pass
        return "libx264"

    # ── Aspect ratio helpers ──────────────────────────────────────────────
    @staticmethod
    def _apply_aspect(clip, mode: str):
        """Return (clip, width, height) after applying the requested framing."""
        w, h = clip.size

        if mode == "9:16 Crop":
            tw = int(h * 9 / 16)
            if w > tw:
                x1 = (w - tw) // 2
                clip = clip.crop(x1=x1, y1=0, x2=x1 + tw, y2=h)
            return clip, tw, h

        elif mode == "9:16 Fit":
            tw = int(h * 9 / 16)
            clip = clip.resize(width=tw)
            ch = int(tw * 16 / 9)
            clip = clip.on_color(size=(tw, ch), color=(0, 0, 0), pos="center")
            return clip, tw, ch

        elif mode == "1:1 Square":
            side = min(w, h)
            x1 = (w - side) // 2
            y1 = (h - side) // 2
            clip = clip.crop(x1=x1, y1=y1, x2=x1 + side, y2=y1 + side)
            return clip, side, side

        elif mode == "16:9 Original":
            # keep as-is (most podcasts are already 16:9)
            return clip, w, h

        else:
            # Legacy modes
            if mode == "Crop (Center)":
                tw = int(h * 9 / 16)
                if w > tw:
                    x1 = (w - tw) // 2
                    clip = clip.crop(x1=x1, y1=0, x2=x1 + tw, y2=h)
                return clip, tw, h
            elif mode == "Fit (Add Borders)":
                tw = int(h * 9 / 16)
                clip = clip.resize(width=tw)
                ch = int(tw * 16 / 9)
                clip = clip.on_color(size=(tw, ch), color=(0, 0, 0), pos="center")
                return clip, tw, ch
            return clip, w, h

    # ── Main pipeline ─────────────────────────────────────────────────────
    def process_clip(self, input_path, output_path, start_time, end_time,
                     mode="9:16 Crop",
                     subtitle_path=None,
                     enhanced_audio_path=None,
                     callback=None):
        """
        Full render pipeline:
        1. Extract subclip → apply aspect ratio
        2. Render to temp file
        3. (optional) Burn-in subtitles via ffmpeg
        4. (optional) Replace audio with enhanced version
        """
        clip = None
        tmp_video = None
        try:
            if callback:
                callback(f"Loading: {os.path.basename(input_path)}…")

            clip = VideoFileClip(input_path).subclip(start_time, end_time)
            clip, out_w, out_h = self._apply_aspect(clip, mode)

            # Decide if we need a temp render (for subtitle/audio post-processing)
            needs_post = subtitle_path or enhanced_audio_path
            render_target = output_path

            if needs_post:
                tmp_video = tempfile.NamedTemporaryFile(
                    suffix=".mp4", prefix="pcv_", delete=False
                ).name
                render_target = tmp_video

            if callback:
                callback(f"Rendering ({self.codec}): {os.path.basename(output_path)}…")

            write_kw = dict(
                codec=self.codec, audio_codec="aac",
                logger=None, threads=4,
            )
            if self.codec == "h264_nvenc":
                write_kw["preset"] = "fast"

            clip.write_videofile(render_target, **write_kw)
            clip.close()
            clip = None

            # ── Post-process with ffmpeg ──────────────────────────────────
            if needs_post:
                self._ffmpeg_post(render_target, output_path,
                                  subtitle_path, enhanced_audio_path,
                                  callback)
        except Exception as e:
            print(f"Video Processing Error: {e}")
            raise
        finally:
            if clip is not None:
                clip.close()
            if tmp_video and os.path.exists(tmp_video):
                try:
                    os.remove(tmp_video)
                except OSError:
                    pass

    def _ffmpeg_post(self, input_video, output_path,
                     subtitle_path, audio_path, callback):
        """Run ffmpeg to burn subtitles and/or replace audio."""
        cmd = ["ffmpeg", "-y", "-i", input_video]

        filters = []

        if audio_path and os.path.isfile(audio_path):
            cmd.extend(["-i", audio_path])

        if subtitle_path and os.path.isfile(subtitle_path):
            # Escape backslashes and colons for the ASS filter on Windows
            safe_sub = subtitle_path.replace("\\", "/").replace(":", "\\:")
            filters.append(f"subtitles='{safe_sub}'")

        if filters:
            cmd.extend(["-vf", ",".join(filters)])

        if audio_path and os.path.isfile(audio_path):
            # Map: video from input 0, audio from input 1
            cmd.extend(["-map", "0:v", "-map", "1:a", "-shortest"])
        else:
            cmd.extend(["-c:a", "copy"])

        cmd.extend(["-c:v", self.codec])
        if self.codec == "h264_nvenc":
            cmd.extend(["-preset", "fast"])

        cmd.append(output_path)

        if callback:
            callback("Burning captions / remixing audio…")

        subprocess.run(
            cmd, check=True,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
