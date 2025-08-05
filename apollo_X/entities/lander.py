import math
import pygame
from typing import Optional, List, Dict, Tuple, Any
from config import Config


def _angle_diff(target: float, source: float) -> float:
    """Minimal signed difference in degrees between target and source (−180, +180]."""
    return (target - source + 180) % 360 - 180


class SurfaceSensor:
    """Sensor that measures vertical altitude from the lander base to terrain at arbitrary x."""

    def __init__(self, lander: "Lander"):
        self.lander = lander

    def _terrain_height_at(self, terrain: Any, x_world: float) -> float:
        """Return interpolated terrain surface y (screen coords) at given world x."""
        # Map world x to topo index (integer) with linear interpolation
        pix_per_step = Config.PIXEL_SIZE
        idx_float = x_world / pix_per_step
        left_i = int(math.floor(idx_float))
        right_i = int(math.ceil(idx_float))

        topo = terrain.topo
        max_i = len(topo) - 1
        left_i_clamped = max(0, min(left_i, max_i))
        right_i_clamped = max(0, min(right_i, max_i))

        y_left = topo[left_i_clamped]
        y_right = topo[right_i_clamped]
        if left_i_clamped == right_i_clamped:
            return y_left
        t = idx_float - left_i_clamped
        return y_left * (1 - t) + y_right * t

    def altitude_at(self, terrain: Any, offset: float, reading_offset: float) -> float:
        """
        Returns altitude in meters from the lander base to the terrain surface at x_world.
        If x_world is None, uses the lander base x coordinate.
        Positive means surface is below the base.
        """
        if reading_offset is None:
            base_x, _ = self.lander.base_coords
            reading_offset = base_x

        base_x, base_y = self.lander.base_coords  # screen coords
        surface_y = self._terrain_height_at(terrain, base_x + reading_offset)

        reading_coords = (base_x - offset + reading_offset, surface_y)

        # y increases downward; surface below base means surface_y > base_y
        altitude_pixels = surface_y - base_y
        return altitude_pixels / self.lander.px_per_m , reading_coords  # in meters


class RockSensor:
    """Sensor for detecting rocks near a given x coordinate."""

    def __init__(self, lander: "Lander"):
        self.lander = lander

    def _to_pixels(self, radius_m: float) -> float:
        return radius_m * self.lander.px_per_m

    def rocks_near_x(
        self,
        rocks: Any,
        x_world: Optional[float] = None,
        horizontal_tol_m: float = 5.0
    ) -> List[Dict]:
        """
        Returns a list of rocks whose horizontal region overlaps x_world within horizontal_tol_m.
        Adds 'distance_m' (horizontal) to each returned rock.
        """
        if rocks is None:
            return []

        if x_world is None:
            base_x, _ = self.lander.base_coords
            x_world = base_x

        tol_pixels = horizontal_tol_m * self.lander.px_per_m
        found = []
        for rock in rocks:
            rock_x = rock.get('x', 0)
            if rock_x is None:
                continue
            # Determine effective horizontal radius in pixels
            if "radius_m" in rock:
                radius_px = self._to_pixels(rock["radius_m"])
            else:
                radius_px = rock.get("radius", 0)

            dx = abs(rock_x - x_world)
            if dx <= radius_px + tol_pixels:
                # Compute straight-line distance from lander base to rock center
                _, base_y = self.lander.base_coords
                rock_y = rock.get("y", 0)
                dy = rock_y - base_y
                dist_pixels = math.hypot(dx, dy)
                dist_m = dist_pixels / self.lander.px_per_m
                rock_info = dict(rock)  # shallow copy to avoid mutating original
                rock_info["distance_m"] = dist_m
                found.append(rock_info)
        return found

    def nearest_rock(
        self,
        rocks: Any,
        x_world: Optional[float] = None,
        max_distance_m: float = 50.0
    ) -> Optional[Dict]:
        """
        Returns the nearest rock (with distance) near x_world within max_distance_m, or None.
        """
        rocks = self.rocks_near_x(rocks, x_world, horizontal_tol_m=max_distance_m)
        if not rocks:
            return None
        # Pick rock with smallest distance
        nearest = min(rocks, key=lambda r: r.get("distance_m", float("inf")))
        if nearest.get("distance_m", float("inf")) <= max_distance_m:
            return nearest
        return None

    def rock_in_path(
        self,
        rocks: Any,
        x_world: Optional[float] = None,
        max_distance_m: float = 50.0
    ) -> bool:
        """Convenience boolean: is there any rock near x_world within max_distance_m?"""
        return self.nearest_rock(rocks, x_world, max_distance_m) is not None


class LanderSensors:
    def __init__(self, lander: "Lander"):
        self.surface = SurfaceSensor(lander)
        self.rock = RockSensor(lander)


class Lander:
    """Lander state, physics, draw helpers with smooth settlement on touchdown."""

    def __init__(self, gfx_assets):
        # Graphics & scaling
        self.img = gfx_assets.lander
        self.thruster = gfx_assets.thruster
        self.crash_frames = gfx_assets.crash_frames
        self.px_per_m = self.img.get_height() / Config.LANDER_HEIGHT_M

        # Fixed pivot in the original image: bottom-center pixel
        w, h = self.img.get_width(), self.img.get_height()

        # World coordinate of that pivot once landed
        self._gravity_center = None
        self._contact_screen = None
        self._contact_slope = None

        self.sensors = LanderSensors(self)

        self.reset()

    # ----------------- Convenience Properties -----------------

    @property
    def mass(self) -> float:
        return Config.DRY_MASS + self.fuel

    @property
    def base_coords(self) -> Tuple[float, float]:
        """
        Returns bottom-center of the lander in world coordinates (x, y).
        """

        base_x = self.x + self.img.get_width() / 2
        base_y = self.y + self.img.get_height() - 29
        return base_x, base_y

    # -------------- Public Sensor Accessors (for convenience) -------------

    def get_surface_altitude(self, rocks: Any, offset: float, reading_offset: float) -> float:
        return self.sensors.surface.altitude_at(rocks, offset, reading_offset)

    def detect_rocks(self, rocks: Any, x_world: Optional[float] = None, horizontal_tol_m: float = 5.0) -> List[Dict]:
        return self.sensors.rock.rocks_near_x(rocks, x_world, horizontal_tol_m)

    def nearest_rock(self, rocks: Any, x_world: Optional[float] = None, max_distance_m: float = 50.0) -> Optional[Dict]:
        return self.sensors.rock.nearest_rock(rocks, x_world, max_distance_m)

    def rock_in_path(self, rocks: Any, x_world: Optional[float] = None, max_distance_m: float = 50.0) -> bool:
        return self.sensors.rock.rock_in_path(rocks, x_world, max_distance_m)

    # --------------------------------------------------------------------

    def reset(self):
        # Position & motion
        self.x = Config.SCREEN_SIZE // 2
        self.y = Config.SCREEN_SIZE // 4
        self.world_x = None
        self.world_y = None
        self.vx = Config.LANDER_VX_ENTRY
        self.vy = 0.0
        self.ax = self.ay = 0.0
        self.angle = 0.0
        self.angular_velocity = Config.lander_angular_velocity

        # Resources & status
        self.fuel = Config.FUEL_START
        self.oxygen = Config.MAX_OXYGEN
        self.battery = Config.MAX_BATTERY
        self.temperature = 20.0
        self.damage = 0.0
        self.gforce = 0.0
        self.apu_on = False
        self.engine_startup_count = 0
        self.engine_out = False
        self.engine_on = False
        self.throttle = 1.0

        # Flags & reporting
        self.crashed = False
        self.landed = False
        self.crash_anim = False
        self.crash_index = 0
        self.crash_timer = 0
        self.report = None
        self.science = 0

        # Clear settlement pivot
        self._gravity_center = (
            int(self.x + self.img.get_width() / 2),
            int(self.y + self.img.get_height() / 2)
        )
        self._contact_screen = None
        self._contact_slope = None

    def compute_surface_slope(self, terrain: Any) -> float:
        """Slope (degrees) under lander's center: positive means ground rises to the left."""
        centre = int((self.x + self.img.get_width() / 2) // Config.PIXEL_SIZE)
        half = 5
        left_i = max(0, centre - half)
        right_i = min(len(terrain.topo) - 1, centre + half)
        y_left = terrain.topo[left_i]
        y_right = terrain.topo[right_i]
        dx = (right_i - left_i) * Config.PIXEL_SIZE
        dy = (y_left - y_right)
        return math.degrees(math.atan2(dy, dx))

    def update_physics(self, keys: pygame.key.ScancodeWrapper, dt: float, terrain: Any) -> None:
        """
        Update the lander’s physics each frame: time scaling, life-support drains,
        power/APU recharge, rotational dynamics with torque/inertia, flight or landed dynamics.
        """
        # 1) Scale simulation time
        dt_sim = dt * Config.TIME_SCALE

        # 2) Abort early if crashed
        if self.crashed:
            return

        # ---------------- Life-support & power ----------------
        self.oxygen = max(self.oxygen - Config.OXYGEN_DRAIN_RATE * dt_sim, 0.0)
        self.battery = max(self.battery - Config.BATTERY_DRAIN_RATE * dt_sim, 0.0)
        if self.battery <= 0 and not self.apu_on:
            self.apu_on = True
        elif self.battery >= 50 and self.apu_on:
            self.apu_on = False

        if self.apu_on and self.battery < Config.MAX_BATTERY:
            fuel_used = Config.APU_FUEL_RATE * dt_sim
            self.fuel = max(self.fuel - fuel_used, 0.0)
            self.battery = min(self.battery + Config.APU_RECHARGE_RATE * dt_sim, Config.MAX_BATTERY)

        has_power = (self.battery > 0.0)

        # ---------------- Rotational dynamics ----------------
        if has_power and not self.landed:
            net_torque = 0.0
            if keys[pygame.K_LEFT]:
                net_torque += Config.ROTATION_TORQUE
            if keys[pygame.K_RIGHT]:
                net_torque -= Config.ROTATION_TORQUE
            angular_accel = net_torque / Config.ANGULAR_INERTIA
            self.angular_velocity += angular_accel * dt_sim

        self.angle = (self.angle + self.angular_velocity * dt_sim) % 360

        # ---------------- Translational (flight) vs landed ----------------
        if not self._contact_screen and not self.landed:
            # 6a) Compute accelerations
            ax = 0.0
            ay = Config.G0_MOON  # lunar gravity

            # Throttle selection overrides
            if keys[pygame.K_1]:
                self.throttle = 1.0
            elif keys[pygame.K_2]:
                self.throttle = 0.5
            elif keys[pygame.K_3]:
                self.throttle = 0.33

            if keys[pygame.K_UP] and self.fuel > 0 and not self.engine_out:
                if not self.engine_on and not self.engine_out:
                    self.engine_startup_count += 1
                    if self.engine_startup_count >= Config.ENGINE_STARTUP_LIMIT:
                        self.report = {
                            "ENGINE FAILURE": "START_UP",
                        }
                        self.engine_out = True
                        self.engine_on = False
                    else:
                        self.engine_on = True
                thrust = Config.MAX_THRUST * self.throttle
                mflow = thrust / (Config.ISP * Config.G0_MOON)
                fuel_used = mflow * dt_sim * self.throttle
                self.fuel = max(self.fuel - fuel_used, 0.0)
                rad = math.radians(self.angle)
                ax += (thrust / self.mass) * -math.sin(rad)
                ay += (thrust / self.mass) * -math.cos(rad)
            elif self.fuel <= 0:
                self.engine_out = True
                self.engine_on = False
            else:
                self.engine_on = False

            # 6b) Integrate translational motion
            self.ax, self.ay = ax, ay
            self.vx += ax * dt_sim
            self.vy += ay * dt_sim
            self.gforce = math.hypot(ax, ay) / 9.81
            self.x += self.vx * dt_sim * self.px_per_m
            self.y += self.vy * dt_sim * self.px_per_m

            # Temperature rise from G-forces
            self.temperature = min(
                self.temperature + 0.01 * self.gforce * dt_sim,
                Config.MAX_TEMPERATURE
            )
        elif self._contact_screen and not self.crashed:
            # Landed: pivot/settle on slope or allow lift-off
            target_slope = self.compute_surface_slope(terrain)
            rotation_step = Config.ROTATION_SPEED * dt_sim
            angle_diff = _angle_diff(target_slope, self.angle)
            self.angular_velocity = 0.0

            # Possible lift-off thrust from landed state
            self.engine_on = False
            ax = ay = 0.0
            self.ax, self.ay = ax, ay

            if keys[pygame.K_UP] and self.fuel > 0 and not self.engine_out:
                self.engine_on = True
                self.landed = False
                thrust = Config.MAX_THRUST * self.throttle
                mflow = thrust / (Config.ISP * Config.G0_MOON)
                fuel_used = mflow * dt_sim * self.throttle
                self.fuel = max(self.fuel - fuel_used, 0.0)
                rad = math.radians(self.angle)
                ax += (thrust / self.mass) * -math.sin(rad)
                ay += (thrust / self.mass) * -math.cos(rad)
                # 6b) Integrate translational motion
                self.ax, self.ay = ax, ay
                self.vx += ax * dt_sim
                self.vy += -abs(ay * dt_sim)
                self.gforce = math.hypot(ax, ay) / 9.81
                self.x += self.vx * dt_sim * self.px_per_m
                self.y += self.vy * dt_sim * self.px_per_m
            elif abs(angle_diff) >= rotation_step:
                # --- pivot physics around contact point ---
                pivot_x, pivot_y = self._contact_screen
                cg_x, cg_y = self._gravity_center

                # Lever arm vector (meters)
                dx0 = (cg_x - pivot_x) / self.px_per_m
                dy0 = (cg_y - pivot_y) / self.px_per_m
                arm0 = math.atan2(dy0, dx0)

                # Tangential unit vector and gravity projection
                R = math.hypot(dx0, dy0)
                tx, ty = -dy0 / R, dx0 / R
                g = Config.G0_MOON
                tang_acc = g * ty * 2
                ax = tang_acc * tx
                ay = tang_acc * ty

                # Integrate pivot motion
                self.ax, self.ay = ax, ay
                self.vx += ax * dt_sim
                self.vy += ay * dt_sim
                self.x += self.vx * dt_sim * self.px_per_m
                self.y += self.vy * dt_sim * self.px_per_m

                # Compute new lever-arm angle
                cg2_x = cg_x + self.vx * dt_sim * self.px_per_m
                cg2_y = cg_y + self.vy * dt_sim * self.px_per_m
                dx1 = (cg2_x - pivot_x) / self.px_per_m
                dy1 = (cg2_y - pivot_y) / self.px_per_m
                arm1 = math.atan2(dy1, dx1)

                # How much the sprite actually rotated around pivot
                delta_arm = (math.degrees(arm1 - arm0) + 180) % 360 - 180
                self.angle = (self.angle - delta_arm) % 360

            else:
                self.ax = self.ay = 0.0
                self.vx = self.vy = 0.0
                self.angle = target_slope % 360
                self.landed = True

    def detect_rock_collision(self, terrain, screen, offset_x: float) -> Optional[Dict]:
        """
        Pixel-perfect test: returns the first rock the lander is colliding with, or None.
        Use its presence to set rock_hit in collision_check.
        """

        if not hasattr(terrain, "rocks") or terrain.rocks is None:
            return None

        rocks = terrain.rocks

        # Current rotated lander and its mask
        rotated_img = pygame.transform.rotate(self.img, self.angle)
        ship_mask = pygame.mask.from_surface(rotated_img)

        # Compute top-left of rotated sprite on the screen (NOT world coordinates)
        cx_center = self.x + self.img.get_width() / 2
        cy_center = self.y + self.img.get_height() / 2
        screen_center_x = self.x - offset_x + self.img.get_width() / 2
        screen_center_y = self.y + self.img.get_height() / 2
        lander_rect = rotated_img.get_rect(center=(int(screen_center_x), int(screen_center_y)))

        #lander_rect = rotated_img.get_rect(center=(int(cx_center), int(cy_center)))
        lander_topleft_screen = lander_rect.topleft

        for rock in rocks:
            rx = rock.get("x")
            ry = rock.get("y")

            if rx is None or ry is None:
                continue

            # Determine rock radius in pixels
            if "radius_m" in rock:
                radius_px = rock["radius_m"] * self.px_per_m * 0.6
            else:
                radius_px = rock.get("radius", 0)* 0.6
            if radius_px <= 0:
                continue

            # Step 1: Get visual rock center (you already fixed this part)
            img = rock.get("surface")
            rx = rock.get("x")
            ry = rock.get("y")
            rock_cx = rx + img.get_width() / 2
            rock_cy = ry + img.get_height() / 2 + radius_px*0.25

            # Step 2: Convert to screen position
            rock_screen_x = rock_cx - offset_x
            rock_screen_y = rock_cy

            # Step 3: Rock mask top-left
            rock_rect_left = rock_screen_x - radius_px
            rock_rect_top = rock_screen_y - radius_px

            # Step 4: Compute mask-space offset for collision check
            offset_mask = (
                int(rock_rect_left - lander_topleft_screen[0]),
                int(rock_rect_top - lander_topleft_screen[1]),
            )

            # Create circular rock surface centered at (rx, ry)
            size = int(math.ceil(radius_px * 2)) + 2
            rock_surf = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.circle(
                rock_surf,
                (255, 255, 255, 255),
                (size // 2, size // 2),
                int(radius_px),
            )
            rock_mask = pygame.mask.from_surface(rock_surf)

            # Size of the debug circle surface
            size = int(math.ceil(radius_px * 2)) + 2

            # Draw debug circle centered on (rock_screen_x, rock_screen_y)
            debug_circle = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.circle(
                debug_circle,
                (255, 0, 0, 100),  # semi-transparent red
                (size // 2, size // 2),
                int(radius_px),
            )

            # Top-left for blitting
            screen_pos = (
                int(rock_screen_x - size / 2),
                int(rock_screen_y - size / 2)
            )

            screen.blit(debug_circle, screen_pos)

            if ship_mask.overlap(rock_mask, offset_mask):
                # Collision: return a copy with distance for convenience
                base_x, base_y = self.base_coords
                dx = rx - base_x
                dy = ry - base_y
                dist_m = math.hypot(dx, dy) / self.px_per_m
                rock_info = dict(rock)
                rock_info["distance_m"] = dist_m
                return rock_info

        return None



    def collision_check(self, screen, keys: Any, terrain: Any, offset_x: float, special_hit: bool) -> None:
        """
        Check for collisions with the terrain, handle landing/takeoff,
        crashes, and rock sampling.
        """
        rock_hit = self.detect_rock_collision(terrain, screen, offset_x)
        if rock_hit:
            self._crash("CRASHED INTO ROCKS")
            print(rock_hit)
            return

        orig_vy = self.vy
        abs_vy = abs(orig_vy)
        vel_abs = math.hypot(self.vy, self.vx)
        slope = self.compute_surface_slope(terrain)
        self._contact_slope = slope

        # Rotate sprite and build masks
        rotated_img = pygame.transform.rotate(self.img, self.angle)
        ship_mask = pygame.mask.from_surface(rotated_img)
        terrain_mask = terrain.mask

        # Compute world‐coords of the rotated sprite’s topleft
        cx_center = self.x - offset_x + self.img.get_width() / 2
        cy_center = self.y + self.img.get_height() / 2
        rect = rotated_img.get_rect(center=(int(cx_center), int(cy_center)))
        self.world_x = rect.left + offset_x
        self.world_y = rect.top

        # Pixel-perfect overlap?
        contact = ship_mask.overlap(terrain_mask, (-self.world_x, -self.world_y))
        if not contact:
            if self._contact_screen and keys[pygame.K_UP]:
                self._contact_screen = None
            return
        elif not self._contact_screen and contact:
            cx_mask, cy_mask = contact
            # Record on-screen contact point
            screen_x = int((self.world_x - offset_x) + cx_mask)
            screen_y = int(self.world_y + cy_mask)
            self._contact_screen = (screen_x, screen_y)

            # Minimal signed angle difference in (−180, +180]
            angle_diff = _angle_diff(slope, self.angle)

            # --- Hard‐crash conditions ---
            vel_ratio = vel_abs / Config.LAND_DAMAGE_SPEED
            angle_ratio = abs(angle_diff) / Config.MAX_LANDING_ANGLE

            if (vel_ratio + angle_ratio) > 0.25:
                damage_amount = (vel_ratio + angle_ratio) * 100
                self.damage = min(self.damage + damage_amount, 100)
                if self.damage >= 100 and (vel_ratio + angle_ratio) > 0.75:
                    self._crash("STRUCTURAL DAMAGE")
                    return
                elif (vel_ratio + angle_ratio) > 1.5:
                    self._crash("HARD LANDING")
                return

            # --- Soft landing --
            self.report = {
                "landing_speed": abs_vy,
            }

            if special_hit:
                # Rock sampling
                self.science += 10
                self.report = self.report or {}
                self.report["sample"] = "cool rock"
            return

    def draw(self, screen: pygame.Surface, offset: float):
        firing = self.engine_on
        sprite = self.thruster if firing else self.img

        # crashed → simple center-rotate
        if self.crashed:
            rot_plain = pygame.transform.rotate(self.img, self.angle)
            return rot_plain, pygame.Rect(0, 0, 0, 0)

        if self.landed or self._contact_screen:
            pygame.draw.circle(screen, (255, 0, 0), self._contact_screen, 4)

            rot = pygame.transform.rotate(sprite, self.angle)
            cx = int(self.x - offset + sprite.get_width() / 2)
            cy = int(self.y + sprite.get_height() / 2)
            rect = rot.get_rect(center=(cx, cy))

            screen.blit(rot, rect.topleft)
            return rot, rect
        else:
            # flying → center-rotate around sprite center
            rot = pygame.transform.rotate(sprite, self.angle)
            cx = int(self.x - offset + sprite.get_width() / 2)
            cy = int(self.y + sprite.get_height() / 2)
            rect = rot.get_rect(center=(cx, cy))
            screen.blit(rot, rect.topleft)

            # red dot at the **rotated** image’s center
            pygame.draw.circle(screen, (255, 0, 0), rect.center, 5)

            # blue dot at the **original** sprite’s center in world coords
            orig_center = (
                int(self.x - offset + self.img.get_width() / 2),
                int(self.y + self.img.get_height() / 2),
            )
            self._gravity_center = orig_center
            pygame.draw.circle(screen, (0, 0, 255), orig_center, 5)

        return rot, rect

    # ---------------- Crash Animation & Reporting -----------------

    def tick_crash_anim(self) -> None:
        if not self.crash_anim:
            return
        now = pygame.time.get_ticks()
        if now - self.crash_timer >= Config.FRAME_DELAY_MS:
            self.crash_timer = now
            self.crash_index += 1
            if self.crash_index >= len(self.crash_frames):
                self.crash_anim = False
                self.crash_index = len(self.crash_frames) - 1

    def _crash(self, reason: str) -> None:
        self.crashed = True
        self.crash_anim = True
        self.crash_index = 0
        self.engine_on = False
        self.crash_timer = pygame.time.get_ticks()
        impact_speed = math.hypot(self.vx, self.vy)
        self.report = {
            "CAUSE:": reason,
            "impact_speed": round(impact_speed, 2),
            "impact_angle": round(self.angle, 1),
        }

    def draw_crash(self, screen: pygame.Surface, offset: float) -> None:
        idx = min(self.crash_index, len(self.crash_frames) - 1)
        img = self.crash_frames[idx]
        x = self.x - offset
        y = self.y
        screen.blit(img, (x, y))
