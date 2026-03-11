import os
import sys
import threading
import queue
import time
import psutil
import customtkinter as ctk
from tkinter import filedialog, messagebox
try:
    import GPUtil
except ImportError:
    GPUtil = None

# Import backend modules
from backend.transcribe_util import TranscriptionEngine
from backend.video_util import VideoEngine

# CustomTkinter theme setup (Framer-like aesthetic)
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green")

# Design Tokens (Framer Vibe: Deep minimalist dark mode with vibrant interactive accents)
COLORS = {
    "bg_app": "#09090B",       # Very dark, almost black background
    "bg_panel": "#18181B",     # Slightly lighter for panels
    "bg_card": "#27272A",      # Elevated cards
    "accent": "#8B5CF6",       # Vibrant Violet (Primary)
    "accent_hover": "#7C3AED", # Deep Violet (Hover)
    "text_pr": "#FAFAFA",      # Primary Text
    "text_sec": "#A1A1AA",     # Secondary Text
    "danger": "#EF4444",       # Destructive Actions
    "danger_hover": "#DC2626", # Destructive Hover
    "success": "#10B981"       # Success indicator
}

class ToolTip(object):
    """Custom Hover Tooltip implementation"""
    def __init__(self, widget, text='widget info'):
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.close)
        self.tw = None

    def enter(self, event=None):
        x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        self.tw = ctk.CTkToplevel(self.widget)
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry(f"+{x}+{y}")
        # Lift above everything
        self.tw.attributes('-topmost', True)
        label = ctk.CTkLabel(self.tw, text=self.text, fg_color="#3F3F46", text_color="#FFFFFF", corner_radius=6, padx=8, pady=4, font=ctk.CTkFont(size=11))
        label.pack(ipadx=1)

    def close(self, event=None):
        if self.tw:
            self.tw.destroy()
            self.tw = None

class PodcastClipperApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Load custom application icon if it exists
        icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.ico")
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)

        self.title("Podcast-to-Shorts")
        self.geometry("1400x800")
        self.minsize(1100, 650)
        self.configure(fg_color=COLORS["bg_app"])

        # State
        self.input_file = None
        self.output_dir = None
        self.transcription_data = []  
        self.clip_queue = []          # List of dicts: {'id', 'start', 'end', 'label', 'mode'}
        self.queue_counter = 1
        
        # Threading queues
        self.msg_queue = queue.Queue()

        # Build UI
        self._build_ui()
        
        # Start loops
        self.after(100, self._process_msg_queue)
        
        # Start Resource Monitor Thread
        self.monitor_active = True
        self.monitor_thread = threading.Thread(target=self._update_resources_loop, daemon=True)
        self.monitor_thread.start()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=2)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # --- Left Pane: Video / Transcription ---
        self.left_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_panel"], corner_radius=16)
        self.left_frame.grid(row=0, column=0, padx=15, pady=(20, 10), sticky="nsew")
        
        self.lbl_transcript_title = ctk.CTkLabel(self.left_frame, text="Transcription Output", font=ctk.CTkFont(family="Inter", size=22, weight="bold"), text_color=COLORS["text_pr"])
        self.lbl_transcript_title.pack(pady=(20, 10), padx=20, anchor="w")
        
        ctk.CTkLabel(self.left_frame, text="Click a highlighted block to add it to your queue.", text_color=COLORS["text_sec"], font=ctk.CTkFont(size=12)).pack(padx=20, anchor="w")
        
        self.transcript_scrollable = ctk.CTkScrollableFrame(self.left_frame, fg_color="transparent")
        self.transcript_scrollable.pack(expand=True, fill="both", padx=10, pady=10)

        # --- Center Pane: Controls ---
        self.center_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_panel"], corner_radius=16)
        self.center_frame.grid(row=0, column=1, padx=5, pady=(20, 10), sticky="nsew")
        
        self.lbl_controls_title = ctk.CTkLabel(self.center_frame, text="Configurations", font=ctk.CTkFont(family="Inter", size=22, weight="bold"), text_color=COLORS["text_pr"])
        self.lbl_controls_title.pack(pady=(20, 20), padx=20, anchor="w")
        
        # File Pickers
        self.btn_load_video = ctk.CTkButton(self.center_frame, text="1. Load Source Video", font=ctk.CTkFont(weight="bold"), fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"], height=40, corner_radius=8, command=self._load_video)
        self.btn_load_video.pack(pady=(10, 5), padx=20, fill="x")
        ToolTip(self.btn_load_video, "Select the raw podcast video file (.mp4, .mkv, .mov).")
        
        self.lbl_input_path = ctk.CTkLabel(self.center_frame, text="No video selected", text_color=COLORS["text_sec"], font=ctk.CTkFont(size=12), wraplength=200)
        self.lbl_input_path.pack(pady=(0, 20))

        self.btn_set_output = ctk.CTkButton(self.center_frame, text="2. Set Output Directory", font=ctk.CTkFont(weight="bold"), fg_color=COLORS["bg_card"], hover_color="#3F3F46", border_width=1, border_color="#52525B", height=40, corner_radius=8, command=self._set_output_dir)
        self.btn_set_output.pack(pady=(10, 5), padx=20, fill="x")
        ToolTip(self.btn_set_output, "Target folder where the final vertical shorts will be saved.")
        
        self.lbl_output_path = ctk.CTkLabel(self.center_frame, text="No directory selected", text_color=COLORS["text_sec"], font=ctk.CTkFont(size=12), wraplength=200)
        self.lbl_output_path.pack(pady=(0, 30))
        
        # Actions
        self.btn_transcribe = ctk.CTkButton(self.center_frame, text="Generate Transcript", height=45, corner_radius=8, font=ctk.CTkFont(weight="bold"), fg_color=COLORS["bg_app"], border_color=COLORS["accent"], border_width=2, hover_color=COLORS["bg_card"], command=self._start_transcription)
        self.btn_transcribe.pack(pady=(10, 10), padx=20, fill="x")
        ToolTip(self.btn_transcribe, "Uses AI (Whisper) to generate clickable timestamps based on speech.")
        
        self.btn_render = ctk.CTkButton(self.center_frame, text="Batch Render Queue", height=45, corner_radius=8, font=ctk.CTkFont(weight="bold"), fg_color=COLORS["success"], hover_color="#059669", text_color="#FFFFFF", command=self._start_rendering)
        self.btn_render.pack(pady=(10, 10), padx=20, fill="x")
        ToolTip(self.btn_render, "Process all clips in the queue into vertical shorts using your GPU.")
        
        # Progress Log
        self.lbl_status = ctk.CTkLabel(self.center_frame, text="Awaiting Input...", text_color=COLORS["text_sec"])
        self.lbl_status.pack(side="bottom", pady=20)
        self.progressbar = ctk.CTkProgressBar(self.center_frame, progress_color=COLORS["accent"], fg_color=COLORS["bg_card"])
        self.progressbar.pack(side="bottom", padx=20, fill="x", pady=10)
        self.progressbar.set(0)

        # --- Right Pane: Clip Queue ---
        self.right_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_panel"], corner_radius=16)
        self.right_frame.grid(row=0, column=2, padx=15, pady=(20, 10), sticky="nsew")
        
        self.lbl_queue_title = ctk.CTkLabel(self.right_frame, text="Clip Queue", font=ctk.CTkFont(family="Inter", size=22, weight="bold"), text_color=COLORS["text_pr"])
        self.lbl_queue_title.pack(pady=(20, 10), padx=20, anchor="w")
        
        ctk.CTkLabel(self.right_frame, text="Define aspect ratio and refine timestamps here.", text_color=COLORS["text_sec"], font=ctk.CTkFont(size=12)).pack(padx=20, anchor="w")
        
        # Manual Add
        self.manual_add_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        self.manual_add_frame.pack(fill="x", padx=15, pady=(15, 5))
        
        self.entry_start = ctk.CTkEntry(self.manual_add_frame, placeholder_text="Start (s)", width=80, corner_radius=6, border_width=1, fg_color=COLORS["bg_card"])
        self.entry_start.pack(side="left", padx=2)
        self.entry_end = ctk.CTkEntry(self.manual_add_frame, placeholder_text="End (s)", width=80, corner_radius=6, border_width=1, fg_color=COLORS["bg_card"])
        self.entry_end.pack(side="left", padx=2)
        self.btn_add_clip = ctk.CTkButton(self.manual_add_frame, text="Add Custom", width=80, corner_radius=6, fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"], command=self._manual_add_clip_to_queue)
        self.btn_add_clip.pack(side="left", padx=(5,0), fill="x", expand=True)

        self.queue_scrollable = ctk.CTkScrollableFrame(self.right_frame, fg_color="transparent")
        self.queue_scrollable.pack(expand=True, fill="both", padx=10, pady=10)
        
        self._refresh_queue_ui()

        # --- Footer ---
        self.footer_frame = ctk.CTkFrame(self, fg_color="transparent", height=40)
        self.footer_frame.grid(row=1, column=0, columnspan=3, sticky="ew", padx=15, pady=(0, 10))
        
        # Links
        links_frame = ctk.CTkFrame(self.footer_frame, fg_color="transparent")
        links_frame.pack(side="left")
        
        import webbrowser
        ctk.CTkLabel(links_frame, text="Built with <3 by Gyanesh  • ", text_color=COLORS["text_sec"], font=ctk.CTkFont(size=12)).pack(side="left")
        link_font = ctk.CTkFont(size=12, underline=True)
        lbl_li = ctk.CTkLabel(links_frame, text="LinkedIn", text_color=COLORS["text_pr"], cursor="hand2", font=link_font)
        lbl_li.pack(side="left", padx=5)
        lbl_li.bind("<Button-1>", lambda e: webbrowser.open_new("https://www.linkedin.com/in/gyanesh-samanta/"))
        lbl_gh = ctk.CTkLabel(links_frame, text="GitHub", text_color=COLORS["text_pr"], cursor="hand2", font=link_font)
        lbl_gh.pack(side="left", padx=5)
        lbl_gh.bind("<Button-1>", lambda e: webbrowser.open_new("https://github.com/GyaneshSamanta"))
        
        # Resource Monitor Label
        self.lbl_resources = ctk.CTkLabel(self.footer_frame, text="System: CPU: 0% | RAM: 0GB | VRAM: 0GB", text_color=COLORS["text_sec"], font=ctk.CTkFont(size=11, family="Consolas"))
        self.lbl_resources.pack(side="right", padx=10)

    # --- Methods ---
    def _log_msg(self, msg):
        self.msg_queue.put({"type": "log", "msg": msg})
        
    def _update_resources_loop(self):
        while self.monitor_active:
            try:
                cpu = psutil.cpu_percent()
                ram_gb = psutil.virtual_memory().used / (1024**3)
                vram_str = "N/A"
                if GPUtil:
                    gpus = GPUtil.getGPUs()
                    if gpus:
                        vram_str = f"{gpus[0].memoryUsed}MB"
                
                res_string = f"Sys: CPU {cpu}% | RAM {ram_gb:.1f}GB | GPU VRAM: {vram_str}"
                self.msg_queue.put({"type": "resource_tick", "msg": res_string})
            except Exception:
                pass
            time.sleep(2)
            
    def destroy(self):
        self.monitor_active = False
        super().destroy()

    def _process_msg_queue(self):
        try:
            while not self.msg_queue.empty():
                msg = self.msg_queue.get_nowait()
                if msg["type"] == "log":
                    self.lbl_status.configure(text=msg["msg"])
                elif msg["type"] == "progress":
                    self.progressbar.set(msg["val"])
                elif msg["type"] == "transcribe_done":
                    self._populate_transcription_ui()
                elif msg["type"] == "render_done":
                    messagebox.showinfo("Success", "Batch rendering complete!")
                elif msg["type"] == "error":
                    messagebox.showerror("Error", msg["msg"])
                elif msg["type"] == "resource_tick":
                    self.lbl_resources.configure(text=msg["msg"])
        except Exception:
            pass
        self.after(100, self._process_msg_queue)

    def _load_video(self):
        filetypes = [("Video Files", "*.mp4 *.mkv *.mov")]
        path = filedialog.askopenfilename(title="Select Video", filetypes=filetypes)
        if path:
            self.input_file = path
            title = os.path.basename(path)
            self.lbl_input_path.configure(text=f"...{title[-30:] if len(title) > 30 else title}")
            self._log_msg(f"Loaded: {title}")

    def _set_output_dir(self):
        path = filedialog.askdirectory(title="Select Output Directory")
        if path:
            self.output_dir = path
            title = os.path.basename(path)
            self.lbl_output_path.configure(text=f"...{title[-30:] if len(title) > 30 else title}")
            self._log_msg(f"Output dir set.")

    # --- Transcription Logic ---
    def _start_transcription(self):
        if not self.input_file:
            messagebox.showwarning("Warning", "Please load a video first.")
            return
            
        self.btn_transcribe.configure(state="disabled")
        self.progressbar.configure(mode="indeterminate")
        self.progressbar.start()
        
        thread = threading.Thread(target=self._worker_transcribe)
        thread.daemon = True
        thread.start()

    def _worker_transcribe(self):
        try:
            self._log_msg("Initializing Whisper Medium model...")
            engine = TranscriptionEngine(model_size="medium")
            segments = engine.transcribe(self.input_file, callback=self._log_msg)
            self.transcription_data = segments
            self._log_msg("Transcription complete.")
            self.msg_queue.put({"type": "transcribe_done"})
        except Exception as e:
            self.msg_queue.put({"type": "error", "msg": str(e)})
            self._log_msg("Transcription failed.")
        finally:
            self.msg_queue.put({"type": "progress", "val": 0})
            def reset_pb():
                self.progressbar.stop()
                self.progressbar.configure(mode="determinate")
                self.progressbar.set(0)
                self.btn_transcribe.configure(state="normal")
            self.after(0, reset_pb)

    def _populate_transcription_ui(self):
        for widget in self.transcript_scrollable.winfo_children():
            widget.destroy()
            
        if not self.transcription_data:
            return
            
        for seg in self.transcription_data:
            frame = ctk.CTkFrame(self.transcript_scrollable, fg_color=COLORS["bg_card"], corner_radius=8)
            frame.pack(fill="x", pady=4, padx=5)
            
            time_str = f"[{seg['start']:.1f}s - {seg['end']:.1f}s]"
            
            # Button to act as clickable timestamp block
            btn = ctk.CTkButton(
                frame, 
                text=f"{time_str} {seg['text'][:80]}...", 
                anchor="w",
                fg_color="transparent",
                hover_color="#3F3F46",
                text_color=COLORS["text_pr"],
                font=ctk.CTkFont(size=12),
                command=lambda s=seg['start'], e=seg['end']: self._add_clip_to_queue(s, e) # Fix: Only pass start/end
            )
            btn.pack(fill="x", padx=5, pady=8)

    # --- Queue Logic ---
    def _add_clip_to_queue(self, start, end):
        clip_label = f"Clip {self.queue_counter}"
        self.queue_counter += 1
        self.clip_queue.append({
            "id": str(time.time()),
            "start": round(float(start), 2),
            "end": round(float(end), 2),
            "label": clip_label,
            "mode": "Crop (Center)" # Default mode
        })
        self._refresh_queue_ui()
        
    def _manual_add_clip_to_queue(self):
        try:
            s = float(self.entry_start.get())
            e = float(self.entry_end.get())
            if s >= e: raise ValueError
            self._add_clip_to_queue(s, e)
            self.entry_start.delete(0, 'end')
            self.entry_end.delete(0, 'end')
        except ValueError:
            messagebox.showwarning("Warning", "Invalid manual timestamps.")

    def _delete_clip(self, clip_id):
        self.clip_queue = [c for c in self.clip_queue if c["id"] != clip_id]
        self._refresh_queue_ui()
        
    def _move_clip(self, clip_id, direction):
        idx = next((i for i, c in enumerate(self.clip_queue) if c["id"] == clip_id), -1)
        if idx == -1: return
        
        if direction == "up" and idx > 0:
            self.clip_queue[idx], self.clip_queue[idx-1] = self.clip_queue[idx-1], self.clip_queue[idx]
        elif direction == "down" and idx < len(self.clip_queue) - 1:
            self.clip_queue[idx], self.clip_queue[idx+1] = self.clip_queue[idx+1], self.clip_queue[idx]
            
        self._refresh_queue_ui()

    def _update_clip_time(self, clip_id, key, new_val):
        try:
            val = float(new_val)
            for c in self.clip_queue:
                if c["id"] == clip_id:
                    c[key] = round(val, 2)
                    break
        except ValueError:
            pass
            
    def _update_clip_attr(self, clip_id, key, new_val):
        for c in self.clip_queue:
            if c["id"] == clip_id:
                c[key] = new_val
                break

    def _refresh_queue_ui(self):
        for widget in self.queue_scrollable.winfo_children():
            widget.destroy()
            
        for clip in self.clip_queue:
            self._create_queue_card(clip)
            
    def _create_queue_card(self, clip):
        card = ctk.CTkFrame(self.queue_scrollable, fg_color=COLORS["bg_card"], corner_radius=10, border_color="#3F3F46", border_width=1)
        card.pack(fill="x", pady=6, padx=5)
        
        # Header (Label + arrows + trash)
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 5))
        
        lbl = ctk.CTkLabel(header, text=clip['label'], font=ctk.CTkFont(weight="bold", size=14))
        lbl.pack(side="left")
        
        # Controls
        btn_del = ctk.CTkButton(header, text="Delete", width=60, height=24, corner_radius=6, fg_color=COLORS["danger"], hover_color=COLORS["danger_hover"], font=ctk.CTkFont(size=11), command=lambda cid=clip['id']: self._delete_clip(cid))
        btn_del.pack(side="right", padx=(5, 0))
        ToolTip(btn_del, "Remove this clip from the queue.")
        
        btn_down = ctk.CTkButton(header, text="↓", width=28, height=24, fg_color="#3F3F46", hover_color="#52525B", command=lambda cid=clip['id']: self._move_clip(cid, "down"))
        btn_down.pack(side="right", padx=2)
        btn_up = ctk.CTkButton(header, text="↑", width=28, height=24, fg_color="#3F3F46", hover_color="#52525B", command=lambda cid=clip['id']: self._move_clip(cid, "up"))
        btn_up.pack(side="right", padx=2)
        
        # Body (Editable Timestamps & Settings)
        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=10, pady=(5, 10))
        
        ctk.CTkLabel(body, text="In:", font=ctk.CTkFont(size=11)).pack(side="left")
        ent_start = ctk.CTkEntry(body, width=55, height=24, justify="center")
        ent_start.insert(0, str(clip['start']))
        ent_start.bind("<FocusOut>", lambda e, cid=clip['id'], ent=ent_start: self._update_clip_time(cid, 'start', ent.get()))
        ent_start.pack(side="left", padx=(2, 10))
        
        ctk.CTkLabel(body, text="Out:", font=ctk.CTkFont(size=11)).pack(side="left")
        ent_end = ctk.CTkEntry(body, width=55, height=24, justify="center")
        ent_end.insert(0, str(clip['end']))
        ent_end.bind("<FocusOut>", lambda e, cid=clip['id'], ent=ent_end: self._update_clip_time(cid, 'end', ent.get()))
        ent_end.pack(side="left", padx=(2, 10))
        
        # Aspect Ratio Mode (Crop vs Fit)
        mode_var = ctk.StringVar(value=clip.get("mode", "Crop (Center)"))
        opt_mode = ctk.CTkOptionMenu(body, values=["Crop (Center)", "Fit (Add Borders)"], variable=mode_var, width=120, height=24, 
                                     font=ctk.CTkFont(size=11), fg_color="#3F3F46", button_color="#52525B", button_hover_color="#71717A",
                                     command=lambda val, cid=clip['id']: self._update_clip_attr(cid, 'mode', val))
        opt_mode.pack(side="right")
        ToolTip(opt_mode, "Select whether to crop the video to fill the screen or fit it within standard borders.")

    # --- Rendering Logic ---
    def _start_rendering(self):
        if not self.input_file or not self.output_dir:
            messagebox.showwarning("Warning", "Please set input video and output directory.")
            return
        if not self.clip_queue:
            messagebox.showwarning("Warning", "Clip queue is empty!")
            return
            
        self.btn_render.configure(state="disabled")
        self.progressbar.set(0)
        self.progressbar.configure(mode="determinate")
        
        thread = threading.Thread(target=self._worker_render)
        thread.daemon = True
        thread.start()

    def _worker_render(self):
        try:
            engine = VideoEngine()
            total = len(self.clip_queue)
            
            for i, clip in enumerate(self.clip_queue):
                out_name = f"{clip['label'].replace(' ', '_')}.mp4"
                out_path = os.path.join(self.output_dir, out_name)
                
                # Fetch mode ('Crop (Center)' or 'Fit (Add Borders)')
                mode = clip.get('mode', 'Crop (Center)')
                
                self._log_msg(f"Rendering {i+1}/{total}: {out_name} [{mode}]")
                
                engine.process_clip(
                    input_path=self.input_file,
                    output_path=out_path,
                    start_time=clip['start'],
                    end_time=clip['end'],
                    mode=mode # Pass mode to engine
                )
                
                progress_val = (i + 1) / total
                self.msg_queue.put({"type": "progress", "val": progress_val})
                
            self._log_msg("All clips rendered successfully.")
            self.msg_queue.put({"type": "render_done"})
            
        except Exception as e:
            self.msg_queue.put({"type": "error", "msg": str(e)})
            self._log_msg("Rendering failed.")
        finally:
            def reset_btn():
                self.btn_render.configure(state="normal")
                self.progressbar.set(1.0)
            self.after(0, reset_btn)

if __name__ == "__main__":
    app = PodcastClipperApp()
    app.mainloop()
