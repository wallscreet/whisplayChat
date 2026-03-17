# #!/usr/bin/env python3

# import asyncio
# import queue
# import websockets
# import json
# import base64
# import os
# from dotenv import load_dotenv

# from helpers import ScreenHelper, AudioHelper

# load_dotenv()

# class VoiceAgent:
#     """
#     Full VoiceAgent — integrates ScreenHelper + AudioHelper + xAI Realtime
#     """
#     def __init__(self, debug: bool = True):
#         self.debug = debug
#         self.screen = ScreenHelper(debug=debug)
#         self.audio = AudioHelper(debug=debug)

#         self.api_key = os.getenv("XAI_API_KEY")
#         if not self.api_key:
#             raise ValueError("XAI_API_KEY not found in .env — check your file!")

#         # Wire up button callbacks  
#         self.screen.board.on_button_press(self.on_button_press)
#         self.screen.board.on_button_release(self.on_button_release)

#         self.ws = None
#         self.screen.show_idle()

#     def on_button_press(self):
#         """Called when button is pressed"""
#         self.screen.show_listening()
#         self.audio.start_input_stream()
#         if self.debug:
#             print("Button PRESS → listening started")

#     def on_button_release(self):
#         """Called when button is released"""
#         self.screen.show_processing()
#         self.audio.stop_input_stream()
        
#         if self.debug:
#             print("Button RELEASE → input stopped, waiting for response")

#     async def connect_and_run(self):
#         url = "wss://api.x.ai/v1/realtime"
#         headers = {"Authorization": f"Bearer {self.api_key}"}

#         async with websockets.connect(url, additional_headers=headers) as self.ws:
#             # Initial session setup
#             await self.ws.send(json.dumps({
#                 "type": "session.update",
#                 "session": {
#                     "instructions": (
#                         "You are Grok running on a portable Whisplay HAT. "
#                         "Be witty, concise, and helpful. Keep spoken responses natural."
#                     ),
#                     "voice": "eve",  # also available: ara, leo, rex
#                     "turn_detection": {"type": "server_vad"},
#                 }
#             }))

#             if self.debug:
#                 print("✅ Connected to xAI realtime API")

#             # Start the async queue sender
#             sender_task = asyncio.create_task(self._audio_sender())

#             try:
#                 while True:
#                     message = await self.ws.recv()
#                     data = json.loads(message)

#                     if data.get("type") == "response.output_audio.delta":
#                         b64 = data.get("delta")
#                         if b64:
#                             audio_bytes = base64.b64decode(b64)
#                             self.audio.play_audio_chunk(audio_bytes)
#                             self.screen.show_text("Grok:", "speaking...")

#                     elif data.get("type") == "response.output_audio_transcript.delta":
#                         # You can accumulate and show streaming text here later
#                         if self.debug:
#                             print(f"Text delta: {data.get('delta', '')}")

#                     elif data.get("type") in ["response.done", "response.audio.done"]:
#                         self.screen.show_idle()
#                         if self.debug:
#                             print("Response complete → back to idle")

#             except Exception as e:
#                 print(f"WebSocket error: {e}")
#             finally:
#                 sender_task.cancel()
#                 try:
#                     await sender_task
#                 except asyncio.CancelledError:
#                     pass

#     async def _audio_sender(self):
#         """Drains queue and sends chunks to xAI"""
#         while True:
#             try:
#                 chunk = await asyncio.get_running_loop().run_in_executor(
#                     None, self.audio.get_next_chunk
#                 )
#                 if chunk is None:
#                     await asyncio.sleep(0.01)
#                     continue

#                 b64 = base64.b64encode(chunk).decode('utf-8')
#                 await self.ws.send(json.dumps({
#                     "type": "input_audio_buffer.append",
#                     "audio": b64
#                 }))
#                 if self.debug:
#                     print("Sent audio chunk → xAI")
#             except Exception as e:
#                 print(f"Sender error: {e}")
#                 break

#     def run(self):
#         """Entry point"""
#         try:
#             asyncio.run(self.connect_and_run())
#         except KeyboardInterrupt:
#             print("\n👋 Shutting down...")
#         finally:
#             self.audio.cleanup()
#             self.screen.board.set_rgb(0, 0, 0)
#             self.screen.board.set_backlight(0)


# if __name__ == "__main__":
#     agent = VoiceAgent(debug=True)
#     agent.run()

#!/usr/bin/env python3

import asyncio
import queue
import websockets
import json
import base64
import os
from dotenv import load_dotenv

from helpers import ScreenHelper, AudioHelper

load_dotenv()

class VoiceAgent:
    def __init__(self, debug: bool = True):
        self.debug = debug
        self.screen = ScreenHelper(debug=debug)
        self.audio = AudioHelper(debug=debug)

        self.api_key = os.getenv("XAI_API_KEY")
        if not self.api_key:
            raise ValueError("XAI_API_KEY missing")

        self.screen.board.on_button_press(self.on_button_press)
        self.screen.board.on_button_release(self.on_button_release)

        self.ws = None
        self.screen.show_idle()

    def on_button_press(self):
        self.screen.show_listening()
        self.audio.start_input_stream()
        if self.debug: print("PRESS → listening")

    def on_button_release(self):
        self.screen.show_processing()
        self.audio.stop_input_stream()
        # Clear old chunks
        while not self.audio.audio_queue.empty():
            try:
                self.audio.audio_queue.get_nowait()
            except queue.Empty:
                break

        if self.ws and self.ws.open:
            asyncio.run_coroutine_threadsafe(
                self.ws.send(json.dumps({"type": "input_audio_buffer.commit"})),
                asyncio.get_running_loop()
            )

        if self.debug: print("RELEASE → committed")

    async def connect_and_run(self):
        url = "wss://api.x.ai/v1/realtime"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        async with websockets.connect(url, additional_headers=headers) as self.ws:
            await self.ws.send(json.dumps({
                "type": "session.update",
                "session": {
                    "instructions": "You are Grok on a portable Whisplay HAT. Be witty, concise, helpful.",
                    "voice": "eve",
                    "turn_detection": {"type": "server_vad"},
                }
            }))

            if self.debug: print("Connected")

            sender_task = asyncio.create_task(self._audio_sender())

            try:
                while True:
                    message = await self.ws.recv()
                    data = json.loads(message)

                    if data.get("type") == "response.output_audio.delta":
                        b64 = data.get("delta")
                        if b64:
                            audio_bytes = base64.b64decode(b64)
                            self.audio.play_audio_chunk(audio_bytes)

                    elif data.get("type") == "response.output_audio_transcript.delta":
                        if self.debug:
                            print(f"Text: {data.get('delta', '')}")

                    elif data.get("type") in ["response.done", "response.audio.done"]:
                        self.screen.show_idle()
                        if self.debug: print("Done")

            except Exception as e:
                print(f"WS error: {e}")
            finally:
                sender_task.cancel()

    async def _audio_sender(self):
        while True:
            try:
                chunk = await asyncio.get_running_loop().run_in_executor(
                    None, self.audio.get_next_chunk
                )
                if chunk is None:
                    await asyncio.sleep(0.01)
                    continue

                b64 = base64.b64encode(chunk).decode('utf-8')
                await self.ws.send(json.dumps({
                    "type": "input_audio_buffer.append",
                    "audio": b64
                }))
                if self.debug: print("Chunk sent")
            except Exception as e:
                print(f"Sender error: {e}")
                break

    def run(self):
        try:
            asyncio.run(self.connect_and_run())
        except KeyboardInterrupt:
            print("Shutdown")
        finally:
            self.audio.cleanup()
            self.screen.board.set_rgb(0, 0, 0)
            self.screen.board.set_backlight(0)


if __name__ == "__main__":
    agent = VoiceAgent(debug=True)
    agent.run()