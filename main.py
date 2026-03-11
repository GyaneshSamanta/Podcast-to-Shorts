import os
import sys
import threading
import queue
import time
import collections
import tempfile
import psutil
import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog
from PIL import Image as PILImage, ImageTk

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False
try:
    import GPUtil
    HAS_GPU = True
except ImportError:
    HAS_GPU = False

from backend.transcribe_util import TranscriptionEngine
from backend.video_util import VideoEngine
from backend.audio_util import enhance_audio
from backend.subtitle_util import generate_ass

# ── Theme ─────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green")

C = {
    "bg":       "#0C0C0E",
    "panel":    "#141416",
    "card":     "#1F1F23",
    "border":   "#2A2A2E",
    "accent":   "#8B5CF6",
    "accent_h": "#7C3AED",
    "glow":     "#7C3AED",
    "green":    "#10B981",
    "green_h":  "#059669",
    "red":      "#EF4444",
    "red_h":    "#DC2626",
    "txt":      "#FAFAFA",
    "txt2":     "#9CA3AF",
    "txt3":     "#6B7280",
    "link":     "#A78BFA",
}

ASPECT_MODES = ["9:16 Crop", "9:16 Fit", "1:1 Square", "16:9 Original"]
HISTORY_LEN = 30


# ─── Info-Button Tooltip ──────────────────────────────────────────────────
class InfoButton(ctk.CTkButton):
    def __init__(self, master, tip_text, **kw):
        super().__init__(
            master, text="ⓘ", width=22, height=22, corner_radius=11,
            fg_color="transparent", hover_color=C["card"],
            text_color=C["txt3"], font=ctk.CTkFont(size=13), **kw
        )
        self.tip_text = tip_text
        self._tw = None
        self.bind("<Enter>", self._show)
        self.bind("<Leave>", self._hide)

    def _show(self, event=None):
        if self._tw:
            return
        x = self.winfo_rootx() + 30
        y = self.winfo_rooty() - 5
        self._tw = tk.Toplevel(self)
        self._tw.wm_overrideredirect(True)
        self._tw.wm_geometry(f"+{x}+{y}")
        self._tw.attributes("-topmost", True)
        lbl = tk.Label(
            self._tw, text=self.tip_text, background="#27272A",
            foreground="#FFFFFF", padx=8, pady=4,
            font=("Segoe UI", 9), wraplength=250, justify="left"
        )
        lbl.pack()

    def _hide(self, event=None):
        if self._tw:
            self._tw.destroy()
            self._tw = None


def section_header(parent, title, tip=None):
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", padx=20, pady=(18, 4))
    ctk.CTkLabel(
        row, text=title,
        font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
        text_color=C["txt"]
    ).pack(side="left")
    if tip:
        InfoButton(row, tip).pack(side="left", padx=6)
    return row


# ─── Toast Notification ───────────────────────────────────────────────────
class Toast:
    """Non-blocking corner notification that auto-fades."""
    @staticmethod
    def show(parent, message, kind="success", duration=3500):
        bg = {"success": C["green"], "error": C["red"], "info": C["accent"]}.get(kind, C["card"])
        frame = ctk.CTkFrame(parent, fg_color=bg, corner_radius=10)
        frame.place(relx=1.0, rely=1.0, anchor="se", x=-20, y=-20)
        ctk.CTkLabel(
            frame, text=message, text_color="#FFFFFF",
            font=ctk.CTkFont(size=12, weight="bold"),
            wraplength=300
        ).pack(padx=16, pady=10)
        parent.after(duration, frame.destroy)


# ═══════════════════════════════════════════════════════════════════════════
class PodcastClipperApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icon.ico")
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)

        self.title("PodcastClipper Pro")
        self.geometry("1440x820")
        self.minsize(1100, 650)
        self.configure(fg_color=C["bg"])

        # ── State ──
        self.input_file = None
        self.output_dir = None
        self.transcription_data = []
        self.clip_queue = []
        self.queue_counter = 1
        self.msg_queue = queue.Queue()
        self.enhance_audio_var = ctk.BooleanVar(value=False)
        self.burn_captions_var = ctk.BooleanVar(value=False)
        self._preview_photo = None  # prevent GC

        # Resource history
        self.cpu_hist = collections.deque([0]*HISTORY_LEN, maxlen=HISTORY_LEN)
        self.ram_hist = collections.deque([0]*HISTORY_LEN, maxlen=HISTORY_LEN)

        self._build_ui()
        self.after(100, self._poll_queue)

        self.monitor_active = True
        threading.Thread(target=self._resource_loop, daemon=True).start()

    # ─────────────────────────────────────────────────────────────────────
    #  UI Construction
    # ─────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_columnconfigure(0, weight=1)

        self.pw = tk.PanedWindow(
            self, orient=tk.HORIZONTAL, sashwidth=6,
            bg=C["border"], bd=0, handlesize=0
        )
        self.pw.grid(row=0, column=0, sticky="nsew", padx=12, pady=(12, 4))

        self.left_frame  = ctk.CTkFrame(self.pw, fg_color=C["panel"], corner_radius=14)
        self.center_frame = ctk.CTkFrame(self.pw, fg_color=C["panel"], corner_radius=14)
        self.right_frame  = ctk.CTkFrame(self.pw, fg_color=C["panel"], corner_radius=14)

        self.pw.add(self.left_frame,   minsize=280, stretch="always")
        self.pw.add(self.center_frame, minsize=260, stretch="middle")
        self.pw.add(self.right_frame,  minsize=280, stretch="always")

        self._build_left()
        self._build_center()
        self._build_right()
        self._build_footer()

    # ── Left Pane ─────────────────────────────────────────────────────────
    def _build_left(self):
        section_header(self.left_frame, "Preview & Transcription",
                       "Click any segment to add it to the queue. A frame preview appears above.")

        # Video preview canvas
        self.preview_canvas = tk.Canvas(
            self.left_frame, height=200, bg="#000000",
            highlightthickness=0, bd=0
        )
        self.preview_canvas.pack(fill="x", padx=12, pady=(8, 4))
        self.preview_canvas.create_text(
            10, 100, text="No preview — load a video and click a segment",
            fill=C["txt3"], anchor="w", font=("Segoe UI", 10)
        )

        ctk.CTkLabel(
            self.left_frame, text="Transcript segments:",
            text_color=C["txt2"], font=ctk.CTkFont(size=11)
        ).pack(padx=20, anchor="w", pady=(6, 2))

        self.transcript_scroll = ctk.CTkScrollableFrame(
            self.left_frame, fg_color="transparent",
            scrollbar_button_color=C["border"],
            scrollbar_button_hover_color=C["accent"]
        )
        self.transcript_scroll.pack(expand=True, fill="both", padx=8, pady=(0, 10))

    # ── Center Pane ───────────────────────────────────────────────────────
    def _build_center(self):
        section_header(self.center_frame, "Controls",
                       "Follow steps 1→5 to generate your shorts.")

        self._step_label(self.center_frame, "STEP 1")
        self.btn_load = ctk.CTkButton(
            self.center_frame, text="Load Source Video",
            font=ctk.CTkFont(weight="bold"), height=42, corner_radius=8,
            fg_color=C["accent"], hover_color=C["accent_h"],
            command=self._load_video
        )
        self.btn_load.pack(padx=20, fill="x", pady=(0, 2))
        self.lbl_input = ctk.CTkLabel(
            self.center_frame, text="No video selected",
            text_color=C["txt3"], font=ctk.CTkFont(size=11)
        )
        self.lbl_input.pack(pady=(0, 10))

        self._step_label(self.center_frame, "STEP 2")
        self.btn_output = ctk.CTkButton(
            self.center_frame, text="Set Output Folder",
            font=ctk.CTkFont(weight="bold"), height=42, corner_radius=8,
            fg_color=C["card"], hover_color="#2A2A2E",
            border_width=1, border_color=C["border"],
            command=self._set_output_dir
        )
        self.btn_output.pack(padx=20, fill="x", pady=(0, 2))
        self.lbl_output = ctk.CTkLabel(
            self.center_frame, text="No directory selected",
            text_color=C["txt3"], font=ctk.CTkFont(size=11)
        )
        self.lbl_output.pack(pady=(0, 10))

        self._step_label(self.center_frame, "STEP 3")
        self.btn_transcribe = ctk.CTkButton(
            self.center_frame, text="Generate Transcript",
            font=ctk.CTkFont(weight="bold"), height=42, corner_radius=8,
            fg_color="transparent", border_width=2, border_color=C["accent"],
            hover_color=C["card"], command=self._start_transcription
        )
        self.btn_transcribe.pack(padx=20, fill="x", pady=(0, 10))

        # ── Audio & Captions toggles ──
        self._step_label(self.center_frame, "STEP 4 — OPTIONS")

        toggle_frame = ctk.CTkFrame(self.center_frame, fg_color=C["card"], corner_radius=10)
        toggle_frame.pack(padx=20, fill="x", pady=(0, 10))

        r1 = ctk.CTkFrame(toggle_frame, fg_color="transparent")
        r1.pack(fill="x", padx=12, pady=(10, 4))
        ctk.CTkLabel(r1, text="🎧 Enhance Audio", text_color=C["txt"],
                     font=ctk.CTkFont(size=12)).pack(side="left")
        ctk.CTkSwitch(
            r1, text="", variable=self.enhance_audio_var,
            width=40, height=20,
            progress_color=C["accent"], button_color=C["txt"],
            fg_color=C["border"]
        ).pack(side="right")
        InfoButton(r1, "AI noise removal + Podcast Master EQ.\nBoosts warmth & clarity.").pack(side="right", padx=4)

        r2 = ctk.CTkFrame(toggle_frame, fg_color="transparent")
        r2.pack(fill="x", padx=12, pady=(4, 10))
        ctk.CTkLabel(r2, text="💬 Burn-In Captions", text_color=C["txt"],
                     font=ctk.CTkFont(size=12)).pack(side="left")
        ctk.CTkSwitch(
            r2, text="", variable=self.burn_captions_var,
            width=40, height=20,
            progress_color=C["accent"], button_color=C["txt"],
            fg_color=C["border"]
        ).pack(side="right")
        InfoButton(r2, "Overlay transcription subtitles directly on the video.").pack(side="right", padx=4)

        # ── Render button ──
        self._step_label(self.center_frame, "STEP 5")
        self.btn_render = ctk.CTkButton(
            self.center_frame, text="Batch Render Queue",
            font=ctk.CTkFont(weight="bold"), height=42, corner_radius=8,
            fg_color=C["green"], hover_color=C["green_h"],
            text_color="#FFFFFF", command=self._start_rendering
        )
        self.btn_render.pack(padx=20, fill="x", pady=(0, 10))

        # Progress
        self.lbl_stage = ctk.CTkLabel(
            self.center_frame, text="",
            text_color=C["accent"], font=ctk.CTkFont(size=10, weight="bold")
        )
        self.lbl_stage.pack(side="bottom", pady=(0, 2))
        self.progressbar = ctk.CTkProgressBar(
            self.center_frame, progress_color=C["accent"], fg_color=C["card"]
        )
        self.progressbar.pack(side="bottom", padx=20, fill="x", pady=(0, 4))
        self.progressbar.set(0)
        self.lbl_status = ctk.CTkLabel(
            self.center_frame, text="Awaiting input…",
            text_color=C["txt2"], font=ctk.CTkFont(size=11)
        )
        self.lbl_status.pack(side="bottom", pady=(0, 4))

    def _step_label(self, parent, text):
        ctk.CTkLabel(
            parent, text=text,
            text_color=C["accent"], font=ctk.CTkFont(size=10, weight="bold")
        ).pack(padx=22, anchor="w", pady=(6, 2))

    # ── Right Pane ────────────────────────────────────────────────────────
    def _build_right(self):
        section_header(self.right_frame, "Clip Queue",
                       "Each clip can have its own framing. Use ↑↓ to reorder.")

        ctk.CTkLabel(
            self.right_frame,
            text="Add clips manually or click transcript blocks.",
            text_color=C["txt3"], font=ctk.CTkFont(size=11)
        ).pack(padx=20, anchor="w", pady=(0, 8))

        add_row = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        add_row.pack(fill="x", padx=14, pady=(0, 6))
        self.entry_start = ctk.CTkEntry(
            add_row, placeholder_text="Start (s)", width=80,
            corner_radius=6, fg_color=C["card"], border_width=1, border_color=C["border"]
        )
        self.entry_start.pack(side="left", padx=2)
        self.entry_end = ctk.CTkEntry(
            add_row, placeholder_text="End (s)", width=80,
            corner_radius=6, fg_color=C["card"], border_width=1, border_color=C["border"]
        )
        self.entry_end.pack(side="left", padx=2)
        ctk.CTkButton(
            add_row, text="+ Add", width=70, corner_radius=6,
            fg_color=C["accent"], hover_color=C["accent_h"],
            command=self._manual_add
        ).pack(side="left", padx=(6, 0), fill="x", expand=True)

        self.queue_scroll = ctk.CTkScrollableFrame(
            self.right_frame, fg_color="transparent",
            scrollbar_button_color=C["border"],
            scrollbar_button_hover_color=C["accent"]
        )
        self.queue_scroll.pack(expand=True, fill="both", padx=8, pady=(0, 10))
        self._refresh_queue()

    # ── Footer ────────────────────────────────────────────────────────────
    def _build_footer(self):
        import webbrowser
        ft = ctk.CTkFrame(self, fg_color=C["panel"], corner_radius=10, height=70)
        ft.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 10))
        ft.grid_propagate(False)

        left = ctk.CTkFrame(ft, fg_color="transparent")
        left.pack(side="left", padx=16, pady=8)
        ctk.CTkLabel(left, text="Built with <3 by Gyanesh  •",
                     text_color=C["txt3"], font=ctk.CTkFont(size=11)).pack(side="left")
        lf = ctk.CTkFont(size=11, underline=True)
        for name, url in [
            ("LinkedIn", "https://www.linkedin.com/in/gyanesh-samanta/"),
            ("GitHub",   "https://github.com/GyaneshSamanta"),
            ("Newsletter", "https://www.linkedin.com/newsletters/gyanesh-on-product-6979386586404651008/"),
        ]:
            lbl = ctk.CTkLabel(left, text=name, text_color=C["link"], cursor="hand2", font=lf)
            lbl.pack(side="left", padx=5)
            lbl.bind("<Button-1>", lambda e, u=url: webbrowser.open_new(u))

        right = ctk.CTkFrame(ft, fg_color="transparent")
        right.pack(side="right", padx=16, pady=4)
        self.lbl_res = ctk.CTkLabel(
            right, text="CPU 0%  •  RAM 0 GB  •  VRAM N/A",
            text_color=C["txt3"], font=ctk.CTkFont(size=10, family="Consolas")
        )
        self.lbl_res.pack(anchor="e")
        self.canvas_graph = tk.Canvas(
            right, width=180, height=32, bg=C["panel"],
            highlightthickness=0, bd=0
        )
        self.canvas_graph.pack(anchor="e", pady=(2, 0))

    # ─────────────────────────────────────────────────────────────────────
    #  Resource Monitor
    # ─────────────────────────────────────────────────────────────────────
    def _resource_loop(self):
        while self.monitor_active:
            try:
                cpu = psutil.cpu_percent()
                ram = psutil.virtual_memory().used / (1024**3)
                vram = "N/A"
                if HAS_GPU:
                    gpus = GPUtil.getGPUs()
                    if gpus:
                        vram = f"{gpus[0].memoryUsed}MB"
                self.cpu_hist.append(cpu)
                self.ram_hist.append(ram)
                self.msg_queue.put({
                    "type": "res",
                    "txt": f"CPU {cpu:.0f}%  •  RAM {ram:.1f} GB  •  VRAM {vram}"
                })
            except Exception:
                pass
            time.sleep(2)

    def _draw_graph(self):
        c = self.canvas_graph
        c.delete("all")
        w, h = 180, 32
        pts = list(self.cpu_hist)
        if len(pts) > 1:
            step = w / (len(pts) - 1)
            coords = []
            for i, v in enumerate(pts):
                coords.extend([i * step, h - (v / 100) * h])
            c.create_line(coords, fill=C["accent"], width=1.5, smooth=True)
        pts_r = list(self.ram_hist)
        if len(pts_r) > 1:
            step = w / (len(pts_r) - 1)
            coords = []
            for i, v in enumerate(pts_r):
                coords.extend([i * step, h - (min(v, 32) / 32) * h])
            c.create_line(coords, fill=C["green"], width=1.5, smooth=True)

    def destroy(self):
        self.monitor_active = False
        super().destroy()

    # ─────────────────────────────────────────────────────────────────────
    #  Message Queue
    # ─────────────────────────────────────────────────────────────────────
    def _log(self, msg):
        self.msg_queue.put({"type": "log", "msg": msg})

    def _set_stage(self, stage_text):
        self.msg_queue.put({"type": "stage", "msg": stage_text})

    def _poll_queue(self):
        try:
            while not self.msg_queue.empty():
                m = self.msg_queue.get_nowait()
                t = m["type"]
                if t == "log":
                    self.lbl_status.configure(text=m["msg"])
                elif t == "stage":
                    self.lbl_stage.configure(text=m["msg"])
                elif t == "progress":
                    self.progressbar.set(m["val"])
                elif t == "transcribe_done":
                    self._populate_transcript()
                    Toast.show(self, f"✓ {len(self.transcription_data)} segments found", "success")
                elif t == "render_done":
                    Toast.show(self, "✓ All clips rendered successfully!", "success")
                elif t == "error":
                    Toast.show(self, f"✗ {m['msg']}", "error", 5000)
                elif t == "res":
                    self.lbl_res.configure(text=m["txt"])
                    self._draw_graph()
        except Exception:
            pass
        self.after(100, self._poll_queue)

    # ─────────────────────────────────────────────────────────────────────
    #  File I/O
    # ─────────────────────────────────────────────────────────────────────
    def _load_video(self):
        path = filedialog.askopenfilename(
            title="Select Video",
            filetypes=[("Video Files", "*.mp4 *.mkv *.mov")]
        )
        if path:
            self.input_file = os.path.normpath(path)
            name = os.path.basename(self.input_file)
            self.lbl_input.configure(text=name if len(name) <= 35 else f"…{name[-32:]}")
            self._log(f"Loaded: {name}")
            self._show_preview_frame(0)  # Show first frame

    def _set_output_dir(self):
        path = filedialog.askdirectory(title="Select Output Directory")
        if path:
            self.output_dir = os.path.normpath(path)
            name = os.path.basename(self.output_dir)
            self.lbl_output.configure(text=name if len(name) <= 35 else f"…{name[-32:]}")
            self._log("Output folder set.")

    # ─────────────────────────────────────────────────────────────────────
    #  Video Preview (OpenCV)
    # ─────────────────────────────────────────────────────────────────────
    def _show_preview_frame(self, time_sec, mode="9:16 Crop"):
        """Extract a frame and draw crop overlay on the preview canvas."""
        if not self.input_file or not HAS_CV2:
            return

        def _extract():
            try:
                cap = cv2.VideoCapture(self.input_file)
                fps = cap.get(cv2.CAP_PROP_FPS) or 25
                cap.set(cv2.CAP_PROP_POS_FRAMES, int(time_sec * fps))
                ret, frame = cap.read()
                cap.release()
                if not ret:
                    return

                src_h, src_w = frame.shape[:2]

                # Scale to preview width
                canvas_w = self.preview_canvas.winfo_width() or 400
                scale = canvas_w / src_w
                disp_w = canvas_w
                disp_h = int(src_h * scale)

                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = PILImage.fromarray(frame_rgb).resize((disp_w, disp_h), PILImage.LANCZOS)

                # Draw crop overlay rectangle
                self._preview_photo = ImageTk.PhotoImage(img)

                def _update():
                    self.preview_canvas.delete("all")
                    self.preview_canvas.configure(height=disp_h)
                    self.preview_canvas.create_image(0, 0, anchor="nw", image=self._preview_photo)

                    # Draw crop rectangle
                    if "Crop" in mode or "9:16" in mode:
                        crop_w = int(disp_h * 9 / 16)
                        x1 = (disp_w - crop_w) // 2
                        self.preview_canvas.create_rectangle(
                            x1, 0, x1 + crop_w, disp_h,
                            outline=C["glow"], width=2, dash=(6, 4)
                        )
                    elif "1:1" in mode:
                        side = min(disp_w, disp_h)
                        x1 = (disp_w - side) // 2
                        y1 = (disp_h - side) // 2
                        self.preview_canvas.create_rectangle(
                            x1, y1, x1 + side, y1 + side,
                            outline=C["green"], width=2, dash=(6, 4)
                        )

                self.after(0, _update)
            except Exception as exc:
                print(f"[Preview] {exc}")

        threading.Thread(target=_extract, daemon=True).start()

    # ─────────────────────────────────────────────────────────────────────
    #  Transcription
    # ─────────────────────────────────────────────────────────────────────
    def _start_transcription(self):
        if not self.input_file:
            Toast.show(self, "Load a video first!", "error")
            return
        if not os.path.isfile(self.input_file):
            Toast.show(self, f"File not found: {self.input_file}", "error")
            return
        self.btn_transcribe.configure(state="disabled")
        self.progressbar.configure(mode="indeterminate")
        self.progressbar.start()
        self._set_stage("STAGE 1 / 3  —  Transcribing")
        threading.Thread(target=self._worker_transcribe, daemon=True).start()

    def _worker_transcribe(self):
        try:
            self._log("Loading Whisper model…")
            engine = TranscriptionEngine(model_size="medium")
            self._log("Model loaded. Transcribing audio…")
            segs = engine.transcribe(self.input_file, callback=self._log)
            self.transcription_data = segs
            self._log(f"Transcription complete — {len(segs)} segments.")
            self.msg_queue.put({"type": "transcribe_done"})
        except Exception as e:
            self.msg_queue.put({"type": "error", "msg": f"Transcription failed: {e}"})
            self._log("Transcription failed.")
        finally:
            self._set_stage("")
            def _reset():
                self.progressbar.stop()
                self.progressbar.configure(mode="determinate")
                self.progressbar.set(0)
                self.btn_transcribe.configure(state="normal")
            self.after(0, _reset)

    def _populate_transcript(self):
        for w in self.transcript_scroll.winfo_children():
            w.destroy()
        if not self.transcription_data:
            return
        for seg in self.transcription_data:
            ts = f"[{seg['start']:.1f}s – {seg['end']:.1f}s]"
            txt = seg["text"][:90]
            frame = ctk.CTkFrame(self.transcript_scroll, fg_color=C["card"], corner_radius=8)
            frame.pack(fill="x", pady=3, padx=4)
            btn = ctk.CTkButton(
                frame, text=f"{ts}  {txt}", anchor="w",
                fg_color="transparent", hover_color="#2A2A30",
                text_color=C["txt"], font=ctk.CTkFont(size=12),
                command=lambda s=seg["start"], e=seg["end"]: self._add_clip(s, e)
            )
            btn.pack(fill="x", padx=4, pady=6)

    # ─────────────────────────────────────────────────────────────────────
    #  Queue Management
    # ─────────────────────────────────────────────────────────────────────
    def _add_clip(self, start, end):
        label = f"Clip {self.queue_counter}"
        self.queue_counter += 1
        self.clip_queue.append({
            "id": str(time.time()),
            "start": round(float(start), 2),
            "end": round(float(end), 2),
            "label": label,
            "mode": "9:16 Crop"
        })
        self._refresh_queue()
        self._show_preview_frame(start, "9:16 Crop")

    def _manual_add(self):
        try:
            s = float(self.entry_start.get())
            e = float(self.entry_end.get())
            if s >= e:
                raise ValueError
            self._add_clip(s, e)
            self.entry_start.delete(0, "end")
            self.entry_end.delete(0, "end")
        except ValueError:
            Toast.show(self, "Enter valid Start < End seconds.", "error")

    def _del_clip(self, cid):
        self.clip_queue = [c for c in self.clip_queue if c["id"] != cid]
        self._refresh_queue()

    def _move_clip(self, cid, direction):
        idx = next((i for i, c in enumerate(self.clip_queue) if c["id"] == cid), -1)
        if idx == -1:
            return
        if direction == "up" and idx > 0:
            self.clip_queue[idx], self.clip_queue[idx-1] = self.clip_queue[idx-1], self.clip_queue[idx]
        elif direction == "down" and idx < len(self.clip_queue) - 1:
            self.clip_queue[idx], self.clip_queue[idx+1] = self.clip_queue[idx+1], self.clip_queue[idx]
        self._refresh_queue()

    def _set_clip(self, cid, key, val):
        for c in self.clip_queue:
            if c["id"] == cid:
                if key in ("start", "end"):
                    try:
                        c[key] = round(float(val), 2)
                    except ValueError:
                        pass
                else:
                    c[key] = val
                if key == "mode":
                    self._show_preview_frame(c["start"], val)
                break

    def _refresh_queue(self):
        for w in self.queue_scroll.winfo_children():
            w.destroy()
        for clip in self.clip_queue:
            self._queue_card(clip)

    def _queue_card(self, clip):
        card = ctk.CTkFrame(
            self.queue_scroll, fg_color=C["card"], corner_radius=10,
            border_color=C["border"], border_width=1
        )
        card.pack(fill="x", pady=5, padx=4)

        # ── Glow hover effect ──
        def _enter(e):
            card.configure(border_color=C["glow"], border_width=2)
        def _leave(e):
            card.configure(border_color=C["border"], border_width=1)
        card.bind("<Enter>", _enter)
        card.bind("<Leave>", _leave)

        # Row 1 – label + controls
        r1 = ctk.CTkFrame(card, fg_color="transparent")
        r1.pack(fill="x", padx=10, pady=(8, 4))
        ctk.CTkLabel(r1, text=clip["label"],
                     font=ctk.CTkFont(weight="bold", size=13)).pack(side="left")
        ctk.CTkButton(
            r1, text="✕", width=26, height=22, corner_radius=6,
            fg_color=C["red"], hover_color=C["red_h"],
            font=ctk.CTkFont(size=11),
            command=lambda: self._del_clip(clip["id"])
        ).pack(side="right", padx=(4, 0))
        ctk.CTkButton(
            r1, text="↓", width=26, height=22,
            fg_color="#2A2A2E", hover_color="#3A3A3E",
            command=lambda: self._move_clip(clip["id"], "down")
        ).pack(side="right", padx=2)
        ctk.CTkButton(
            r1, text="↑", width=26, height=22,
            fg_color="#2A2A2E", hover_color="#3A3A3E",
            command=lambda: self._move_clip(clip["id"], "up")
        ).pack(side="right", padx=2)

        # Row 2 – timestamps + aspect mode
        r2 = ctk.CTkFrame(card, fg_color="transparent")
        r2.pack(fill="x", padx=10, pady=(0, 8))

        ctk.CTkLabel(r2, text="In:", font=ctk.CTkFont(size=10),
                     text_color=C["txt3"]).pack(side="left")
        e_s = ctk.CTkEntry(r2, width=52, height=22, justify="center",
                           fg_color=C["bg"], border_width=0)
        e_s.insert(0, str(clip["start"]))
        e_s.bind("<FocusOut>", lambda ev: self._set_clip(clip["id"], "start", e_s.get()))
        e_s.pack(side="left", padx=(2, 8))

        ctk.CTkLabel(r2, text="Out:", font=ctk.CTkFont(size=10),
                     text_color=C["txt3"]).pack(side="left")
        e_e = ctk.CTkEntry(r2, width=52, height=22, justify="center",
                           fg_color=C["bg"], border_width=0)
        e_e.insert(0, str(clip["end"]))
        e_e.bind("<FocusOut>", lambda ev: self._set_clip(clip["id"], "end", e_e.get()))
        e_e.pack(side="left", padx=(2, 8))

        mode_var = ctk.StringVar(value=clip.get("mode", "9:16 Crop"))
        ctk.CTkOptionMenu(
            r2, values=ASPECT_MODES,
            variable=mode_var, width=130, height=22,
            font=ctk.CTkFont(size=10),
            fg_color="#2A2A2E", button_color="#3A3A3E",
            button_hover_color="#4A4A4E",
            command=lambda v: self._set_clip(clip["id"], "mode", v)
        ).pack(side="right")

    # ─────────────────────────────────────────────────────────────────────
    #  Rendering Pipeline
    # ─────────────────────────────────────────────────────────────────────
    def _start_rendering(self):
        if not self.input_file or not self.output_dir:
            Toast.show(self, "Set both video and output folder first.", "error")
            return
        if not self.clip_queue:
            Toast.show(self, "Add at least one clip to the queue.", "error")
            return
        self.btn_render.configure(state="disabled")
        self.progressbar.set(0)
        self.progressbar.configure(mode="determinate")
        threading.Thread(target=self._worker_render, daemon=True).start()

    def _worker_render(self):
        try:
            engine = VideoEngine()
            total = len(self.clip_queue)

            # ── Stage 2: Audio Enhancement (if enabled) ──
            enhanced_wav = None
            if self.enhance_audio_var.get():
                self._set_stage("STAGE 2 / 3  —  Enhancing Audio")
                enhanced_wav = enhance_audio(self.input_file, callback=self._log)
                if enhanced_wav:
                    self._log("Audio enhanced successfully.")
                else:
                    self._log("Audio enhancement skipped (not available).")

            # ── Stage 3: Rendering ──
            self._set_stage("STAGE 3 / 3  —  Rendering Clips")

            for i, clip in enumerate(self.clip_queue):
                name = f"{clip['label'].replace(' ', '_')}.mp4"
                out = os.path.join(self.output_dir, name)
                mode = clip.get("mode", "9:16 Crop")

                # Generate subtitles if enabled
                sub_path = None
                if self.burn_captions_var.get() and self.transcription_data:
                    sub_path = generate_ass(
                        self.transcription_data,
                        clip["start"], clip["end"]
                    )

                self._log(f"Rendering {i+1}/{total}: {name} [{mode}]")

                engine.process_clip(
                    self.input_file, out,
                    clip["start"], clip["end"],
                    mode=mode,
                    subtitle_path=sub_path,
                    enhanced_audio_path=enhanced_wav,
                    callback=self._log,
                )

                # Clean up subtitle temp file
                if sub_path and os.path.exists(sub_path):
                    try:
                        os.remove(sub_path)
                    except OSError:
                        pass

                self.msg_queue.put({"type": "progress", "val": (i+1)/total})

            self._log("All clips rendered.")
            self.msg_queue.put({"type": "render_done"})

        except Exception as e:
            self.msg_queue.put({"type": "error", "msg": str(e)})
            self._log("Render failed.")
        finally:
            self._set_stage("")
            self.after(0, lambda: (
                self.btn_render.configure(state="normal"),
                self.progressbar.set(1.0)
            ))


if __name__ == "__main__":
    app = PodcastClipperApp()
    app.mainloop()
