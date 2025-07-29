# render.py
from __future__ import annotations
import pygame
from typing import Tuple
from config import Config

class RenderSystem:
    """All screen drawing. Keeps order: background → world → entities → UI."""

    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen

    # ----- Frame control ----------------------------------------------------
    def begin_frame(self) -> None:
        self.screen.fill(Config.BLACK)

    def end_frame(self) -> None:
        pygame.display.flip()

    # ----- World ------------------------------------------------------------
    def draw_world(self, terrain, starfield, offset: float, elapsed: float) -> None:
        starfield.draw(self.screen, offset, elapsed)
        self.screen.blit(terrain.surface, (-offset, 0))

    # ----- Entities ---------------------------------------------------------
    def draw_entity(self, entity, offset: float) -> Tuple[pygame.Surface, pygame.Rect]:
        """Return the rotated collision sprite and rect (for collisions)."""
        return entity.draw(self.screen, offset)

    def draw_crash(self, lander, offset: float) -> None:
        """If the lander crashed, draw its crash animation frame."""
        lander.draw_crash(self.screen, offset)

    # ----- UI ---------------------------------------------------------------
    def draw_hud(self, hud, **data) -> None:
        hud.draw(self.screen, **data)

    def draw_button(self, rect: pygame.Rect, text: str, font: pygame.font.Font) -> None:
        pygame.draw.rect(self.screen, Config.WHITE, rect, border_radius=5)
        lbl = font.render(text, True, Config.BLACK)
        self.screen.blit(lbl, (rect.x + (rect.w - lbl.get_width()) // 2,
                               rect.y + (rect.h - lbl.get_height()) // 2))
