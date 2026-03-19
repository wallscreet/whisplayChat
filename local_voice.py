import io
import queue
import wave
from clients import XAIClient
import requests
import time
import os
from dotenv import load_dotenv
from helpers import ScreenHelper, AudioHelper
import traceback


load_dotenv()

SERVER_URL = "http://192.168.86.35:8000"

class VoiceAgent:
    def __init__(self, debug: bool = True):
        self.debug = debug
        self.screen = ScreenHelper(debug=debug)
        self.audio = AudioHelper(debug=debug)

        self.screen.board.on_button_press(self.on_button_press)
        self.screen.board.on_button_release(self.on_button_release)
        self.client = XAIClient()

        self.screen.show_idle()
        
        self.messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant"
            }
        ]

    def on_button_press(self):
        self.screen.show_listening()
        self.audio.start_input_stream()
        if self.debug: print("PRESS → listening")

    def on_button_release(self):
        self.screen.show_processing()
        self.audio.stop_input_stream()
        
        # Clear queue (not needed anymore, but harmless)
        while not self.audio.audio_queue.empty():
            try:
                self.audio.audio_queue.get_nowait()
            except queue.Empty:
                break

        if self.debug:
            print("RELEASE → sending request")

        # Get last recording (add this method to AudioHelper)
        wav_bytes = self.audio.get_last_recording_bytes()

        # 1. STT
        try:
            files = {"file": ("input.wav", wav_bytes, "audio/wav")}
            r = requests.post(f"{SERVER_URL}/stt", files=files, timeout=15)
            r.raise_for_status()
            user_text = r.json()["text"]
            if self.debug: print(f"You: {user_text}")
        except Exception as e:
            print(f"STT error: {e}")
            self.screen.show_idle()
            return

        # 2. LLM
        try:
            model = "grok-4-1-fast-non-reasoning"
            self.messages.append({"role": "user", "content": user_text})
            response = self.client.get_response(model=model, messages=self.messages)
            if self.debug: print(f"Grok: {response}")
        except Exception as e:
            print(f"LLM error: {e}")
            self.screen.show_idle()
            return

        # 3. TTS
        # try:
        #     r = requests.post(f"{SERVER_URL}/tts", json={"text": response}, timeout=30, stream=True)
        #     r.raise_for_status()
        #     for chunk in r.iter_content(chunk_size=4096):
        #         if chunk:
        #             self.audio.play_audio_chunk(chunk)
        # except Exception as e:
        #     print(f"TTS error: {e}")
        try:
            r = requests.post(
                f"{SERVER_URL}/tts",
                json={"text": response},
                timeout=30
            )
            r.raise_for_status()

            wav_bytes = r.content

            # Decode WAV
            wf = wave.open(io.BytesIO(wav_bytes), 'rb')

            channels = wf.getnchannels()
            rate = wf.getframerate()
            width = wf.getsampwidth()

            print(f"TTS format → channels={channels}, rate={rate}, width={width}")

            # Ensure format matches output stream
            # assert wf.getnchannels() == 1
            # assert wf.getframerate() == 22050
            # assert wf.getsampwidth() == 2  # 16-bit

            # Stream decoded PCM
            while True:
                frames = wf.readframes(self.audio.chunk_size)
                if not frames:
                    break
                self.audio.play_audio_chunk(frames)

        except Exception as e:
            print("TTS error:")
            print(repr(e))  # shows the actual exception type
            traceback.print_exc()  # full stack trace

        self.screen.show_idle()
        if self.debug: print("Done")

    def run(self):
        print("VoiceAgent running (non-realtime mode)")
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("Shutdown")
        finally:
            self.audio.cleanup()
            self.screen.board.set_rgb(0, 0, 0)
            self.screen.board.set_backlight(0)


if __name__ == "__main__":
    agent = VoiceAgent(debug=True)
    agent.run()