#!/usr/bin/env python3

from PIL import Image, ImageDraw, ImageFont
import subprocess
import sys
import os


def set_wm8960_volume_stable(volume_level: str):
    """
    Sets the 'Speaker' volume for the wm8960 sound card using the amixer command.

    Args:
        volume_level (str): The desired volume value, e.g., '90%' or '121'.
    """

    CARD_NAME = 'wm8960soundcard'
    CONTROL_NAME = 'Speaker'
    DEVICE_ARG = f'hw:{CARD_NAME}'

    command = [
        'amixer',
        '-D', DEVICE_ARG,
        'sset',
        CONTROL_NAME,
        volume_level
    ]

    try:
        subprocess.run(command, check=True, capture_output=True, text=True)

        print(
            f"INFO: Successfully set '{CONTROL_NAME}' volume to {volume_level} on card '{CARD_NAME}'.")

    except subprocess.CalledProcessError as e:
        print(f"ERROR: Failed to execute amixer.", file=sys.stderr)
        print(f"Command: {' '.join(command)}", file=sys.stderr)
        print(f"Return Code: {e.returncode}", file=sys.stderr)
        print(f"Error Output:\n{e.stderr}", file=sys.stderr)
    except FileNotFoundError:
        print("ERROR: 'amixer' command not found. Ensure it is installed and in PATH.", file=sys.stderr)


def load_jpg_as_rgb565(filepath, screen_width, screen_height):
    img = Image.open(filepath).convert('RGB')
    original_width, original_height = img.size

    aspect_ratio = original_width / original_height
    screen_aspect_ratio = screen_width / screen_height

    if aspect_ratio > screen_aspect_ratio:
        # Original image is wider, scale based on screen height
        new_height = screen_height
        new_width = int(new_height * aspect_ratio)
        resized_img = img.resize((new_width, new_height))
        # Calculate horizontal offset to center the image
        offset_x = (new_width - screen_width) // 2
        # Crop the image to fit screen width
        cropped_img = resized_img.crop(
            (offset_x, 0, offset_x + screen_width, screen_height))
    else:
        # Original image is taller or has the same aspect ratio, scale based on screen width
        new_width = screen_width
        new_height = int(new_width / aspect_ratio)
        resized_img = img.resize((new_width, new_height))
        # Calculate vertical offset to center the image
        offset_y = (new_height - screen_height) // 2
        # Crop the image to fit screen height
        cropped_img = resized_img.crop(
            (0, offset_y, screen_width, offset_y + screen_height))

    pixel_data = []
    for y in range(screen_height):
        for x in range(screen_width):
            r, g, b = cropped_img.getpixel((x, y))
            rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
            pixel_data.extend([(rgb565 >> 8) & 0xFF, rgb565 & 0xFF])

    return pixel_data


def make_text_image(text, sub_text="", bg_color=(0, 0, 0), text_color=(255, 255, 255),
                    width=240, height=280):
    """Generate RGB565 pixel data with text (for LCD display)"""
    img = Image.new('RGB', (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    # Try to load font, fall back to default
    font_large = None
    font_small = None
    for fpath in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                  "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"]:
        if os.path.exists(fpath):
            try:
                font_large = ImageFont.truetype(fpath, 28)
                font_small = ImageFont.truetype(fpath, 18)
            except Exception:
                pass
            break

    if font_large is None:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Center main text
    bbox = draw.textbbox((0, 0), text, font=font_large)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (width - tw) // 2
    y = (height - th) // 2 - 15
    draw.text((x, y), text, fill=text_color, font=font_large)

    # Sub text
    if sub_text:
        bbox2 = draw.textbbox((0, 0), sub_text, font=font_small)
        tw2 = bbox2[2] - bbox2[0]
        x2 = (width - tw2) // 2
        draw.text((x2, y + th + 15), sub_text, fill=text_color, font=font_small)

    # Convert to RGB565
    pixel_data = []
    for py in range(height):
        for px in range(width):
            r, g, b = img.getpixel((px, py))
            rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
            pixel_data.extend([(rgb565 >> 8) & 0xFF, rgb565 & 0xFF])
    return pixel_data