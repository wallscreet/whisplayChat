import asyncio
from openai import AsyncOpenAI
from piper import PiperVoice
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

class GrokTTSClient:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=os.getenv("XAI_API_KEY"),
            base_url="https://api.x.ai/v1",
        )
        self.voice = PiperVoice.load(Path("models/en_US-lessac-medium.onnx"))  # adjust model path

    async def stream_response_to_speech(self, messages, model="grok-4-1-fast-non-reasoning"):
        stream = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
            temperature=0.7,
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                # Stream text to Piper (synthesizes & plays immediately)
                self.voice.synthesize(delta)

# Usage example
async def main():
    client = GrokTTSClient()
    messages = [
        {"role": "system", "content": "You are Grok. Be concise."},
        {"role": "user", "content": "Tell me a short joke."}
    ]
    await client.stream_response_to_speech(messages)

if __name__ == "__main__":
    asyncio.run(main())