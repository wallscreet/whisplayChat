import argparse
from time import sleep
from helpers import ScreenHelper


screen_helper = ScreenHelper()

global_image_data = None
image_filepath = None

parser = argparse.ArgumentParser()
parser.add_argument("--image", default="example/data/DiscoRoverLogo.png", help="Path to the image file (default: example/data/test.png)")

args = parser.parse_args()

image_filepath = args.image

def on_button_pressed():
    print("Button Pressed!")
    

try:
    screen_helper.show_image(filepath=image_filepath)
    sleep(10)
    screen_helper.show_idle()
    sleep(5)
    screen_helper.show_listening()
    sleep(5)
    screen_helper.show_processing()
    sleep(5)
    screen_helper.show_image(filepath=image_filepath)
except Exception as e:
    print(f"Failed to load image from {image_filepath}: {e}")

try:
    print("Loaded and waiting.. Press Ctrl+c to exit")
    while True:
        sleep(0.1)

except KeyboardInterrupt:
    print("Exiting test...")

finally:
    screen_helper.board.cleanup()