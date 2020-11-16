# coding: utf-8
# license: GPLv3

# Стрельников Андрей и Билецкая Злата
from typing import Tuple, Callable

import pygame
from pygame.font import SysFont, get_default_font
from tkinter.filedialog import *
from solar_vis import calculate_scale_factor, create_star_image, create_planet_image, update_object_position, \
    window_width, window_height
from solar_model import recalculate_space_objects_positions
from solar_input import read_space_objects_data_from_file, write_space_objects_data_to_file

pygame.init()

perform_execution = False
"""Флаг цикличности выполнения расчёта"""

physical_time = 999
"""Физическое время от начала расчёта.
Тип: float"""

displayed_time = None
"""Отображаемое на экране время.
Тип: переменная tkinter"""

time_step = None
"""Шаг по времени при моделировании.
Тип: float"""

space_objects = []
"""Список космических объектов."""

screen = pygame.display.set_mode((window_width, window_height))
red = (255, 0, 0)
blue = (0, 0, 255)
yellow = (255, 255, 0)
green = (0, 255, 0)
magenta = (255, 0, 255)
cyan = (0, 255, 255)
black = (0, 0, 0)
white = (255, 255, 255)
orange = (255, 165, 0)
gray = (128, 128, 128)


def _round_rect(surface, rect, color, radius=None):
    trans = (255, 255, 1)
    if not radius:
        pygame.draw.rect(surface, color, rect)
        return

    radius = min(radius, rect.width / 2, rect.height / 2)

    r = rect.inflate(-radius * 2, -radius * 2)
    for corn in (r.topleft, r.topright, r.bottomleft, r.bottomright):
        pygame.draw.circle(surface, color, corn, radius)
    pygame.draw.rect(surface, color, r.inflate(radius * 2, 0))
    pygame.draw.rect(surface, color, r.inflate(0, radius * 2))


class Button:
    def __init__(
            self,
            surface,
            x: int,
            y: int,
            click_handler: Callable = lambda: None,
            text="",
            width=0,
            height=0,
            color: Tuple[int] = None,
            border_width=0,
            hover_color=None,
            clicked_color=None,
            border_radius=0,
            border_color=None,
            font: pygame.font.Font = None,
            font_color=None
    ):

        self.surface = surface
        self.x = x
        self.y = y
        self.click_handler = click_handler
        self.color = color or (224, 224, 224)
        self.border_width = border_width
        self.hover_color = hover_color
        self.clicked_color = clicked_color
        self.border_radius = border_radius
        self.text = text

        if font is None:
            self.font = SysFont('couriernew', 20)

        text_size = self.font.size(text)
        self.width = width or text_size[0] + self.border_width + 2
        self.height = height or text_size[1] + self.border_width + 2
        self.font_color = font_color or (0, 0, 0)

        self.hovered = False
        self.clicked = False
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)

    def __repr__(self):
        return f'<Button "{self.text}" at ({self.x}, {self.y})>'

    def __contains__(self, point: Tuple[int]):
        return self.rect.collidepoint(point)

    def draw(self):
        color = self.color
        if self.clicked and self.clicked_color:
            color = self.clicked_color
        elif self.hovered and self.hover_color:
            color = self.hover_color

        if not self.border_width:
            _round_rect(self.surface, self.rect, color, self.border_radius)
        else:
            _round_rect(self.surface, self.rect, (0, 0, 0), self.border_radius)
            _round_rect(
                self.surface,
                self.rect.inflate(-self.border_width, -self.border_width),
                color,
                self.border_radius
            )
        text = self.font.render(self.text, 1, self.font_color)
        place = text.get_rect(center=self.rect.center)
        self.surface.blit(text, place)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hovered = event.pos in self
        elif event.type == pygame.MOUSEBUTTONDOWN and event.pos in self:
            self.clicked = True
            self.click_handler()
        elif event.type == pygame.MOUSEBUTTONUP:
            self.clicked = False

    def handle_events(self, event_list):
        for event in event_list:
            self.handle_event(event)


def execution():
    """Функция исполнения -- выполняется циклически, вызывая обработку всех небесных тел,
    а также обновляя их положение на экране.
    Цикличность выполнения зависит от значения глобальной переменной perform_execution.
    При perform_execution == True функция запрашивает вызов самой себя по таймеру через от 1 мс до 100 мс.
    """
    global physical_time
    recalculate_space_objects_positions(space_objects, physical_time)
    for body in space_objects:
        update_object_position(screen, body)


def start_execution():
    """Обработчик события нажатия на кнопку Start.
    Запускает циклическое исполнение функции execution.
    """
    global perform_execution
    perform_execution = True
    start_button.text = "Pause"
    start_button.click_handler = stop_execution
    print('Started execution...')


def stop_execution():
    """Обработчик события нажатия на кнопку Start.
    Останавливает циклическое исполнение функции execution.
    """
    global perform_execution
    perform_execution = False
    start_button.text = "Start"
    start_button.click_handler = start_execution
    print('Paused execution.')


def open_file_dialog():
    """Открывает диалоговое окно выбора имени файла и вызывает
    функцию считывания параметров системы небесных тел из данного файла.
    Считанные объекты сохраняются в глобальный список space_objects
    """
    global space_objects
    global perform_execution
    perform_execution = False
    pygame.display.update()  # удаление старых изображений планет
    in_filename = askopenfilename(filetypes=(("Text file", ".txt"),))
    space_objects = read_space_objects_data_from_file(in_filename)
    max_distance = max([max(abs(obj.x), abs(obj.y)) for obj in space_objects])
    calculate_scale_factor(max_distance)
    draw_planets()


def draw_planets():
    for obj in space_objects:
        if obj.type == 'star':
            fix_color(obj)
            create_star_image(screen, obj)
        elif obj.type == 'planet':
            fix_color(obj)
            create_planet_image(screen, obj)
        else:
            raise AssertionError()


def fix_color(body):
    if body.color == 'red':
        body.color = red
    if body.color == 'blue':
        body.color = blue
    if body.color == 'yellow':
        body.color = yellow
    if body.color == 'green':
        body.color = green
    if body.color == 'magenta':
        body.color = magenta
    if body.color == 'cyan':
        body.color = cyan
    if body.color == 'black':
        body.color = black
    if body.color == 'white':
        body.color = white
    if body.color == 'gray':
        body.color = gray
    if body.color == 'orange':
        body.color = orange


def save_file_dialog():
    """Открывает диалоговое окно выбора имени файла и вызывает
    функцию считывания параметров системы небесных тел из данного файла.
    Считанные объекты сохраняются в глобальный список space_objects
    """
    out_filename = asksaveasfilename(filetypes=(("Text file", ".txt"),))
    write_space_objects_data_to_file(out_filename, space_objects)


def speed_up():
    global physical_time
    physical_time *= 2


def speed_down():
    global physical_time
    physical_time //= 2


def draw_interface():
    pygame.draw.rect(screen, gray, ([0, window_height - 100], [window_width, window_height]))
    start_button.draw()
    save_button.draw()
    open_button.draw()
    speed_down_button.draw()
    speed_up_button.draw()


start_button = Button(screen, 1, 1)
start_button = Button(screen, (window_width - 100) // 2, window_height - 50, start_execution, text="Start", width=60,
                      height=40, hover_color=white, clicked_color=red)
open_button = Button(screen, window_width // 2 + 50, window_height - 50, open_file_dialog, text="Open file", width=120,
                     height=40, hover_color=white, clicked_color=red)
save_button = Button(screen, window_width // 2 + 200, window_height - 50, save_file_dialog, text="Save file", width=120,
                     height=40, hover_color=white, clicked_color=red)
speed_up_button = Button(screen, window_width // 2 - 200, window_height - 50, speed_up, text="Speed up",
                         width=120, height=40, hover_color=white, clicked_color=red)
speed_down_button = Button(screen, window_width // 2 - 350, window_height - 50, speed_down, text="Speed down",
                           width=120, height=40, hover_color=white, clicked_color=red)


def main():
    """Главная функция главного модуля.
    """
    global physical_time
    global displayed_time
    global time_step
    global screen
    global start_button
    global perform_execution

    print('Modelling started!')
    FPS = 30
    pygame.display.set_caption("SolarSystem")
    clock = pygame.time.Clock()
    pygame.display.update()

    perform_execution = True
    while True:
        clock.tick(FPS)
        for event in pygame.event.get():
            start_button.handle_event(event)
            open_button.handle_event(event)
            save_button.handle_event(event)
            speed_down_button.handle_event(event)
            speed_up_button.handle_event(event)
            if event.type == pygame.QUIT:
                exit()

        # космическое пространство отображается на экране
        if perform_execution:
            execution()
        draw_planets()
        draw_interface()
        pygame.display.update()
        screen.fill((black))
    pygame.quit()
    print('Modelling finished!')


if __name__ == "__main__":
    main()
