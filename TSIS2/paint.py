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
SIZES = {1: 2, 2: 5, 3: 10}


def make_buttons():
    buttons = []
    x = 8
    for name, label in TOOLS:
        rect = pygame.Rect(x, 10, 76, 28)
        buttons.append(ToolButton(rect, name, label))
        x += 82
    return buttons


def draw_toolbar(screen, font, buttons, active_tool, color, brush_size):
    pygame.draw.rect(screen, (246, 248, 250), (0, 0, WIDTH, 72))
    for button in buttons:
        button.draw(screen, font, active=button.name == active_tool)

    for index, swatch in enumerate(PALETTE):
        rect = pygame.Rect(12 + index * 34, 44, 24, 20)
        pygame.draw.rect(screen, swatch, rect, border_radius=4)
        border = (0, 0, 0) if swatch == color else (160, 166, 176)
        pygame.draw.rect(screen, border, rect, width=2, border_radius=4)

    size_text = font.render(f"Size: {brush_size}px", True, BLACK)
    screen.blit(size_text, (300, 45))


def save_canvas(canvas):
    output_dir = BASE_DIR / "saves"
    output_dir.mkdir(exist_ok=True)
    filename = output_dir / f"paint_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    pygame.image.save(canvas, filename)
    return filename


def print_instructions():
    print("=== TSIS2 Paint Controls ===")
    print("Mouse: click a tool, click a color, drag on the canvas to draw.")
    print("Tools: Pencil, Line, Rect, Circle, Square, Triangles, Rhombus, Eraser, Fill, Text.")
    print("Keyboard: 1/2/3 - brush size, Ctrl+S - save image.")
    print("Text tool: click canvas, type text, Enter - place text, Escape - cancel.")
    print("============================")


def main():
    pygame.init()
    pygame.font.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("TSIS2 Paint")
    font = pygame.font.SysFont("arial", 16)
    text_font = pygame.font.SysFont("arial", 28)
    clock = pygame.time.Clock()

    buttons = make_buttons()
    canvas = pygame.Surface(CANVAS_RECT.size)
    canvas.fill(WHITE)

    active_tool = "pencil"
    color = BLACK
    brush_size = SIZES[2]
    drawing = False
    start_pos = None
    last_pos = None
    text_mode = False
    text_pos = None
    text_value = ""
    status = ""

    print_instructions()

    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()
        canvas_mouse = (mouse_pos[0] - CANVAS_RECT.x, mouse_pos[1] - CANVAS_RECT.y)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                print("Paint closed.")

            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                    brush_size = SIZES[int(event.unicode)]
                    print(f"Brush size changed to {brush_size}px.")
                elif event.key == pygame.K_s and (event.mod & pygame.KMOD_CTRL):
                    saved_file = save_canvas(canvas)
                    status = f"Saved: {saved_file.name}"
                    print(f"Canvas saved to {saved_file}.")
                elif text_mode:
                    if event.key == pygame.K_RETURN:
                        rendered = text_font.render(text_value, True, color)
                        canvas.blit(rendered, text_pos)
                        text_mode = False
                        print(f"Text placed: {text_value}.")
                        text_value = ""
                    elif event.key == pygame.K_ESCAPE:
                        text_mode = False
                        text_value = ""
                        print("Text input cancelled.")
                    elif event.key == pygame.K_BACKSPACE:
                        text_value = text_value[:-1]
                    elif event.unicode:
                        text_value += event.unicode

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                clicked_toolbar = False
                for button in buttons:
                    if button.rect.collidepoint(event.pos):
                        active_tool = button.name
                        clicked_toolbar = True
                        print(f"Tool selected: {button.label}.")
                for index, swatch in enumerate(PALETTE):
                    if pygame.Rect(12 + index * 34, 44, 24, 20).collidepoint(event.pos):
                        color = swatch
                        clicked_toolbar = True
                        print(f"Color selected: RGB{color}.")

                if clicked_toolbar:
                    continue
                if not CANVAS_RECT.collidepoint(event.pos):
                    continue

                if active_tool == "fill":
                    flood_fill(canvas, canvas_mouse, color)
                    print(f"Fill applied at {canvas_mouse} with RGB{color}.")
                elif active_tool == "text":
                    text_mode = True
                    text_pos = canvas_mouse
                    text_value = ""
                    print(f"Text input started at {text_pos}.")
                else:
                    drawing = True
                    start_pos = canvas_mouse
                    last_pos = canvas_mouse
                    print(f"Started {active_tool} at {start_pos}.")

            elif event.type == pygame.MOUSEMOTION and drawing:
                if active_tool in {"pencil", "eraser"} and CANVAS_RECT.collidepoint(event.pos):
                    draw_color = WHITE if active_tool == "eraser" else color
                    pygame.draw.line(canvas, draw_color, last_pos, canvas_mouse, brush_size)
                    last_pos = canvas_mouse

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and drawing:
                drawing = False
                if active_tool not in {"pencil", "eraser"}:
                    draw_shape(canvas, active_tool, start_pos, canvas_mouse, color, brush_size)
                    print(f"Drew {active_tool} from {start_pos} to {canvas_mouse}.")
                else:
                    print(f"Finished {active_tool} stroke at {canvas_mouse}.")

        screen.fill((222, 226, 232))
        screen.blit(canvas, CANVAS_RECT.topleft)

        if drawing and active_tool not in {"pencil", "eraser"}:
            preview = canvas.copy()
            draw_shape(preview, active_tool, start_pos, canvas_mouse, color, brush_size)
            screen.blit(preview, CANVAS_RECT.topleft)

        if text_mode:
            rendered = text_font.render(text_value + "|", True, color)
            screen.blit(rendered, (CANVAS_RECT.x + text_pos[0], CANVAS_RECT.y + text_pos[1]))

        draw_toolbar(screen, font, buttons, active_tool, color, brush_size)
        if status:
            screen.blit(font.render(status, True, BLACK), (410, 45))
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
