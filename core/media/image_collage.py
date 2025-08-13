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

    img_refs = []
    for img_path in images:
        with Image.open(img_path) as img:
            original_width, original_height = img.size
            max_dimension = 1024
            if original_width > max_dimension or original_height > max_dimension:
                scale_factor = min(max_dimension / original_width, max_dimension / original_height)
                new_width = int(original_width * scale_factor)
                new_height = int(original_height * scale_factor)
                new_width = min(new_width, max_dimension)
                new_height = min(new_height, max_dimension)
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            img_refs.append(img.copy())

    max_widths = [max((img_refs[i + j * columns] for j in range(rows) if i + j * columns < len(img_refs)), key=lambda img: img.width).width for i in range(columns)]
    max_heights = [max((img_refs[i * columns: (i + 1) * columns]), key=lambda img: img.height).height for i in range(rows)]

    total_width = sum(max_widths) + space * (columns - 1)
    total_height = sum(max_heights) + space * (rows - 1)

    background = Image.new('RGBA', (total_width, total_height), (255, 255, 255, 0))

    x, y = 0, 0
    for i, img in enumerate(img_refs):
        x_offset = (max_widths[i % columns] - img.width) // 2
        y_offset = (max_heights[i // columns] - img.height) // 2
        background.paste(img, (x + x_offset, y + y_offset))
        if (i + 1) % columns == 0:
            x = 0
            y += max_heights[i // columns] + space
        else:
            x += max_widths[i % columns] + space

    if new_image_path == 'auto':
        directory = Path(images[0]).parent
        new_image_name = str(uuid4()) + '.png'
        new_image_path = directory / new_image_name

    background.save(new_image_path, 'PNG', optimize=True)

    compression_attempts = 0
    max_compression_attempts = 10
    while Path(new_image_path).stat().st_size > size_limit and compression_attempts < max_compression_attempts:
        compression_attempts += 1
        scale_factor = 0.8 ** compression_attempts
        new_width = int(background.width * scale_factor)
        new_height = int(background.height * scale_factor)
        background = background.resize((new_width, new_height), Image.Resampling.LANCZOS)
        background.save(new_image_path, 'PNG', optimize=True, compress_level=9)

    if Path(new_image_path).stat().st_size > size_limit:
        jpeg_path = new_image_path.with_suffix('.jpg')
        background = background.convert('RGB')
        background.save(jpeg_path, 'JPEG', quality=60, optimize=True)
        if jpeg_path.stat().st_size < new_image_path.stat().st_size:
            new_image_path.unlink()
            new_image_path = jpeg_path
        else:
            jpeg_path.unlink()

    return new_image_path

import imageio
from skimage.transform import resize
from PIL import Image
from pathlib import Path
from uuid import uuid4
import numpy as np

def resize_gif___(image_path: Path):
    print(image_path)
    gif = imageio.mimread(image_path)
    first_frame_shape = gif[0].shape
    resized_gif = []
    for img in gif:
        new_img = resize(img, (int(img.shape[0] // 1.25), int(img.shape[1] // 1.25)), mode='reflect', anti_aliasing=True)
        empty_img = Image.new('RGBA', (int(first_frame_shape[1] // 1.25) , int(first_frame_shape[0] // 1.25)))
        empty_img.paste(Image.fromarray((new_img * 255).astype(np.uint8)), (0, 0))
        resized_gif.append(np.array(empty_img))
    new_image_name = str(uuid4()) + '.gif'
    new_image_path = image_path.parent / new_image_name
    imageio.mimsave(new_image_path, resized_gif, 'GIF')
    return new_image_path

def resize_gif(image_path: Path):
    reader = imageio.get_reader(image_path)
    first_frame_shape = reader.get_data(0).shape
    resized_gif = []
    for i, img in enumerate(reader):
        new_img = resize(img, (int(img.shape[0] // 1.25), int(img.shape[1] // 1.25)), mode='reflect', anti_aliasing=True)
        empty_img = Image.new('RGBA', (int(first_frame_shape[1] // 1.25), int(first_frame_shape[0] // 1.25)))
        empty_img.paste(Image.fromarray((new_img * 255).astype(np.uint8)), (0, 0))
        resized_gif.append(np.array(empty_img))
    new_image_name = str(uuid4()) + '.gif'
    new_image_path = image_path.parent / new_image_name
    imageio.mimsave(new_image_path, resized_gif, 'GIF')
    reader.close()
    return new_image_path


