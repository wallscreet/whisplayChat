from PIL import Image, ImageDraw, ImageFont
import os
from Driver.WhisPlay import WhisPlayBoard


class ScreenHelper:
    def __init__(self, debug: bool = False):
        self.board = WhisPlayBoard()
        self.board.set_backlight(60)
        self.width = self.board.LCD_WIDTH
        self.height = self.board.LCD_HEIGHT
        self.debug = debug
        self._cache = {}

    def _load_jpg_as_rgb565(self, filepath: str):
        if not os.path.isfile(filepath):
            raise FileNotFoundError(f"Image not found: {filepath}")
        
        img = Image.open(filepath).convert('RGB')
        original_width, original_height = img.size
        aspect_ratio = original_width / original_height
        screen_aspect = self.width / self.height

        if aspect_ratio > screen_aspect:
            new_height = self.height
            new_width = int(new_height * aspect_ratio)
            resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            offset_x = (new_width - self.width) // 2
            cropped = resized.crop((offset_x, 0, offset_x + self.width, self.height))
        else:
            new_width = self.width
            new_height = int(new_width / aspect_ratio)
            resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            offset_y = (new_height - self.height) // 2
            cropped = resized.crop((0, offset_y, self.width, offset_y + self.height))

        pixel_data = []
        for y in range(self.height):
            for x in range(self.width):
                r, g, b = cropped.getpixel((x, y))
                rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
                pixel_data.extend([(rgb565 >> 8) & 0xFF, rgb565 & 0xFF])
        return pixel_data

    def _make_text_image(self, text: str, sub_text: str = "", bg_color=(0,0,0), text_color=(255,255,255)):
        img = Image.new('RGB', (self.width, self.height), bg_color)
        draw = ImageDraw.Draw(img)

        font_large = font_small = ImageFont.load_default()
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        ]
        for path in font_paths:
            if os.path.exists(path):
                try:
                    font_large = ImageFont.truetype(path, 28)
                    font_small = ImageFont.truetype(path, 18)
                    break
                except:
                    pass

        # Main text
        bbox = draw.textbbox((0, 0), text, font=font_large)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(((self.width - tw) // 2, (self.height - th) // 2 - 15), text, fill=text_color, font=font_large)

        # Sub text
        if sub_text:
            bbox2 = draw.textbbox((0, 0), sub_text, font=font_small)
            tw2 = bbox2[2] - bbox2[0]
            draw.text(((self.width - tw2) // 2, (self.height - th) // 2 + 30), sub_text, fill=text_color, font=font_small)

        pixel_data = []
        for y in range(self.height):
            for x in range(self.width):
                r, g, b = img.getpixel((x, y))
                rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
                pixel_data.extend([(rgb565 >> 8) & 0xFF, rgb565 & 0xFF])
        return pixel_data

    def show_text(self, main_text: str, sub_text: str = "", bg_color=(0,0,40), text_color=(255,255,255)):
        try:
            pixel_data = self._make_text_image(main_text, sub_text, bg_color, text_color)
            self.board.draw_image(0, 0, self.width, self.height, pixel_data)
            if self.debug:
                print(f"Displayed: {main_text}")
        except Exception as e:
            print(f"show_text failed: {e}")

    def show_image(self, filepath: str):
        try:
            pixel_data = self._load_jpg_as_rgb565(filepath)
            self.board.draw_image(0, 0, self.width, self.height, pixel_data)
            if self.debug:
                print(f"Displayed image: {os.path.basename(filepath)}")
        except Exception as e:
            print(f"show_image failed: {e}")