#rock_manager.py

import pygame
from random import randint, choice
from typing import List, Tuple
from config import Config


class RockManager:
    """Holds different rock types and handles drawing / collision flags."""
    def __init__(self, assets: "GfxAssets", terrain: "Terrain") -> None:
        self.assets = assets
        self.terrain = terrain
        self.topo: List[int] = []
        self.terrain_mask: pygame.Mask | None = None
        self.neutral: List[Tuple[int, int, pygame.Surface]] = []
        self.rocks:  List[Tuple[int, int, pygame.Surface]] = []
        self.special: List[Tuple[int, int, pygame.Surface]] = []


    def reset(self) -> None:
        """Regenerate rock placements based on the current terrain."""
        self.topo = self.terrain.topo
        self.terrain_mask = self.terrain.mask
        self.neutral = [self._make_rock(self.assets.neutral_rock_sprites) for _ in range(400)]
        self.special = [self._make_rock(self.assets.special_rock_sprites) for _ in range(2)]
        self.rocks = [self._make_rock(self.assets.rock_sprites) for _ in range(50)]
        
        
    def pixel_collision(self, surf1: pygame.Surface, pos1: Tuple[int, int],
                    surf2: pygame.Surface, pos2: Tuple[int, int]) -> bool:
        """Return True if two surfaces overlap using pixel-perfect masks."""
        mask1 = pygame.mask.from_surface(surf1)
        mask2 = pygame.mask.from_surface(surf2)
        offset = (int(pos2[0] - pos1[0]), int(pos2[1] - pos1[1]))
        return mask1.overlap(mask2, offset) is not None

    def _make_rock(self, sprite_list: List[pygame.Surface]) -> Tuple[int, int, pygame.Surface]:
        """Place a rock so it rests 'on' the terrain using mask overlap."""
        rx = randint(0, Config.TERRAIN_LENGTH - Config.PIXEL_SIZE * 2)
        sprite = choice(sprite_list)
        img = sprite.copy()
        rock_mask = pygame.mask.from_surface(img)

        # Drop rock until it hits terrain
        for ry in range(Config.SCREEN_SIZE):
            if self.terrain_mask and self.terrain_mask.overlap(rock_mask, (rx, ry)):
                ry += randint(1, 50)
                break
        else:
            ry = Config.SCREEN_SIZE - img.get_height()

        ry = max(0, min(ry, Config.SCREEN_SIZE - img.get_height()))
        return rx, ry, img

    def draw_and_check(self,
                       screen: pygame.Surface,
                       offset: float,
                       lander_img: pygame.Surface,
                       lander_pos: Tuple[int, int]) -> Tuple[bool, bool]:
        """Draw rocks and report if the lander hit any (rock_hit, special_hit)."""
        rock_hit = False
        special_hit = False

        def draw_and_test(bucket: List[Tuple[int, int, pygame.Surface]], set_flag: str) -> None:
            nonlocal rock_hit, special_hit
            for rx, ry, img in bucket:
                dx = rx - offset
                if -img.get_width() <= dx <= Config.SCREEN_SIZE:
                    screen.blit(img, (dx, ry))
                    if self.pixel_collision(lander_img, lander_pos, img, (dx, ry)):
                        if set_flag == "rock":
                            rock_hit = True
                        else:
                            special_hit = True


        for rx, ry, img in self.neutral:
            dx = rx - offset
            if -img.get_width() <= dx <= Config.SCREEN_SIZE:
                screen.blit(img, (dx, ry))
                
        draw_and_test(self.special, "special")   
        draw_and_test(self.rocks, "rock")
        
        # neutral rocks are non-collidable (visual only)

        return rock_hit, special_hit
