import json
from pathlib import Path
from random import choice, randint, random

import pygame

from assets import SoundBox, load_image
from db import Database


BASE_DIR = Path(__file__).resolve().parent
SETTINGS_FILE = BASE_DIR / "settings.json"

WIDTH, HEIGHT = 640, 680
TOP_PANEL = 80
CELL = 20
GRID_W = WIDTH // CELL
GRID_H = (HEIGHT - TOP_PANEL) // CELL

DEFAULT_SETTINGS = {
    "snake_color": [45, 160, 95],
    "grid": True,
    "sound": True,
}

FOOD_COLORS = [(230, 190, 60), (80, 170, 230), (120, 200, 80)]
POWER_COLORS = {
    "speed": (45, 145, 230),
    "slow": (120, 85, 210),
    "shield": (60, 180, 120),
}


def load_settings():
    if not SETTINGS_FILE.exists():
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS.copy()

    data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    settings = DEFAULT_SETTINGS.copy()
    settings.update(data)
    return settings


def save_settings(settings):
    SETTINGS_FILE.write_text(json.dumps(settings, indent=2), encoding="utf-8")


class SnakeGame:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("TSIS4 Snake")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 22)
        self.big_font = pygame.font.SysFont("arial", 38)

        self.db = Database()
        self.settings = load_settings()
        self.images = self.load_images()
        self.sound = SoundBox()
        self.sound.load()

        self.username = ""
        self.state = "menu"
        self.reset_game()

    def load_images(self):
        return {
            "snake_head": load_image("snake_head.bmp", (CELL, CELL)),
            "snake_body": load_image("snake_body.bmp", (CELL, CELL)),
            "food": load_image("food.bmp", (CELL, CELL)),
            "poison": load_image("poison.bmp", (CELL, CELL)),
            "speed": load_image("speed.bmp", (CELL, CELL)),
            "slow": load_image("slow.bmp", (CELL, CELL)),
            "shield": load_image("shield.bmp", (CELL, CELL)),
            "obstacle": load_image("obstacle.bmp", (CELL, CELL)),
            "ui_panel": load_image("ui_panel.bmp", (WIDTH, TOP_PANEL)),
        }

    def reset_game(self):
        self.snake = [(8, 8), (7, 8), (6, 8)]
        self.direction = (1, 0)
        self.next_direction = (1, 0)

        self.score = 0
        self.level = 1
        self.food_eaten = 0
        self.saved = False
        self.personal_best = self.db.personal_best(self.username)

        self.food_pos = None
        self.food_weight = 1
        self.food_color = FOOD_COLORS[0]
        self.food_until = 0
        self.poison_pos = None

        self.power_pos = None
        self.power_type = None
        self.power_until = 0
        self.active_power = None
        self.active_until = 0
        self.shield = False

        self.obstacles = []
        self.spawn_food()

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                else:
                    self.handle_event(event)

            if self.state == "game":
                self.update_game()

            self.draw()
            pygame.display.flip()
            self.clock.tick(self.current_fps())

        pygame.quit()

    def current_fps(self):
        base_fps = 7 + self.level
        now = pygame.time.get_ticks()

        if self.active_power == "speed" and now < self.active_until:
            return base_fps + 5
        if self.active_power == "slow" and now < self.active_until:
            return max(4, base_fps - 4)
        return base_fps

    def handle_event(self, event):
        if self.state == "menu":
            self.handle_menu(event)
        elif self.state == "game":
            self.handle_game_keys(event)
        elif self.state == "settings":
            self.handle_settings(event)
        elif self.state == "leaderboard":
            self.handle_back_button(event)
        elif self.state == "gameover":
            self.handle_gameover(event)

    def handle_menu(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self.username = self.username[:-1]
            elif event.key == pygame.K_RETURN and self.username:
                self.start_game()
            elif event.unicode and len(self.username) < 16:
                self.username += event.unicode

        if event.type != pygame.MOUSEBUTTONDOWN:
            return

        if self.button(220, 250).collidepoint(event.pos) and self.username:
            self.start_game()
        elif self.button(220, 305).collidepoint(event.pos):
            self.open_screen("leaderboard")
        elif self.button(220, 360).collidepoint(event.pos):
            self.open_screen("settings")
        elif self.button(220, 415).collidepoint(event.pos):
            pygame.event.post(pygame.event.Event(pygame.QUIT))

    def handle_game_keys(self, event):
        if event.type != pygame.KEYDOWN:
            return

        keys = {
            pygame.K_UP: (0, -1),
            pygame.K_DOWN: (0, 1),
            pygame.K_LEFT: (-1, 0),
            pygame.K_RIGHT: (1, 0),
        }
        if event.key not in keys:
            return

        new_direction = keys[event.key]
        is_opposite = (
            new_direction[0] + self.direction[0] == 0
            and new_direction[1] + self.direction[1] == 0
        )
        if not is_opposite:
            self.next_direction = new_direction

    def handle_settings(self, event):
        if event.type != pygame.MOUSEBUTTONDOWN:
            return

        colors = [[45, 160, 95], [55, 120, 220], [220, 70, 90]]

        if self.button(220, 245).collidepoint(event.pos):
            if self.settings["snake_color"] in colors:
                current = colors.index(self.settings["snake_color"])
            else:
                current = 0
            self.settings["snake_color"] = colors[(current + 1) % len(colors)]
            self.sound.play("menu", self.settings)
        elif self.button(220, 300).collidepoint(event.pos):
            self.settings["grid"] = not self.settings["grid"]
            self.sound.play("menu", self.settings)
        elif self.button(220, 355).collidepoint(event.pos):
            self.settings["sound"] = not self.settings["sound"]
        elif self.button(220, 455).collidepoint(event.pos):
            save_settings(self.settings)
            self.open_screen("menu")

    def handle_back_button(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and self.button(220, 610).collidepoint(event.pos):
            self.open_screen("menu")

    def handle_gameover(self, event):
        if event.type != pygame.MOUSEBUTTONDOWN:
            return

        if self.button(90, 610).collidepoint(event.pos):
            self.start_game()
        elif self.button(350, 610).collidepoint(event.pos):
            self.open_screen("menu")

    def start_game(self):
        self.sound.play("menu", self.settings)
        self.reset_game()
        self.state = "game"

    def open_screen(self, state):
        self.sound.play("menu", self.settings)
        self.state = state

    def random_free_cell(self):
        while True:
            cell = (randint(1, GRID_W - 2), randint(1, GRID_H - 2))
            if self.cell_is_free(cell):
                return cell

    def cell_is_free(self, cell):
        if cell in self.snake:
            return False
        if cell in self.obstacles:
            return False
        if cell == self.food_pos or cell == self.poison_pos or cell == self.power_pos:
            return False
        return True

    def spawn_food(self):
        self.food_pos = self.random_free_cell()
        self.food_weight = choice([1, 2, 3])
        self.food_color = choice(FOOD_COLORS)
        self.food_until = pygame.time.get_ticks() + 7000

        self.poison_pos = None
        if random() < 0.4:
            self.poison_pos = self.random_free_cell()

    def spawn_powerup(self):
        if self.power_pos is not None:
            return
        if random() >= 0.12:
            return

        self.power_pos = self.random_free_cell()
        self.power_type = choice(["speed", "slow", "shield"])
        self.power_until = pygame.time.get_ticks() + 8000

    def place_obstacles(self):
        if self.level < 3:
            return

        head_x, head_y = self.snake[0]
        safe_cells = [
            (head_x + 1, head_y),
            (head_x - 1, head_y),
            (head_x, head_y + 1),
            (head_x, head_y - 1),
        ]

        self.obstacles = []
        obstacle_count = min(18, self.level * 3)
        while len(self.obstacles) < obstacle_count:
            cell = self.random_free_cell()
            if cell not in safe_cells:
                self.obstacles.append(cell)

    def update_game(self):
        self.update_timers()
        self.spawn_powerup()

        self.direction = self.next_direction
        new_head = self.next_head()

        if self.hit_wall_or_body(new_head) or new_head in self.obstacles:
            if not self.use_shield():
                self.game_over()
                return
            new_head = self.snake[0]

        self.snake.insert(0, new_head)
        grow_by = self.check_food(new_head)
        if self.check_poison(new_head):
            self.game_over()
            return
        self.check_powerup(new_head)
        self.cut_tail(grow_by)

        if len(self.snake) <= 1:
            self.game_over()

    def update_timers(self):
        now = pygame.time.get_ticks()

        if now > self.food_until:
            self.spawn_food()
        if self.power_pos is not None and now > self.power_until:
            self.power_pos = None
            self.power_type = None
        if self.active_power in ["speed", "slow"] and now > self.active_until:
            self.active_power = None

    def next_head(self):
        head_x, head_y = self.snake[0]
        dx, dy = self.direction
        return head_x + dx, head_y + dy

    def hit_wall_or_body(self, cell):
        x, y = cell
        outside = x < 0 or x >= GRID_W or y < 0 or y >= GRID_H
        return outside or cell in self.snake

    def use_shield(self):
        self.sound.play("collision", self.settings)
        if not self.shield:
            return False
        self.shield = False
        self.active_power = None
        return True

    def check_food(self, head):
        if head != self.food_pos:
            return 0

        self.score += 10 * self.food_weight
        self.food_eaten += 1
        self.sound.play("eat", self.settings)

        if self.food_eaten % 4 == 0:
            self.level += 1
            self.place_obstacles()

        grow_by = self.food_weight
        self.spawn_food()
        return grow_by

    def check_poison(self, head):
        if head != self.poison_pos:
            return False

        self.poison_pos = None
        self.sound.play("poison", self.settings)
        for _ in range(2):
            if self.snake:
                self.snake.pop()
        return len(self.snake) <= 1

    def check_powerup(self, head):
        if head != self.power_pos:
            return

        kind = self.power_type
        self.power_pos = None
        self.power_type = None
        self.sound.play("powerup", self.settings)

        if kind == "shield":
            self.shield = True
            self.active_power = "shield"
        else:
            self.active_power = kind
            self.active_until = pygame.time.get_ticks() + 5000

    def cut_tail(self, grow_by):
        if grow_by > 0:
            for _ in range(grow_by - 1):
                self.snake.append(self.snake[-1])
        else:
            self.snake.pop()

    def game_over(self):
        if self.saved:
            self.state = "gameover"
            return

        self.db.save_result(self.username or "Player", self.score, self.level)
        self.saved = True
        self.sound.play("gameover", self.settings)
        self.state = "gameover"

    def button(self, x, y):
        return pygame.Rect(x, y, 200, 42)

    def draw_button(self, x, y, text):
        rect = self.button(x, y)
        hover = rect.collidepoint(pygame.mouse.get_pos())
        bg_color = (49, 92, 145) if hover else (232, 236, 240)
        text_color = (255, 255, 255) if hover else (24, 30, 38)

        pygame.draw.rect(self.screen, bg_color, rect, border_radius=6)
        pygame.draw.rect(self.screen, (38, 53, 75), rect, 1, border_radius=6)

        label = self.font.render(text, True, text_color)
        self.screen.blit(label, label.get_rect(center=rect.center))

    def draw_text(self, font, value, pos, center=False, color=(26, 31, 38)):
        text = font.render(str(value), True, color)
        rect = text.get_rect(center=pos) if center else text.get_rect(topleft=pos)
        self.screen.blit(text, rect)

    def draw(self):
        if self.state == "menu":
            self.draw_menu()
        elif self.state == "game":
            self.draw_game()
        elif self.state == "leaderboard":
            self.draw_leaderboard()
        elif self.state == "settings":
            self.draw_settings()
        elif self.state == "gameover":
            self.draw_gameover()

    def draw_menu(self):
        self.screen.fill((245, 247, 250))
        self.draw_text(self.big_font, "TSIS4 Snake", (WIDTH // 2, 120), center=True)
        self.draw_text(self.font, f"Name: {self.username or 'type your name'}", (WIDTH // 2, 185), center=True)

        if not self.db.available:
            self.draw_text(self.font, "DB offline: leaderboard disabled", (WIDTH // 2, 215), center=True, color=(170, 60, 60))

        self.draw_button(220, 250, "Play")
        self.draw_button(220, 305, "Leaderboard")
        self.draw_button(220, 360, "Settings")
        self.draw_button(220, 415, "Quit")

    def draw_game(self):
        self.screen.fill((32, 35, 42))
        self.draw_arena()
        self.draw_game_objects()
        self.draw_score_panel()

    def draw_arena(self):
        pygame.draw.rect(self.screen, (238, 241, 244), (0, TOP_PANEL, WIDTH, HEIGHT - TOP_PANEL))

        if self.images["ui_panel"]:
            self.screen.blit(self.images["ui_panel"], (0, 0))

        if not self.settings["grid"]:
            return

        for x in range(0, WIDTH, CELL):
            pygame.draw.line(self.screen, (220, 224, 228), (x, TOP_PANEL), (x, HEIGHT))
        for y in range(TOP_PANEL, HEIGHT, CELL):
            pygame.draw.line(self.screen, (220, 224, 228), (0, y), (WIDTH, y))

    def draw_game_objects(self):
        for cell in self.obstacles:
            self.draw_cell(cell, (80, 84, 92), "obstacle")

        self.draw_cell(self.food_pos, self.food_color, "food")

        if self.poison_pos:
            self.draw_cell(self.poison_pos, (120, 20, 35), "poison")
        if self.power_pos:
            self.draw_cell(self.power_pos, POWER_COLORS[self.power_type], self.power_type)

        for index, cell in enumerate(self.snake):
            if index == 0:
                self.draw_cell(cell, tuple(self.settings["snake_color"]), "snake_head")
            else:
                self.draw_cell(cell, (72, 175, 110), "snake_body")

    def draw_score_panel(self):
        self.draw_text(self.font, f"Score {self.score}  Level {self.level}  Best {self.personal_best}", (10, 14), color=(255, 255, 255))

        power = self.active_power or "none"
        if self.shield:
            power = "shield"
        self.draw_text(self.font, f"Power: {power}", (10, 44), color=(255, 255, 255))

    def draw_cell(self, cell, color, image_name=None):
        x, y = cell
        rect = pygame.Rect(x * CELL, TOP_PANEL + y * CELL, CELL, CELL)
        image = self.images.get(image_name)

        if image:
            self.screen.blit(image, rect)
        else:
            pygame.draw.rect(self.screen, color, (rect.x + 1, rect.y + 1, CELL - 2, CELL - 2), border_radius=4)

    def draw_leaderboard(self):
        self.screen.fill((245, 247, 250))
        self.draw_text(self.big_font, "Leaderboard", (WIDTH // 2, 60), center=True)

        rows = self.db.top10()
        if not rows:
            self.draw_text(self.font, "No database records yet.", (WIDTH // 2, 220), center=True)

        for index, row in enumerate(rows, 1):
            date = str(row["played_at"])[:16]
            text = f"{index}. {row['username']}  {row['score']}  lvl {row['level_reached']}  {date}"
            self.draw_text(self.font, text, (55, 105 + index * 38))

        self.draw_button(220, 610, "Back")

    def draw_settings(self):
        self.screen.fill((245, 247, 250))
        self.draw_text(self.big_font, "Settings", (WIDTH // 2, 120), center=True)

        self.draw_text(self.font, f"Snake color: {self.settings['snake_color']}", (205, 215))
        self.draw_text(self.font, f"Grid overlay: {self.settings['grid']}", (205, 270))
        self.draw_text(self.font, f"Sound: {self.settings['sound']}", (205, 325))

        self.draw_button(220, 245, "Color")
        self.draw_button(220, 300, "Grid")
        self.draw_button(220, 355, "Sound")
        self.draw_button(220, 455, "Save & Back")

    def draw_gameover(self):
        self.screen.fill((245, 247, 250))
        self.draw_text(self.big_font, "Game Over", (WIDTH // 2, 170), center=True)
        self.draw_text(self.font, f"Score: {self.score}", (WIDTH // 2, 250), center=True)
        self.draw_text(self.font, f"Level reached: {self.level}", (WIDTH // 2, 285), center=True)
        self.draw_text(self.font, f"Personal best: {max(self.personal_best, self.score)}", (WIDTH // 2, 320), center=True)

        self.draw_button(90, 610, "Retry")
        self.draw_button(350, 610, "Back")
