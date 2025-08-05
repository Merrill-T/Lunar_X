from pathlib import Path
from pygame import mixer
from config import Config

ASSETS_ROOT = Path(__file__).resolve().parents[1]  # .../apollo_X/assets
SFX_DIR     = ASSETS_ROOT / "assets/sfx"                  # .../apollo_X/assets/sfx

class AudioAssets:
    def __init__(self) -> None:
        if not mixer.get_init():
            mixer.init()
        self.sounds = {}
        for name, relpath in Config.SOUND_FILES.items():
            path = (SFX_DIR / Path(relpath).name)  # allow just filenames in SOUND_FILES
            try:
                snd = mixer.Sound(str(path))
                snd.set_volume(Config.SND_VOLUME)
                self.sounds[name] = snd
            except FileNotFoundError:
                print(f"[WARN] missing sound: {path}")

