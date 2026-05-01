from collections import deque

import pygame


CANVAS_RECT = pygame.Rect(0, 0, 880, 614)


class ToolButton:
    def __init__(self, rect, name, label):
        self.rect = rect
        self.name = name
        self.label = label

    def draw(self, screen, font, active=False):
        bg = (196, 86, 56) if active else (252, 250, 245)
        border = (126, 49, 34) if active else (180, 171, 158)
        text_color = (255, 255, 255) if active else (38, 35, 32)

        shadow = self.rect.move(2, 2)
        pygame.draw.rect(screen, (205, 199, 190), shadow, border_radius=5)
        pygame.draw.rect(screen, bg, self.rect, border_radius=5)
        pygame.draw.rect(screen, border, self.rect, 1, border_radius=5)
        text = font.render(self.label, True, text_color)
        screen.blit(text, text.get_rect(center=self.rect.center))


def flood_fill(surface, start_pos, new_color):
    width, height = surface.get_size()
    x, y = start_pos
    if not (0 <= x < width and 0 <= y < height):
        return

    target_color = surface.get_at((x, y))
    replacement = pygame.Color(*new_color)
    if target_color == replacement:
        return

    queue = deque([(x, y)])
    while queue:
        px, py = queue.popleft()
        if not (0 <= px < width and 0 <= py < height):
            continue
        if surface.get_at((px, py)) != target_color:
            continue
        surface.set_at((px, py), replacement)
        queue.extend(((px + 1, py), (px - 1, py), (px, py + 1), (px, py - 1)))


def draw_shape(surface, tool, start, end, color, width):
    x1, y1 = start
    x2, y2 = end
    rect = pygame.Rect(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))

    if tool == "line":
        pygame.draw.line(surface, color, start, end, width)
    elif tool == "rectangle":
        pygame.draw.rect(surface, color, rect, width)
    elif tool == "circle":
        radius = max(rect.width, rect.height) // 2
        pygame.draw.circle(surface, color, rect.center, radius, width)
    elif tool == "square":
        side = max(rect.width, rect.height)
        square = pygame.Rect(x1, y1, side if x2 >= x1 else -side, side if y2 >= y1 else -side)
        square.normalize()
        pygame.draw.rect(surface, color, square, width)
    elif tool == "right_triangle":
        pygame.draw.polygon(surface, color, [(x1, y1), (x1, y2), (x2, y2)], width)
    elif tool == "equilateral_triangle":
        points = [(rect.centerx, rect.top), (rect.left, rect.bottom), (rect.right, rect.bottom)]
        pygame.draw.polygon(surface, color, points, width)
    elif tool == "rhombus":
        points = [
            (rect.centerx, rect.top),
            (rect.right, rect.centery),
            (rect.centerx, rect.bottom),
            (rect.left, rect.centery),
        ]
        pygame.draw.polygon(surface, color, points, width)
