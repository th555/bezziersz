import pyray as pr

import numpy as np
import random
import datetime
import subprocess
from collections import deque

import colours

size = (1280, 800)
fps = 60
lw = 2 #linewidth
lw2 = 0
bgcol = (255,255,255,255)
linecol = (255,255,255,255)
opacity = 12 # Set to 255 for normal opaque curves

pr.set_trace_log_level(pr.LOG_WARNING | pr.LOG_ERROR)
# pr.set_config_flags(pr.FLAG_MSAA_4X_HINT) # Enable anti-aliasing, but doesn't work when recording sadly
pr.init_window(*size, 'bezziersz')
pr.set_target_fps(fps)

rseed = random.random()
print(f'seed: {rseed}') # For reproducibility



t0 = 0

class Globals:
    """ Storage of parameters that can be changed by button mashing. In addition to these some other keys have effect too,
    see README.md """
    inout = 1   # Toggle whether to fill the inside or outside part of the curve (key: Q)
    lines = 0   # Toggle whether to draw lines (curve and bezier control lines) (key: W)
    clen = 6    # Curve length in number of segments (clen - 1 when closed, clen - 2 when open) (keys: + and - )
    zoom = 0    # Zoomed in or not (key: E)
    speeds = [  # Pairs of speeds in x and y direction (keys: R and F)
        (0.1, 0.1),
        (0.1, 1),
        (1, 0.1),
        (0.1, 2),
        (2, 0.1),
        (0.1, 5),
        (5, 0.1),
        (1, 10),
        (10, 1),
        (5, 20),
        (20, 5),
        (10, 50),
        (50, 10),
    ]
    speed = speeds[0]
    close = 1   # Open-ended or closed loop curve (key: T)
    def __init__(s):
        random.seed(rseed)

g = Globals()


def midpoint(p1, p2):
    x = (p1[0] + p2[0])/2
    y = (p1[1] + p2[1])/2
    return (x, y)

def add(p1, p2):
    x = p1[0] + p2[0]
    y = p1[1] + p2[1]
    return (x, y)


class Drawable:
    def draw(s):
        pr.draw_circle_gradient(int(s.pos[0]), int(s.pos[1]), 20, (255,255,255,255), (255,0,0,255))


class Point(Drawable):
    def __init__(s, pos):
        s.pos = pos
        s.speed = (random.gauss(0, g.speed[0]), random.gauss(0, g.speed[1]))

    def move(s):
        s.pos = add(s.pos, s.speed)


class Midpoint(Drawable):
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

        s.colour = colours.rand_from_palette(exclude=bgcol) + (opacity,)
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
        num = 64
        ax, ay = s.start.pos
        bx, by = s.mid.pos
        cx, cy = s.end.pos
        lin1x = np.linspace(ax, bx, num, True)
        lin1y = np.linspace(ay, by, num, True)
        lin2x = np.linspace(bx, cx, num, True)
        lin2y = np.linspace(by, cy, num, True)
        px = lin1x + (lin2x - lin1x)/(num-1)*np.arange(num)
        py = lin1y + (lin2y - lin1y)/(num-1)*np.arange(num)
        poly = np.dstack((px, py)).tolist()[0]


        if g.inout == 0:
            s.bezier_points = [s.mid.pos] + poly
            s.bezier_points2 = [s.mid.pos] + poly[::-1]
        elif g.inout == 1:
            s.bezier_points = [] + poly
            s.bezier_points2 = [] + poly[::-1]

    def draw(s):
        pr.draw_triangle_fan(s.bezier_points, len(s.bezier_points), s.colour)
        pr.draw_triangle_fan(s.bezier_points2, len(s.bezier_points2), s.colour)
        if g.lines == 1:
            pr.draw_line_ex(s.start.pos, s.mid.pos, lw2, (0,0,0,255))
            pr.draw_line_ex(s.mid.pos, s.end.pos, lw2, (0,0,0,255))
            pr.draw_line_bezier_quad(s.start.pos, s.end.pos, s.mid.pos, lw, linecol)


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
    if g.zoom:
        for _ in range(g.clen):
            x = random.randrange(-size[0], 2*size[0])
            y = random.randrange(-size[1], 2*size[1])
            curve.add_point((x,y))
    else:
        for _ in range(g.clen):
            x = random.randrange(size[0])
            y = random.randrange(size[1])
            curve.add_point((x,y))
    if g.close:
        curve.close()


class Recorder:
    def __init__(s):
        s.recording = False
        s.t0 = 0
        s.events = deque()

        s.audio = 'sound/brimble.mp3' # Set sound here!
        s.fname = str(datetime.datetime.now()).replace(':','_').replace('-','_').replace(' ','_').split('.')[0]

        # s.ffmpeg = f"ffmpeg -r {fps} -f rawvideo -pix_fmt rgba -s {size[0]}x{size[1]} -i - -an -c:v libvpx -y {s.fname}.webm"
        # s.ffmpeg = f"ffmpeg -r {fps} -f rawvideo -pix_fmt rgba -s {size[0]}x{size[1]} -y -i - -c:v libx264 -profile:v baseline -level 3.0 -pix_fmt yuv420p {s.fname}.mp4"
        s.ffmpeg = f"ffmpeg -r {fps} -f rawvideo -pix_fmt rgba -s {size[0]}x{size[1]} -y -i - -c:v libx264 -crf 17 -pix_fmt yuv420p -preset veryslow -tune animation {s.fname}.mp4"

    def start_recording(s):
        global g
        if not s.recording:
            pr.init_audio_device()
            s.sound = pr.load_sound(s.audio)
            pr.play_sound(s.sound)

            s.t0 = pr.get_time()
            s.recording = True

            g = Globals()
            reset()

    def writeframe(s):
        img = pr.load_image_from_texture(s.texture.texture)
        data_size = img.width * img.height * 4
        img_bytes = pr.ffi.unpack(pr.ffi.cast("char*", img.data), data_size)
        s.ffmpeg_process.stdin.write(img_bytes)
        pr.unload_image(img) # Don't forget!

    def replay(s):
        global g
        g = Globals()
        reset()

        pr.stop_sound(s.sound)
        s.recording = False
        s.ffmpeg_process = subprocess.Popen(s.ffmpeg, stdin=subprocess.PIPE, shell=True)

        frame = 0
        dobreak = False
        # Have to render to texture because directly grabbing the screen results in stuttering.
        # Unfortunately no anti-aliasing in this case.
        s.texture = pr.load_render_texture(*size)
        while True:
            t = frame/fps

            while t >= s.events[0][0]:
                key = s.events.popleft()[1]
                if key == 'stop!':
                    dobreak = True
                    break
                s.handle_event(key)
            
            advance_frame(s.texture)
            s.writeframe()
            frame += 1
            if dobreak:
                break
        pr.unload_render_texture(s.texture)
        
        s.ffmpeg_process.stdin.close()
        s.ffmpeg_process.wait()

        joined_fname = s.audio.split('.')[0].split('/')[-1]+'_'+s.fname+'.mp4'
        proc2 = subprocess.Popen(f'ffmpeg -i {s.fname}.mp4 -i {s.audio} -c:v copy -c:a copy -shortest {joined_fname}', stdin=subprocess.PIPE, shell=True)
        proc2.wait()
        print(joined_fname)

        exit()


    def now(s):
        return pr.get_time() - s.t0

    def handle_event(s, key):
        rec_key = True
        if key == pr.KEY_LEFT_BRACKET:
            s.start_recording()
            rec_key = False # Don't record this one...
        if key == pr.KEY_RIGHT_BRACKET:
            s.events.append((s.now(), "stop!"))
            if s.recording:
                s.replay()

        match key:
            case pr.KEY_SPACE:
                reset()
            case pr.KEY_Q:
                g.inout = not g.inout
                curve.update()
            case pr.KEY_W:
                g.lines = not g.lines
            case pr.KEY_E:
                g.zoom = not g.zoom
                reset()
            case pr.KEY_R:
                i = g.speeds.index(g.speed)
                g.speed = g.speeds[(i+1)%len(g.speeds)]
                reset()
            case pr.KEY_F:
                i = g.speeds.index(g.speed)
                g.speed = g.speeds[(i-1)%len(g.speeds)]
                reset()
            case pr.KEY_T:
                g.close = not g.close
                reset()
            case pr.KEY_Y:
                pts = [c.mid for c in curve.beziers]
                if not g.close:
                    pts += [curve.beziers[0].start, curve.beziers[-1].end]
                pt = random.choice(pts)
                if g.zoom:
                    x = random.randrange(-size[0], 2*size[0])
                    y = random.randrange(-size[1], 2*size[1])
                else:
                    x = random.randrange(size[0])
                    y = random.randrange(size[1])
                pt.pos = (x, y)
            case pr.KEY_MINUS:
                g.clen -= 1
                reset()
            case pr.KEY_EQUAL:
                g.clen += 1
                reset()
            case _:
                rec_key = False

        if rec_key and s.recording:
            s.events.append((s.now(), key))

rec = Recorder()

reset()

def advance_frame(texture=None):
    global curve
    curve.move()
    curve.update()

    if texture:
        pr.begin_texture_mode(texture)
    else:
        pr.begin_drawing()


    # Swap these two lines to disable the fade out effect
    # pr.clear_background(bgcol)
    pr.draw_rectangle_v((0,0),size, (*bgcol,10))

    curve.draw()

    if texture:
        pr.end_texture_mode()
    else:
        pr.end_drawing()


while not pr.window_should_close():

    if pr.is_mouse_button_pressed(pr.MOUSE_BUTTON_LEFT):
        v = pr.get_mouse_position()
        curve.add_point((v.x, v.y))

    keys = []
    while(key := pr.get_key_pressed()):
        keys.append(key)

    for key in keys:
        rec.handle_event(key)
     
    advance_frame()


pr.close_window()
