import pyautogui
import numpy as np
import time
import datetime
import pkg_resources
import serial
import re

from res.settings import DEV, MOCK
PORT_GAUSS = 'COM7'  # Nobody else is going to use this library anyway!
PORT_PSU = 'COMX'
# IMG_XPLUS = 'res/x+.png'
IMG_XPLUS = pkg_resources.resource_filename(__name__, 'res/x+.png')
# IMG_ZMINUS = 'res/z-.png'
IMG_ZMINUS = pkg_resources.resource_filename(__name__, 'res/z-.png')
IMG_LINK = pkg_resources.resource_filename(__name__, 'res/link.png')
IMG_IDLE = pkg_resources.resource_filename(__name__, 'res/idle.png')


class idleFinder(object):
    def __init__(self):
        self.x, self.y = None, None

    def find_idle(self):
        if self.x is not None:
            xy = pyautogui.locateCenterOnScreen(IMG_IDLE, minSearchTime=5,
                                                region=(self.x-100, self.y-100, self.x+100, self.y+100))
            if xy is not None:
                return xy
        xy = pyautogui.locateCenterOnScreen(IMG_IDLE, minSearchTime=5)
        if xy is not None:
            self.x, self.y = xy
            return xy
        else:
            return None


finder = idleFinder()  # singleton


class MC4000(object):
    def __init__(self):
        self._position = np.array([0, 0, 0])
        self.step_lengths = [1, 1, 1]
        # X+ X-
        # Y+ Y-
        # Z+ Z-
        self._buttons = None
        self.initialize_buttons()
        self.check_link()

    @property
    def position(self):
        return self._position

    @staticmethod
    def check_link():
        coord = pyautogui.locateCenterOnScreen(IMG_LINK, minSearchTime=5)
        if coord is None:
            raise RuntimeError('MC4000 link inactive or not up at all. Please start software and click "link".')

    def moveto(self, target, relative=False, polarity=1):
        """
        Move to coordinates.
        :param target: Target coords. Length-3 iterable: x, y, z.
        :param relative: True for relative movement.
        :param polarity: Backlash compensation. 1 for always approach in positive direction. -1 for negative direction.
        0 for no-check.
        :return: None
        """
        if relative:
            delta = np.asarray(target)
        else:
            delta = np.asarray(target) - self._position
        for i in range(3):  # x y z axes
            move_dir = 1
            if delta[i] < 0:
                move_dir = -1
            steps = abs(delta[i])
            for _ in range(steps):
                self.step(i, move_dir)
            if move_dir * polarity * steps < 0:
                self.step(i, -1 * polarity)
                self.step(i, polarity)

    def step(self, axis, direction):
        """
        Move one step in along axis and direction.
        :param axis: 0 or 1 or 2. 0 for x, 1 for y, 2 for z.
        :param direction: 1 for positive, 0 for negative.
        :return: None
        """
        if direction not in (-1, 1):
            raise ValueError('Only 1 (plus) or -1 (minus) accepted as stepping directions')
        if axis not in (0, 1, 2):
            raise ValueError('stepping axis: 0-x 1-y 2-z. No other values accepted.')
        if direction == 1:
            button_ind = 0
        else:
            button_ind = 1
        finder.find_idle()  # Make sure drive is idle before attempting
        pyautogui.moveTo(*self._buttons[axis][button_ind], duration=0.05)
        pyautogui.click()
        finder.find_idle()  # Make sure drive is idle after attempting
        if not MOCK:
            time.sleep(0.1)  # delay a little anyway.
        self._position[axis] += direction
        if DEV:
            print('pressing UI button %d, %d' % (axis, button_ind))
            print('now at %s' % str(self.position))

    def initialize_buttons(self):
        """
        Finds UI buttons and return coordinates
        :return: A bunch of coordinates on screen. Don't move the window after initialization!
        """
        coord_xplus = np.array(pyautogui.locateCenterOnScreen(IMG_XPLUS))
        if coord_xplus.size != 2:
            raise ValueError('Failed to locate X+ button. Check if MC4000 UI is running and is on top.')
        coord_zminus = np.array(pyautogui.locateCenterOnScreen(IMG_ZMINUS))
        if coord_zminus.size != 2:
            raise ValueError('Failed to locate Z- button. Check if MC4000 UI is running and is on top.')
        x1, x2 = (coord_xplus[0], coord_zminus[0])
        y1, y2, y3 = (coord_xplus[1], (coord_xplus[1] + coord_zminus[1]) / 2, coord_zminus[1])
        self._buttons = [[[x1, y1], [x2, y1]],
                         [[x1, y2], [x2, y2]],
                         [[x1, y3], [x2, y3]]]
        if DEV:
            print(coord_xplus, coord_zminus)
            print(self._buttons)


xyz = MC4000()  # singleton


if not MOCK:
    _s_gauss = serial.Serial(PORT_GAUSS, 115200, timeout=1)
    _s_gauss.write(b'DATA?>')


def read_once():
    """
    Reads latest reading from CH330 gaussmeter.
    :return: Length-3 ndarray, fields in x, y, z directions.
    """
    if MOCK:
        print('read once!')
        return np.array([1, 2, 3])
    _s_gauss.read_all()
    _s_gauss.read_until('\n')
    raw_msg = _s_gauss.read_until('\n').decode(encoding='ascii')
    pattern = '#([-+]?\d*\.{0,1}\d+)/([-+]?\d*\.{0,1}\d+)/([-+]?\d*\.{0,1}\d+)\>'
    msg = re.findall(pattern, raw_msg)
    if len(msg) == 0:
        raise ValueError('Invalid raw message received: %s' % msg)
    else:
        msg = msg[0]
    if DEV:
        print('raw: %s, trimmedL %s' % (raw_msg, msg))
    return np.array([float(x) for x in msg])


def read_n_times(reps):
    return np.average([read_once() for _ in range(reps)], axis=0)


def scan(steps, filename):
    """
    Automated scan.
    :param steps: steps to take to either side of zero. 0 for fixed. [xsteps, ysteps, zsteps].
    :param filename: Filename to save into, append mode.
    :return: None
    """
    steps = np.asarray(steps)
    with open(filename, 'a') as f:
        f.write('Test started %s\n' % str(datetime.datetime.now()))
        f.write('x,y,z,mag_x,mag_y,mag_z\n')
        for x in range(-steps[0], steps[0] + 1):
            for y in range(-steps[1], steps[1] + 1):
                for z in range(-steps[2], steps[2] + 1):
                    xyz.moveto([x, y, z])
                    while True:
                        try:
                            mag = read_once()
                            break
                        except (ValueError, RuntimeError, OSError, IndexError):
                            print("Error! retrying...")
                    pos = np.array([x, y, z]) * xyz.step_lengths
                    numbers = np.hstack((pos, mag))
                    print("measured at%.2f, %.2f %.2f: %s" % (x, y, z, str(numbers[3:])))
                    f.write(','.join([str(n) for n in numbers]) + '\n')
        xyz.moveto([0, 0, 0])
