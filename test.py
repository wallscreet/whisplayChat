import os
import argparse
from Driver.WhisPlay import WhisPlayBoard
from utils import load_jpg_as_rgb565
from time import sleep


board = WhisPlayBoard()
board.set_backlight(50)

global_image_data = None
image_filepath = None

parser = argparse.ArgumentParser()
parser.add_argument("--image", default="example/data/test.png", help="Path to the image file (default: example/data/test.png)")

args = parser.parse_args()

image_filepath = args.image

try:
    global_image_data = load_jpg_as_rgb565(
        image_filepath, board.LCD_WIDTH, board.LCD_HEIGHT)
    
    board.draw_image(0, 0, board.LCD_WIDTH, board.LCD_HEIGHT, global_image_data)
    
    print(f"Image {os.path.basename(image_filepath)} loaded and displayed.")
except Exception as e:
    print(f"Failed to load image from {image_filepath}: {e}")

try:
    print("Loaded and waiting.. Press Ctrl+c to exit")
    while True:
        sleep(0.1)

except KeyboardInterrupt:
    print("Exiting test...")

finally:
    board.cleanup()