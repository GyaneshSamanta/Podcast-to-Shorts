import os
import threading
import queue
import time
import customtkinter as ctk
from tkinter import filedialog, messagebox

# Import backend modules
from backend.transcribe_util import TranscriptionEngine
from backend.video_util import VideoEngine

# CustomTkinter theme setup
ctk.set_appearance_mode("Dark")  # Match '#0F172A' vibe
ctk.set_default_color_theme("green") # We will override specific colors for Royal Purple '#7C3AED'

class PodcastClipperApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Podcast-to-Shorts")
        self.geometry("1400x800")
        self.minsize(1000, 600)
        self.configure(fg_color="#0F172A") # Background

        # State
        self.input_file = None
        self.output_dir = None
        self.transcription_data = []  # List of dicts: {'start', 'end', 'text'}
        self.clip_queue = []          # List of dicts: {'id', 'start', 'end', 'label'}
        self.queue_counter = 1
        
        # Threading queues
        self.msg_queue = queue.Queue()

        # Build UI
        self._build_ui()
        
        # Start message polling loop
        self.after(100, self._process_msg_queue)

    def _build_ui(self):
        # Configure grid for three-pane layout + footer
        # Col 0: Transcriptions (Left, weight 2)
        # Col 1: Controls (Center, weight 1)
        # Col 2: Queue (Right, weight 1)
        # Row 0: Main content (weight 1)
        # Row 1: Footer (weight 0)
        self.grid_columnconfigure(0, weight=2)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # --- Left Pane: Video / Transcription ---
        self.left_frame = ctk.CTkFrame(self, fg_color="#1E293B", corner_radius=10)
        self.left_frame.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="nsew")
        
        self.lbl_transcript_title = ctk.CTkLabel(self.left_frame, text="Transcription Output", font=ctk.CTkFont(size=18, weight="bold"), text_color="#F8FAFC")
        self.lbl_transcript_title.pack(pady=10)
        
        self.transcript_scrollable = ctk.CTkScrollableFrame(self.left_frame, fg_color="transparent")
        self.transcript_scrollable.pack(expand=True, fill="both", padx=10, pady=10)
        # (Content filled dynamically)

        # --- Center Pane: Controls ---
        self.center_frame = ctk.CTkFrame(self, fg_color="#1E293B", corner_radius=10)
        self.center_frame.grid(row=0, column=1, padx=5, pady=(10, 0), sticky="nsew")
        
        self.lbl_controls_title = ctk.CTkLabel(self.center_frame, text="Controls", font=ctk.CTkFont(size=18, weight="bold"), text_color="#F8FAFC")
        self.lbl_controls_title.pack(pady=10)
        
        # File Pickers
        self.btn_load_video = ctk.CTkButton(self.center_frame, text="Load Video (.mp4, .mkv, .mov)", fg_color="#7C3AED", hover_color="#5B21B6", command=self._load_video)
        self.btn_load_video.pack(pady=10, padx=20, fill="x")
        self.lbl_input_path = ctk.CTkLabel(self.center_frame, text="No video selected", text_color="#94A3B8", font=ctk.CTkFont(size=11), wraplength=200)
        self.lbl_input_path.pack(pady=(0, 10))

        self.btn_set_output = ctk.CTkButton(self.center_frame, text="Set Output Directory", fg_color="#7C3AED", hover_color="#5B21B6", command=self._set_output_dir)
        self.btn_set_output.pack(pady=10, padx=20, fill="x")
        self.lbl_output_path = ctk.CTkLabel(self.center_frame, text="No directory selected", text_color="#94A3B8", font=ctk.CTkFont(size=11), wraplength=200)
        self.lbl_output_path.pack(pady=(0, 20))
        
        # Actions
        self.btn_transcribe = ctk.CTkButton(self.center_frame, text="Transcribe (Whisper Medium)", command=self._start_transcription)
        self.btn_transcribe.pack(pady=10, padx=20, fill="x")
        
        self.btn_render = ctk.CTkButton(self.center_frame, text="Batch Render (NVENC)", fg_color="#059669", hover_color="#047857", command=self._start_rendering)
        self.btn_render.pack(pady=10, padx=20, fill="x")
        
        # Progress Log
        self.lbl_status = ctk.CTkLabel(self.center_frame, text="Idle", text_color="#F8FAFC")
        self.lbl_status.pack(side="bottom", pady=20)
        self.progressbar = ctk.CTkProgressBar(self.center_frame, progress_color="#7C3AED")
        self.progressbar.pack(side="bottom", padx=20, fill="x", pady=10)
        self.progressbar.set(0)

        # --- Right Pane: Clip Queue ---
        self.right_frame = ctk.CTkFrame(self, fg_color="#1E293B", corner_radius=10)
        self.right_frame.grid(row=0, column=2, padx=10, pady=(10, 0), sticky="nsew")
        
        self.lbl_queue_title = ctk.CTkLabel(self.right_frame, text="Clip Queue (9:16)", font=ctk.CTkFont(size=18, weight="bold"), text_color="#F8FAFC")
        self.lbl_queue_title.pack(pady=10)
        
        # Manual Add
        self.manual_add_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        self.manual_add_frame.pack(fill="x", padx=10, pady=5)
        
        self.entry_start = ctk.CTkEntry(self.manual_add_frame, placeholder_text="Start (s)", width=70)
        self.entry_start.pack(side="left", padx=5)
        self.entry_end = ctk.CTkEntry(self.manual_add_frame, placeholder_text="End (s)", width=70)
        self.entry_end.pack(side="left", padx=5)
        self.btn_add_clip = ctk.CTkButton(self.manual_add_frame, text="Add", width=50, fg_color="#7C3AED", hover_color="#5B21B6", command=self._manual_add_clip_to_queue)
        self.btn_add_clip.pack(side="left", padx=5)

        self.queue_scrollable = ctk.CTkScrollableFrame(self.right_frame, fg_color="transparent")
        self.queue_scrollable.pack(expand=True, fill="both", padx=10, pady=10)
        
        self._refresh_queue_ui()

        # --- Footer ---
        self.footer_frame = ctk.CTkFrame(self, fg_color="#0F172A", height=40)
        self.footer_frame.grid(row=1, column=0, columnspan=3, sticky="ew")
        
        # We simulate links with buttons or labels that open webbrowser
        import webbrowser
        
        footer_text = ctk.CTkLabel(self.footer_frame, text="Built with <3 by Gyanesh | ", text_color="#94A3B8")
        footer_text.pack(side="left", padx=(20, 0), pady=10)
        
        link_font = ctk.CTkFont(underline=True)
        
        lbl_li = ctk.CTkLabel(self.footer_frame, text="LinkedIn", text_color="#38BDF8", cursor="hand2", font=link_font)
        lbl_li.pack(side="left", padx=5)
        lbl_li.bind("<Button-1>", lambda e: webbrowser.open_new("https://www.linkedin.com/in/gyanesh-samanta/"))
        
        lbl_gh = ctk.CTkLabel(self.footer_frame, text="GitHub", text_color="#38BDF8", cursor="hand2", font=link_font)
        lbl_gh.pack(side="left", padx=5)
        lbl_gh.bind("<Button-1>", lambda e: webbrowser.open_new("https://github.com/GyaneshSamanta"))
        
        lbl_nl = ctk.CTkLabel(self.footer_frame, text="Newsletter", text_color="#38BDF8", cursor="hand2", font=link_font)
        lbl_nl.pack(side="left", padx=5)
        lbl_nl.bind("<Button-1>", lambda e: webbrowser.open_new("https://www.linkedin.com/newsletters/gyanesh-on-product-6979386586404651008/"))


    # --- Methods ---
    def _log_msg(self, msg):
        """Thread-safe way to update status label"""
        self.msg_queue.put({"type": "log", "msg": msg})
        
    def _process_msg_queue(self):
        """Polls the queue to update GUI from worker threads."""
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
        except Exception:
            pass
        self.after(100, self._process_msg_queue)

    def _load_video(self):
        filetypes = [("Video Files", "*.mp4 *.mkv *.mov")]
        path = filedialog.askopenfilename(title="Select Video", filetypes=filetypes)
        if path:
            self.input_file = path
            self.lbl_input_path.configure(text=f"...{os.path.basename(path)}")
            self._log_msg(f"Loaded: {os.path.basename(path)}")

    def _set_output_dir(self):
        path = filedialog.askdirectory(title="Select Output Directory")
        if path:
            self.output_dir = path
            self.lbl_output_path.configure(text=f"...{os.path.basename(path)}")
            self._log_msg(f"Output dir set.")

    # --- Transcription Logic ---
    def _start_transcription(self):
        if not self.input_file:
            messagebox.showwarning("Warning", "Please load a video first.")
            return
            
        self.btn_transcribe.configure(state="disabled")
        self.progressbar.configure(mode="indeterminate")
        self.progressbar.start()
        
        # Run in thread to keep UI active
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
            self.msg_queue.put({"type": "stop_progress_anim", "val": 0}) # Custom message handled by simply setting val 0 usually
            
            # Need a thread safe way to stop and reset progressbar
            def reset_pb():
                self.progressbar.stop()
                self.progressbar.configure(mode="determinate")
                self.progressbar.set(0)
                self.btn_transcribe.configure(state="normal")
            self.after(0, reset_pb)

    def _populate_transcription_ui(self):
        # Clear existing
        for widget in self.transcript_scrollable.winfo_children():
            widget.destroy()
            
        if not self.transcription_data:
            return
            
        for seg in self.transcription_data:
            frame = ctk.CTkFrame(self.transcript_scrollable, fg_color="#334155", corner_radius=5)
            frame.pack(fill="x", pady=2, padx=5)
            
            time_str = f"[{seg['start']:.1f}s - {seg['end']:.1f}s]"
            
            # Button to act as clickable timestamp block
            btn = ctk.CTkButton(
                frame, 
                text=f"{time_str} {seg['text'][:60]}...", 
                anchor="w",
                fg_color="transparent",
                hover_color="#475569",
                text_color="#CBD5E1",
                font=ctk.CTkFont(size=12),
                command=lambda s=seg['start'], e=seg['end']: self._add_clip_to_queue(s, e)
            )
            btn.pack(fill="x", padx=5, pady=5)

    # --- Queue Logic ---
    def _add_clip_to_queue(self, start, end):
        clip_label = f"Clip {self.queue_counter}"
        self.queue_counter += 1
        self.clip_queue.append({
            "id": str(time.time()),
            "start": round(float(start), 2),
            "end": round(float(end), 2),
            "label": clip_label
        })
        self._refresh_queue_ui()
        
    def _manual_add_clip_to_queue(self):
        try:
            s = float(self.entry_start.get())
            e = float(self.entry_end.get())
            if s >= e:
                raise ValueError
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
            pass # Ignore invalid edits

    def _refresh_queue_ui(self):
        for widget in self.queue_scrollable.winfo_children():
            widget.destroy()
            
        for clip in self.clip_queue:
            self._create_queue_card(clip)
            
    def _create_queue_card(self, clip):
        card = ctk.CTkFrame(self.queue_scrollable, fg_color="#334155", corner_radius=5)
        card.pack(fill="x", pady=5, padx=5)
        
        # Header (Label + arrows + trash)
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=5, pady=2)
        
        lbl = ctk.CTkLabel(header, text=clip['label'], font=ctk.CTkFont(weight="bold"))
        lbl.pack(side="left")
        
        # Arrows and delete
        btn_del = ctk.CTkButton(header, text="X", width=25, fg_color="#EF4444", hover_color="#B91C1C", command=lambda cid=clip['id']: self._delete_clip(cid))
        btn_del.pack(side="right", padx=2)
        
        btn_down = ctk.CTkButton(header, text="↓", width=25, command=lambda cid=clip['id']: self._move_clip(cid, "down"))
        btn_down.pack(side="right", padx=2)
        
        btn_up = ctk.CTkButton(header, text="↑", width=25, command=lambda cid=clip['id']: self._move_clip(cid, "up"))
        btn_up.pack(side="right", padx=2)
        
        # Body (Editable Timestamps)
        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(body, text="Start:").pack(side="left")
        ent_start = ctk.CTkEntry(body, width=60)
        ent_start.insert(0, str(clip['start']))
        # Bind focus out to update internal state
        ent_start.bind("<FocusOut>", lambda e, cid=clip['id'], ent=ent_start: self._update_clip_time(cid, 'start', ent.get()))
        ent_start.pack(side="left", padx=(5, 10))
        
        ctk.CTkLabel(body, text="End:").pack(side="left")
        ent_end = ctk.CTkEntry(body, width=60)
        ent_end.insert(0, str(clip['end']))
        ent_end.bind("<FocusOut>", lambda e, cid=clip['id'], ent=ent_end: self._update_clip_time(cid, 'end', ent.get()))
        ent_end.pack(side="left", padx=5)

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
                # Ensure values represent current edits before processing
                out_name = f"{clip['label'].replace(' ', '_')}.mp4"
                out_path = os.path.join(self.output_dir, out_name)
                
                self._log_msg(f"Rendering {i+1}/{total}: {out_name} (NVENC)")
                
                engine.process_clip(
                    input_path=self.input_file,
                    output_path=out_path,
                    start_time=clip['start'],
                    end_time=clip['end']
                )
                
                # Update progress
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
