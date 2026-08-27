from PIL import Image
import sys

img = Image.open(sys.argv[1])
print(f"Size: {img.size}, Mode: {img.mode}")

data = img.tobytes()
print(f"Data length: {len(data)} bytes")

colors = img.getcolors(maxcolors=100000)
if colors:
    print(f"Unique colors: {len(colors)}")
    for count, color in sorted(colors, reverse=True)[:5]:
        print(f"  {count} pixels: {color}")
else:
    print("Unique colors: >100k")
