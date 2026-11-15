from PIL import Image, ImageDraw, ImageFont

# Create a blank grey image
img = Image.new('RGB', (640, 480), color=(180, 180, 180))
draw = ImageDraw.Draw(img)

# Text to display
text = "Placeholder Image"
font_size = 32

# Load a font
try:
    font = ImageFont.truetype("arial.ttf", font_size)
except:
    font = ImageFont.load_default()

# Get text size using textbbox
bbox = draw.textbbox((0, 0), text, font=font)
text_width = bbox[2] - bbox[0]
text_height = bbox[3] - bbox[1]

# Center the text
position = ((640 - text_width) // 2, (480 - text_height) // 2)
draw.text(position, text, fill=(0, 0, 0), font=font)

# Save the image
img.save("placeholder.jpg")
print("Saved to static/placeholder.jpg")
