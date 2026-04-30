from datetime import datetime
from pathlib import Path

import pygame

from tools import CANVAS_RECT, ToolButton, draw_shape, flood_fill


BASE_DIR = Path(__file__).resolve().parent
WIDTH, HEIGHT = 1000, 700
WHITE = (255, 255, 255)
BLACK = (24, 28, 34)
PALETTE = [(20, 20, 20), (220, 50, 47), (38, 139, 210), (42, 161, 152), (133, 153, 0), (181, 137, 0), (211, 54, 130)]
TOOLS = [
    ("pencil", "Pencil"),
    ("line", "Line"),
    ("rectangle", "Rect"),
    ("circle", "Circle"),
    ("square", "Square"),
    ("right_triangle", "Right Tri"),
    ("equilateral_triangle", "Eq Tri"),
    ("rhombus", "Rhombus"),
    ("eraser", "Eraser"),
    ("fill", "Fill"),
    ("text", "Text"),
]
SIZES = {pygame.K_1: 2, pygame.K_2: 5, pygame.K_3: 10}


def make_buttons():
    return [ToolButton(pygame.Rect(8 + i * 82, 10, 76, 28), name, label) for i, (name, label) in enumerate(TOOLS)]


def save_canvas(canvas):
    folder = BASE_DIR / "saves"
    folder.mkdir(exist_ok=True)
    path = folder / f"paint_{datetime.now():%Y%m%d_%H%M%S}.png"
    pygame.image.save(canvas, path)
    return path


def draw_toolbar(screen, font, buttons, tool, color, size, status):
    pygame.draw.rect(screen, (246, 248, 250), (0, 0, WIDTH, 72))
    for button in buttons:
        button.draw(screen, font, button.name == tool)
    for i, swatch in enumerate(PALETTE):
        rect = pygame.Rect(12 + i * 34, 44, 24, 20)
        pygame.draw.rect(screen, swatch, rect, border_radius=4)
        pygame.draw.rect(screen, BLACK if swatch == color else (160, 166, 176), rect, 2, border_radius=4)
    screen.blit(font.render(f"Size: {size}px", True, BLACK), (300, 45))
    screen.blit(font.render(status, True, BLACK), (410, 45))


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("TSIS2 Paint")
    font = pygame.font.SysFont("arial", 16)
    text_font = pygame.font.SysFont("arial", 28)
    clock = pygame.time.Clock()

    buttons = make_buttons()
    canvas = pygame.Surface(CANVAS_RECT.size)
    canvas.fill(WHITE)

    tool, color, size = "pencil", BLACK, 5
    drawing, start, last = False, None, None
    text_mode, text_pos, text = False, None, ""
    status = ""

    while True:
        mouse = pygame.mouse.get_pos()
        canvas_mouse = (mouse[0] - CANVAS_RECT.x, mouse[1] - CANVAS_RECT.y)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return

            if event.type == pygame.KEYDOWN:
                if event.key in SIZES:
                    size = SIZES[event.key]
                elif event.key == pygame.K_s and event.mod & pygame.KMOD_CTRL:
                    status = f"Saved: {save_canvas(canvas).name}"
                elif text_mode:
                    if event.key == pygame.K_RETURN:
                        canvas.blit(text_font.render(text, True, color), text_pos)
                        text_mode, text = False, ""
                    elif event.key == pygame.K_ESCAPE:
                        text_mode, text = False, ""
                    elif event.key == pygame.K_BACKSPACE:
                        text = text[:-1]
                    elif event.unicode:
                        text += event.unicode

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                clicked = False
                for button in buttons:
                    if button.rect.collidepoint(event.pos):
                        tool, clicked = button.name, True
                for i, swatch in enumerate(PALETTE):
                    if pygame.Rect(12 + i * 34, 44, 24, 20).collidepoint(event.pos):
                        color, clicked = swatch, True
                if clicked or not CANVAS_RECT.collidepoint(event.pos):
                    continue
                if tool == "fill":
                    flood_fill(canvas, canvas_mouse, color)
                elif tool == "text":
                    text_mode, text_pos, text = True, canvas_mouse, ""
                else:
                    drawing, start, last = True, canvas_mouse, canvas_mouse

            if event.type == pygame.MOUSEMOTION and drawing and tool in {"pencil", "eraser"}:
                draw_color = WHITE if tool == "eraser" else color
                pygame.draw.line(canvas, draw_color, last, canvas_mouse, size)
                last = canvas_mouse

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and drawing:
                drawing = False
                if tool not in {"pencil", "eraser"}:
                    draw_shape(canvas, tool, start, canvas_mouse, color, size)

        screen.fill((222, 226, 232))
        screen.blit(canvas, CANVAS_RECT.topleft)
        if drawing and tool not in {"pencil", "eraser"}:
            preview = canvas.copy()
            draw_shape(preview, tool, start, canvas_mouse, color, size)
            screen.blit(preview, CANVAS_RECT.topleft)
        if text_mode:
            screen.blit(text_font.render(text + "|", True, color), (CANVAS_RECT.x + text_pos[0], CANVAS_RECT.y + text_pos[1]))
        draw_toolbar(screen, font, buttons, tool, color, size, status)
        pygame.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    main()
