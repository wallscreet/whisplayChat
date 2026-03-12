import queue
import subprocess
import threading
from typing import Optional
import wave

from PIL import Image, ImageDraw, ImageFont
import os
from Driver.WhisPlay import WhisPlayBoard
import pyaudio


class ScreenHelper:
    def __init__(self, debug: bool = False):
        self.board = WhisPlayBoard()
        self.board.set_backlight(60)
        self.width = self.board.LCD_WIDTH
        self.height = self.board.LCD_HEIGHT
        self.debug = debug
        self._cache = {}
        
        self._preload_common_screens()

    def _load_jpg_as_rgb565(self, filepath: str):
        if not os.path.isfile(filepath):
            raise FileNotFoundError(f"Image not found: {filepath}")
        
        img = Image.open(filepath).convert('RGB')
        original_width, original_height = img.size
        aspect_ratio = original_width / original_height
        screen_aspect = self.width / self.height

        if aspect_ratio > screen_aspect:
            new_height = self.height
            new_width = int(new_height * aspect_ratio)
            resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            offset_x = (new_width - self.width) // 2
            cropped = resized.crop((offset_x, 0, offset_x + self.width, self.height))
        else:
            new_width = self.width
            new_height = int(new_width / aspect_ratio)
            resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            offset_y = (new_height - self.height) // 2
            cropped = resized.crop((0, offset_y, self.width, offset_y + self.height))

        pixel_data = []
        for y in range(self.height):
            for x in range(self.width):
                r, g, b = cropped.getpixel((x, y))
                rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
                pixel_data.extend([(rgb565 >> 8) & 0xFF, rgb565 & 0xFF])
        return pixel_data

    def _make_text_image(self, text: str, sub_text: str = "", bg_color=(0,0,0), text_color=(255,255,255)):
        img = Image.new('RGB', (self.width, self.height), bg_color)
        draw = ImageDraw.Draw(img)

        font_large = font_small = ImageFont.load_default()
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        ]
        for path in font_paths:
            if os.path.exists(path):
                try:
                    font_large = ImageFont.truetype(path, 28)
                    font_small = ImageFont.truetype(path, 18)
                    break
                except:
                    pass

        # Main text
        bbox = draw.textbbox((0, 0), text, font=font_large)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(((self.width - tw) // 2, (self.height - th) // 2 - 15), text, fill=text_color, font=font_large)

        # Sub text
        if sub_text:
            bbox2 = draw.textbbox((0, 0), sub_text, font=font_small)
            tw2 = bbox2[2] - bbox2[0]
            draw.text(((self.width - tw2) // 2, (self.height - th) // 2 + 30), sub_text, fill=text_color, font=font_small)

        pixel_data = []
        for y in range(self.height):
            for x in range(self.width):
                r, g, b = img.getpixel((x, y))
                rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
                pixel_data.extend([(rgb565 >> 8) & 0xFF, rgb565 & 0xFF])
        return pixel_data

    def show_text(self, main_text: str, sub_text: str = "", bg_color=(0,0,40), text_color=(255,255,255)):
        try:
            pixel_data = self._make_text_image(main_text, sub_text, bg_color, text_color)
            self.board.draw_image(0, 0, self.width, self.height, pixel_data)
            if self.debug:
                print(f"Displayed: {main_text}")
        except Exception as e:
            print(f"show_text failed: {e}")

    def show_image(self, filepath: str):
        try:
            pixel_data = self._load_jpg_as_rgb565(filepath)
            self.board.draw_image(0, 0, self.width, self.height, pixel_data)
            if self.debug:
                print(f"Displayed image: {os.path.basename(filepath)}")
        except Exception as e:
            print(f"show_image failed: {e}")
    
    def _preload_common_screens(self):
        """Generate and cache common screens at startup"""
        # Idle / Ready screen
        self._cache["idle"] = self._make_text_image(
            text="READY",
            sub_text="Hold button to talk",
            bg_color=(0, 0, 40),
            text_color=(100, 180, 255)
        )

        # Listening / Recording screen
        self._cache["listening"] = self._make_text_image(
            text="● LISTENING",
            sub_text="Release to send",
            bg_color=(60, 0, 0),
            text_color=(255, 80, 80)
        )

        # Processing / Thinking screen
        self._cache["processing"] = self._make_text_image(
            text="🤔...",
            sub_text="Juliet thinking...",
            bg_color=(20, 20, 40),
            text_color=(180, 180, 255)
        )

        if self.debug:
            print(f"ScreenHelper: Preloaded {len(self._cache)} screens")

    def show_idle(self):
        """Quick show ready screen (cached)"""
        self._show_cached("idle")

    def show_listening(self):
        """Quick show listening screen (cached)"""
        self._show_cached("listening")

    def show_processing(self):
        """Quick show thinking/processing screen (cached)"""
        self._show_cached("processing")

    def _show_cached(self, key: str):
        if key in self._cache:
            try:
                self.board.draw_image(0, 0, self.width, self.height, self._cache[key])
                if self.debug:
                    print(f"Displayed cached screen: {key}")
            except Exception as e:
                print(f"Failed to show cached screen '{key}': {e}")
        else:
            print(f"Cached screen '{key}' not found")


class AudioHelper:
    def __init__(self, debug: bool = False, sample_rate: int = 24000, channels: int = 1):
        """
        Manages audio input/output for the Whisplay HAT + xAI realtime voice.
        
        Args:
            debug: If True, saves last utterance to /tmp/last_utterance.wav for inspection
            sample_rate: Target rate for xAI (24000 Hz mono)
            channels: 1 = mono (required for xAI)
        """
        self.debug = debug
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = 1024  # ~42 ms at 24kHz

        self.card_index = self._find_card()
        self._setup_mixer()

        self.p = pyaudio.PyAudio()
        self.audio_queue = queue.Queue(maxsize=200)  # buffer ~8 seconds max

        self.input_stream: Optional[pyaudio.Stream] = None
        self.output_stream: Optional[pyaudio.Stream] = None

        self._listening = False
        self._capture_thread: Optional[threading.Thread] = None

        self.temp_file = "/test_audio_file.wav"

    def _find_card(self) -> int:
        """Auto-detect WM8960 card number"""
        try:
            with open("/proc/asound/cards") as f:
                for line in f:
                    if "wm8960" in line.lower():
                        return int(line.strip().split()[0])
        except Exception:
            pass
        return 1  # fallback

    def _setup_mixer(self):
        """Apply the same mixer settings as the original demo"""
        card = str(self.card_index)
        cmds = [
            # Playback
            ['amixer', '-c', card, 'sset', 'Left Output Mixer PCM', 'on'],
            ['amixer', '-c', card, 'sset', 'Right Output Mixer PCM', 'on'],
            ['amixer', '-c', card, 'sset', 'Speaker', '121'],
            ['amixer', '-c', card, 'sset', 'Playback', '230'],
            # Capture
            ['amixer', '-c', card, 'sset', 'Left Input Mixer Boost', 'on'],
            ['amixer', '-c', card, 'sset', 'Right Input Mixer Boost', 'on'],
            ['amixer', '-c', card, 'sset', 'Capture', '45'],
            ['amixer', '-c', card, 'sset', 'ADC PCM', '195'],
            ['amixer', '-c', card, 'sset', 'Left Input Boost Mixer LINPUT1', '2'],
            ['amixer', '-c', card, 'sset', 'Right Input Boost Mixer RINPUT1', '2'],
        ]
        for cmd in cmds:
            try:
                subprocess.run(cmd, capture_output=True, timeout=3)
            except Exception:
                pass
        if self.debug:
            print(f"AudioHelper: WM8960 mixer configured (card {card})")

    def start_input_stream(self):
        """Start capturing microphone audio and feeding the queue (called on button press)"""
        if self._listening:
            return  # already running

        try:
            self.input_stream = self.p.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )
            self._listening = True
            self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self._capture_thread.start()

            if self.debug:
                print("AudioHelper: Input stream started")
        except Exception as e:
            print(f"AudioHelper: Failed to start input stream: {e}")

    def stop_input_stream(self):
        """Stop capturing (called on button release)"""
        self._listening = False
        if self._capture_thread and self._capture_thread.is_alive():
            self._capture_thread.join(timeout=1.0)

        if self.input_stream:
            try:
                self.input_stream.stop_stream()
                self.input_stream.close()
                self.input_stream = None
            except Exception as e:
                print(f"AudioHelper: Error closing input stream: {e}")

        if self.debug:
            print("AudioHelper: Input stream stopped")

    def _capture_loop(self):
        """Background thread: read mic chunks → queue (and optional debug save)"""
        frames = []  # only used if debug=True
        try:
            while self._listening:
                data = self.input_stream.read(self.chunk_size, exception_on_overflow=False)
                self.audio_queue.put_nowait(data)

                if self.debug:
                    frames.append(data)

            # After loop ends → optional debug save
            if self.debug and frames:
                self._save_debug_wav(frames)
        except Exception as e:
            print(f"AudioHelper: Capture loop error: {e}")
        finally:
            if self.debug:
                print("AudioHelper: Capture loop ended")

    def _save_debug_wav(self, frames):
        """Save last utterance to temp file for debugging"""
        try:
            wf = wave.open(self.temp_file, 'wb')
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.p.get_sample_size(pyaudio.paInt16))
            wf.setframerate(self.sample_rate)
            wf.writeframes(b''.join(frames))
            wf.close()
            if self.debug:
                print(f"AudioHelper: Debug WAV saved: {self.temp_file} ({len(frames) * self.chunk_size / self.sample_rate:.1f}s)")
        except Exception as e:
            print(f"AudioHelper: Failed to save debug WAV: {e}")

    def get_next_chunk(self) -> Optional[bytes]:
        """Called by the async sender task — non-blocking get from queue"""
        try:
            return self.audio_queue.get_nowait()
        except queue.Empty:
            return None

    def play_audio_chunk(self, audio_bytes: bytes):
        """Play incoming audio from xAI response.output_audio.delta"""
        if not self.output_stream:
            try:
                self.output_stream = self.p.open(
                    format=pyaudio.paInt16,
                    channels=self.channels,
                    rate=self.sample_rate,
                    output=True,
                    frames_per_buffer=self.chunk_size
                )
                if self.debug:
                    print("AudioHelper: Output stream opened")
            except Exception as e:
                print(f"AudioHelper: Failed to open output stream: {e}")
                return

        try:
            self.output_stream.write(audio_bytes)
        except Exception as e:
            print(f"AudioHelper: Playback error: {e}")

    def cleanup(self):
        """Call on shutdown"""
        self.stop_input_stream()
        if self.output_stream:
            try:
                self.output_stream.stop_stream()
                self.output_stream.close()
            except:
                pass
        self.p.terminate()
        if self.debug and os.path.exists(self.temp_file):
            try:
                os.remove(self.temp_file)
                print("AudioHelper: Temp debug file removed")
            except:
                pass