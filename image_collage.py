from PIL import Image
from uuid import uuid4
from pathlib import Path

def combine_images(images, new_image_path='auto', columns='auto', space=0, size_limit= 18* 1024 ** 2):
    """
    Combines multiple images into a single image.
    size_limit is in bytes, can be at most 25 MB for now (for discord free users)
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
    img_refs = [Image.open(img) for img in images]

    # Find the maximum width and height per column and row
    max_widths = [max((img_refs[i + j * columns] for j in range(rows) if i + j * columns < len(img_refs)), key=lambda img: img.width).width for i in range(columns)]
    max_heights = [max((img_refs[i * columns: (i + 1) * columns]), key=lambda img: img.height).height for i in range(rows)]

    # Calculate the total size of the background image
    total_width = sum(max_widths) + space * (columns - 1)
    total_height = sum(max_heights) + space * (rows - 1)

    # Create the background image
    background = Image.new('RGBA', (total_width, total_height), (255, 255, 255, 0))
    # background = Image.new('RGB', (total_width, total_height), (255, 255, 255))

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

    # resize the image if it's too large
    background.save(new_image_path)

    while Path(new_image_path).stat().st_size > size_limit:
        # 0.5 of current size
        max_size = (int(background.width * 0.8), int(background.height * 0.8))
        background.thumbnail(max_size)
        background.save(new_image_path)

    return new_image_path

import imageio
from skimage.transform import resize
from PIL import Image
from pathlib import Path
from uuid import uuid4
import numpy as np

def resize_gif(image_path: Path):
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

