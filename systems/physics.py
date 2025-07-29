import math
import pygame
from config import Config

__all__ = ["compute_altitude"]

def compute_altitude(lander, terrain) -> float:
    idx = int((lander.x + lander.img.get_width()/2) // Config.PIXEL_SIZE)
    if 0 <= idx < len(terrain.topo):
        ground_y = terrain.topo[idx]
        rot = pygame.transform.rotate(lander.img, lander.angle)
        rect = rot.get_rect(center=(lander.x, lander.y))
        alt_px = max(0, ground_y - rect.bottom)
        return alt_px / lander.px_per_m
    return 0.0
