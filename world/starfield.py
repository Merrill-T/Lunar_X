#starfield.py

from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from random import randint, choice, uniform, random
from typing import List, Tuple
from config import Config
import pygame



from dataclasses import dataclass

@dataclass(slots=True)
class Star:
    x: int
    y: int
    parallax: float
    color: tuple[int, int, int]
    twinkle: bool
    twinkle_rate: float
    size: int
    
    
class Starfield:
    """Static star background with parallax and simple twinkle."""
    def __init__(self, count: int) -> None:
        self.stars: List[Star] = [self._make_star() for _ in range(count)]

    @staticmethod
    def _make_star() -> Star:
        return Star(
            x=randint(0, Config.TERRAIN_LENGTH),
            y=randint(0, Config.SCREEN_SIZE),
            parallax=uniform(0.2, 0.8),
            color=choice([Config.WHITE, Config.RED, Config.BLUE]),
            twinkle=random() < 0.2,
            twinkle_rate=uniform(1.0, 3.0),
            size=randint(1, 3),
        )

    def draw(self, screen: pygame.Surface, offset: float, elapsed: float) -> None:
        """Draw stars if they are within the viewport."""
        for s in self.stars:
            dx = int(s.x - offset * s.parallax)
            if 0 <= dx < Config.SCREEN_SIZE:
                if s.twinkle:
                    phase = math.sin((2 * math.pi / s.twinkle_rate) * elapsed)
                    if phase < 0:
                        continue
                pygame.draw.circle(screen, s.color, (dx, s.y), s.size)
