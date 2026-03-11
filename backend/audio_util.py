"""
Audio Enhancement Engine
Uses ffmpeg for EQ processing (no pydub dependency).
Optionally uses DeepFilterNet for AI noise removal.
"""
import os
import subprocess
import tempfile

# Try DeepFilterNet – it's optional
try:
    from df.enhance import enhance, init_df, load_audio, save_audio
    HAS_DF = True
except ImportError:
    HAS_DF = False


def _ffmpeg(*args, **kwargs):
    """Run ffmpeg with hidden console window."""
    return subprocess.run(
        ["ffmpeg", *args],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        **kwargs,
    )


def extract_audio(video_path: str, out_wav: str):
    """Extract audio from a video file to a mono 48kHz WAV."""
    _ffmpeg(
        "-y", "-i", video_path,
        "-vn", "-acodec", "pcm_s16le", "-ar", "48000", "-ac", "1",
        out_wav, check=True,
    )


def _deep_filter(wav_in: str, wav_out: str) -> bool:
    """Run DeepFilterNet noise suppression. Returns True on success."""
    if not HAS_DF:
        return False
    try:
        model, df_state, _ = init_df()
        audio, _ = load_audio(wav_in, sr=df_state.sr())
        enhanced = enhance(model, df_state, audio)
        save_audio(wav_out, enhanced, sr=df_state.sr())
        return True
    except Exception as exc:
        print(f"[Audio] DeepFilterNet skipped: {exc}")
        return False


def _podcast_eq_ffmpeg(wav_in: str, wav_out: str):
    """
    'Podcast Master' EQ via ffmpeg audio filters:
    - High-pass at 80 Hz (kill rumble)
    - Low-mid shelf boost +2dB at 150 Hz (warmth)
    - Presence boost +3dB at 3.5 kHz (clarity)
    - Loudness normalisation to -16 LUFS
    """
    af = (
        "highpass=f=80,"
        "equalizer=f=150:t=h:width_type=o:w=1.5:g=2,"
        "equalizer=f=3500:t=h:width_type=o:w=2:g=3,"
        "loudnorm=I=-16:TP=-1.5"
    )
    _ffmpeg(
        "-y", "-i", wav_in, "-af", af, wav_out,
        check=True,
    )


def enhance_audio(video_path: str, callback=None) -> str | None:
    """
    Full pipeline: extract → denoise → EQ → return path to enhanced WAV.
    Returns None on failure.
    """
    tmp_dir = tempfile.mkdtemp(prefix="pc_audio_")
    raw_wav   = os.path.join(tmp_dir, "raw.wav")
    clean_wav = os.path.join(tmp_dir, "clean.wav")
    final_wav = os.path.join(tmp_dir, "final.wav")

    try:
        # Step 1 – Extract
        if callback:
            callback("Extracting audio…")
        extract_audio(video_path, raw_wav)

        # Step 2 – DeepFilterNet (optional)
        used_df = False
        if HAS_DF:
            if callback:
                callback("Running AI noise removal…")
            used_df = _deep_filter(raw_wav, clean_wav)

        source_wav = clean_wav if used_df else raw_wav

        # Step 3 – Podcast Master EQ via ffmpeg
        if callback:
            callback("Applying Podcast Master EQ…")
        _podcast_eq_ffmpeg(source_wav, final_wav)

        return final_wav

    except Exception as exc:
        print(f"[Audio] Enhancement failed: {exc}")
        if callback:
            callback(f"Audio enhancement failed: {exc}")
        return None
