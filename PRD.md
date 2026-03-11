# PRD: Podcast-to-Shorts (Windows Desktop)

## 1. Product Objective
A specialized, local-only Windows utility that automates the transcription of long-form podcasts and the batch-generation of 9:16 vertical "Shorts" based on a user-defined queue of timestamps.

## 2. Functional Requirements
### 2.1 File & Path Handling (Strict Local)
* **Path-Based Execution:** The app must work directly with file paths. No internal "upload" or "copying" to temp folders unless required by the Whisper library.
* **Format Support:** Input restricted to `.mp4`, `.mkv`, and `.mov`.
* **Output:** User must explicitly select an output directory via a `directory_picker`.

### 2.2 Transcription Engine
* **Model:** `openai-whisper` implementation.
* **Default Model:** `medium` (to fit within 4GB VRAM of 3050 Ti).
* **Output Format:** Display timestamps in the UI as clickable text blocks.

### 2.3 The Sidebar Queue (Core Feature)
* **Clip Card System:** Every selected timestamp creates a "Card" in the right sidebar.
* **Card Attributes:** Contains `ID`, `Start Time`, `End Time`, and a `Label` (e.g., Clip 1).
* **Queue Interaction:**
    * **Reorder:** Drag-and-drop or "Up/Down" buttons to change the order of rendering.
    * **Delete:** A "Trash" icon on each card to remove it from the batch.
    * **Edit:** Inline editing of start/end timestamps on the card.

### 2.4 Rendering Logic
* **Ratio:** Forced 9:16 vertical crop (Center-weighted).
* **Batch Processing:** Sequential rendering of all clips in the sidebar queue.

## 3. User Interface (UI) Design
* **Theme:** "Modern Dark" (Background: `#0F172A`, Foreground: `#F8FAFC`).
* **Accents:** Royal Purple (`#7C3AED`) for buttons and progress bars.
* **Layout:** Three-pane layout (Video/Transcription Left | Controls Center | Clip Queue Right).
* **Footer:** Fixed bottom bar containing:
    * Text: "Built with <3 by Gyanesh"
    * Hyperlinks: 
        * [LinkedIn](https://www.linkedin.com/in/gyanesh-samanta/)
        * [GitHub](https://github.com/GyaneshSamanta)
        * [Newsletter](https://www.linkedin.com/newsletters/gyanesh-on-product-6979386586404651008/)

## 4. Scope Guardrails (Out of Scope)
* NO automatic caption generation on the video.
* NO cloud storage or API integrations.
* NO face-tracking/AI-reframing (Manual center-crop only).