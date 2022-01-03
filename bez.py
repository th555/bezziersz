import pyray as pr
import numpy as np
import random
import colours

size = (1280, 800)
fps = 60
lw = 5 #linewidth
lw2 = 2
bgcol = (255,255,255,255)

pr.set_config_flags(pr.FLAG_MSAA_4X_HINT) # Enable anti-aliasing
pr.init_window(*size, 'bezziersz')
pr.set_target_fps(fps)

inout = 0
lines = 1
clen = 8
zoom = 0
speeds = [
    (0.1, 0.1),
    (0.1, 1),
    (1, 0.1),
    (1, 1),
    (1, 10),
    (10, 1),
    (10, 10),
    (10, 50),
    (50, 10),
]
speed = speeds[0]
close = 0


def midpoint(p1, p2):
    x = (p1[0] + p2[0])/2
    y = (p1[1] + p2[1])/2
    return (x, y)

def add(p1, p2):
    x = p1[0] + p2[0]
    y = p1[1] + p2[1]
    return (x, y)


class Point:
    def __init__(s, pos):
        ''' If between is defined, the point moves to always be at the midpoint of these two points
        and its own speed is ignored.
        '''
        s.pos = pos
        s.speed = (random.gauss(0, speed[0]), random.gauss(0, speed[1]))

    def draw(s):
        pr.draw_circle_v(s.pos, lw/2, (0,0,0,255))

    def move(s):
        s.pos = add(s.pos, s.speed)


class Midpoint:
    def __init__(s, a, b):
        '''A point between a and b'''
        s.a = a
        s.b = b

    @property
    def pos(s):
        return midpoint(s.a.pos, s.b.pos)


class Line:
    def __init__(s, start, end):
        s.start = Point(start)
        s.end = Point(end)

    def draw(s):
        pr.draw_line_ex(s.start.pos, s.end.pos, lw, (0,0,0,255))


class Bezier:
    def __init__(s, start, mid, end):
        '''
        Raylib lets us draw bezier lines easily, but since it doesn't support filled polylines or curves,
        we still have to compute our own polyline anyway and draw it as a triangle fan. Since the fan
        must be given in a specific order (cw or ccw), just store both of them at generation time and
        draw both.
        '''
        s.complete = False
        s.start = start
        s.mid = mid
        s.complete = True # set complete so the s.end assignment calls update_bezier_points
        s.end = end

        s.colour = colours.rand_from_palette(exclude=bgcol) + (200,)
        s.colour2 = colours.rand_from_palette(exclude=bgcol) + (255,)
        s.colour3 = colours.rand_from_palette(exclude=bgcol) + (255,)

    @property
    def points(s):
        return (s.start, s.mid, s.end)

    @property
    def start(s):
        return s._start

    @start.setter
    def start(s, val):
        s._start = val
        if s.complete:
            s.update_bezier_points()

    @property
    def mid(s):
        return s._mid

    @mid.setter
    def mid(s, val):
        s._mid = val
        if s.complete:
            s.update_bezier_points()

    @property
    def end(s):
        return s._end

    @end.setter
    def end(s, val):
        s._end = val
        if s.complete:
            s.update_bezier_points()


    def update_bezier_points(s):
        ''' Manually calculate bezier points and store the resulting triangle fans for later drawing. '''
        num = 24
        lin1 = list(zip(*[np.linspace(xy1, xy2, num, True).astype(int) for xy1, xy2 in zip(s.start.pos, s.mid.pos)]))
        lin2 = list(zip(*[np.linspace(xy1, xy2, num, True).astype(int) for xy1, xy2 in zip(s.mid.pos, s.end.pos)]))
        poly = [[float(np.linspace(xy1, xy2, num, True)[i]) for xy1, xy2 in zip(lin1[i], lin2[i])] for i in range(num)]
        if inout == 0:
            s.bezier_points = [s.mid.pos] + poly
            s.bezier_points2 = [s.mid.pos] + poly[::-1]
        elif inout == 1:
            s.bezier_points = [] + poly
            s.bezier_points2 = [] + poly[::-1]

    def draw(s):
        pr.draw_triangle_fan(s.bezier_points, len(s.bezier_points), s.colour)
        pr.draw_triangle_fan(s.bezier_points2, len(s.bezier_points2), s.colour)
        if lines == 1:
            pr.draw_line_ex(s.start.pos, s.mid.pos, lw2, (0,0,0,255))
            pr.draw_line_ex(s.mid.pos, s.end.pos, lw2, (0,0,0,255))
            pr.draw_line_bezier_quad(s.start.pos, s.end.pos, s.mid.pos, lw, (0,0,0,255))

    def move(s):
        for p in s.points:
            if isinstance(p, Point):
                p.move()


class Curve:
    ''' A collection of chained bezier curves '''
    def __init__(s):
        s.beziers = []

    def draw(s):
        for bez in s.beziers:
            bez.draw()

    def add_point(s, pos):
        if not s.beziers:
            s.beziers.append(Point(pos))
        else:
            last = s.beziers[-1]
            if isinstance(last, Point):
                s.beziers[-1] = Line(last.pos, pos)
            elif isinstance(last, Line):
                s.beziers[-1] = Bezier(last.start, last.end, Point(pos))
            elif isinstance(last, Bezier):
                mid = Midpoint(last.mid, last.end)
                end = last.end
                last.end = mid
                s.beziers.append(Bezier(mid, end, Point(pos)))

    def close(s):
        first = s.beziers[0]
        last = s.beziers[-1]
        new_mid = first.start
        mid_start = Midpoint(first.mid, new_mid)
        mid_end = Midpoint(last.mid, new_mid)
        first.start = mid_start
        last.end = mid_end

        s.beziers.append(Bezier(mid_start, new_mid, mid_end))

    def reset(s):
        s.beziers.clear()

    def update(s):
        for bez in s.beziers:
            bez.update_bezier_points()

    def move(s):
        for bez in s.beziers:
            bez.move()




curve = Curve()

def reset(fixed_bg=True):
    ''' fixed_bg: always use the 1st colour of the palette for the background, and take other
    colours from the rest of the palette '''
    global bgcol
    colours.randomize_palette()
    if fixed_bg:
        bgcol = colours.active_palette[0]
    else:
        bgcol = colours.rand_from_palette()
    curve.reset()
    if zoom:
        for _ in range(clen+3):
            x = random.randrange(-size[0], 2*size[0])
            y = random.randrange(-size[1], 2*size[1])
            curve.add_point((x,y))
    else:
        for _ in range(clen):
            x = random.randrange(size[0])
            y = random.randrange(size[1])
            curve.add_point((x,y))
    if close:
        curve.close()

reset()

while not pr.window_should_close():

    if pr.is_mouse_button_pressed(pr.MOUSE_BUTTON_LEFT):
        v = pr.get_mouse_position()
        curve.add_point((v.x, v.y))

    if pr.is_key_pressed(pr.KEY_SPACE):
        reset()
    if pr.is_key_pressed(pr.KEY_Q):
        inout = not inout
        curve.update()
    if pr.is_key_pressed(pr.KEY_W):
        lines = not lines
    if pr.is_key_pressed(pr.KEY_E):
        zoom = not zoom
        reset()
    if pr.is_key_pressed(pr.KEY_R):
        i = speeds.index(speed)
        speed = speeds[(i+1)%len(speeds)]
        reset()
    if pr.is_key_pressed(pr.KEY_F):
        i = speeds.index(speed)
        speed = speeds[(i-1)%len(speeds)]
        reset()
    if pr.is_key_pressed(pr.KEY_T):
        close = not close
        reset()
    if pr.is_key_pressed(pr.KEY_Y):
        bez = random.choice(curve.beziers)
        x = random.randrange(size[0])
        y = random.randrange(size[1])
        bez.mid.pos = (x, y)



    curve.move()
    curve.update()

    pr.begin_drawing()
    pr.clear_background(bgcol)
    # pr.draw_rectangle_gradient_v(0, 0, size[0], size[1], bgcol, colours.active_palette[1]+(255,))
    curve.draw()
    pr.end_drawing()

pr.close_window()
