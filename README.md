# 🎬 Podcast-to-Shorts (PodcastClipper Pro)

![Podcast-to-Shorts Banner](https://img.shields.io/badge/Podcast--to--Shorts-AI--Powered-blueviolet?style=for-the-badge&logo=python)
![Python Version](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![CustomTkinter](https://img.shields.io/badge/UI-CustomTkinter-10B981?style=for-the-badge)

An elite Windows application designed to transform long-form podcasts into viral short-form content. Using AI-powered transcription, creative framing, and professional audio mastering, you can generate months of clips in minutes.

---

## ✨ Key Features

### 🎙️ AI-Powered Transcription
- **Whisper Integration:** Uses OpenAI's Whisper model (Medium) for industry-leading speech-to-text accuracy.
- **Segmented Logic:** Click on any transcribed segment to instantly add it to your render queue.

### 🖼️ WYSIWYG Visual Editor
- **Real-time Preview:** See exactly what your clip looks like before rendering with the dynamic crop overlay.
- **Multi-Aspect Ratio Support:**
  - `9:16 Crop` (Vertical Shorts/TikTok)
  - `9:16 Fit` (Letterboxed)
  - `1:1 Square` (Instagram/Facebook)
  - `16:9 Original` (YouTube)

### 💬 Burned-In Captions
- **Open Captions:** Automatically overlay transcription segments as burned-in subtitles.
- **Styled Delivery:** Professional bold white text with black outlines for maximum readability.

### 🎧 Audio Mastering Suite
- **Noise Suppression:** Integrated AI noise removal (via optional DeepFilterNet).
- **Podcast Master EQ:** Automated high-pass filtering (80Hz), warmth boost at 150Hz, and presence boost at 3.5kHz.
- **Loudness Normalization:** Ensures all clips are standardized to -16 LUFS.

### 🚀 High-Performance UI
- **Paned Layout:** Fully resizable 3-pane interface (Transcription | Controls | Queue).
- **Resource Monitoring:** Real-time mini-graph for CPU, RAM, and VRAM usage.
- **Toast Notifications:** Modern, non-blocking notifications for status updates.

---

## 🛠️ Tech Stack

- **GUI:** [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) & `PanedWindow`
- **Transcription:** [OpenAI Whisper](https://github.com/openai/whisper)
- **Video Processing:** [MoviePy](https://zulko.github.io/moviepy/) & [FFmpeg](https://ffmpeg.org/)
- **Computer Vision:** [OpenCV](https://opencv.org/) (for preview extraction)
- **Audio Processing:** Pure FFmpeg filters (Loudnorm, Highpass, Equalizer)
- **Resource Monitoring:** `psutil` & `GPUtil`

---

## 💻 Installation

### 👤 For Users (Easy Start)

1. **Prerequisites:** Ensure you have [Python 3.10+](https://www.python.org/downloads/) installed and on your PATH.
2. **Setup:** Run `start_app.bat`. This will automatically create a virtual environment, install all dependencies, and launch the app.
3. **Optional:** Run `python create_shortcut.py` to create a "Podcast-to-Shorts" shortcut on your Desktop with the official icon.

### 👩‍💻 For Developers (Manual Setup)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/GyaneshSamanta/Podcast-to-Shorts.git
   cd Podcast-to-Shorts
   ```
2. **Create a Virtual Environment:**
   ```bash
   python -m venv venv
   source venv/Scripts/activate  # Windows
   ```
3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Run Application:**
   ```bash
   python main.py
   ```

---

## 📖 Usage Guide

1.  **STEP 1:** Click **Load Source Video** to select your podcast file (.mp4, .mkv, .mov).
2.  **STEP 2:** Click **Set Output Folder** where your clips will be saved.
3.  **STEP 3:** Click **Generate Transcript**. This may take a minute as the AI model loads.
4.  **CLIP SELECTION:** Click on any text block in the left pane to add that segment to the queue. You will see a preview frame appear.
5.  **STEP 4 (Optional):** Toggle **Enhance Audio** or **Burn-In Captions** if desired.
6.  **STEP 5:** Click **Batch Render Queue** and relax while the app handles the heavy lifting!

---

## 📂 Project Structure

```text
Podcast-to-Shorts/
├── assets/             # Icons and visual assets
├── backend/            # Processing engines
│   ├── audio_util.py   # Audio mastering logic
│   ├── subtitle_util.py# ASS subtitle generation
│   ├── transcribe_util.py# Whisper integration
│   └── video_util.py   # MoviePy/FFmpeg pipeline
├── main.py             # Main entry point & UI
├── requirements.txt    # Project dependencies
├── start_app.bat       # User-friendly launcher
└── Launch PodcastClipper.vbs # Silent VBS launcher
```

---

## 🤝 Contributing

Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## ❤️ Support the Developer

If you find this project useful, consider supporting the journey!

<a href="https://buymeachai.ezee.li/GyaneshOnProduct">
  <img src="https://buymeachai.ezee.li/assets/images/buymeachai-button.png" alt="Buy Me A Chai" height="28">
</a>

---

*Built with ❤️ by [Gyanesh Samanta](https://www.linkedin.com/in/gyanesh-samanta/)*
