import pygame


class Button:
    def __init__(self, rect, text):
        self.rect = pygame.Rect(rect)
        self.text = text

    def draw(self, screen, font):
        mouse = pygame.mouse.get_pos()
        bg = (219, 86, 54) if self.rect.collidepoint(mouse) else (255, 246, 232)
        fg = (255, 255, 255) if self.rect.collidepoint(mouse) else (39, 36, 33)
        pygame.draw.rect(screen, (43, 39, 36), self.rect.move(3, 3), border_radius=4)
        pygame.draw.rect(screen, bg, self.rect, border_radius=4)
        pygame.draw.rect(screen, (95, 72, 55), self.rect, 1, border_radius=4)
        label = font.render(self.text, True, fg)
        screen.blit(label, label.get_rect(center=self.rect.center))

    def clicked(self, event):
        return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos)


def draw_text(screen, font, text, pos, color=(28, 32, 40), center=False):
    surface = font.render(str(text), True, color)
    rect = surface.get_rect(center=pos) if center else surface.get_rect(topleft=pos)
    screen.blit(surface, rect)
