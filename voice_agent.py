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

# class VoiceAgent:
#     def __init__(self, debug: bool = True):
#         self.debug = debug
#         self.screen = ScreenHelper(debug=debug)
#         self.audio = AudioHelper(debug=debug)

#         self.api_key = os.getenv("XAI_API_KEY")
#         if not self.api_key:
#             raise ValueError("XAI_API_KEY missing")

#         self.screen.board.on_button_press(self.on_button_press)
#         self.screen.board.on_button_release(self.on_button_release)

#         self.ws = None
#         # Last activity and timeout vars add
#         self.last_activity = asyncio.get_event_loop().time()
#         self.INACTIVITY_TIMEOUT = 20.0  # seconds
        
#         self.screen.show_idle()

#     def on_button_press(self):
#         self.screen.show_listening()
#         self.audio.start_input_stream()
#         self.last_activity = asyncio.get_event_loop().time()
#         if self.debug: print("PRESS → listening")

#     def on_button_release(self):
#         self.screen.show_processing()
#         self.audio.stop_input_stream()
        
#         # Clear queue
#         while not self.audio.audio_queue.empty():
#             try:
#                 self.audio.audio_queue.get_nowait()
#             except queue.Empty:
#                 break
        
#         self.last_activity = asyncio.get_event_loop().time()

#         if self.ws is not None:
#             try:
#                 asyncio.run_coroutine_threadsafe(
#                     self.ws.send(json.dumps({"type": "input_audio_buffer.commit"})),
#                     asyncio.get_running_loop()
#                 )
#             except Exception as e:
#                 if self.debug:
#                     print(f"Commit failed (normal if ws closed): {e}")

#         if self.debug:
#             print("RELEASE → committed")

#     async def connect_and_run(self):
#         url = "wss://api.x.ai/v1/realtime"
#         headers = {"Authorization": f"Bearer {self.api_key}"}

#         async with websockets.connect(url, additional_headers=headers) as self.ws:
#             await self.ws.send(json.dumps({
#                 "type": "session.update",
#                 "session": {
#                     "instructions": "You are Grok on a portable Whisplay HAT. Be witty, concise, helpful.",
#                     "voice": "eve",
#                     "turn_detection": {"type": "server_vad"},
#                 }
#             }))

#             if self.debug: print("Connected")

#             sender_task = asyncio.create_task(self._audio_sender())

#             try:
#                 while True:
#                     # Timeout add
#                     now = asyncio.get_event_loop().time()
#                     if now - self.last_activity > self.INACTIVITY_TIMEOUT:
#                         if self.debug: print("Inactivity timeout → closing WS")
#                         await self.ws.close()
#                         break
#                     # End Timeout add
                    
#                     message = await self.ws.recv()
#                     data = json.loads(message)

#                     if data.get("type") == "response.output_audio.delta":
#                         b64 = data.get("delta")
#                         if b64:
#                             audio_bytes = base64.b64decode(b64)
#                             self.audio.play_audio_chunk(audio_bytes)

#                     elif data.get("type") == "response.output_audio_transcript.delta":
#                         if self.debug:
#                             print(f"Text: {data.get('delta', '')}")

#                     elif data.get("type") in ["response.done", "response.audio.done"]:
#                         self.screen.show_idle()
#                         if self.debug: print("Done")
                    
#                     # Update last activity on any meaningful event
#                     self.last_activity = asyncio.get_event_loop().time()

#             except Exception as e:
#                 print(f"WS error: {e}")
#             finally:
#                 sender_task.cancel()

#     async def _audio_sender(self):
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
#                 if self.debug: print("Chunk sent")
#             except Exception as e:
#                 print(f"Sender error: {e}")
#                 break

#     def run(self):
#         try:
#             asyncio.run(self.connect_and_run())
#         except KeyboardInterrupt:
#             self.ws.close()
#             print("Shutdown")
#         finally:
#             self.audio.cleanup()
#             self.screen.board.set_rgb(0, 0, 0)
#             self.screen.board.set_backlight(0)

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
        self.last_activity = 0.0
        self.INACTIVITY_TIMEOUT = 20.0

        self.screen.show_idle()

    def on_button_press(self):
        self.screen.show_listening()
        self.audio.start_input_stream()
        # Update activity in main loop later
        if self.debug: print("PRESS → listening")

    def on_button_release(self):
        self.screen.show_processing()
        self.audio.stop_input_stream()
        
        while not self.audio.audio_queue.empty():
            try:
                self.audio.audio_queue.get_nowait()
            except queue.Empty:
                break

        # Commit moved to async loop
        if self.debug: print("RELEASE → queued commit")

    async def connect_and_run(self):
        url = "wss://api.x.ai/v1/realtime"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        while True:
            try:
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
                    self.last_activity = asyncio.get_running_loop().time()

                    try:
                        while True:
                            now = asyncio.get_running_loop().time()
                            if now - self.last_activity > self.INACTIVITY_TIMEOUT:
                                if self.debug: print("Timeout → closing WS")
                                await self.ws.close()
                                break

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

                            # Update activity
                            self.last_activity = asyncio.get_running_loop().time()

                    except websockets.ConnectionClosed:
                        if self.debug: print("WS closed normally")
                    finally:
                        sender_task.cancel()

            except Exception as e:
                print(f"Connection error: {e}")
                await asyncio.sleep(2)

            await asyncio.sleep(0.1)  # wait for next press

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
                if self.ws and self.ws.open:
                    await self.ws.send(json.dumps({
                        "type": "input_audio_buffer.append",
                        "audio": b64
                    }))
                    if self.debug: print("Chunk sent")
            except Exception as e:
                print(f"Sender error: {e}")
                break

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.connect_and_run())
        except KeyboardInterrupt:
            print("Shutdown (KeyboardInterrupt)")
            if self.ws:
                loop.run_until_complete(self.ws.close())
        finally:
            self.audio.cleanup()
            self.screen.board.set_rgb(0, 0, 0)
            self.screen.board.set_backlight(0)
            loop.close()


if __name__ == "__main__":
    agent = VoiceAgent(debug=True)
    agent.run()