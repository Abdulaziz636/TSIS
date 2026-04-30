import pygame


class Button:
    def __init__(self, rect, text):
        self.rect = pygame.Rect(rect)
        self.text = text

    def draw(self, screen, font):
        mouse = pygame.mouse.get_pos()
        bg = (52, 92, 146) if self.rect.collidepoint(mouse) else (232, 236, 240)
        fg = (255, 255, 255) if self.rect.collidepoint(mouse) else (24, 29, 36)
        pygame.draw.rect(screen, bg, self.rect, border_radius=6)
        pygame.draw.rect(screen, (38, 53, 75), self.rect, 1, border_radius=6)
        label = font.render(self.text, True, fg)
        screen.blit(label, label.get_rect(center=self.rect.center))

    def clicked(self, event):
        return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos)


def draw_text(screen, font, text, pos, color=(28, 32, 40), center=False):
    surface = font.render(str(text), True, color)
    rect = surface.get_rect(center=pos) if center else surface.get_rect(topleft=pos)
    screen.blit(surface, rect)
