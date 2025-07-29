import pygame
from config import Config
from typing import List, Tuple

class HUD:
    """Heads-up display for telemetry, systems, and messages."""
    def __init__(self, font: pygame.font.Font) -> None:
        self.font = font

    def draw(self,
             screen: pygame.Surface,
             fuel: float, vx: float, vy: float, angle: float, alt: float, elapsed: float,
             status: str, science: float,
             oxygen: float, battery: float, temperature: float,
             damage: float, gforce: float, apu_on: bool,
             report: dict | None = None) -> None:
        panel = pygame.Surface((Config.SCREEN_SIZE, Config.HUD_PANEL_HEIGHT), pygame.SRCALPHA)
        panel.fill((0, 0, 0, Config.HUD_BG_ALPHA))
        screen.blit(panel, (0, 0))

        def lbl(txt: str, x: int, y: int, c: Tuple[int, int, int] = Config.HUD_COLOR) -> None:
            surf = self.font.render(txt, True, c)
            screen.blit(surf, (x, y))

        # Telemetry
        lbl("---- TELEMETRY -----", 10, 10)
        lbl(f"ALT  {alt:>5.0f} m", 10, 30)
        lbl(f"VS   {vy:+5.1f} m/s", 10, 50)
        lbl(f"HS   {vx:+5.1f} m/s", 10, 70)
        lbl(f"ATT  {angle:>5.1f}°", 200, 30)
        lbl(f"G_load   {gforce:>5.2f}g", 200, 50)
        lbl(f"FUEL {fuel:+5.1f}", 200, 70)
        lbl(f"T+   {elapsed:06.1f}s", Config.SCREEN_SIZE - 150, 10)

        # Systems
        base_y = 100
        lbl("---- SYSTEMS -----", 10, base_y)
        lbl(f"SCI   {science:>5.1f}a", 200, base_y + 20)
        lbl(f"OXY   {oxygen:>5.1f}%", 10, base_y + 20)
        lbl(f"BATT  {battery:>5.1f}%", 10, base_y + 40)
        lbl(f"TEMP  {temperature:>5.1f}°C", 10, base_y + 60)
        lbl(f"DMG   {damage:>5.1f}%", 10, base_y + 80)
        lbl(f"APU   {'ON' if apu_on else 'OFF'}", 10, base_y + 120, Config.YELLOW)

        # Status / Reports
        lbl("---- STATUS MSG -----", Config.SCREEN_SIZE - 250, 30)
        y = 50
        if status:
            lbl(status, Config.SCREEN_SIZE - 250, y, Config.RED)
            y += 20
        if report:
            for k, v in report.items():
                lbl(f"{k}: {v}", Config.SCREEN_SIZE - 250, y, Config.RED if k == "reason" else Config.HUD_COLOR)
                y += 20

