from pathlib import Path

import pygame


ASSETS_DIR = Path(__file__).resolve().parent / "assets"


def load_image(name, size=None):
    # Images are loaded from TSIS3/assets/images by relative path.
    # If loading fails, None is returned and the game continues with pygame.draw.
    path = ASSETS_DIR / "images" / name
    try:
        image = pygame.image.load(str(path)).convert()
        if size:
            image = pygame.transform.smoothscale(image, size)
        return image
    except (pygame.error, FileNotFoundError):
        return None


def load_sound(name):
    # Sounds are optional. Missing files disable only that effect, not the game.
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
            # Some computers have no audio device. In that case sound is skipped.
            self.enabled = False

    def load(self):
        if not self.enabled:
            return
        for name in ["coin", "collision", "menu", "powerup", "gameover"]:
            self.sounds[name] = load_sound(f"{name}.wav")

    def play(self, name, settings):
        # The settings.json sound flag controls all sound effects.
        if not self.enabled or not settings.get("sound", True):
            return
        sound = self.sounds.get(name)
        if sound:
            sound.play()

