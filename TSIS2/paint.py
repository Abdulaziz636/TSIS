from datetime import datetime
from pathlib import Path

import pygame

from tools import CANVAS_RECT, ToolButton, draw_shape, flood_fill


BASE_DIR = Path(__file__).resolve().parent
WIDTH, HEIGHT = 1000, 700
PALETTE_PANEL = pygame.Rect(880, 0, 120, 614)
TOOLBAR_RECT = pygame.Rect(0, 614, WIDTH, 86)
WHITE = (255, 255, 255)
BLACK = (24, 28, 34)
PALETTE = [
    (30, 33, 36),
    (196, 86, 56),
    (48, 103, 145),
    (54, 138, 112),
    (235, 177, 66),
    (132, 91, 165),
    (238, 238, 232),
]
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
FREE_DRAW_TOOLS = {"pencil", "eraser"}


def make_buttons():
    return [ToolButton(pygame.Rect(10 + i * 82, 626, 76, 28), name, label) for i, (name, label) in enumerate(TOOLS)]


def swatch_rect(index):
    column = index % 2
    row = index // 2
    return pygame.Rect(908 + column * 42, 82 + row * 42, 30, 30)


def clicked_tool(buttons, pos):
    for button in buttons:
        if button.rect.collidepoint(pos):
            return button.name
    return None


def clicked_color(pos):
    for i, color in enumerate(PALETTE):
        if swatch_rect(i).collidepoint(pos):
            return color
    return None


def save_canvas(canvas):
    folder = BASE_DIR / "saves"
    folder.mkdir(exist_ok=True)
    path = folder / f"paint_{datetime.now():%Y%m%d_%H%M%S}.png"
    pygame.image.save(canvas, path)
    return path


def handle_text_key(event, canvas, font, text, pos, color):
    if event.key == pygame.K_RETURN:
        canvas.blit(font.render(text, True, color), pos)
        return False, ""
    if event.key == pygame.K_ESCAPE:
        return False, ""
    if event.key == pygame.K_BACKSPACE:
        return True, text[:-1]
    if event.unicode:
        return True, text + event.unicode
    return True, text


def draw_toolbar(screen, font, buttons, tool, color, size, status):
    pygame.draw.rect(screen, (242, 236, 226), TOOLBAR_RECT)
    pygame.draw.line(screen, (177, 162, 144), (0, TOOLBAR_RECT.y), (WIDTH, TOOLBAR_RECT.y), 2)

    for button in buttons:
        button.draw(screen, font, button.name == tool)

    pygame.draw.rect(screen, (232, 225, 214), PALETTE_PANEL)
    pygame.draw.line(screen, (177, 162, 144), PALETTE_PANEL.topleft, PALETTE_PANEL.bottomleft, 2)
    screen.blit(font.render("Palette", True, BLACK), (904, 32))

    for i, palette_color in enumerate(PALETTE):
        rect = swatch_rect(i)
        border = BLACK if palette_color == color else (160, 166, 176)
        pygame.draw.rect(screen, palette_color, rect, border_radius=4)
        pygame.draw.rect(screen, border, rect, 2, border_radius=4)

    pygame.draw.rect(screen, color, (910, 274, 48, 28), border_radius=4)
    pygame.draw.rect(screen, BLACK, (910, 274, 48, 28), 2, border_radius=4)
    screen.blit(font.render("Current", True, (82, 75, 68)), (900, 314))

    screen.blit(font.render(f"Brush {size}px", True, BLACK), (18, 666))
    screen.blit(font.render(status or "Ctrl+S saves the canvas", True, (82, 75, 68)), (140, 666))


def print_controls():
    print("TSIS2 Paint controls:")
    print("  Mouse: choose a tool, pick a color, draw on the canvas.")
    print("  1 / 2 / 3: brush sizes 2px, 5px, 10px.")
    print("  Text tool: click canvas, type, Enter to place, Esc to cancel.")
    print("  Ctrl+S: save the current canvas.")


def main():
    print_controls()
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("KBTU Sketchboard")
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
                    text_mode, text = handle_text_key(event, canvas, text_font, text, text_pos, color)

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                new_tool = clicked_tool(buttons, event.pos)
                new_color = clicked_color(event.pos)

                if new_tool:
                    tool = new_tool
                    continue
                if new_color:
                    color = new_color
                    continue
                if not CANVAS_RECT.collidepoint(event.pos):
                    continue

                if tool == "fill":
                    flood_fill(canvas, canvas_mouse, color)
                elif tool == "text":
                    text_mode, text_pos, text = True, canvas_mouse, ""
                else:
                    drawing, start, last = True, canvas_mouse, canvas_mouse

            if event.type == pygame.MOUSEMOTION and drawing and tool in FREE_DRAW_TOOLS:
                draw_color = WHITE if tool == "eraser" else color
                pygame.draw.line(canvas, draw_color, last, canvas_mouse, size)
                last = canvas_mouse

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and drawing:
                drawing = False
                if tool not in FREE_DRAW_TOOLS:
                    draw_shape(canvas, tool, start, canvas_mouse, color, size)

        screen.fill((214, 207, 196))
        screen.blit(canvas, CANVAS_RECT.topleft)
        if drawing and tool not in FREE_DRAW_TOOLS:
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
