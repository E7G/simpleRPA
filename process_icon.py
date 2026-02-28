#!/usr/bin/env python3
from PIL import Image, ImageDraw, ImageFilter
import os
import math

script_dir = os.path.dirname(os.path.abspath(__file__))
icon_path = os.path.join(script_dir, 'icon.png')

img = Image.open(icon_path).convert('RGBA')
width, height = img.size
pixels = img.load()

def is_near_white(r, g, b, threshold=220):
    brightness = (r + g + b) / 3
    return brightness >= threshold

mask = Image.new('L', (width, height), 0)
mask_pixels = mask.load()

for y in range(height):
    for x in range(width):
        r, g, b, a = pixels[x, y]
        if is_near_white(r, g, b, threshold=220):
            mask_pixels[x, y] = 255

mask = mask.filter(ImageFilter.MaxFilter(15))
mask = mask.filter(ImageFilter.MinFilter(15))

mask_pixels = mask.load()

flood_mask = Image.new('L', (width, height), 0)
flood_pixels = flood_mask.load()

from collections import deque

def flood_fill(mask_pixels, flood_pixels, width, height, start_x, start_y):
    if mask_pixels[start_x, start_y] == 0:
        return
    if flood_pixels[start_x, start_y] == 255:
        return
    
    queue = deque([(start_x, start_y)])
    
    while queue:
        x, y = queue.popleft()
        
        if x < 0 or x >= width or y < 0 or y >= height:
            continue
        if flood_pixels[x, y] == 255:
            continue
        if mask_pixels[x, y] == 0:
            continue
            
        flood_pixels[x, y] = 255
        
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            queue.append((x + dx, y + dy))

edge_points = [
    (0, 0), (width-1, 0), (0, height-1), (width-1, height-1),
    (width//2, 0), (width//2, height-1), (0, height//2), (width-1, height//2),
]

for x, y in edge_points:
    flood_fill(mask_pixels, flood_pixels, width, height, x, y)

flood_pixels = flood_mask.load()

removed = 0
for y in range(height):
    for x in range(width):
        if flood_pixels[x, y] == 255:
            r, g, b, a = pixels[x, y]
            pixels[x, y] = (r, g, b, 0)
            removed += 1

output_png = os.path.join(script_dir, 'icon_processed.png')
img.save(output_png, 'PNG')
print(f"PNG 处理完成: {output_png}")

output_ico = os.path.join(script_dir, 'icon_processed.ico')
sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
icons = []
for size in sizes:
    resized = img.resize(size, Image.Resampling.LANCZOS)
    icons.append(resized)

img.save(output_ico, format='ICO', sizes=sizes)
print(f"ICO 转换完成: {output_ico}")
print(f"图片尺寸: {width}x{height}")
print(f"移除白色像素: {removed}")
