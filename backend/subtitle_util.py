"""
Subtitle Engine – ASS subtitle generation from Whisper segments.
Generates styled .ass files for ffmpeg burn-in.
"""
import os
import tempfile


def _format_ass_time(seconds: float) -> str:
    """Convert seconds to ASS timestamp format H:MM:SS.cc"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def generate_ass(segments: list, clip_start: float, clip_end: float,
                 video_width: int = 1080, video_height: int = 1920) -> str:
    """
    Create a .ass subtitle file for segments within [clip_start, clip_end].

    Parameters
    ----------
    segments : list of dict
        Full Whisper transcription segments (each has start, end, text).
    clip_start, clip_end : float
        The clip boundaries in seconds.
    video_width, video_height : int
        Target output resolution (for subtitle positioning).

    Returns
    -------
    str : Path to the generated .ass file.
    """
    # Filter segments that overlap with the clip range
    relevant = []
    for seg in segments:
        seg_start = seg["start"]
        seg_end   = seg["end"]
        # Overlap check
        if seg_end <= clip_start or seg_start >= clip_end:
            continue
        # Clamp to clip boundaries
        t0 = max(seg_start, clip_start) - clip_start
        t1 = min(seg_end, clip_end)     - clip_start
        relevant.append((t0, t1, seg["text"].strip()))

    if not relevant:
        return None

    # Font size scaled to output height
    font_size = max(18, int(video_height / 28))

    header = f"""[Script Info]
Title: PodcastClipper Captions
ScriptType: v4.00+
PlayResX: {video_width}
PlayResY: {video_height}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Default,Arial,{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,2,1,2,40,40,60,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""

    lines = []
    for t0, t1, text in relevant:
        start_ts = _format_ass_time(t0)
        end_ts   = _format_ass_time(t1)
        # Escape special ASS characters
        safe_text = text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")
        lines.append(f"Dialogue: 0,{start_ts},{end_ts},Default,,0,0,0,,{safe_text}")

    # Write to temp file
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".ass", prefix="pcsub_",
        delete=False, encoding="utf-8"
    )
    tmp.write(header)
    tmp.write("\n".join(lines))
    tmp.write("\n")
    tmp.close()

    return tmp.name
