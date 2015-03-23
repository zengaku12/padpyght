# A simple open source PadLight clone, with custom extensions for analog sticks
# and triggers.
# By Darren Alton

from ConfigParser import ConfigParser
import glob
import itertools
import os
import sys

import pygame

from padpyght.frame_buffer import FrameBuffer
from padpyght.visualizer import ButtonImage, StickImage, TriggerImage


def main(skin, joy_index):
    cfg = ConfigParser()
    if os.path.isdir(skin):
        skin = os.path.join(skin, 'skin.ini')
    cfg.read(skin)
    skin = os.path.dirname(skin)

    data = dict(cfg.items('General'))
    win_size = (int(data['width']), int(data['height']))
    try:
        bg = pygame.image.load(os.path.join(skin, data['file_background']))
    except pygame.error:
        bg = pygame.Surface(win_size)
    bg_color = tuple(int(x) for x in data['backgroundcolor'].split(','))
    screen = FrameBuffer(win_size, bg.get_size(),
                         scale_type='pixelperfect',
                         scale_smooth=int(data.get('aa', 1)),
                         background_color=bg_color)
    screen.fill(bg_color)
    screen.blit(bg, (0, 0))

    pygame.joystick.init()
    joy = pygame.joystick.Joystick(joy_index)
    joy.init()

    dpad_buttons = dict()
    btn_listeners = [set() for _ in xrange(joy.get_numbuttons())]
    axis_listeners = [set() for _ in xrange(joy.get_numaxes())]

    for sec in cfg.sections():
        data = dict(cfg.items(sec))
        if sec in ('Up', 'Down', 'Left', 'Right'):
            dpad_buttons[sec] = ButtonImage(skin, joy, screen, bg, **data)
        elif sec[:5] == 'Stick':
            tmp_obj = StickImage(skin, joy, screen, bg, **data)
            for n in tmp_obj.axes:
                if n < len(axis_listeners):
                    axis_listeners[n].add(tmp_obj)
                else:
                    print 'warning: gamepad does not have Stick axis', n
            if tmp_obj.button is not None:
                if tmp_obj.button <= len(btn_listeners):
                    btn_listeners[int(tmp_obj.button) - 1].add(tmp_obj)
                else:
                    print 'warning: gamepad does not have Stick button', \
                        tmp_obj.button
        elif sec[:6] == 'Button':
            n = int(sec[6:]) - 1
            if n < len(btn_listeners):
                img = ButtonImage(skin, joy, screen, bg, **data)
                btn_listeners[n].add(img)
            else:
                print 'warning: gamepad does not have Button', n
        elif sec[:7] == 'Trigger':
            tmp_obj = TriggerImage(skin, joy, screen, bg, **data)
            if tmp_obj.axis < len(axis_listeners):
                axis_listeners[tmp_obj.axis].add(tmp_obj)
            else:
                print 'warning: gamepad does not have Trigger axis', \
                    tmp_obj.axis
        elif sec != 'General':
            print sec, data

    for t in TriggerImage.all:
        t.update_redraws()

    dirty_screen = True
    running = True
    scale = 1.0
    while running:
        for e in pygame.event.get():
            if e.type == pygame.VIDEORESIZE:
                flags = pygame.display.get_surface().get_flags()
                pygame.display.set_mode(e.size, flags)
                screen.recompute_target_subsurface()
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_KP_MINUS:
                    scale -= 0.1
                elif e.key == pygame.K_KP_PLUS:
                    scale += 0.1
                scale = max(0.1, scale)
                w, h = win_size
                flags = pygame.display.get_surface().get_flags()
                pygame.display.set_mode((int(w*scale), int(h*scale)), flags)
                screen.recompute_target_subsurface()
            elif e.type == pygame.QUIT:
                running = False
                break
            elif e.type == pygame.JOYAXISMOTION:
                for al in axis_listeners[e.axis]:
                    al.move(e.axis, e.value)
                dirty_screen = True
            elif e.type == pygame.JOYHATMOTION:
                x, y = e.value
                for d in dpad_buttons.itervalues():
                    d._release()
                    d.draw()
                if y > 0 and 'Up' in dpad_buttons:
                    dpad_buttons['Up']._press()
                elif y < 0 and 'Down' in dpad_buttons:
                    dpad_buttons['Down']._press()
                if x < 0 and 'Left' in dpad_buttons:
                    dpad_buttons['Left']._press()
                elif x > 0 and 'Right' in dpad_buttons:
                    dpad_buttons['Right']._press()
                dirty_screen = True
            elif e.type == pygame.JOYBUTTONUP and btn_listeners[e.button]:
                for bl in btn_listeners[e.button]:
                    bl._release()
                dirty_screen = True
            elif e.type == pygame.JOYBUTTONDOWN and btn_listeners[e.button]:
                for bl in btn_listeners[e.button]:
                    bl._press()
                dirty_screen = True
        for img_set in itertools.chain(axis_listeners, btn_listeners):
            for img in img_set:
                img.draw()
        for d in dpad_buttons.itervalues():
            d.draw()
        screen.limit_fps()
        if dirty_screen:
            screen.update()
            dirty_screen = False


try:
    if len(sys.argv) > 1:
        raise ImportError  # hack
    from pgu import gui
except ImportError:
    gui = None
    _skin = 'gamecube'
    _joy_index = 0
    if len(sys.argv) > 1:
        _skin = sys.argv[1]
    if len(sys.argv) > 2:
        _joy_index = int(sys.argv[2])
    main(_skin, _joy_index)
    sys.exit()

app = gui.Desktop()
app.connect(gui.QUIT, app.quit, None)
box = gui.Container(width=320, height=400)
joy_list = gui.List(width=320, height=160)
skin_list = gui.List(width=320, height=160)
btn = gui.Button("run", width=300, height=40)
box.add(joy_list, 4, 10)
box.add(skin_list, 4, 180)
box.add(btn, 4, 350)

pygame.joystick.init()
for i in xrange(pygame.joystick.get_count()):
    name = pygame.joystick.Joystick(i).get_name()
    joy_list.add('{}: {}'.format(i, name), value=i)

for dir_name in os.listdir('.'):
    default_skin = os.path.join(dir_name, 'skin.ini')
    if os.path.exists(default_skin):
        skin_list.add(dir_name, value=default_skin)
    for alternate_skin in glob.iglob(os.path.join(dir_name, 'skin-*.ini')):
        start = alternate_skin.rfind('skin-') + 5
        alt_name = alternate_skin[start:-4]
        skin_list.add('{} ({})'.format(dir_name, alt_name),
                      value=alternate_skin)


def main_wrapper():
    if skin_list.value is not None and joy_list.value is not None:
        screen = pygame.display.get_surface()
        size, flags = screen.get_size(), screen.get_flags()
        main(skin_list.value, joy_list.value)
        pygame.display.set_mode(size, flags)
        app.repaint()

btn.connect(gui.CLICK, main_wrapper)
app.run(box)
