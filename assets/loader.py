# Save this as assets_loader.py in the same folder as your main game file
import pygame

def load_sprite(name, scale=1):
    """
    Load a sprite image from the assets folder and scale it.

    Args:
        name (str): name of the image file (without extension)
        scale (float): scaling factor (default is 1)

    Returns:
        pygame.Surface: the loaded and scaled image
    """
    image = pygame.image.load(f"assets/gfx/{name}.png").convert_alpha()
    if scale != 1:
        width = int(image.get_width() * scale)
        height = int(image.get_height() * scale)
        image = pygame.transform.scale(image, (width, height))
    return image
