#!/usr/bin/env python3
"""
Promo Code Image Generator
Generates attractive promotional images with promo codes embedded
"""

from PIL import Image, ImageDraw, ImageFont
import io
import os
from typing import Optional, Tuple

class PromoImageGenerator:
    def __init__(self):
        self.width = 800
        self.height = 400
        self.background_color = (45, 52, 54)  # Dark gray
        self.accent_color = (0, 184, 148)     # Teal
        self.text_color = (255, 255, 255)    # White
        self.code_color = (255, 234, 167)    # Light yellow
        
    def create_promo_image(self, promo_code: str, discount_type: str, value: str, promo_type: str = "discount", bot_name: str = "TELESHOP") -> io.BytesIO:
        """
        Create a promotional image with the promo code
        
        Args:
            promo_code: The promotional code
            discount_type: Type of discount (e.g., "Discount", "Balance")
            value: The value (e.g., "25%", "50 PLN")
            promo_type: Type of promo ("discount" or "balance")
            
        Returns:
            BytesIO object containing the image
        """
        # Create image
        img = Image.new('RGB', (self.width, self.height), self.background_color)
        draw = ImageDraw.Draw(img)
        
        # Try to load custom fonts, fallback to default if not available
        try:
            # Try Windows system fonts first
            title_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 48)
            code_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 36)
            value_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 42)
            subtitle_font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 24)
        except:
            try:
                # Try alternative Windows fonts
                title_font = ImageFont.truetype("C:/Windows/Fonts/calibri.ttf", 48)
                code_font = ImageFont.truetype("C:/Windows/Fonts/calibri.ttf", 36)
                value_font = ImageFont.truetype("C:/Windows/Fonts/calibri.ttf", 42)
                subtitle_font = ImageFont.truetype("C:/Windows/Fonts/calibri.ttf", 24)
            except:
                # Final fallback to default font with size simulation
                title_font = ImageFont.load_default()
                code_font = ImageFont.load_default()
                value_font = ImageFont.load_default()
                subtitle_font = ImageFont.load_default()
        
        # Draw background gradient effect
        self._draw_gradient_background(draw)
        
        # Draw decorative elements
        self._draw_decorative_elements(draw)
        
        # Draw main title
        if promo_type == "discount":
            title = "🎉 SPECIAL DISCOUNT 🎉"
            emoji = "💸"
        else:
            title = "💰 BALANCE BONUS 💰"
            emoji = "💳"
            
        title_bbox = draw.textbbox((0, 0), title, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        title_x = (self.width - title_width) // 2
        draw.text((title_x, 30), title, fill=self.text_color, font=title_font)
        
        # Draw value with emoji
        value_text = f"{emoji} {value} OFF" if promo_type == "discount" else f"{emoji} {value} BONUS"
        value_bbox = draw.textbbox((0, 0), value_text, font=value_font)
        value_width = value_bbox[2] - value_bbox[0]
        value_x = (self.width - value_width) // 2
        draw.text((value_x, 100), value_text, fill=self.accent_color, font=value_font)
        
        # Draw promo code box
        code_box_y = 180
        code_box_height = 80
        code_box_margin = 50
        
        # Draw code background box
        draw.rounded_rectangle(
            [code_box_margin, code_box_y, self.width - code_box_margin, code_box_y + code_box_height],
            radius=15,
            fill=self.code_color,
            outline=self.accent_color,
            width=3
        )
        
        # Draw promo code text
        code_bbox = draw.textbbox((0, 0), promo_code, font=code_font)
        code_width = code_bbox[2] - code_bbox[0]
        code_x = (self.width - code_width) // 2
        code_y = code_box_y + (code_box_height - (code_bbox[3] - code_bbox[1])) // 2
        draw.text((code_x, code_y), promo_code, fill=self.background_color, font=code_font)
        
        # Draw instructions
        instruction = "Use this code at checkout to get your discount!"
        instruction_bbox = draw.textbbox((0, 0), instruction, font=subtitle_font)
        instruction_width = instruction_bbox[2] - instruction_bbox[0]
        instruction_x = (self.width - instruction_width) // 2
        draw.text((instruction_x, 290), instruction, fill=self.text_color, font=subtitle_font)
        
        # Draw shop name
        shop_name = f"🛒 {bot_name.upper()} - Premium Cannabis Store"
        shop_bbox = draw.textbbox((0, 0), shop_name, font=subtitle_font)
        shop_width = shop_bbox[2] - shop_bbox[0]
        shop_x = (self.width - shop_width) // 2
        draw.text((shop_x, 330), shop_name, fill=(150, 150, 150), font=subtitle_font)
        
        # Save to BytesIO
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG', quality=95)
        img_buffer.seek(0)
        
        return img_buffer
    
    def _draw_gradient_background(self, draw: ImageDraw.Draw):
        """Draw a subtle gradient background effect"""
        for i in range(self.height):
            alpha = int(255 * (1 - i / self.height) * 0.1)
            color = (self.background_color[0] + alpha//4, 
                    self.background_color[1] + alpha//4, 
                    self.background_color[2] + alpha//4)
            draw.line([(0, i), (self.width, i)], fill=color)
    
    def _draw_decorative_elements(self, draw: ImageDraw.Draw):
        """Draw decorative elements like corners and borders"""
        # Draw corner decorations
        corner_size = 30
        corner_color = self.accent_color
        
        # Top-left corner
        draw.arc([10, 10, 10 + corner_size, 10 + corner_size], 180, 270, fill=corner_color, width=3)
        
        # Top-right corner
        draw.arc([self.width - 10 - corner_size, 10, self.width - 10, 10 + corner_size], 270, 360, fill=corner_color, width=3)
        
        # Bottom-left corner
        draw.arc([10, self.height - 10 - corner_size, 10 + corner_size, self.height - 10], 90, 180, fill=corner_color, width=3)
        
        # Bottom-right corner
        draw.arc([self.width - 10 - corner_size, self.height - 10 - corner_size, self.width - 10, self.height - 10], 0, 90, fill=corner_color, width=3)
        
        # Draw side decorative lines
        for i in range(5):
            y_pos = 150 + i * 20
            draw.line([(20, y_pos), (40, y_pos)], fill=corner_color, width=2)
            draw.line([(self.width - 40, y_pos), (self.width - 20, y_pos)], fill=corner_color, width=2)

# Global instance
promo_generator = PromoImageGenerator()