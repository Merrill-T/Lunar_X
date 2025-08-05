from __future__ import annotations

import sys
import pygame
import math

from config import Config
from assets.gfx_assets import GfxAssets
from assets.audio_assets import AudioAssets
from systems.render import RenderSystem
from systems.audio import SoundManager
from systems.physics import compute_altitude
from entities.lander import Lander
from world.terrain import Terrain
from world.starfield import Starfield
from world.rock_manager import RockManager
from systems.ui import HUD


def main() -> None:
    # ------------------- Init -------------------
    pygame.init()
    pygame.font.init()

    screen = pygame.display.set_mode((Config.SCREEN_SIZE, Config.SCREEN_SIZE))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(Config.FONT_NAME, Config.FONT_SIZE)

    # Assets / systems
    gfx_assets = GfxAssets()
    audio_assets = AudioAssets()
    renderer = RenderSystem(screen)
    sound_mgr = SoundManager(audio_assets)

    exit_program = False
    while not exit_program:
        # --- Main Menu ---
        difficulty_levels = ["Easy", "Medium", "Hard"]
        selected_diff = 1
        btn_w, btn_h = 120, 40
        spacing = 20
        cx = Config.SCREEN_SIZE // 2
        cy = Config.SCREEN_SIZE // 2

        diff_y = cy - 40
        diff_btns = [pygame.Rect(cx - (btn_w*3 + spacing*2)//2 + i*(btn_w+spacing), diff_y, btn_w, btn_h)
                     for i in range(3)]
        start_btn = pygame.Rect(cx - btn_w//2, cy + 60, btn_w, btn_h)
        quit_btn  = pygame.Rect(cx - btn_w//2, cy + 120, btn_w, btn_h)

        in_menu = True
        while in_menu:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    in_menu = False
                    exit_program = True
                elif e.type == pygame.MOUSEBUTTONDOWN:
                    if start_btn.collidepoint(e.pos):
                        in_menu = False
                    elif quit_btn.collidepoint(e.pos):
                        in_menu = False
                        exit_program = True
                    else:
                        for idx, btn in enumerate(diff_btns):
                            if btn.collidepoint(e.pos):
                                selected_diff = idx

            screen.fill((0, 0, 0))
            # Title
            title_surf = font.render("LUNAR LANDER", True, (255, 255, 255))
            screen.blit(title_surf, title_surf.get_rect(center=(cx, cy - 150)))
            # Difficulty
            diff_label = font.render(f"Difficulty: {difficulty_levels[selected_diff]}", True, (255, 255, 255))
            screen.blit(diff_label, diff_label.get_rect(center=(cx, diff_y - 40)))
            for idx, btn in enumerate(diff_btns):
                color = (200, 200, 50) if idx == selected_diff else (100, 100, 100)
                pygame.draw.rect(screen, color, btn)
                text = font.render(difficulty_levels[idx], True, (0, 0, 0))
                screen.blit(text, text.get_rect(center=btn.center))
            renderer.draw_button(start_btn, "START", font)
            renderer.draw_button(quit_btn,  "QUIT",  font)

            pygame.display.flip()
            clock.tick(30)

        if exit_program:
            break

        # --- Apply Difficulty Modifiers ---
        diff = difficulty_levels[selected_diff]
        if diff == "Easy":
            Config.FUEL_START *= 1.75
            Config.LANDER_VX_ENTRY *= 0.5
            Config.LAND_DAMAGE_SPEED *= 1.25
            Config.MAX_LANDING_ANGLE *= 1.5
            Config.ENGINE_STARTUP_LIMIT *= 10
        elif diff == "Hard":
            Config.FUEL_START         = 1100
            Config.ANGULAR_INERTIA    = 2
            Config.ROTATION_TORQUE    = 300
            Config.LANDER_VX_ENTRY    = 15
            Config.ENGINE_STARTUP_LIMIT = 3
            Config.TIME_SCALE         = 1.75
            Config.MAX_LANDING_SPEED  = 2.0
            Config.MAX_LANDING_ANGLE  = 15.0
            Config.ROCK_DAMAGE_SPEED  = 2.0
            Config.LAND_DAMAGE_SPEED  = 5.0
            Config.OXYGEN_DRAIN_RATE  = 1.75
            Config.BATTERY_DRAIN_RATE = 15
            Config.APU_FUEL_RATE      = 10.0
            Config.APU_RECHARGE_RATE  = 10.0
            Config.lander_angular_velocity = -75

        # ------------------- Game Setup -------------------

        starfield = Starfield(Config.STAR_COUNT)
        terrain   = Terrain()
        print("terrain.rocks: ", terrain.rocks)
        rocks     = RockManager(gfx_assets, terrain, Lander)
        lander    = Lander(gfx_assets)
        hud       = HUD(font)

        terrain.generate()
        rocks.reset()
        print("terrain.rocks: ", terrain.rocks)
        lander.reset()
        sound_mgr.start_random_beeps()

        start_time = pygame.time.get_ticks()
        crash_played = False

        # Buttons for pause/crash/landed screens
        reset_btn = pygame.Rect(cx - 50, cy + 60, 100, 30)
        new_btn   = pygame.Rect(cx - 50, cy + 100,100, 30)
        cont_btn  = pygame.Rect(cx - 50, cy + 140,100, 30)

        running = True
        while running:
            dt = clock.tick(30) / 1000.0
            elapsed = (pygame.time.get_ticks() - start_time) / 1000.0

            # --- Event Handling ---
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                # Pause menu via ESC
                elif e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE and not (lander.crashed or lander.landed):
                    paused = True
                    while paused:
                        for ev in pygame.event.get():
                            if ev.type == pygame.QUIT:
                                pygame.quit()
                                sys.exit()
                            elif ev.type == pygame.MOUSEBUTTONDOWN:
                                if reset_btn.collidepoint(ev.pos):
                                    # terrain.generate(); rocks.reset();
                                    lander.reset()
                                    start_time = pygame.time.get_ticks(); crash_played = False
                                    paused = False
                                elif new_btn.collidepoint(ev.pos):
                                    running = False; paused = False
                                elif cont_btn.collidepoint(ev.pos):
                                    paused = False
                        # Draw pause overlay
                        renderer.begin_frame()
                        renderer.draw_world(terrain, starfield, 0, elapsed)
                        paused_txt = font.render("PAUSED", True, (255,255,255))
                        screen.blit(paused_txt, paused_txt.get_rect(center=(cx, cy-100)))
                        renderer.draw_button(reset_btn, "RESET", font)
                        renderer.draw_button(new_btn,   "NEW GAME", font)
                        renderer.draw_button(cont_btn,  "CONTINUE", font)
                        renderer.end_frame()
                        clock.tick(30)
                    continue

                # Handle clicks on end-state buttons
                if (lander.crashed or lander.landed) and e.type == pygame.MOUSEBUTTONDOWN:
                    if reset_btn.collidepoint(e.pos):
                        # terrain.generate(); rocks.reset();
                        lander.reset()
                        start_time = pygame.time.get_ticks()
                        crash_played = False
                    elif new_btn.collidepoint(e.pos):
                        running = False
                    elif lander.landed and cont_btn.collidepoint(e.pos):
                        # resume play
                        paused = False


                sound_mgr.handle_event(e, lander)

            if not running:
                break

            # --- Simulation ---
            keys = pygame.key.get_pressed()
            sound_mgr.update_engine(lander, keys)
            #lander.control_system(dt)
            lander.update_physics(keys, dt, terrain)

            offset = compute_camera_offset(lander.x, Config)

            # --- Rendering ---
            renderer.begin_frame()
            renderer.draw_world(terrain, starfield, offset, elapsed)
            surf, rect = renderer.draw_entity(lander, offset)
            hit1, hit2 = rocks.draw_and_check(renderer.screen, offset, surf, rect.topleft)
            if not (lander.landed or lander.crashed):
                lander.collision_check(screen, keys, terrain, offset, hit2)

            alt, _ = lander.get_surface_altitude(terrain, offset, 0)
            altitude_at_offset, reading_coords = lander.get_surface_altitude(terrain, offset, 100)  # altitude under base
            #pygame.draw.circle(screen, (255, 0, 0), reading_coords, 4)
            rocks_x = lander.detect_rocks(terrain.rocks, offset)
            nearest = lander.nearest_rock(terrain.rocks)
            if nearest:
                rock_x_world = nearest.get('x', 0)
                rock_y = nearest.get('y', 0)

                # Adjust for scroll/camera offset (same as used in `draw_and_check`)
                rock_x_screen = rock_x_world - offset  # or whatever variable you use for horizontal scroll
                rock_coords = (int(rock_x_screen), int(rock_y))

                pygame.draw.circle(screen, (255, 0, 0), rock_coords, 4)
                # print("Nearest rock info:", nearest)


            msg = determine_status(lander, alt, sound_mgr)
            renderer.draw_hud(
                hud,
                fuel=lander.fuel,
                vx=lander.vx,
                vy=lander.vy,
                angle=lander.angle,
                alt=alt,
                elapsed=elapsed,
                status=msg,
                science=lander.science,
                oxygen=lander.oxygen,
                battery=lander.battery,
                temperature=lander.temperature,
                damage=lander.damage,
                throttle=lander.throttle,
                apu_on=lander.apu_on,
                report=lander.report,
            )

            # Crash end-state
            if lander.crashed:
                sound_mgr.stop("warning_beep")
                if not crash_played:
                    sound_mgr.stop_all
                    sound_mgr.play("crash", once_until_done=True, volume=0.25)
                    crash_played = True
                lander.tick_crash_anim()
                renderer.draw_crash(lander, offset)
                renderer.draw_button(reset_btn, "RESET", font)
                renderer.draw_button(new_btn,   "NEW GAME", font)
                # no continue on crash
                renderer.end_frame()
                continue

            # Landed end-state
            if lander.landed:
                """                renderer.draw_button(reset_btn, "RESET", font)
                                renderer.draw_button(new_btn,   "NEW GAME", font)
                                renderer.end_frame()
                                continue"""
                pass

            renderer.end_frame()

    pygame.quit()


def compute_camera_offset(x: float, cfg: Config) -> float:
    off = x - cfg.SCREEN_SIZE // 2
    return max(0, min(off, cfg.TERRAIN_LENGTH - cfg.SCREEN_SIZE))


def determine_status(lander: Lander, alt_m: float, sound_mgr: SoundManager) -> str:
    status_msg = ""
    # ... replicate your status logic here ...
          # ------------- Status & Warnings -------------
    status_msg = ""
    if lander.landed:
        sound_mgr.stop("warning_beep")
        status_msg = "LANDED SUCCESSFULLY!"
        low_alt_warned = False
    elif lander.crashed:
        status_msg = "*** CRASHED ***"
    else:
        # Low fuel
        if lander.fuel < 200 and not lander.crashed:
            low_fuel_warned = True
            sound_mgr.play(
                "warning_beep",
                once_until_done=True,
                cooldown_ms=2000
            )
            status_msg = "**WARNING**: LOW FUEL!"
        else:
            sound_mgr.stop("warning_beep")
            low_fuel_warned = False

        # Braking distance
        mass    = Config.DRY_MASS + lander.fuel
        max_acc = (Config.MAX_THRUST / mass) - Config.G0_MOON
        stop_dist = (
            float('inf') if max_acc <= 0
            else (lander.vy ** 2) / (2 * max_acc)
        )
        buffer = 5.0

        if alt_m > buffer and alt_m <= stop_dist + buffer and lander.vy > 0:
            sound_mgr.play("caution_beep", once_until_done=True, volume=0.75)
            status_msg = "**WARNING**: BRAKING DISTANCE!"

        # Low altitude
        if alt_m < 5 and not lander.landed and lander.vy > 2:
            status_msg = "**WARNING**: LOW ALT!"

        # Structure damage
        if lander.damage > 75:
            status_msg = "**WARNING**: STRUCTURAL DAMAGE!"

        if lander.engine_out:
            status_msg = "**WARNING**: ENGINE OUT!"

        # Rock collection
        if lander.landed and special_hit and not lander.crashed:
            status_msg = "COLLECTED COOL ROCK!!"
    return status_msg


if __name__ == "__main__":
    main()
