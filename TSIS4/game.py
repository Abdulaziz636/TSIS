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
MENU_BUTTONS = [(380, 245, "Play"), (380, 300, "Leaderboard"), (380, 355, "Settings"), (380, 410, "Quit")]
SETTINGS_BUTTONS = [(360, 245, "Color"), (360, 300, "Grid"), (360, 355, "Sound"), (360, 455, "Save & Back")]


def load_settings():
    settings = DEFAULT_SETTINGS.copy()
    if not SETTINGS_FILE.exists():
        save_settings(settings)
    else:
        settings.update(json.loads(SETTINGS_FILE.read_text(encoding="utf-8")))
    return settings


def save_settings(settings):
    SETTINGS_FILE.write_text(json.dumps(settings, indent=2), encoding="utf-8")


class SnakeGame:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("KBTU Snake Lab")
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
        files = {
            "snake_head": ("snake_head.bmp", (CELL, CELL)),
            "snake_body": ("snake_body.bmp", (CELL, CELL)),
            "food": ("food.bmp", (CELL, CELL)),
            "poison": ("poison.bmp", (CELL, CELL)),
            "speed": ("speed.bmp", (CELL, CELL)),
            "slow": ("slow.bmp", (CELL, CELL)),
            "shield": ("shield.bmp", (CELL, CELL)),
            "obstacle": ("obstacle.bmp", (CELL, CELL)),
            "ui_panel": ("ui_panel.bmp", (WIDTH, TOP_PANEL)),
        }
        return {name: load_image(file, size) for name, (file, size) in files.items()}

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

        for x, y, text in MENU_BUTTONS:
            if not self.button(x, y).collidepoint(event.pos):
                continue
            if text == "Play" and self.username:
                self.start_game()
            elif text == "Leaderboard":
                self.open_screen("leaderboard")
            elif text == "Settings":
                self.open_screen("settings")
            elif text == "Quit":
                pygame.event.post(pygame.event.Event(pygame.QUIT))

    def handle_game_keys(self, event):
        if event.type != pygame.KEYDOWN:
            return

        directions = {
            pygame.K_UP: (0, -1),
            pygame.K_DOWN: (0, 1),
            pygame.K_LEFT: (-1, 0),
            pygame.K_RIGHT: (1, 0),
        }
        if event.key not in directions:
            return

        new_direction = directions[event.key]
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
        clicked = None
        for x, y, text in SETTINGS_BUTTONS:
            if self.button(x, y).collidepoint(event.pos):
                clicked = text

        if clicked is None:
            return

        if clicked == "Color":
            current = colors.index(self.settings["snake_color"]) if self.settings["snake_color"] in colors else 0
            self.settings["snake_color"] = colors[(current + 1) % len(colors)]
            self.sound.play("menu", self.settings)
        elif clicked == "Grid":
            self.settings["grid"] = not self.settings["grid"]
            self.sound.play("menu", self.settings)
        elif clicked == "Sound":
            self.settings["sound"] = not self.settings["sound"]
        elif clicked == "Save & Back":
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
        return cell not in self.snake and cell not in self.obstacles and cell not in {self.food_pos, self.poison_pos, self.power_pos}

    def spawn_food(self):
        self.food_pos = self.random_free_cell()
        self.food_weight = choice([1, 2, 3])
        self.food_color = choice(FOOD_COLORS)
        self.food_until = pygame.time.get_ticks() + 7000

        self.poison_pos = None
        if random() < 0.4:
            self.poison_pos = self.random_free_cell()

    def spawn_powerup(self):
        if self.power_pos is not None or random() >= 0.12:
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
            if not self.use_shield(new_head):
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
        return x < 0 or x >= GRID_W or y < 0 or y >= GRID_H or cell in self.snake

    def use_shield(self, collision_cell):
        self.sound.play("collision", self.settings)
        if not self.shield:
            return False
        if collision_cell in self.obstacles:
            self.obstacles.remove(collision_cell)
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
        bg_color = (62, 177, 139) if hover else (231, 244, 237)
        text_color = (16, 35, 29) if hover else (25, 47, 39)

        pygame.draw.rect(self.screen, (16, 32, 28), rect.move(3, 3), border_radius=4)
        pygame.draw.rect(self.screen, bg_color, rect, border_radius=4)
        pygame.draw.rect(self.screen, (50, 94, 77), rect, 1, border_radius=4)

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
        self.screen.fill((20, 35, 31))
        for x in range(0, WIDTH, CELL * 2):
            pygame.draw.line(self.screen, (31, 53, 47), (x, 0), (x, HEIGHT))
        for y in range(0, HEIGHT, CELL * 2):
            pygame.draw.line(self.screen, (31, 53, 47), (0, y), (WIDTH, y))
        pygame.draw.rect(self.screen, (40, 87, 70), (0, 0, 305, HEIGHT))
        self.draw_text(self.big_font, "Snake Lab", (42, 105), color=(236, 248, 239))
        self.draw_text(self.font, f"Player: {self.username or 'type your name'}", (42, 180), color=(205, 229, 214))

        if not self.db.available:
            self.draw_text(self.font, "DB offline: leaderboard disabled", (42, 215), color=(255, 190, 170))

        for x, y, text in MENU_BUTTONS:
            self.draw_button(x, y, text)

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
        pygame.draw.rect(self.screen, (18, 33, 29), (0, 0, WIDTH, TOP_PANEL))
        pygame.draw.rect(self.screen, (62, 177, 139), (0, TOP_PANEL - 4, WIDTH, 4))
        self.draw_text(self.font, f"Score {self.score}  Level {self.level}  Best {self.personal_best}", (14, 14), color=(236, 248, 239))

        power = self.active_power or "none"
        if self.shield:
            power = "shield"
        self.draw_text(self.font, f"Power: {power}", (14, 44), color=(236, 248, 239))

    def draw_cell(self, cell, color, image_name=None):
        x, y = cell
        rect = pygame.Rect(x * CELL, TOP_PANEL + y * CELL, CELL, CELL)
        image = self.images.get(image_name)

        if image:
            self.screen.blit(image, rect)
        else:
            pygame.draw.rect(self.screen, color, (rect.x + 1, rect.y + 1, CELL - 2, CELL - 2), border_radius=4)

    def draw_leaderboard(self):
        self.screen.fill((231, 244, 237))
        pygame.draw.rect(self.screen, (20, 35, 31), (0, 0, WIDTH, 88))
        self.draw_text(self.big_font, "Leaderboard", (WIDTH // 2, 48), center=True, color=(236, 248, 239))

        rows = self.db.top10()
        if not rows:
            self.draw_text(self.font, "No database records yet.", (WIDTH // 2, 220), center=True)

        for index, row in enumerate(rows, 1):
            date = str(row["played_at"])[:16]
            text = f"{index}. {row['username']}  {row['score']}  lvl {row['level_reached']}  {date}"
            self.draw_text(self.font, text, (55, 105 + index * 38))

        self.draw_button(220, 610, "Back")

    def draw_settings(self):
        self.screen.fill((231, 244, 237))
        self.draw_text(self.big_font, "Lab Settings", (WIDTH // 2, 120), center=True)

        self.draw_text(self.font, f"Snake color: {self.settings['snake_color']}", (70, 255))
        self.draw_text(self.font, f"Grid overlay: {self.settings['grid']}", (70, 310))
        self.draw_text(self.font, f"Sound: {self.settings['sound']}", (70, 365))

        for x, y, text in SETTINGS_BUTTONS:
            self.draw_button(x, y, text)

    def draw_gameover(self):
        self.screen.fill((20, 35, 31))
        self.draw_text(self.big_font, "Game Over", (WIDTH // 2, 170), center=True, color=(236, 248, 239))
        self.draw_text(self.font, f"Score: {self.score}", (WIDTH // 2, 250), center=True, color=(205, 229, 214))
        self.draw_text(self.font, f"Level reached: {self.level}", (WIDTH // 2, 285), center=True, color=(205, 229, 214))
        self.draw_text(self.font, f"Personal best: {max(self.personal_best, self.score)}", (WIDTH // 2, 320), center=True, color=(205, 229, 214))

        self.draw_button(90, 610, "Retry")
        self.draw_button(350, 610, "Back")
