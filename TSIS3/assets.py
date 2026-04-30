from pathlib import Path

import pygame


ASSETS_DIR = Path(__file__).resolve().parent / "assets"


def load_image(name, size=None):
    path = ASSETS_DIR / "images" / name
    try:
        image = pygame.image.load(str(path)).convert()
        return pygame.transform.smoothscale(image, size) if size else image
    except (pygame.error, FileNotFoundError):
        return None


def load_sound(name):
    try:
        return pygame.mixer.Sound(str(ASSETS_DIR / "sounds" / name))
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
            self.enabled = False

    def load(self):
        if not self.enabled:
            return
        self.sounds = {name: load_sound(f"{name}.wav") for name in ["coin", "collision", "menu", "powerup", "gameover"]}

    def play(self, name, settings):
        sound = self.sounds.get(name) if self.enabled and settings.get("sound", True) else None
        if sound is not None:
            sound.play()
