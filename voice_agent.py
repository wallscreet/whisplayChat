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
import time
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

        # Async state (initialized later)
        self.ws = None
        self.loop = None

        # Timing
        self.last_activity = time.monotonic()
        self.INACTIVITY_TIMEOUT = 20.0

        # Button wiring
        self.screen.board.on_button_press(self.on_button_press)
        self.screen.board.on_button_release(self.on_button_release)

        self.screen.show_idle()

    # ---------------------------
    # Thread-safe helpers
    # ---------------------------

    def _update_activity(self):
        """Safely update last_activity from any thread."""
        if self.loop:
            self.loop.call_soon_threadsafe(
                lambda: setattr(self, "last_activity", time.monotonic())
            )
        else:
            self.last_activity = time.monotonic()

    def _send_ws_event(self, payload: dict):
        """Send a websocket message safely from any thread."""
        if self.ws and self.loop:
            asyncio.run_coroutine_threadsafe(
                self.ws.send(json.dumps(payload)),
                self.loop
            )

    # ---------------------------
    # Button callbacks (THREAD)
    # ---------------------------

    def on_button_press(self):
        self.screen.show_listening()
        self.audio.start_input_stream()
        self._update_activity()

        if self.debug:
            print("PRESS → listening")

    def on_button_release(self):
        self.screen.show_processing()
        self.audio.stop_input_stream()

        # Clear queue
        while not self.audio.audio_queue.empty():
            try:
                self.audio.audio_queue.get_nowait()
            except queue.Empty:
                break

        self._update_activity()

        # Commit audio buffer
        self._send_ws_event({"type": "input_audio_buffer.commit"})

        if self.debug:
            print("RELEASE → committed")

    # ---------------------------
    # Async runtime
    # ---------------------------

    async def connect_and_run(self):
        url = "wss://api.x.ai/v1/realtime"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        async with websockets.connect(url, additional_headers=headers) as self.ws:
            self.loop = asyncio.get_running_loop()

            await self.ws.send(json.dumps({
                "type": "session.update",
                "session": {
                    "instructions": "You are Grok on a portable Whisplay HAT. Be witty, concise, helpful.",
                    "voice": "eve",
                    "turn_detection": {"type": "server_vad"},
                }
            }))

            if self.debug:
                print("Connected")

            sender_task = asyncio.create_task(self._audio_sender())

            try:
                while True:
                    now = time.monotonic()

                    # Inactivity timeout
                    if now - self.last_activity > self.INACTIVITY_TIMEOUT:
                        if self.debug:
                            print("Inactivity timeout → closing WS")
                        await self.ws.close()
                        break

                    # Non-blocking recv with timeout
                    try:
                        message = await asyncio.wait_for(
                            self.ws.recv(),
                            timeout=1.0
                        )
                    except asyncio.TimeoutError:
                        continue

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
                        if self.debug:
                            print("Done")

                    # Update activity on any response
                    self.last_activity = time.monotonic()

            except Exception as e:
                print(f"WS error: {e}")

            finally:
                sender_task.cancel()
                try:
                    await sender_task
                except asyncio.CancelledError:
                    pass

    async def _audio_sender(self):
        """Continuously sends audio chunks to the websocket."""
        while True:
            try:
                chunk = await asyncio.get_running_loop().run_in_executor(
                    None,
                    self.audio.get_next_chunk
                )

                if chunk is None:
                    await asyncio.sleep(0.01)
                    continue

                b64 = base64.b64encode(chunk).decode("utf-8")

                await self.ws.send(json.dumps({
                    "type": "input_audio_buffer.append",
                    "audio": b64
                }))

                if self.debug:
                    print("Chunk sent")

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Sender error: {e}")
                break

    # ---------------------------
    # Entrypoint
    # ---------------------------

    def run(self):
        try:
            asyncio.run(self.connect_and_run())
        except KeyboardInterrupt:
            if self.debug:
                print("Shutdown requested")

            if self.ws:
                try:
                    asyncio.run(self.ws.close())
                except Exception:
                    pass

        finally:
            self.audio.cleanup()
            self.screen.board.set_rgb(0, 0, 0)
            self.screen.board.set_backlight(0)


if __name__ == "__main__":
    agent = VoiceAgent(debug=True)
    agent.run()