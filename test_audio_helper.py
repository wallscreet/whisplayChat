#!/usr/bin/env python3
import time
from helpers import AudioHelper

def main():
    audio = AudioHelper(debug=True)
    print("[Simulated press]")
    audio.start_input_stream()
    time.sleep(10)
    print("[Simulated release]")
    audio.stop_input_stream()
    #audio.cleanup()

if __name__ == "__main__":
    main()