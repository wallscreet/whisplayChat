import asyncio
from openai import AsyncOpenAI
from piper import PiperVoice
from pathlib import Path
import os
from dotenv import load_dotenv
import pyaudio

load_dotenv()


class GrokTTSClient:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=os.getenv("XAI_API_KEY"),
            base_url="https://api.x.ai/v1",
        )
        self.voice = PiperVoice.load(Path("models/en_US-lessac-medium.onnx"))

        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.voice.config.sample_rate,
            output=True,
            output_device_index=1
        )
        self.buffer = ""

    # async def stream_response_to_speech(self, messages, model="grok-4-1-fast-non-reasoning"):
    #     stream = await self.client.chat.completions.create(
    #         model=model,
    #         messages=messages,
    #         stream=True,
    #         temperature=0.7,
    #     )

    #     async for chunk in stream:  # ← async for
    #         delta = chunk.choices[0].delta.content or ""
    #         self.buffer += delta
    #         while '.' in self.buffer or '!' in self.buffer or '?' in self.buffer:
    #             end_idx = min(
    #                 self.buffer.find('.') if '.' in self.buffer else len(self.buffer),
    #                 self.buffer.find('!') if '!' in self.buffer else len(self.buffer),
    #                 self.buffer.find('?') if '?' in self.buffer else len(self.buffer)
    #             ) + 1
    #             sentence = self.buffer[:end_idx].strip()
    #             self.buffer = self.buffer[end_idx:].lstrip()
    #             if sentence:
    #                 for audio_chunk in self.voice.synthesize(sentence):
    #                     self.stream.write(audio_chunk.audio_int16_bytes)
    async def stream_response_to_speech(self, messages, model="grok-4-1-fast-non-reasoning"):
        full_response = ""
        self.buffer = ""

        stream = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
            temperature=0.7,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            full_response += delta
            self.buffer += delta

            while '.' in self.buffer or '!' in self.buffer or '?' in self.buffer:
                end_idx = min(
                    self.buffer.find('.') if '.' in self.buffer else len(self.buffer),
                    self.buffer.find('!') if '!' in self.buffer else len(self.buffer),
                    self.buffer.find('?') if '?' in self.buffer else len(self.buffer)
                ) + 1
                sentence = self.buffer[:end_idx].strip()
                self.buffer = self.buffer[end_idx:].lstrip()
                if sentence:
                    for audio_chunk in self.voice.synthesize(sentence):
                        self.stream.write(audio_chunk.audio_int16_bytes)

        # Send any remaining buffer as final sentence
        if self.buffer.strip():
            for audio_chunk in self.voice.synthesize(self.buffer.strip()):
                self.stream.write(audio_chunk.audio_int16_bytes)

        return full_response

    def cleanup(self):
        self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()

# Usage
# async def main():
#     client = GrokTTSClient()
#     print("Grok Client loaded...")
#     prompt = input("What would you like to ask?")
#     messages = [
#         {"role": "system", "content": "You are Grok, an ai personal assistant. Please be honest and keep your responses concise."},
#         {"role": "user", "content": prompt}
#     ]
#     print("Sending Request...")
#     try:
#         await client.stream_response_to_speech(messages)
#     finally:
#         client.cleanup()
async def main():
    client = GrokTTSClient()
    print("Grok Client loaded...")

    messages = [
        {"role": "system", "content": "You are Grok, an ai personal assistant. Please always be honest and keep your responses concise."}
    ]

    while True:
        prompt = input("\nYou: ").strip()
        if prompt.lower() in ("exit", "quit"):
            break
        if not prompt:
            continue

        messages.append({"role": "user", "content": prompt})
        print("Grok thinking...")

        full_text = await client.stream_response_to_speech(messages)
        print(f"Grok: {full_text}")

        messages.append({"role": "assistant", "content": full_text})

    client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())