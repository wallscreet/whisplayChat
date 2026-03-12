#!/usr/bin/env python3
import time
from helpers import AudioHelper  # adjust import path if needed

def main():
    print("Starting AudioHelper test...")
    audio = AudioHelper(debug=True)  # debug=True → will save WAV after release

    print("\nHold the button for ~5-10 seconds, then release.")
    print("Speak something clearly into the mic.")
    print("After release, check if /tmp/last_utterance.wav was created.\n")

    # Simulate button press (in real code this comes from board callback)
    print("[Simulated press]")
    audio.start_input_stream()

    # Wait ~10 seconds (in real use, this is until release)
    time.sleep(10)

    # Simulate release
    print("[Simulated release]")
    audio.stop_input_stream()

    print("\nTest complete.")
    print("Check:")
    print("1. Did you hear any errors?")
    print("2. Is /tmp/last_utterance.wav present?")
    print("   → Play it: aplay /tmp/last_utterance.wav")
    print("   → Duration should be ~10 seconds")
    print("3. File size roughly: 10s × 24000 samples/s × 2 bytes = ~480 KB")

    # Cleanup
    audio.cleanup()

if __name__ == "__main__":
    main()