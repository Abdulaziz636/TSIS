from pathlib import Path

import pygame


ASSETS_DIR = Path(__file__).resolve().parent / "assets"


def load_image(name, size=None):
    # Images are loaded by relative path from TSIS4/assets/images.
    # Missing images return None, so drawing can fall back to pygame.draw.
    path = ASSETS_DIR / "images" / name
    try:
        image = pygame.image.load(str(path)).convert()
        if size:
            image = pygame.transform.smoothscale(image, size)
        return image
    except (pygame.error, FileNotFoundError):
        return None


def load_sound(name):
    # Sounds are optional. A missing WAV disables only that sound effect.
    path = ASSETS_DIR / "sounds" / name
    try:
        return pygame.mixer.Sound(str(path))
    except (pygame.error, FileNotFoundError):
        return None


class SoundBox:
    def __init__(self):
        self.enabled = False
        self.sounds = {}
        try:
            pygame.mixer.init()
            self.enabled = True
        except pygame.error:
            # The game must still run on computers without an audio device.
            self.enabled = False

    def load(self):
        if not self.enabled:
            return
        for name in ["eat", "poison", "powerup", "collision", "menu", "gameover"]:
            self.sounds[name] = load_sound(f"{name}.wav")

    def play(self, name, settings):
        # settings.json has a sound on/off flag. If it is off, do nothing.
        if not self.enabled or not settings.get("sound", True):
            return
        sound = self.sounds.get(name)
        if sound:
            sound.play()

