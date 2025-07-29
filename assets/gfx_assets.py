import pygame
from .loader import load_sprite
from config import Config

class GfxAssets:
    """Load all image/sprite resources."""
    def __init__(self) -> None:
        self.lander   = load_sprite("lander_v3", scale=1.5)
        self.thruster = load_sprite("lander_v3_thruster", scale=1.5)
        self.rock_sprites         = [load_sprite(f"rock_{i}") for i in (1,2,3,4,5,6,7,8,9,10)]
        self.special_rock_sprites = [load_sprite(f"radioactive_rock_{i}") for i in (1,2,3,4,5, 6)]
        self.neutral_rock_sprites = [load_sprite(f"neutral_rock_{i}") for i in (1,2,3,4,5)]
        self.crash_frames         = [load_sprite(f"lander_colored_crash_{i}", scale=2)
                                     for i in range(1, Config.CRASH_FRAME_COUNT + 1)]
