from PIL import Image
from uuid import uuid4
from pathlib import Path

def combine_images(images, new_image_path='auto', columns='auto', space=0, size_limit=3*1024*1024):
    """
    Combines multiple images into a single image.
    size_limit is in bytes, set to 3MB for Discord webhook compatibility
    """
    if columns == 'auto':
        l = len(images)
        if l == 1:
            columns = 1
        elif l == 2:
            columns = 2
        elif l == 3:
            columns = 3
        elif l == 4:
            columns = 2
        elif l >= 4:
            columns = 3

    rows = len(images) // columns
    if len(images) % columns:
        rows += 1

    # Open all images once and store the references
    img_refs = []
    for img_path in images:
        with Image.open(img_path) as img:
            # Resize images to max 1024x1024 while preserving aspect ratio
            original_width, original_height = img.size
            max_dimension = 1024
            
            if original_width > max_dimension or original_height > max_dimension:
                # Calculate scale factor to fit within 1024x1024
                scale_factor = min(max_dimension / original_width, max_dimension / original_height)
                new_width = int(original_width * scale_factor)
                new_height = int(original_height * scale_factor)
                
                # Ensure dimensions don't exceed 1024
                new_width = min(new_width, max_dimension)
                new_height = min(new_height, max_dimension)
                
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                print(f"Resized image for collage from {original_width}x{original_height} to {new_width}x{new_height}")
            
            img_refs.append(img.copy())

    # Find the maximum width and height per column and row
    max_widths = [max((img_refs[i + j * columns] for j in range(rows) if i + j * columns < len(img_refs)), key=lambda img: img.width).width for i in range(columns)]
    max_heights = [max((img_refs[i * columns: (i + 1) * columns]), key=lambda img: img.height).height for i in range(rows)]

    # Calculate the total size of the background image
    total_width = sum(max_widths) + space * (columns - 1)
    total_height = sum(max_heights) + space * (rows - 1)

    # Create the background image
    background = Image.new('RGBA', (total_width, total_height), (255, 255, 255, 0))

    x, y = 0, 0
    for i, img in enumerate(img_refs):
        # Calculate offsets to center each image in its cell
        x_offset = (max_widths[i % columns] - img.width) // 2
        y_offset = (max_heights[i // columns] - img.height) // 2

        # Paste the image onto the background
        background.paste(img, (x + x_offset, y + y_offset))

        # Update the x coordinate, or if at the end of a row, reset x and update y
        if (i + 1) % columns == 0:
            x = 0
            y += max_heights[i // columns] + space
        else:
            x += max_widths[i % columns] + space

    # Generate a unique filename if none was provided
    if new_image_path == 'auto':
        directory = Path(images[0]).parent
        new_image_name = str(uuid4()) + '.png'
        new_image_path = directory / new_image_name

    # Save the image and compress if needed
    background.save(new_image_path, 'PNG', optimize=True)
    
    # Compress the image if it's too large
    compression_attempts = 0
    max_compression_attempts = 10
    
    while Path(new_image_path).stat().st_size > size_limit and compression_attempts < max_compression_attempts:
        compression_attempts += 1
        
        # Calculate new size (reduce by 20% each time)
        scale_factor = 0.8 ** compression_attempts
        new_width = int(background.width * scale_factor)
        new_height = int(background.height * scale_factor)
        
        # Resize the image
        background = background.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Save with higher compression
        background.save(new_image_path, 'PNG', optimize=True, compress_level=9)
        
        print(f"Compression attempt {compression_attempts}: {Path(new_image_path).stat().st_size / (1024*1024):.1f}MB")
    
    # If still too large, try converting to JPEG with high compression
    if Path(new_image_path).stat().st_size > size_limit:
        print("PNG too large, converting to JPEG...")
        jpeg_path = new_image_path.with_suffix('.jpg')
        background = background.convert('RGB')  # Convert to RGB for JPEG
        background.save(jpeg_path, 'JPEG', quality=60, optimize=True)
        
        # Check if JPEG is smaller
        if jpeg_path.stat().st_size < new_image_path.stat().st_size:
            new_image_path.unlink()  # Remove PNG
            new_image_path = jpeg_path
            print(f"Converted to JPEG: {new_image_path.stat().st_size / (1024*1024):.1f}MB")
        else:
            jpeg_path.unlink()  # Remove JPEG, keep PNG
            print("JPEG not smaller, keeping PNG")

    return new_image_path

import imageio
from skimage.transform import resize
from PIL import Image
from pathlib import Path
from uuid import uuid4
import numpy as np

def resize_gif___(image_path: Path):
    # Read the GIF file
    print(image_path)
    gif = imageio.mimread(image_path)
    
    # Get the dimensions of the first frame
    first_frame_shape = gif[0].shape
    
    # Resize each frame to half its original size
    resized_gif = []
    for img in gif:
        new_img = resize(img, (int(img.shape[0] // 1.25), int(img.shape[1] // 1.25)), mode='reflect', anti_aliasing=True)
        
        # Create an empty image of the same size as the first frame
        empty_img = Image.new('RGBA', (int(first_frame_shape[1] // 1.25) , int(first_frame_shape[0] // 1.25)))
        
        # Paste the resized image into the empty image
        empty_img.paste(Image.fromarray((new_img * 255).astype(np.uint8)), (0, 0))
        
        # Add the new image to the list
        resized_gif.append(np.array(empty_img))

    # Generate a unique filename
    new_image_name = str(uuid4()) + '.gif'
    new_image_path = image_path.parent / new_image_name

    # Save the new GIF
    imageio.mimsave(new_image_path, resized_gif, 'GIF')

    return new_image_path

def resize_gif(image_path: Path):
    # Read the GIF file
    # print(image_path)
    reader = imageio.get_reader(image_path)

    # Get the dimensions of the first frame
    first_frame_shape = reader.get_data(0).shape

    # Resize each frame to half its original size
    resized_gif = []
    for i, img in enumerate(reader):
        new_img = resize(img, (int(img.shape[0] // 1.25), int(img.shape[1] // 1.25)), mode='reflect', anti_aliasing=True)

        # Create an empty image of the same size as the first frame
        empty_img = Image.new('RGBA', (int(first_frame_shape[1] // 1.25), int(first_frame_shape[0] // 1.25)))

        # Paste the resized image into the empty image
        empty_img.paste(Image.fromarray((new_img * 255).astype(np.uint8)), (0, 0))

        # Add the new image to the list
        resized_gif.append(np.array(empty_img))

    # Generate a unique filename
    new_image_name = str(uuid4()) + '.gif'
    new_image_path = image_path.parent / new_image_name

    # Save the new GIF
    imageio.mimsave(new_image_path, resized_gif, 'GIF')

    # Close the reader
    reader.close()

    return new_image_path


