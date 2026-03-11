# Technical Specification: PodcastClipper Pro

## 1. High-Refresh UI & Performance Logic
* **Framerate Unlock:** Set `CustomTkinter` update intervals to match the 165Hz refresh rate ($1000/165 \approx 6ms$ update loops). Use `threaded` GUI updates to prevent the "Main Thread" from choking on window resizing.
* **Memory Optimization:** Use `OpenCV` (cv2) for the preview window instead of standard Tkinter ImageLabels for lower latency.

## 2. The Audio Engine (Voice Focus)
* **Library:** `DeepFilterNet` (The industry standard for Python-based real-time noise suppression).
* **Logic:** 1. Extract Audio -> 2. Pass through DeepFilterNet -> 3. Apply `pydub` High-Pass Filter (80Hz) and a Mid-High Shelf (+3dB at 3kHz) -> 4. Remux with Video.
* **Control:** `Enhance_Audio: Boolean` state in the Global Dictionary.

## 3. Subtitle Engine (Burned-In)
* **Implementation:** Generate a temporary `.ass` (Advanced Substation Alpha) file from the Whisper timestamps.
* **FFmpeg Integration:** Use the `-vf "subtitles=file.ass"` filter during the final render pass. This is 10x faster than rendering subtitles frame-by-frame via MoviePy.

## 4. Visual Preview Math
* **Interactive Cropping:**
    ```python
    preview_scale = display_width / source_width
    crop_width_px = source_height * (9/16)
    offset_x = (source_width - crop_width_px) / 2
    # Draw a purple rectangle on the preview at (offset_x, 0) to (offset_x + crop_width_px, source_height)
    ```

## 5. Deployment Specs (Production)
* **NVIDIA Driver Check:** App must verify `nvenc` availability at launch. If absent, fallback to `libx264` (CPU) but warn the user.
* **Dependency Update:** Add `deepfilternet`, `pydub`, `opencv-python`.
* **PyInstaller:** Must bundle the `DeepFilterNet` pre-trained model weights in the `assets/` folder.