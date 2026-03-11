# PRD: PodcastClipper Pro (Gyanesh Edition)

## 1. Advanced Functional Requirements
### 1.1 Visual "Shorts" Preview (The WYSIWYG Editor)
* **Real-time Crop Preview:** Before rendering, the app must show a 9:16 overlay on a frame of the video.
* **Aspect Ratio Selection:** Toggle between 9:16 (Shorts), 1:1 (Instagram), and 16:9 (Original).
* **Burned-In Captions:** The transcription for the selected clip must be automatically overlaid as "Open Captions" (Burned-in) on the output video.

### 1.2 Audio Mastering Suite
* **Noise Profile:** Integration of `DeepFilterNet` or `Noisey` for AI-based background noise removal.
* **Voice Equalizer:** A toggle for "Podcast Master" EQ (Boosts 100Hz-200Hz for warmth, 3kHz-5kHz for clarity).
* **Toggle Interface:** A simple "Enhance Audio" checkbox in the main control panel.

### 1.3 High-Performance UI
* **165Hz Optimization:** The GUI must decouple the rendering of the video preview from the UI thread to eliminate resizing lag.
* **Responsive Layout:** Panes must use a grid-weight system that doesn't trigger a full window redraw on every pixel of movement.

## 2. Production-Ready Design Enhancements
* **Dynamic Progress:** Multi-stage progress bar (Stage 1: Transcribing -> Stage 2: Audio Cleaning -> Stage 3: Rendering).
* **Hover States:** All sidebar cards must have "Glow" hover states (Purple #7C3AED).
* **Toast Notifications:** Success/Error messages that pop up in the corner rather than blocking the main UI with popups.

## 3. Mandatory Footer (Updated)
* **Text:** Built with <3 by Gyanesh
* **Links:** [LinkedIn](https://www.linkedin.com/in/gyanesh-samanta/) | [GitHub](https://github.com/GyaneshSamanta) | [Newsletter](https://www.linkedin.com/newsletters/gyanesh-on-product-6979386586404651008/)