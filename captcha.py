import random
import io
from PIL import Image, ImageDraw, ImageFont
from typing import Dict, List
import base64
import string

class CaptchaManager:
    def __init__(self):
        # Characters to use in captcha (excluding confusing ones like 0, O, l, I)
        self.captcha_chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
        self.captcha_length = 5
    
    def generate_captcha(self) -> Dict:
        """Generate a lightweight captcha with minimal processing"""
        return self._generate_text_captcha()
    
    def _generate_text_captcha(self) -> Dict:
        """Generate simple alphanumeric captcha"""
        # Generate random code
        captcha_code = ''.join(random.choices(self.captcha_chars, k=self.captcha_length))
        
        # Create image with the code
        image_data = self._create_captcha_image(captcha_code)
        
        return {
            'type': 'text',
            'question': 'Please type the code shown in the image:',
            'image_data': image_data,
            'correct_answer': captcha_code
        }
    
    def _create_captcha_image(self, code: str) -> bytes:
        """Create a captcha image with bigger characters, varying sizes and moderate noise"""
        # Extremely large image for extremely big characters
        width, height = 450, 180
        img = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(img)
        
        # Add heavy background noise with vibrant randomized colors
        for _ in range(200):
            x = random.randint(0, width)
            y = random.randint(0, height)
            # Generate more vibrant random colors
            r = random.randint(180, 240)
            g = random.randint(180, 240)
            b = random.randint(180, 240)
            color = f'#{r:02x}{g:02x}{b:02x}'
            draw.point((x, y), fill=color)
        
        # Add more random circles for noise with vibrant randomized colors
        for _ in range(15):
            x = random.randint(0, width)
            y = random.randint(0, height)
            radius = random.randint(2, 8)
            # Generate more vibrant random colors for circles
            r = random.randint(150, 220)
            g = random.randint(150, 220)
            b = random.randint(150, 220)
            color = f'#{r:02x}{g:02x}{b:02x}'
            draw.ellipse([x-radius, y-radius, x+radius, y+radius], fill=color)
        
        # Add random rectangles for additional noise with vibrant randomized colors
        for _ in range(10):
            x1 = random.randint(0, width-20)
            y1 = random.randint(0, height-10)
            x2 = x1 + random.randint(5, 20)
            y2 = y1 + random.randint(3, 10)
            # Generate more vibrant random colors for rectangles
            r = random.randint(160, 230)
            g = random.randint(160, 230)
            b = random.randint(160, 230)
            color = f'#{r:02x}{g:02x}{b:02x}'
            draw.rectangle([x1, y1, x2, y2], fill=color)
        
        # Add curved noise lines with vibrant randomized colors
        for _ in range(8):
            points = []
            for i in range(4):
                x = random.randint(0, width)
                y = random.randint(0, height)
                points.extend([x, y])
            # Generate more vibrant random colors for polygons
            r = random.randint(120, 200)
            g = random.randint(120, 200)
            b = random.randint(120, 200)
            color = f'#{r:02x}{g:02x}{b:02x}'
            if len(points) >= 4:
                try:
                    draw.polygon(points[:8], outline=color)
                except:
                    pass
        
        # Try to load a much larger font, fallback to default
        try:
            # Try to load a system font with moderate base size for fallback
            font_size = random.randint(50, 80)  # Moderate base font size for fallback
            # Try common system fonts
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except:
                try:
                    font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", font_size)
                except:
                    try:
                        font = ImageFont.truetype("C:\\Windows\\Fonts\\calibri.ttf", font_size)
                    except:
                        font = ImageFont.load_default()
        except:
            font = ImageFont.load_default()
        
        # Draw the code with varying sizes and positions
        text_width = len(code) * 75  # Approximate width for randomized characters
        x_start = (width - text_width) // 2
        
        for i, char in enumerate(code):
            # Varying horizontal position with adaptive spread
            x = x_start + i * 75 + random.randint(-15, 15)
            # Varying vertical position with more range
            y = 60 + random.randint(-25, 25)
            
            # Random color (darker colors for contrast)
            color = random.choice(['#000000', '#333333', '#000080', '#800000', '#004000', '#800080'])
            
            # Create highly randomized font sizes with readable limits
            # Min size: 45 (readable), Max size: 95 (won't cover other elements)
            char_font_size = random.randint(45, 95)
            try:
                # Try to create different sized fonts with system fonts
                try:
                    char_font = ImageFont.truetype("arial.ttf", char_font_size)
                except:
                    try:
                        char_font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", char_font_size)
                    except:
                        try:
                            char_font = ImageFont.truetype("C:\\Windows\\Fonts\\calibri.ttf", char_font_size)
                        except:
                            char_font = font
            except:
                char_font = font
            
            # Draw character with slight rotation for variety
            if char_font:
                # Create adaptive temporary image size based on font size
                temp_size = min(150, max(100, char_font_size + 40))
                char_img = Image.new('RGBA', (temp_size, temp_size), (255, 255, 255, 0))
                char_draw = ImageDraw.Draw(char_img)
                # Center the character in the temporary image
                text_x = temp_size // 2 - char_font_size // 3
                text_y = temp_size // 2 - char_font_size // 2
                char_draw.text((text_x, text_y), char, fill=color, font=char_font)
                
                # Rotate the character slightly
                rotation = random.randint(-15, 15)
                rotated_char = char_img.rotate(rotation, expand=True)
                
                # Paste the rotated character with adaptive positioning
                paste_x = x - temp_size // 2
                paste_y = y - temp_size // 2
                img.paste(rotated_char, (paste_x, paste_y), rotated_char)
            else:
                # Fallback: draw single text directly with random size
                fallback_size = random.randint(45, 95)
                draw.text((x, y), char, fill=color)
        
        # Add many more noise lines with vibrant randomized colors
        for _ in range(12):
            x1 = random.randint(0, width)
            y1 = random.randint(0, height)
            x2 = random.randint(0, width)
            y2 = random.randint(0, height)
            # Generate more vibrant random colors for lines
            r = random.randint(100, 200)
            g = random.randint(100, 200)
            b = random.randint(100, 200)
            color = f'#{r:02x}{g:02x}{b:02x}'
            line_width = random.randint(1, 3)
            draw.line([(x1, y1), (x2, y2)], fill=color, width=line_width)
        
        # Add diagonal grid pattern with vibrant randomized colors
        for i in range(0, width, 30):
            # Generate more vibrant random colors for diagonal lines
            r = random.randint(140, 210)
            g = random.randint(140, 210)
            b = random.randint(140, 210)
            color = f'#{r:02x}{g:02x}{b:02x}'
            draw.line([(i, 0), (i + height//2, height)], fill=color, width=1)
        
        for i in range(0, width, 35):
            # Generate more vibrant random colors for diagonal lines
            r = random.randint(140, 210)
            g = random.randint(140, 210)
            b = random.randint(140, 210)
            color = f'#{r:02x}{g:02x}{b:02x}'
            draw.line([(i, height), (i + height//2, 0)], fill=color, width=1)
        
        # Add significantly more random dots for extra noise with vibrant randomized colors
        for _ in range(50):
            x = random.randint(0, width)
            y = random.randint(0, height)
            # Generate more vibrant random colors for dots
            r = random.randint(130, 200)
            g = random.randint(130, 200)
            b = random.randint(130, 200)
            color = f'#{r:02x}{g:02x}{b:02x}'
            radius = random.randint(1, 3)
            draw.ellipse([x-radius, y-radius, x+radius, y+radius], fill=color)
        
        # Add random arcs for more complex noise with vibrant randomized colors
        for _ in range(6):
            x = random.randint(10, width-10)
            y = random.randint(10, height-10)
            width_arc = random.randint(20, 60)
            height_arc = random.randint(15, 40)
            start_angle = random.randint(0, 360)
            end_angle = start_angle + random.randint(30, 180)
            # Generate more vibrant random colors for arcs
            r = random.randint(110, 190)
            g = random.randint(110, 190)
            b = random.randint(110, 190)
            color = f'#{r:02x}{g:02x}{b:02x}'
            try:
                draw.arc([x-width_arc//2, y-height_arc//2, x+width_arc//2, y+height_arc//2], 
                        start_angle, end_angle, fill=color, width=2)
            except:
                pass
        
        # Convert to bytes with optimization
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG', optimize=True)
        return img_byte_arr.getvalue()
    
    def verify_answer(self, user_answer: str, correct_answer: str) -> bool:
        """Verify if the user's answer is correct"""
        # Simple case-insensitive comparison for text captcha
        return user_answer.upper().strip() == correct_answer.upper().strip()