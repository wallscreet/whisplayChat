import pyaudio
import wave
import time

p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt16, channels=1, rate=24000, input=True, frames_per_buffer=1024)

print("Recording 5 seconds...")
frames = []
for _ in range(0, int(24000 / 1024 * 5)):
    data = stream.read(1024)
    frames.append(data)

stream.stop_stream()
stream.close()
p.terminate()

print("Saving test_recording.wav...")
wf = wave.open("test_recording.wav", 'wb')
wf.setnchannels(1)
wf.setsampwidth(2)
wf.setframerate(24000)
wf.writeframes(b''.join(frames))
wf.close()

print("Done. Play with: aplay test_recording.wav")