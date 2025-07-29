import pygame
from pygame import mixer
from config import Config
from assets.audio_assets import AudioAssets

class SoundManager:
    """Centralized audio playback & engine/beep logic."""

    BEEP_EVENT          = pygame.USEREVENT + 1
    ENGINE_START_DONE   = pygame.USEREVENT + 2

    def __init__(self, assets: AudioAssets) -> None:
        self.assets = assets
        self.engine_on = False
        # dedicated engine channel
        self.engine_chan = mixer.Channel(0)
        # generic registry for cooldown
        self._last_play: dict[str, int] = {}

    # -------- simple one-liner ----------
    def play(self, name: str, *, loops: int = 0, volume: float | None = None,
             fade_ms: int = 0, channel: pygame.mixer.Channel | None = None,
             once_until_done: bool = False, cooldown_ms: int = 0) -> None:
        snd = self.assets.sounds.get(name)
        if not snd:
            return

        # avoid spam: same sound already playing anywhere
        if once_until_done:
            for i in range(mixer.get_num_channels()):
                ch_i = mixer.Channel(i)
                if ch_i.get_sound() is snd and ch_i.get_busy():
                    return
        # cooldown check
        if cooldown_ms:
            now = pygame.time.get_ticks()
            last = self._last_play.get(name, -10_000_000)
            if now - last < cooldown_ms:
                return
            self._last_play[name] = now

        ch = channel or mixer.find_channel()
        if not ch:
            return
        if volume is not None:
            ch.set_volume(volume)
        ch.play(snd, loops=loops, fade_ms=fade_ms)
        
    def stop(self, name: str) -> None:
        snd = self.assets.sounds.get(name)
        if not snd:
            return
        for i in range(pygame.mixer.get_num_channels()):
            ch = pygame.mixer.Channel(i)
            if ch.get_sound() is snd:
                ch.stop()

    # ---------- Random beep timer ----------
    def start_random_beeps(self) -> None:
        delay = pygame.rand.randint(Config.BEEP_MIN_MS, Config.BEEP_MAX_MS) if hasattr(pygame, 'rand') else __import__('random').randint(Config.BEEP_MIN_MS, Config.BEEP_MAX_MS)
        pygame.time.set_timer(self.BEEP_EVENT, delay, loops=1)

    def handle_event(self, event, lander) -> None:
        if event.type == self.ENGINE_START_DONE:
            if self.engine_on and self.assets.sounds.get("engine_loop"):
                self.engine_chan.play(self.assets.sounds["engine_loop"], loops=-1, fade_ms=Config.ENGINE_FADE_MS)
                self.engine_chan.set_volume(Config.ENGINE_VOL)
            self.engine_chan.set_endevent()
            return

        if event.type == self.BEEP_EVENT:
            if self.assets.sounds.get("beep") and not lander.crashed:
                self.play("beep", once_until_done=False, volume = 0.25)
            self.start_random_beeps()

    # ---------- Engine control ------------
    def update_engine(self, thrusting: bool) -> None:
        if thrusting and not self.engine_on:
            self.engine_on = True
            start = self.assets.sounds.get("engine_start")
            if start:
                self.engine_chan.play(start) # fade_ms=Config.ENGINE_FADE_MS)
                self.engine_chan.set_volume(Config.ENGINE_VOL)
                self.engine_chan.set_endevent(self.ENGINE_START_DONE)
            else:
                loop = self.assets.sounds.get("engine_loop")
                if loop:
                    self.engine_chan.play(loop, loops=-1) # fade_ms=Config.ENGINE_FADE_MS)
                    self.engine_chan.set_volume(Config.ENGINE_VOL)
        elif not thrusting and self.engine_on:
            self.engine_on = False
            self.engine_chan.stop()            # immediate silence, no volume change
            self.engine_chan.set_endevent()
            self.engine_chan.set_volume(Config.ENGINE_VOL)
            self.engine_chan.set_endevent()

    def stop_all(self):
        mixer.stop()
        self.engine_on = False
        self.engine_chan.set_endevent()
