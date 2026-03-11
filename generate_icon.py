import os
from PIL import Image, ImageDraw

def create_placeholder_icon():
    os.makedirs("assets", exist_ok=True)
    icon_path = os.path.join("assets", "icon.ico")
    
    if os.path.exists(icon_path):
        return
        
    # Create a nice vibrant purple generic icon (256x256)
    img = Image.new('RGBA', (256, 256), color=(0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    
    # Draw rounded rectangle
    d.rounded_rectangle([(10, 10), (246, 246)], radius=40, fill=(139, 92, 246, 255))
    
    # Draw a generic play/video symbol inside
    d.polygon([(90, 70), (90, 186), (180, 128)], fill=(255, 255, 255, 255))
    
    img.save(icon_path, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (32, 32)])
    print(f"Created placeholder icon at {icon_path}")

if __name__ == "__main__":
    create_placeholder_icon()
