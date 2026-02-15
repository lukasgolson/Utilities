import argparse
import sys
import random
import os
from PIL import Image, ImageFilter, ImageOps, ImageDraw, ImageChops

try:
    import fitz
except ImportError:
    print("Error: PyMuPDF is not installed. Run 'pip install pymupdf pillow tqdm'")
    sys.exit(1)

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, desc=None):
        print(f"Processing: {desc}...")
        return iterable

class StderrSuppressor:
    def __enter__(self):
        self._original_stderr = sys.stderr
        sys.stderr = open(os.devnull, 'w')

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stderr.close()
        sys.stderr = self._original_stderr

def create_white_page_from_pdf(page, scale):
    with StderrSuppressor():
        pix = page.get_pixmap(matrix=scale, alpha=True)
    
    img_rgba = Image.frombytes("RGBA", [pix.width, pix.height], pix.samples)
    
    solid_bg = Image.new("RGBA", img_rgba.size, (255, 255, 255, 255))
    solid_bg.paste(img_rgba, (0, 0), mask=img_rgba)
    
    return solid_bg

def add_page_border(img, color=(200, 200, 200, 255), width=2):
    """Adds a generic border."""
    draw = ImageDraw.Draw(img)
    w, h = img.size
    draw.rectangle([0, 0, w-1, h-1], outline=color, width=width)
    return img

def create_multiply_shadow(img_size, blur=30, offset=(10, 10)):
    """
    Creates a shadow map designed for MULTIPLY blending.
    """
    w, h = img_size
    shadow_w = w + blur * 4
    shadow_h = h + blur * 4
    
    # Start with pure WHITE canvas
    shadow_layer = Image.new("RGBA", (shadow_w, shadow_h), (255, 255, 255, 255))
    
    # Create shadow box (Grey = shadow intensity)
    shadow_intensity = 160 
    shadow_color = (shadow_intensity, shadow_intensity, shadow_intensity, 255)
    
    shrink = 4
    shadow_box = Image.new("RGBA", (w - shrink*2, h - shrink*2), shadow_color)
    
    center_x = (shadow_w - (w - shrink*2)) // 2
    center_y = (shadow_h - (h - shrink*2)) // 2
    
    # Blur logic
    temp_layer = Image.new("RGBA", (shadow_w, shadow_h), (255, 255, 255, 0))
    temp_layer.paste(shadow_box, (center_x + offset[0], center_y + offset[1]))
    temp_layer = temp_layer.filter(ImageFilter.GaussianBlur(blur))
    
    shadow_layer.paste(temp_layer, (0, 0), mask=temp_layer)
    return shadow_layer

def process_pdf(pdf_path, output_path, max_pages=6, dpi=300):
    print(f"Opening {pdf_path}...")
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"Error: {e}")
        return

    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)
    
    total_pages = len(doc)
    page_indices = []
    if total_pages > 1:
        bg_indices = list(range(1, total_pages))
        random.shuffle(bg_indices)
        page_indices = bg_indices[:max_pages-1]
    page_indices.append(0) # Top page last

    images = []
    print(f"Rendering {len(page_indices)} pages...")
    for i in tqdm(page_indices):
        page = doc.load_page(i)
        img = create_white_page_from_pdf(page, mat)
        img = add_page_border(img)
        images.append(img)
    doc.close()

    # Prepare Canvas
    w, h = images[0].size
    canvas_w = int(w * 1.6)
    canvas_h = int(h * 1.6)
    
    # Initialize transparent canvas
    canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    
    center_x = canvas_w // 2
    center_y = canvas_h // 2
    
    print("Compositing with Multiply Shadows...")

    for i, img in enumerate(tqdm(images)):
        is_top = (i == len(images) - 1)
        
        if is_top:
            angle = random.uniform(-2, 2)
            offset_x, offset_y = 0, 0
            blur_rad = 20
        else:
            angle = random.uniform(-12, 12)
            offset_x = random.randint(-60, 60)
            offset_y = random.randint(-60, 60)
            blur_rad = 35

        # --- SHADOW (MULTIPLY) ---
        shadow_map = create_multiply_shadow(img.size, blur=blur_rad)
        
        # Rotate shadow (filling corners with WHITE)
        shadow_rot = shadow_map.rotate(angle, resample=Image.BICUBIC, expand=True, fillcolor=(255,255,255,255))
        
        shad_x = center_x - (shadow_rot.width // 2) + offset_x
        shad_y = center_y - (shadow_rot.height // 2) + offset_y
        
        # Crop region from canvas to blend
        box = (shad_x, shad_y, shad_x + shadow_rot.width, shad_y + shadow_rot.height)
        
        # Ensure box is within canvas bounds (simple safety check)
        if box[2] > canvas.width or box[3] > canvas.height:
            # If off-canvas, skip shadow blending to prevent crash
            pass 
        else:
            current_bg = canvas.crop(box)
            
            # Multiply RGB
            bg_rgb = current_bg.convert("RGB")
            shadow_rgb = shadow_rot.convert("RGB")
            multiplied = ImageChops.multiply(bg_rgb, shadow_rgb)
            
            # Reconstruct Alpha
            r, g, b, a = current_bg.split()
            mult_r, mult_g, mult_b = multiplied.split()
            
            # Enhance alpha where shadow exists
            grayscale_shadow = shadow_rot.convert("L")
            inverted_shadow = ImageOps.invert(grayscale_shadow)
            new_a = ImageChops.screen(a, inverted_shadow)
            
            # Merge back
            blended_shadow = Image.merge("RGBA", (mult_r, mult_g, mult_b, new_a))
            canvas.paste(blended_shadow, box)

        # --- PASTE PAGE ---
        img_rot = img.rotate(angle, resample=Image.BICUBIC, expand=True)
        
        dest_x = center_x - (img_rot.width // 2) + offset_x
        dest_y = center_y - (img_rot.height // 2) + offset_y
        
        canvas.paste(img_rot, (dest_x, dest_y), mask=img_rot)

    # Final Crop
    bbox = canvas.getbbox()
    if bbox:
        canvas = canvas.crop(bbox)
        canvas = ImageOps.expand(canvas, border=60, fill=(0,0,0,0))
    
    canvas.save(output_path, format="PNG")
    print(f"Success! Saved to: {output_path}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_pdf")
    parser.add_argument("-o", "--output", default="stack_final.png")
    parser.add_argument("-p", "--pages", type=int, default=5)
    parser.add_argument("-d", "--dpi", type=int, default=300)
    args = parser.parse_args()
    
    process_pdf(args.input_pdf, args.output, args.pages, args.dpi)

if __name__ == "__main__":
    main()
