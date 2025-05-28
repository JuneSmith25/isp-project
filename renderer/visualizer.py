import pygame as pg
import json
import os
from math import pi as PI, floor, ceil

class Debug:
    def __init__(self, obj: dict):
        self.messages: list[str] = [str(s) for s in obj['messages']]
        self.renderables = [eval(s) for s in obj['renderables']]


class Line:
    def __init__(self, p1, p2, width, color):
        self.p1 = p1
        self.p2 = p2
        self.width = width
        self.color = color


class Circle:
    def __init__(self, center, radius, color):
        self.center = center
        self.radius = radius
        self.color = color


class Duration:
    def __init__(self, obj: dict):
        self.secs = obj['secs']
        self.nanos = obj['nanos']

    def seconds(self):
        return self.secs + self.nanos / (10 ** 9)


class SimState:
    def __init__(self, obj: dict):
        self.robot_x = obj['robot_x']
        self.robot_y = obj['robot_y']
        self.robot_theta = obj['robot_theta']
        self.blade_on = obj['blade_on']
        self.debug = Debug(obj['debug'])


class SimOutput:
    def __init__(self, obj: dict):
        self.states: list[SimState] = [SimState(s) for s in obj['states']]
        self.delta_time: Duration = Duration(obj['delta_time']).seconds()
        self.wheel_distance: float = obj["wheel_distance"]
        self.wheel_radius: float = obj["wheel_radius"]
        self.max_motor_speed: float = obj["max_motor_speed"]
        self.blade_radius: float = obj["blade_radius"]

        overlay_path = obj["overlay_path"]
        if overlay_path == 'null':
            self.overlay_path = None
        else:
            self.overlay_path = overlay_path[1:-1]


SCREEN_WIDTH = 1600
SCREEN_HEIGHT = 1200
ASPECT_RATIO = SCREEN_WIDTH / SCREEN_HEIGHT

WORLD_SCALE = SCREEN_HEIGHT / 12  # pixels per meter

WORLD_WIDTH = SCREEN_WIDTH * 5
WORLD_HEIGHT = WORLD_WIDTH

camera_pos = [0, 0]


def screencoords(x, y=None):
    if isinstance(x, tuple) and y is None:
        return screencoords(x[0], x[1])

    return ((x - camera_pos[0]) * WORLD_SCALE + SCREEN_WIDTH / 2,
            -(y - camera_pos[1]) * WORLD_SCALE + SCREEN_HEIGHT / 2)


def worldcoords(x, y=None):
    if isinstance(x, tuple) and y is None:
        return worldcoords(x[0], x[1])

    cam_x, cam_y = camera_pos
    return (((x - SCREEN_WIDTH / 2) / WORLD_SCALE) + camera_pos[0],
            ((y - SCREEN_HEIGHT / 2) / -WORLD_SCALE) + camera_pos[1])


if __name__ == '__main__':

    pg.init()
    screen = pg.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

    drag_anchor = None

    dir = os.path.dirname(os.path.realpath(__file__))
    path = dir + "/.isp_auto_output"
    with open(path, 'r') as f:
        d = json.load(f)

    sim_output = SimOutput(d)
    sim_dt = sim_output.delta_time
    states = sim_output.states
    blade_radius = sim_output.blade_radius
    overlay_path = sim_output.overlay_path
    print(overlay_path)
    if overlay_path is not None:
        overlay = pg.transform.smoothscale_by(
                pg.image.load(overlay_path),
                WORLD_SCALE / 96.0)
    else:
        overlay = None

    font = pg.font.Font(pg.font.get_default_font(), floor(SCREEN_HEIGHT / 40))
    robot_sprite_path = f"{dir}/robotDS.png"
    robot_sprite = pg.image.load(robot_sprite_path)
    ratio = robot_sprite.get_height() / robot_sprite.get_width()
    robot_sprite_size = (sim_output.wheel_distance * WORLD_SCALE,
                         sim_output.wheel_distance * WORLD_SCALE * ratio)
    robot_sprite = pg.transform.smoothscale(robot_sprite, robot_sprite_size)

    grass_size = 2
    grass_texture_path = f"{dir}/grass.png"
    grass_texture = pg.image.load(grass_texture_path)
    grass_texture = pg.transform.smoothscale(
            grass_texture,
            (WORLD_SCALE * grass_size, WORLD_SCALE * grass_size))

    world_surface = screen

    clock = pg.time.Clock()
    world_timer = 0.0
    frame_by_frame = False
    frame_skip = 1

    quit = False
    while not quit:
        screen.fill((0, 0, 0))

        grass_width = grass_texture.get_width()
        grass_height = grass_texture.get_height()
        for row in range(-1, ceil(SCREEN_WIDTH / grass_width) + 8):
            for col in range(-1, ceil(SCREEN_HEIGHT / grass_height) + 8):
                ox, oy = screencoords(0, 0)
                ox, oy = ox % grass_width, oy % grass_height
                gx, gy = ox + col * grass_width, oy + row * grass_height
                world_surface.blit(grass_texture, (gx, gy))

        if overlay is not None:
            world_surface.blit(overlay, screencoords(0, 0))

        pressed = pg.key.get_pressed()

        delta_time = clock.get_time() / 1000.0
        if not frame_by_frame:
            world_timer += delta_time

        if delta_time > 1:
            print("too much lag! skipping frame")
            continue
        for event in pg.event.get():
            if event.type == pg.QUIT:
                quit = True
            if event.type == pg.WINDOWRESIZED:
                print("resizing not allowed, expect bugs")
                SCREEN_WIDTH = event.x
                SCREEN_HEIGHT = event.y
                ASPECT_RATIO = SCREEN_WIDTH / SCREEN_HEIGHT

                WORLD_SCALE = SCREEN_HEIGHT / 12  # pixels per meter

                WORLD_WIDTH = SCREEN_WIDTH * 5
                WORLD_HEIGHT = WORLD_WIDTH
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_SPACE:
                    frame_by_frame = not frame_by_frame
                if event.key == pg.K_r:
                    world_timer = 0.0
                if event.key == pg.K_LEFTBRACKET:
                    world_timer -= sim_dt * frame_skip
                if event.key == pg.K_RIGHTBRACKET:
                    world_timer += sim_dt * frame_skip
                if event.key == pg.K_MINUS:
                    frame_skip = max(frame_skip - 1 - 9*pressed[pg.K_LSHIFT], 1)
                if event.key == pg.K_EQUALS:
                    frame_skip = min(frame_skip + 1 + 9*pressed[pg.K_LSHIFT], 100)
            if event.type == pg.MOUSEBUTTONDOWN:
                drag_anchor = worldcoords(event.pos)
            if event.type == pg.MOUSEBUTTONUP:
                drag_anchor = None

        state_index = max(0, floor(world_timer / sim_dt))

        debug_messages = []

        if state_index < len(states):
            state: SimState = states[state_index]
            for i in range(state_index):
                state = states[i]
                x, y = state.robot_x, state.robot_y
                if state.blade_on:
                    pg.draw.circle(world_surface,
                                   (48, 49, 31),
                                   screencoords(x, y),
                                   blade_radius * WORLD_SCALE)

            radians = state.robot_theta
            degrees = radians * 180 / PI
            robot = pg.transform.rotate(robot_sprite, degrees)
            bx, by = screencoords(state.robot_x, state.robot_y)
            world_surface.blit(robot, (bx - robot.get_width() / 2,
                                       by - robot.get_height() / 2))
            debug = state.debug
            for r in debug.renderables:
                if isinstance(r, Circle):
                    circle: Circle = r
                    pg.draw.circle(world_surface,
                                   circle.color,
                                   screencoords(circle.center),
                                   circle.radius * WORLD_SCALE)
                if isinstance(r, Line):
                    line: Line = r
                    pg.draw.line(world_surface, line.color,
                                 screencoords(line.p1),
                                 screencoords(line.p2),
                                 line.width)
            debug_messages += debug.messages
        else:
            frame_by_frame = True
            over_by = state_index - len(states)
            exit(0)
            world_timer -= (sim_dt * over_by * 1.8)

        if drag_anchor is not None:
            mx, my = pg.mouse.get_pos()
            ax, ay = drag_anchor
            camera_pos[0] = ax - ((mx - SCREEN_WIDTH / 2) / WORLD_SCALE)
            camera_pos[1] = ay + (my - SCREEN_HEIGHT / 2) / WORLD_SCALE

        screen.blit(world_surface, (0, 0))

        fs = f"frame skip {frame_skip}" if frame_by_frame else "realtime"
        debug_messages = \
            [f"Frame {state_index}/{len(states)} ({fs})"] + debug_messages

        dec = 4
        t = str(world_timer) + "0" * dec
        debug_messages = [f"Time: {t[:t.find('.')+dec]}"] + debug_messages

        padding = 5
        y = padding
        for line in debug_messages:
            r = font.render(line, True, (0, 0, 0), (255, 255, 255))
            screen.blit(r, (padding, y))
            y += r.get_height() + padding

        pg.display.update()

        clock.tick(60)

    pg.quit()
