import io
import queue
import wave
from clients import XAIClient
import requests
import time
import os
from dotenv import load_dotenv
from helpers import ScreenHelper, AudioHelper
from utils import clean_text_for_tts

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
        
        # self.messages = [
        #     {
        #         "role": "system",
        #         "content": "You are a helpful assistant running on a mobile device. Please do not include any emojis in your responses."
        #     }
        # ]

    def on_button_press(self):
        self.screen.show_listening()
        self.audio.start_input_stream()
        if self.debug: print("PRESS → listening")

    def on_button_release(self):
        self.screen.show_processing()
        self.audio.stop_input_stream()
        
        # Clear queue
        while not self.audio.audio_queue.empty():
            try:
                self.audio.audio_queue.get_nowait()
            except queue.Empty:
                break

        if self.debug:
            print("RELEASE → sending request")

        # Get last recording
        wav_bytes = self.audio.get_last_recording_bytes()

        # =====================================================================================================
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

        # =====================================================================================================
        # 2. LLM
        try:
            model = "grok-4-1-fast-non-reasoning"
            
            messages = [
                {
                    "role": "system",
                    "content": "You are a helpful assistant named Juliet running on a portable device. Please keep your responses short and concise and do not use any emojis."
                },
                {
                    "role": "user",
                    "content": user_text
                }
            ]
            
            response = self.client.get_response(model=model, messages=messages)
            response_cleaned = clean_text_for_tts(text=response)
            
            if self.debug: print(f"Grok: {response}")
        
        except Exception as e:
            print(f"LLM error: {e}")
            self.screen.show_idle()
            return

        # =====================================================================================================
        # 3. TTS
        try:
            r = requests.post(
                f"{SERVER_URL}/tts",
                json={"text": response_cleaned},
                stream=True,
                timeout=45
            )
            r.raise_for_status()

            self.screen.show_text(
                "SPEAKING",
                "Juliet answering…",
                bg_color=(20,40,20),
                text_color=(100,255,100)
            )

            chunk_count = 0
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    chunk_count += 1
                    self.audio.play_piper_stream_chunk(chunk)
                    if self.debug and chunk_count % 5 == 0:
                        print(f"[Audio] Played {chunk_count} Piper chunks")

            # Small drain to avoid cutoff at end
            time.sleep(0.1)

        except Exception as e:
            print("TTS streaming error:")
            import traceback
            traceback.print_exc()
            
        # =====================================================================================================
        
        finally:
            self.screen.show_idle()
            if self.debug: print("Done")

    def run(self):
        print("VoiceAgent running...")
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