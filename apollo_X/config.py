import pygame

class Config:
    """Global tunables & paths. Keep constants here to avoid magic numbers."""

    # ------------------------------------------------------------------
    # Display
    SCREEN_SIZE        = 1000
    PIXEL_SIZE         = 8
    FONT_NAME          = "courier"
    FONT_SIZE          = 16
    # ------------------------------------------------------------------
    # Physics / Lander
    FUEL_START         = 2000
    ROTATION_SPEED     = 90.0
    DRY_MASS           = 13000.0
    ISP                = 311.0
    G0_MOON            = 1.62
    MAX_THRUST         = 45000.0
    CD                 = 0.7
    AREA               = 10.0
    RHO                = 0.02
    ANGULAR_INERTIA    = 2
    ROTATION_TORQUE    = 250
    LANDER_VX_ENTRY    = 10
    ENGINE_STARTUP_LIMIT = 5
    lander_angular_velocity = 0.0


    LANDER_HEIGHT_M    = 7.0
    TIME_SCALE         = 1.0

    MAX_LANDING_SPEED  = 2.0
    MAX_LANDING_ANGLE  = 20.0
    ROCK_DAMAGE_SPEED  = 2.0
    LAND_DAMAGE_SPEED  = 10.0

    MAX_OXYGEN         = 100.0
    MAX_BATTERY        = 100.0
    MAX_TEMPERATURE    = 120.0
    OXYGEN_DRAIN_RATE  = 1.5
    BATTERY_DRAIN_RATE = 5
    APU_FUEL_RATE      = 2.0
    APU_RECHARGE_RATE  = 10.0

    # ------------------------------------------------------------------
    # World
    TERRAIN_LENGTH     = 15000
    STAR_COUNT         = 200

    CRASH_FRAME_COUNT  = 3
    FRAME_DELAY_MS     = 250

    # ------------------------------------------------------------------
    # Audio
    SND_VOLUME         = 0.4
    ENGINE_VOL         = 0.55
    ENGINE_FADE_MS     = 150
    BEEP_MIN_MS        = 3000
    BEEP_MAX_MS        = 9000

    SOUND_FILES = {
        "beep": "Quindar_tones.wav",
        "engine_start": "engine_start.wav",
        "engine_loop": "engine_run_loop.wav",
        "crash": "crash.wav",
        "caution_beep": "caution_beep.mp3",
        "warning_beep": "warning_beep.mp3"
    }

    # ------------------------------------------------------------------
    # Colors
    WHITE  = (255, 255, 255)
    BLACK  = (0,   0,   0)
    GRAY   = (61, 69, 75)
    RED    = (255, 100, 100)
    YELLOW = (255, 255, 100)
    BLUE   = (100, 100, 255)

    HUD_COLOR        = (0, 255, 0)
    HUD_BG_ALPHA     = 150
    HUD_PANEL_HEIGHT = 120
