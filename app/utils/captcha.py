import random
import string
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont


def generate_captcha(length=4, width=120, height=40, font_size=28):
    captcha_text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
    
    image = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    
    try:
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', font_size)
    except IOError:
        try:
            font = ImageFont.truetype('arial.ttf', font_size)
        except IOError:
            font = ImageFont.load_default()
    
    colors = [(0, 0, 139), (139, 0, 0), (0, 100, 0), (75, 0, 130), (139, 69, 19), (0, 139, 139)]
    
    for i, char in enumerate(captcha_text):
        x = 15 + i * (width - 30) // length
        y = random.randint(0, height - font_size - 5)
        color = random.choice(colors)
        
        draw.text((x, y), char, font=font, fill=color)
    
    for _ in range(3):
        x1 = random.randint(0, width // 4)
        y1 = random.randint(0, height)
        x2 = random.randint(width * 3 // 4, width)
        y2 = random.randint(0, height)
        draw.line([(x1, y1), (x2, y2)], fill=random.choice(colors), width=1)
    
    for _ in range(50):
        x = random.randint(0, width)
        y = random.randint(0, height)
        draw.point((x, y), fill=random.choice(colors))
    
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    buffer.seek(0)
    image_bytes = buffer.getvalue()
    
    return image_bytes, captcha_text
