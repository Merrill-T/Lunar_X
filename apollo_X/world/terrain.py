#terrain.py

import pygame
from config import Config
import math
from random import randint, choice
from typing import List, Tuple

class Terrain:
    """Procedurally generated terrain surface + mask."""
    def __init__(self) -> None:
        self.topo: List[int] = []
        self.surface = pygame.Surface((Config.TERRAIN_LENGTH, Config.SCREEN_SIZE), pygame.SRCALPHA)
        self.rocks: List[Tuple[int, int, pygame.Surface]] = []
        self.mask: pygame.Mask | None = None
        self.generate()

    def generate(self) -> None:
        """Create the height map and draw the solid ground surface."""
        base = Config.SCREEN_SIZE - 100
        topo = [int(base + 20 * math.sin(i * 0.01) + 10 * math.sin(i * 0.05 + math.pi / 3))
                for i in range(Config.TERRAIN_LENGTH // Config.PIXEL_SIZE)]

        # Carve a few large craters
        for _ in range(5):
            center = randint(30, len(topo) - 30)
            w = randint(12, 24)
            d = randint(20, 50)
            r = randint(6, 16)
            for i in range(-w * 2, w * 2):
                idx = center + i
                if 0 <= idx < len(topo):
                    dist = abs(i) / w
                    if dist <= 1:
                        topo[idx] += int((1 - dist**2) * d)
                    elif dist <= 2:
                        topo[idx] -= int((1 - (dist - 1))**2 * r)

        self.topo = topo
        self.surface.fill((0, 0, 0, 0))

        # Draw columns
        draw_rect = pygame.draw.rect
        for x, h in enumerate(self.topo):
            px = x * Config.PIXEL_SIZE
            draw_rect(self.surface, Config.GRAY, (px, h, Config.PIXEL_SIZE, Config.SCREEN_SIZE - h))

        self.mask = pygame.mask.from_surface(self.surface)
