import whisper
import torch
import gc

class TranscriptionEngine:
    def __init__(self, model_size="medium"):
        self.model_size = model_size
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None

    def _load_model(self):
        """Loads the model into VRAM/RAM only when needed."""
        if self.model is None:
            print(f"Loading Whisper '{self.model_size}' model on {self.device}...")
            # Use float16 on CUDA to save VRAM, fallback to float32 on CPU
            fp16 = True if self.device == "cuda" else False
            self.model = whisper.load_model(self.model_size, device=self.device)

    def _unload_model(self):
        """Unloads the model and clears VRAM strictly."""
        if self.model is not None:
            del self.model
            self.model = None
            if self.device == "cuda":
                torch.cuda.empty_cache()
            gc.collect()
            print("Whisper model unloaded from VRAM.")

    def transcribe(self, file_path, callback=None):
        """
        Transcribes the given file and returns a list of segment dictionaries.
        Each segment contains: start, end, text.
        """
        try:
            self._load_model()
            
            if callback:
                callback("Starting transcription (this might take a while)...")
            
            # Whisper internal FP16 logic handles the inference
            fp16 = True if self.device == "cuda" else False
            result = self.model.transcribe(file_path, fp16=fp16)
            
            # Extract usable segments
            segments = []
            for seg in result["segments"]:
                segments.append({
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": seg["text"].strip()
                })
                
            return segments
            
        except Exception as e:
            print(f"Transcription Error: {e}")
            raise e
        finally:
            # Always ensure VRAM is cleared after transcription
            self._unload_model()
