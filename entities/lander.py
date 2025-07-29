import math
import pygame
from config import Config

class Lander:
    """Lander state, physics, draw helpers with smooth settlement on touchdown."""

    def __init__(self, gfx_assets):
        # Graphics & scaling
        self.img = gfx_assets.lander
        self.thruster = gfx_assets.thruster
        self.crash_frames = gfx_assets.crash_frames
        self.px_per_m = self.img.get_height() / Config.LANDER_HEIGHT_M

        # Fixed pivot in the original image: bottom‑center pixel
        w, h = self.img.get_width(), self.img.get_height()

        # World coordinate of that pivot once landed
        self._gravity_center = None
        self._contact_screen = None
        self._contact_slope = None

        self.reset()

    def reset(self):
        # Position & motion
        self.x = Config.SCREEN_SIZE // 2
        self.y = Config.SCREEN_SIZE // 4
        self.vx = Config.LANDER_VX_ENTRY
        self.vy = 0.0
        self.ax = self.ay = 0.0
        self.angle = 0.0

        # Resources & status
        self.fuel = Config.FUEL_START
        self.oxygen = Config.MAX_OXYGEN
        self.battery = Config.MAX_BATTERY
        self.temperature = 20.0
        self.damage = 0.0
        self.gforce = 0.0
        self.apu_on = False
        self.engine_startup_count = 0
        self.engine_out = 1
        self.engine_on = False

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
            int(self.x + self.img.get_width()  / 2),
            int(self.y       + self.img.get_height() / 2)
        )
        self._contact_screen = None

    def compute_surface_slope(self, terrain) -> float:
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


    def update_physics(self, keys: pygame.key.ScancodeWrapper, dt: float, terrain) -> None:
        """
        Update the lander’s physics each frame: time scaling, life‑support drains,
        power/APU recharge, rotational dynamics with torque/inertia, flight or landed dynamics.
        """
        # 1) Scale simulation time
        dt_sim = dt * Config.TIME_SCALE

        # 3) Abort if we've already crashed
        if self.crashed:
            return

        # 2) Life‑support drains
        self.oxygen  = max(self.oxygen  - Config.OXYGEN_DRAIN_RATE  * dt_sim, 0.0)
        self.battery = max(self.battery - Config.BATTERY_DRAIN_RATE * dt_sim, 0.0)
        if self.battery <= 0 and not self.apu_on:
            self.apu_on = True
        elif self.battery >= 50 and self.apu_on:
            self.apu_on = False

        # 4) APU (auxiliary power unit) recharge logic
        if self.apu_on and self.battery < Config.MAX_BATTERY:
            fuel_used = Config.APU_FUEL_RATE * dt_sim
            self.fuel    = max(self.fuel - fuel_used, 0.0)
            self.battery = min(self.battery + Config.APU_RECHARGE_RATE * dt_sim,
                               Config.MAX_BATTERY)

        has_power = (self.battery > 0.0)

        # 5) Rotational dynamics: torque, angular acceleration, integrate angular velocity
        # Initialize angular_velocity on first use
        if not hasattr(self, 'angular_velocity'):
            self.angular_velocity = 0.0

        if has_power and not self.landed:
            # Compute net torque from left/right keys
            net_torque = 0.0
            if keys[pygame.K_LEFT]:
                net_torque += Config.ROTATION_TORQUE
            if keys[pygame.K_RIGHT]:
                net_torque -= Config.ROTATION_TORQUE
            # Angular acceleration = torque / inertia
            angular_accel = net_torque / Config.ANGULAR_INERTIA
            # Integrate angular velocity
            self.angular_velocity += angular_accel * dt_sim
        # else: no control torque; angular_velocity remains (conserved momentum)

        # Update angle from angular_velocity
        self.angle = (self.angle + self.angular_velocity * dt_sim) % 360

        # 6) In‑flight vs. landed: translational physics
        if not self._contact_screen and not self.landed:
            # 6a) Compute accelerations
            ax = 0.0
            ay = Config.G0_MOON  # lunar gravity

            # Main engine thrust

            if keys[pygame.K_UP] and self.fuel > 0:
                if not self.engine_on:
                    self.engine_startup_count += 1
                    if self.engine_startup_count >= Config.ENGINE_STARTUP_LIMIT:
                        self.report = {
                            "ENGINE FAILURE": "START_UP",
                        }
                        self.engine_out = 0
                        self.engine_on = False
                    else: self.engine_on = True
                thrust = Config.MAX_THRUST * self.engine_out
                mass   = Config.DRY_MASS + self.fuel
                mflow  = thrust / (Config.ISP * Config.G0_MOON)
                fuel_used = mflow * dt_sim
                self.fuel = max(self.fuel - fuel_used, 0.0)
                rad    = math.radians(self.angle)
                ax    += (thrust / mass) * -math.sin(rad)
                ay    += (thrust / mass) * -math.cos(rad)
            else:
                self.engine_on = False

            # Aerodynamic drag
            mass = Config.DRY_MASS + self.fuel
            ax  -= 0.5 * Config.CD   * Config.AREA * Config.RHO * self.vx * abs(self.vx) / mass
            ay  -= 0.5 * Config.CD   * Config.AREA * Config.RHO * self.vy * abs(self.vy) / mass

            # 6b) Integrate translational motion
            self.ax, self.ay = ax, ay
            self.vx += ax * dt_sim
            self.vy += ay * dt_sim
            self.gforce = math.hypot(ax, ay) / 9.81
            self.x  += self.vx * dt_sim * self.px_per_m
            self.y  += self.vy * dt_sim * self.px_per_m

            # Temperature rise from G‑forces
            self.temperature = min(
                self.temperature + 0.01 * self.gforce * dt_sim,
                Config.MAX_TEMPERATURE
            )
        # 7) If landed or pivot physics remains unchanged

        elif self._contact_screen and not self.crashed:
            # Landed: pivot/settle on slope or allow lift‑off
            target_slope    = self.compute_surface_slope(terrain)
            rotation_step   = Config.ROTATION_SPEED * dt_sim
            angle_diff      = (target_slope - self.angle + 180) % 360 - 180
            self.angular_velocity = 0.0

            # Possible lift‑off thrust from landed state
            self.engine_on = False
            if keys[pygame.K_UP] and self.fuel > 0:
                if self.vy > 0:
                    self.vy = 0
                    self.vx = 0
                print("key up in contact")
                ax = 0.0
                ay = Config.G0_MOON  # lunar gravity
                self.landed    = False
                self.engine_on = True
                thrust = Config.MAX_THRUST
                mass   = Config.DRY_MASS + self.fuel
                mflow  = thrust / (Config.ISP * Config.G0_MOON)
                fuel_used = mflow * dt_sim
                self.fuel = max(self.fuel - fuel_used, 0.0)
                rad = math.radians(self.angle)
                ax += (thrust / mass) * -math.sin(rad)
                ay += (thrust / mass) * -math.cos(rad)

                # 5c) Integrate motion
                self.ax, self.ay = ax, ay
                self.vx += ax * dt_sim
                self.vy += ay * dt_sim

                self.gforce = math.hypot(ax, ay) / 9.81
                self.x += self.vx * dt_sim * self.px_per_m
                self.y += self.vy * dt_sim * self.px_per_m

            elif abs(angle_diff) >= rotation_step:
                # --- pivot physics around contact point ---
                pivot_x, pivot_y = self._contact_screen
                cg_x, cg_y       = self._gravity_center

                # Lever arm vector (meters)
                dx0 = (cg_x - pivot_x) / self.px_per_m
                dy0 = (cg_y - pivot_y) / self.px_per_m
                arm0 = math.atan2(dy0, dx0)

                # Tangential unit vector and gravity projection
                R  = math.hypot(dx0, dy0)
                tx, ty = -dy0 / R, dx0 / R
                g      = Config.G0_MOON
                tang_acc = g * ty * 2
                ax = tang_acc * tx
                ay = tang_acc * ty

                # Integrate pivot motion
                self.ax, self.ay = ax, ay
                self.vx += ax * dt_sim
                self.vy += ay * dt_sim
                self.x  += self.vx * dt_sim * self.px_per_m
                self.y  += self.vy * dt_sim * self.px_per_m

                # Compute new lever‑arm angle
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



    def collision_check(self, keys, terrain, offset_x, rock_hit=False, special_hit=False) -> None:
        """
        Check for collisions with the terrain, handle landing/takeoff,
        crashes, and rock sampling.
        """
        if rock_hit:
            self._crash("CRASHED INTO ROCKS")
            return

        # --- 2) Prepare variables ---
        orig_vy   = self.vy
        abs_vy    = abs(orig_vy)
        vel_abs = math.sqrt(self.vy**2 + self.vx**2)
        slope     = self.compute_surface_slope(terrain)
        self._contact_slope = slope

        # Rotate sprite and build masks
        rotated_img    = pygame.transform.rotate(self.img, self.angle)
        ship_mask      = pygame.mask.from_surface(rotated_img)
        terrain_mask   = terrain.mask

        # Compute world‐coords of the rotated sprite’s topleft
        cx_center = self.x - offset_x + self.img.get_width() / 2
        cy_center = self.y + self.img.get_height() / 2
        rect      = rotated_img.get_rect(center=(int(cx_center), int(cy_center)))
        world_x   = rect.left + offset_x
        world_y   = rect.top

        # Pixel‑perfect overlap?
        contact = ship_mask.overlap(terrain_mask, (-world_x, -world_y))
        if not contact:
            if not contact and self._contact_screen and keys[pygame.K_UP]:
                self._contact_screen = None
            return
        elif not self._contact_screen and contact:
            cx_mask, cy_mask = contact
            # Record on‑screen contact point
            screen_x = int((world_x - offset_x) + cx_mask)
            screen_y = int(world_y + cy_mask)
            self._contact_screen = (screen_x, screen_y)


            # Minimal signed angle difference in (−180, +180]
            angle_diff = (slope - self.angle + 180) % 360 - 180

            # --- 3) Hard‐crash conditions ---
            # --- combine velocity and angle for a more realistic HARD‐LANDING check ---
            vel_ratio   = vel_abs / Config.LAND_DAMAGE_SPEED
            angle_ratio = abs(angle_diff) / Config.MAX_LANDING_ANGLE

            if (vel_ratio + angle_ratio) > 0.25:
                print(vel_ratio + angle_ratio)
                damage_amount = (vel_ratio + angle_ratio) * 100
                self.damage = min(self.damage + damage_amount, 100)
                if self.damage >= 100 and (vel_ratio + angle_ratio) < 1 :
                    self._crash("STRUCTURAL DAMAGE")
                    return
                elif (vel_ratio + angle_ratio) > 1.5: self._crash("HARD LANDING")
                return

            # --- 5) Soft landing --

            # Record successful landing
            self.report = {
                "landing_speed": abs_vy,
            }

            if special_hit:
                # Rock sampling
                self.science += 10
                self.report = self.report or {}
                self.report['sample'] = 'cool rock'
            return



    def draw(self, screen: pygame.Surface, offset: float):
        firing = self.engine_on
        sprite = self.thruster if firing else self.img

        # crashed → simple center‑rotate
        if self.crashed:
            rot_plain = pygame.transform.rotate(self.img, self.angle)
            return rot_plain, pygame.Rect(0, 0, 0, 0)

        if self.landed or self._contact_screen:

            pygame.draw.circle(screen, (255, 0, 0), self._contact_screen, 4)

            rot = pygame.transform.rotate(sprite, self.angle)
            cx = int(self.x - offset + sprite.get_width()/2)
            cy = int(self.y + sprite.get_height()/2)
            rect = rot.get_rect(center=(cx, cy))

            screen.blit(rot, rect.topleft)

            return rot, rect
        else:
            # flying → center‑rotate around sprite center
            rot = pygame.transform.rotate(sprite, self.angle)
            cx = int(self.x - offset + sprite.get_width()/2)
            cy = int(self.y + sprite.get_height()/2)
            rect = rot.get_rect(center=(cx, cy))
            screen.blit(rot, rect.topleft)

            # red dot at the **rotated** image’s center
            pygame.draw.circle(screen, (255, 0, 0), rect.center, 5)

            # blue dot at the **original** sprite’s center in world coords
            orig_center = (
                int(self.x - offset + self.img.get_width()  / 2),
                int(self.y       + self.img.get_height() / 2)
            )
            self._gravity_center = orig_center
            pygame.draw.circle(screen, (0, 0, 255), orig_center, 5)

        return rot, rect

    @staticmethod
    def blit_image_at_pivot(screen, image, world_pos, pivot):
        pass
        return

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
