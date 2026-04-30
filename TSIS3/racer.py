from random import choice, randint, random

import pygame

from assets import SoundBox, load_image
from persistence import add_score, load_leaderboard, load_settings, save_settings
from ui import Button, draw_text


WIDTH, HEIGHT = 520, 720
ROAD = pygame.Rect(80, 0, 360, HEIGHT)
LANES = [125, 205, 285, 365]
FINISH_DISTANCE = 3000
DIFFICULTY_SPEED = {"easy": 4, "normal": 5, "hard": 7}
MENU_BUTTONS = [
    ((180, 260, 160, 42), "Play", "game"),
    ((180, 315, 160, 42), "Leaderboard", "leaderboard"),
    ((180, 370, 160, 42), "Settings", "settings"),
    ((180, 425, 160, 42), "Quit", "quit"),
]
SETTINGS_BUTTONS = [
    ((300, 225, 160, 42), "Toggle Sound", "sound"),
    ((300, 280, 160, 42), "Car Color", "color"),
    ((300, 335, 160, 42), "Difficulty", "difficulty"),
    ((180, 450, 160, 42), "Save & Back", "save"),
]


class Entity:
    def __init__(self, rect, color, kind, value=0, ttl=0):
        self.rect = rect
        self.color = color
        self.kind = kind
        self.value = value
        self.ttl = ttl


class RacerApp:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("TSIS3 Racer")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 22)
        self.big = pygame.font.SysFont("arial", 38)
        self.settings = load_settings()
        self.images = self.load_images()
        self.sound = SoundBox()
        self.sound.load()
        self.username = ""
        self.state = "menu"
        self.reset_game()

    def load_images(self):
        files = {
            "player": ("player_car.bmp", (36, 58)),
            "traffic": ("traffic_car.bmp", (36, 58)),
            "coin": ("coin.bmp", (24, 24)),
            "nitro": ("nitro.bmp", (28, 28)),
            "shield": ("shield.bmp", (28, 28)),
            "repair": ("repair.bmp", (28, 28)),
            "barrier": ("barrier.bmp", (44, 28)),
            "oil": ("oil.bmp", (44, 28)),
            "bump": ("bump.bmp", (44, 28)),
            "road": ("road.bmp", (ROAD.width, HEIGHT)),
        }
        return {name: load_image(file, size) for name, (file, size) in files.items()}

    def reset_game(self):
        color = tuple(self.settings.get("car_color", [40, 120, 220]))
        self.player = Entity(pygame.Rect(LANES[1] - 18, HEIGHT - 90, 36, 58), color, "player")
        self.traffic = []
        self.obstacles = []
        self.coins = []
        self.powerups = []
        self.active_power = None
        self.active_until = 0
        self.shield = False
        self.distance = 0
        self.coins_collected = 0
        self.score = 0
        self.spawn_timer = 0
        self.game_over_saved = False

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                self.handle_event(event)

            if self.state == "game":
                self.update_game()

            self.draw()
            pygame.display.flip()
            self.clock.tick(60)
        pygame.quit()

    def handle_event(self, event):
        if self.state == "menu":
            self.handle_menu(event)
        elif self.state == "settings":
            self.handle_settings(event)
        elif self.state in {"leaderboard", "gameover"} and self.clicked(event, (180, 640, 160, 42)):
            self.open_screen("menu")
        if self.state == "gameover" and self.clicked(event, (70, 580, 160, 42)):
            self.start_game()

    def clicked(self, event, rect):
        return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and pygame.Rect(rect).collidepoint(event.pos)

    def start_game(self):
        if not self.username:
            return
        self.sound.play("menu", self.settings)
        self.reset_game()
        self.state = "game"

    def open_screen(self, state):
        self.sound.play("menu", self.settings)
        self.state = state

    def menu_click(self, event):
        for rect, _text, action in MENU_BUTTONS:
            if not self.clicked(event, rect):
                continue
            if action == "game":
                self.start_game()
            elif action == "quit":
                pygame.event.post(pygame.event.Event(pygame.QUIT))
            else:
                self.open_screen(action)
            return

    def settings_click(self, event):
        colors = [[40, 120, 220], [200, 55, 60], [45, 160, 95]]
        difficulties = ["easy", "normal", "hard"]
        for rect, _text, action in SETTINGS_BUTTONS:
            if not self.clicked(event, rect):
                continue
            self.sound.play("menu", self.settings)
            if action == "sound":
                self.settings["sound"] = not self.settings.get("sound", True)
            elif action == "color":
                current = colors.index(self.settings.get("car_color", colors[0])) if self.settings.get("car_color") in colors else 0
                self.settings["car_color"] = colors[(current + 1) % len(colors)]
            elif action == "difficulty":
                current = difficulties.index(self.settings.get("difficulty", "normal"))
                self.settings["difficulty"] = difficulties[(current + 1) % len(difficulties)]
            elif action == "save":
                save_settings(self.settings)
                self.state = "menu"
            return

    def handle_menu(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self.username = self.username[:-1]
            elif event.key == pygame.K_RETURN:
                self.start_game()
            elif event.unicode and len(self.username) < 16:
                self.username += event.unicode
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.menu_click(event)

    def handle_settings(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.settings_click(event)

    def current_speed(self):
        base = DIFFICULTY_SPEED.get(self.settings.get("difficulty", "normal"), 5)
        bonus = min(5, self.distance // 650)
        if self.active_power == "nitro" and pygame.time.get_ticks() < self.active_until:
            return base + bonus + 4
        return base + bonus

    def update_game(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            self.player.rect.x -= 6
        if keys[pygame.K_RIGHT]:
            self.player.rect.x += 6
        self.player.rect.clamp_ip(ROAD)

        speed = self.current_speed()
        self.distance += speed / 4
        self.score = int(self.distance + self.coins_collected * 15)
        self.spawn_timer += 1

        if self.spawn_timer > max(16, 52 - self.distance // 120):
            self.spawn_timer = 0
            self.spawn_entities()

        for group in (self.traffic, self.obstacles, self.coins, self.powerups):
            for item in group[:]:
                item.rect.y += speed
                if item.ttl and pygame.time.get_ticks() > item.ttl:
                    group.remove(item)
                elif item.rect.top > HEIGHT:
                    group.remove(item)

        self.check_collisions()
        if self.distance >= FINISH_DISTANCE:
            self.finish_run()

    def spawn_entities(self):
        lane = choice([x for x in LANES if abs(x - self.player.rect.centerx) > 45 or random() < 0.35])
        density = min(0.65, 0.2 + self.distance / 5000)
        if random() < density:
            self.traffic.append(Entity(pygame.Rect(lane - 18, -70, 36, 58), (180, 60, 70), "traffic"))
        if random() < 0.25 + self.distance / 8000:
            kind = choice(["barrier", "oil", "bump"])
            color = {"barrier": (230, 145, 45), "oil": (30, 30, 36), "bump": (145, 100, 60)}[kind]
            self.obstacles.append(Entity(pygame.Rect(choice(LANES) - 22, -40, 44, 28), color, kind))
        if random() < 0.45:
            value = choice([1, 2, 5])
            self.coins.append(Entity(pygame.Rect(choice(LANES) - 10, -30, 20, 20), (235, 190, 55), "coin", value))
        if random() < 0.12 and not self.powerups and self.active_power is None:
            kind = choice(["nitro", "shield", "repair"])
            color = {"nitro": (40, 170, 230), "shield": (100, 95, 220), "repair": (60, 180, 105)}[kind]
            self.powerups.append(Entity(pygame.Rect(choice(LANES) - 13, -35, 26, 26), color, kind, ttl=pygame.time.get_ticks() + 7000))

    def check_collisions(self):
        for coin in self.coins[:]:
            if self.player.rect.colliderect(coin.rect):
                self.coins.remove(coin)
                self.coins_collected += coin.value
                self.sound.play("coin", self.settings)
        for power in self.powerups[:]:
            if self.player.rect.colliderect(power.rect):
                self.powerups.remove(power)
                self.apply_power(power.kind)
                self.sound.play("powerup", self.settings)
        for hazard in self.traffic + self.obstacles:
            if self.player.rect.colliderect(hazard.rect):
                if self.shield:
                    self.sound.play("collision", self.settings)
                    self.shield = False
                    if hazard in self.traffic:
                        self.traffic.remove(hazard)
                    elif hazard in self.obstacles:
                        self.obstacles.remove(hazard)
                    return
                if hazard.kind == "oil":
                    self.sound.play("collision", self.settings)
                    self.player.rect.x += randint(-35, 35)
                    self.player.rect.clamp_ip(ROAD)
                elif hazard.kind == "bump":
                    self.sound.play("collision", self.settings)
                    self.distance = max(0, self.distance - 25)
                else:
                    self.sound.play("collision", self.settings)
                    self.finish_run()

    def apply_power(self, kind):
        self.active_power = kind
        if kind == "nitro":
            self.active_until = pygame.time.get_ticks() + 4000
        elif kind == "shield":
            self.shield = True
            self.active_until = 0
        elif kind == "repair":
            if self.obstacles:
                self.obstacles.pop(0)
            self.active_power = None

    def finish_run(self):
        if not self.game_over_saved:
            add_score(self.username, self.score, self.distance, self.coins_collected)
            self.game_over_saved = True
            self.sound.play("gameover", self.settings)
        self.state = "gameover"

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
        draw_text(self.screen, self.big, "TSIS3 Racer", (WIDTH // 2, 120), center=True)
        draw_text(self.screen, self.font, f"Name: {self.username or 'type your name'}", (WIDTH // 2, 190), center=True)
        for rect, text, _action in MENU_BUTTONS:
            Button(rect, text).draw(self.screen, self.font)

    def draw_game(self):
        self.screen.fill((65, 125, 80))
        if self.images.get("road"):
            self.screen.blit(self.images["road"], ROAD.topleft)
        else:
            pygame.draw.rect(self.screen, (55, 58, 64), ROAD)
        for x in LANES:
            pygame.draw.line(self.screen, (230, 230, 230), (x + 40, 0), (x + 40, HEIGHT), 2)
        for group in (self.traffic, self.obstacles, self.coins, self.powerups):
            for item in group:
                self.draw_entity(item)
        self.draw_entity(self.player)
        remaining = max(0, FINISH_DISTANCE - int(self.distance))
        draw_text(self.screen, self.font, f"Score {self.score}", (12, 12), (255, 255, 255))
        draw_text(self.screen, self.font, f"Coins {self.coins_collected}", (12, 38), (255, 255, 255))
        draw_text(self.screen, self.font, f"Dist {int(self.distance)} / left {remaining}", (12, 64), (255, 255, 255))
        active = "Shield" if self.shield else self.active_power or "None"
        draw_text(self.screen, self.font, f"Power {active}", (12, 90), (255, 255, 255))

    def draw_entity(self, item):
        image = self.images.get(item.kind)
        if image:
            self.screen.blit(image, item.rect)
        else:
            pygame.draw.rect(self.screen, item.color, item.rect, border_radius=6)

    def draw_leaderboard(self):
        self.screen.fill((245, 247, 250))
        draw_text(self.screen, self.big, "Top 10", (WIDTH // 2, 60), center=True)
        for index, row in enumerate(load_leaderboard(), 1):
            draw_text(self.screen, self.font, f"{index}. {row['name']}  {row['score']} pts  {row['distance']} m", (70, 105 + index * 38))
        Button((180, 640, 160, 42), "Back").draw(self.screen, self.font)

    def draw_settings(self):
        self.screen.fill((245, 247, 250))
        draw_text(self.screen, self.big, "Settings", (WIDTH // 2, 120), center=True)
        draw_text(self.screen, self.font, f"Sound: {self.settings['sound']}", (70, 238))
        draw_text(self.screen, self.font, f"Color: {self.settings['car_color']}", (70, 293))
        draw_text(self.screen, self.font, f"Difficulty: {self.settings['difficulty']}", (70, 348))
        for rect, text, _action in SETTINGS_BUTTONS:
            Button(rect, text).draw(self.screen, self.font)

    def draw_gameover(self):
        self.screen.fill((245, 247, 250))
        draw_text(self.screen, self.big, "Game Over", (WIDTH // 2, 160), center=True)
        draw_text(self.screen, self.font, f"Score: {self.score}", (WIDTH // 2, 240), center=True)
        draw_text(self.screen, self.font, f"Distance: {int(self.distance)}", (WIDTH // 2, 275), center=True)
        draw_text(self.screen, self.font, f"Coins: {self.coins_collected}", (WIDTH // 2, 310), center=True)
        Button((70, 580, 160, 42), "Retry").draw(self.screen, self.font)
        Button((180, 640, 160, 42), "Back").draw(self.screen, self.font)
