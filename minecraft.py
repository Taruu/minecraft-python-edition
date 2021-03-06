# TODO rewrite to multiply files!!!!
from __future__ import division

import random as rand
import pickle
import os
import sys
import math
import random
import time
import math

from collections import deque
from pyglet import image
from pyglet.gl import *
from pyglet.graphics import TextureGroup
from pyglet.window import key, mouse
from pyglet.sprite import Sprite
from pyglet.media import *
from PIL import Image, ImageDraw
from copy import deepcopy

from scripts.noise_gen import *

# image load

# sky = pyglet.resource.image ('textures/ui/sky.png')
# inven_image = pyglet.resource.image ('textures/ui/inven.png')
# music
music_list = ['world', 'world2', 'world3', 'world4']  # TODO fix to serch music
player = pyglet.media.Player()
music = pyglet.media.load('music/' + random.choice(music_list) + '.wav')
# player.loop = True
player.queue(music)
# player.eos_action = 'loop'
player.play()
debug_mode = 1
# player.eos_action = pyglet.media.SourceGroup.loop
#
time_world = 0
time_music = 0

TICKS_PER_SEC = 120

# Size of sectors used to ease block loading.
SECTOR_SIZE = 16

WALKING_SPEED = 5
FLYING_SPEED = 15

CAVESW = 3
CAVESL = [20, 100]
CAVESNUM = 10

# sounds
soundpl = pyglet.media.Player()
sound = pyglet.media.load('sounds/break.wav')
soundpl.queue(sound)

# player.eos_action = pyglet.media.SourceGroup.loop


# finish
GRAVITY = 20.0
MAX_JUMP_HEIGHT = 1.5  # About the height of a block.
# To derive the formula for calculating jump speed, first solve
#    v_t = v_0 + a * t
# for the time at which you achieve maximum height, where a is the acceleration
# due to gravity and v_t = 0. This gives:
#    t = - v_0 / a
# Use t and the desired MAX_JUMP_HEIGHT to solve for v_0 (jump speed) in
#    s = s_0 + v_0 * t + (a * t^2) / 2
JUMP_SPEED = math.sqrt(2 * GRAVITY * MAX_JUMP_HEIGHT)
TERMINAL_VELOCITY = 90

PLAYER_HEIGHT = 2.5

if sys.version_info[0] >= 3:
    xrange = range


def cube_vertices(x, y, z, n):
    """ Return the vertices of the cube at position x, y, z with size 2*n.

    """
    return [
        x - n, y + n, z - n, x - n, y + n, z + n, x + n, y + n, z + n, x + n, y + n, z - n,  # top
        x - n, y - n, z - n, x + n, y - n, z - n, x + n, y - n, z + n, x - n, y - n, z + n,  # bottom
        x - n, y - n, z - n, x - n, y - n, z + n, x - n, y + n, z + n, x - n, y + n, z - n,  # left
        x + n, y - n, z + n, x + n, y - n, z - n, x + n, y + n, z - n, x + n, y + n, z + n,  # right
        x - n, y - n, z + n, x + n, y - n, z + n, x + n, y + n, z + n, x - n, y + n, z + n,  # front
        x + n, y - n, z - n, x - n, y - n, z - n, x - n, y + n, z - n, x + n, y + n, z - n,  # back
    ]


def tex_coord(x, y, n=8):
    """ Return the bounding vertices of the texture square.

    """
    m = 1.0 / n
    dx = x * m
    dy = y * m
    return dx, dy, dx + m, dy, dx + m, dy + m, dx, dy + m


def tex_coords(top, bottom, side):
    """ Return a list of the texture squares for the top, bottom and side.

    """
    top = tex_coord(*top)
    bottom = tex_coord(*bottom)
    side = tex_coord(*side)
    result = []
    result.extend(top)
    result.extend(bottom)
    result.extend(side * 4)
    return result


def parse_tex_atlas(path, mas):
    file = open(path, "r")
    data = file.readlines()
    stage = 0
    name = ""
    path = ""
    for i in data:
        for c in i:
            if c != "\n":
                if stage == 0:
                    if c != " ":
                        name += c
                    else:
                        stage += 1
                elif stage == 1:
                    if c == "$":
                        stage = 0
                        mas[name] = [TextureGroup(image.load(path).get_texture()), path]
                        name = ""
                        path = ""
                    elif c == "&":
                        stage = -1
                        mas[name] = [TextureGroup(image.load(path).get_texture()), path]
                    else:
                        path += c
    return mas


def parse_blocks(path, mas):
    name = ""
    n1 = ""
    n2 = ""
    tempN = ""
    texCords = []
    tags = []
    atlas = ""
    file = open(path, "r")
    data = file.readlines()
    stage = 0
    for i in data:
        for c in i:
            if c != "\n":
                if stage == 0:
                    if c != " ":
                        name += c
                    else:
                        stage += 1
                elif stage == 1:
                    if c == "#":
                        stage += 1
                    elif c == " ":
                        if n1 != "" and n2 != "":
                            texCords.append(tuple([int(n1), int(n2)]))
                            n1 = ""
                            n2 = ""
                    elif n1 == "":
                        n1 += c
                    elif n2 == "":
                        n2 += c
                elif stage == 2:
                    if c == "#":
                        stage += 1
                    else:
                        atlas += c
                elif stage == 3:
                    if c == "$":
                        mas[name] = [tex_coords(tuple(texCords[0]), tuple(texCords[1]), tuple(texCords[2])), atlas,
                                     texCords, tags]
                        name = ""
                        n1 = ""
                        n2 = ""
                        atlas = ""
                        texCords = []
                        tags = []
                        stage = 0
                    elif c == "&":
                        mas[name] = [tex_coords(tuple(texCords[0]), tuple(texCords[1]), tuple(texCords[2])), atlas,
                                     texCords, tags]
                        name = ""
                        n1 = ""
                        n2 = ""
                        atlas = ""
                        texCords = []
                        tags = []
                        stage = -1
                    elif c == " ":
                        tags.append(tempN)
                        tempN = ""
                    else:
                        tempN += c
    return mas


FACES = [
    (0, 1, 0),
    (0, -1, 0),
    (-1, 0, 0),
    (1, 0, 0),
    (0, 0, 1),
    (0, 0, -1),
]


def normalize(position):
    """ Accepts `position` of arbitrary precision and returns the block
    containing that position.

    Parameters
    ----------
    position : tuple of len 3

    Returns
    -------
    block_position : tuple of ints of len 3

    """
    x, y, z = position
    x, y, z = (int(round(x)), int(round(y)), int(round(z)))
    return (x, y, z)


def sectorize(position):
    """ Returns a tuple representing the sector for the given `position`.

    Parameters
    ----------
    position : tuple of len 3

    Returns
    -------
    sector : tuple of len 3

    """
    x, y, z = normalize(position)
    x, y, z = x // SECTOR_SIZE, y // SECTOR_SIZE, z // SECTOR_SIZE
    return (x, 0, z)


class Button:
    def __init__(self, x, y, w, h, on, off):
        self.x, self.y = x, y
        self.imgs = [image.load(off), image.load(on)]
        self.on = False
        self.sprite = Sprite(self.imgs[0])
        self.sprite.x = x
        self.sprite.y = y
        self.w, self.h = w, h
        self.sprite.scale_x = self.w / 910
        self.sprite.scale_y = self.h / 290

    def draw(self):
        self.sprite.image = self.imgs[int(self.on)]
        self.sprite.draw()

    def isHit(self, x, y, b, o, args):
        if b == 1:
            if x > self.x and x < self.x + self.w:
                if y > self.y and y < self.y + self.h:
                    self.on = True
                    self.run(o, args)
        elif b == -1:
            if x > self.x and x < self.x + self.w:
                if y > self.y and y < self.y + self.h:
                    self.on = False

    def run(self, f, args):
        f(args)


class Model(object):

    def __init__(self):
        self.delta = 0

        # A Batch is a collection of vertex lists for batched rendering.
        self.batch = pyglet.graphics.Batch()

        # A TextureGroup manages an OpenGL texture.
        self.atlases = dict()
        self.blocks = dict()
        self.blocksAtlases = dict()
        self.blocksSpritesAtlases = dict()
        self.atlases = parse_tex_atlas("atlas.atl", self.atlases)
        self.blocks = parse_blocks("blocks.bls", self.blocks)
        files = os.listdir("mods/")
        for i in files:
            if i[-1] == "l":
                self.atlases = parse_tex_atlas("mods/" + i, self.atlases)
            elif i[-1] == "s":
                self.blocks = parse_blocks("mods/" + i, self.blocks)
        for i in self.atlases.keys():
            pa = self.atlases[i][1]
            img = Image.open(pa)
            img = img.resize((img.size[0] // 2, img.size[1] // 2))
            p = "tempFiles/" + pa
            z = 0
            while True:
                if p[z] == "/":
                    p = p[:z]
                    break
                z += 1
            tempPath = ""
            for c in p:
                if c != "/":
                    tempPath += c
                else:
                    os.makedirs(tempPath)
            img.save("tempFiles/" + pa)
            self.blocksSpritesAtlases[i] = image.load("tempFiles/" + pa)

        # Block's sprite group
        self.blocksSprites = dict()
        keys = self.blocks.keys()
        for i in keys:
            self.blocksSprites[i] = self.blocksSpritesAtlases[self.blocks[i][1]].get_region(
                self.blocks[i][2][0][0] * 32, self.blocks[i][2][0][1] * 32, 32, 32
            )

        # A mapping from position to the texture of the block at that position.
        # This defines all the blocks that are currently in the world.
        self.world = {}

        # Same mapping as `world` but only contains blocks that are shown.
        self.shown = {}

        # Mapping from position to a pyglet `VertextList` for all shown blocks.
        self._shown = {}

        # Mapping from sector to a list of positions inside that sector.
        self.sectors = {}

        # Simple function queue implementation. The queue is populated with
        # _show_block() and _hide_block() calls
        self.queue = deque()

        self._initialize()

    def _initialize(self):
        """ Initialize the world by placing all the blocks.

        """
        n = 100  # size of the world
        s = 1  # step size
        y = 0  # initial y height
        maxHeight = 30
        gen = NoiseGen(generate(n, maxHeight))
        n = n * 2

        # too lazy to do this properly lol
        heightMap = [4]
        for x in xrange(0, n, s):
            for z in xrange(0, n, s):
                heightMap.append(0)
        for x in xrange(0, n, s):
            for z in xrange(0, n, s):
                heightMap[z + x * n] = int(gen.getHeight(x, z))

        # Generate the world
        for x in xrange(0, n, s):
            for z in xrange(0, n, s):
                h = heightMap[z + x * n]
                if (h < 17):
                    self.add_block((x, h, z), self.blocks["SAND"], immediate=True)
                    for y in range(h, 16):
                        self.add_block((x, y, z), self.blocks["WATER"], immediate=True)
                    for y in xrange(h - 1, 0, -1):
                        self.add_block((x, y, z), self.blocks["STONE"], immediate=True)
                    continue
                elif (h < 18):
                    self.add_block((x, h, z), self.blocks["SAND"], immediate=True)
                else:
                    self.add_block((x, h, z), self.blocks["GRASS"], immediate=True)
                for y in xrange(h - 1, 0, -1):
                    self.add_block((x, y, z), self.blocks["STONE"], immediate=True)
                # Maybe add tree at this (x, z)
                if (h > 10):
                    if random.randrange(0, 1000000) > 999900:
                        cobblestone = (2)
                        for y in xrange(h + 0, h + cobblestone):
                            self.add_block((x, y, z), self.blocks["OLDR"], immediate=False)
                if (h > 20):
                    if random.randrange(0, 1000) > 990:
                        treeHeight = random.randrange(3, 5)
                        # Tree trunk
                        GENERATABLETREES = [[self.blocks["WOOD"], self.blocks["BWOOD"]],
                                            [self.blocks["LEAF"], self.blocks["BLEAF"]]]
                        wind = random.randrange(0, len(GENERATABLETREES[0]))
                        for y in xrange(h + 1, h + treeHeight):
                            self.add_block((x, y, z), GENERATABLETREES[0][wind], immediate=False)
                        # Tree leaves
                        leafh = h + treeHeight
                        for lz in xrange(z + -1, z + 2):
                            for lx in xrange(x + -1, x + 2):
                                for ly in xrange(2):
                                    self.add_block((lx, leafh + ly, lz), GENERATABLETREES[1][wind], immediate=False)
                        # for y in xrange(1):
                        # for x in xrange(1):
                        # self.add_block((x, y, z), OLDR, immediate=False)
        for i in range(CAVESNUM):
            looping = True
            x = random.randint(0, n)
            y = random.randint(0, n)
            z = random.randint(0, n)
            tx = x + random.randint(-10, 11)
            ty = y + random.randint(-10, 11)
            tz = z + random.randint(-10, 11)
            curlen = 0
            maxlen = random.randint(CAVESL[0], CAVESL[1])
            while looping:
                curlen += 1
                if curlen >= maxlen:
                    looping = False
                if tx == x:
                    tx = x + random.randint(-10, 11)
                    tx = self._bound(0, n, tx)
                if ty == y:
                    ty = y + random.randint(-10, 11)
                    ty = self._bound(0, 48, ty)
                if tz == z:
                    tz = z + random.randint(-10, 11)
                    tz = self._bound(0, n, tz)
                if x < tx:
                    x += 1
                elif x > tx:
                    x -= 1
                if y < ty:
                    y += 1
                elif y > ty:
                    y -= 1
                if z < tz:
                    z += 1
                elif z > tz:
                    z -= 1

                w = random.randint(CAVESW - 1, CAVESW)
                for xx in range(-w, w):
                    for yy in range(-w, w):
                        for zz in range(-w, w):
                            if math.sqrt(xx * xx + yy * yy) <= w and math.sqrt(xx * xx + zz * zz) <= w:
                                if x + xx > 0 and y + yy > 0 and z + zz > 0:
                                    try:
                                        self.remove_block((x + xx, y + yy, z + zz), True)
                                    except:
                                        pass
                x = self._bound(0, n, x)
                z = self._bound(0, n, z)
                y = self._bound(0, 50, y)

    def _bound(self, mn, mx, v):
        if v <= mn:
            v = mx
        elif v >= mx:
            v = mn
        return v

    def hit_test(self, position, vector, max_distance=6):
        """ Line of sight search from current position. If a block is
        intersected it is returned, along with the block previously in the line
        of sight. If no block is found, return None, None.

        Parameters
        ----------
        position : tuple of len 3
            The (x, y, z) position to check visibility from.
        vector : tuple of len 3
            The line of sight vector.
        max_distance : int
            How many blocks away to search for a hit.

        """
        m = 8
        x, y, z = position
        dx, dy, dz = vector
        previous = None
        for _ in xrange(max_distance * m):
            key = normalize((x, y, z))
            if key != previous and key in self.world:
                return key, previous
            previous = key
            x, y, z = x + dx / m, y + dy / m, z + dz / m
        return None, None

    def exposed(self, position):
        """ Returns False is given `position` is surrounded on all 6 sides by
        blocks, True otherwise.

        """
        x, y, z = position
        for dx, dy, dz in FACES:
            if (x + dx, y + dy, z + dz) not in self.world:
                return True
        return False

    def add_block(self, position, texture, immediate=True):
        """ Add a block with the given `texture` and `position` to the world.

        Parameters
        ----------
        position : tuple of len 3
            The (x, y, z) position of the block to add.
        texture : list of len 3
            The coordinates of the texture squares. Use `tex_coords()` to
            generate.
        immediate : bool
            Whether or not to draw the block immediately.

        """
        if position in self.world:
            self.remove_block(position, immediate)
        self.world[position] = texture
        self.sectors.setdefault(sectorize(position), []).append(position)
        if immediate:
            if self.exposed(position):
                self.show_block(position)
            self.check_neighbors(position)

    def remove_block(self, position, immediate=True, byPlayer=False):
        """ Remove the block at the given `position`.

        Parameters
        ----------
        position : tuple of len 3
            The (x, y, z) position of the block to remove.
        immediate : bool
            Whether or not to immediately remove block from canvas.

        """
        del self.world[position]
        self.sectors[sectorize(position)].remove(position)
        if immediate:
            if position in self.shown:
                self.hide_block(position)
            self.check_neighbors(position)
        if byPlayer:
            pass

    def check_neighbors(self, position):
        """ Check all blocks surrounding `position` and ensure their visual
        state is current. This means hiding blocks that are not exposed and
        ensuring that all exposed blocks are shown. Usually used after a block
        is added or removed.

        """
        x, y, z = position
        for dx, dy, dz in FACES:
            key = (x + dx, y + dy, z + dz)
            if key not in self.world:
                continue
            if self.exposed(key):
                if key not in self.shown:
                    self.show_block(key)
            else:
                if key in self.shown:
                    self.hide_block(key)

    def show_block(self, position, immediate=True):
        """ Show the block at the given `position`. This method assumes the
        block has already been added with add_block()

        Parameters
        ----------
        position : tuple of len 3
            The (x, y, z) position of the block to show.
        immediate : bool
            Whether or not to show the block immediately.

        """
        texture = self.world[position]
        self.shown[position] = texture
        if immediate:
            self._show_block(position, texture)
        else:
            self._enqueue(self._show_block, position, texture)

    def _show_block(self, position, texture):
        """ Private implementation of the `show_block()` method.

        Parameters
        ----------
        position : tuple of len 3
            The (x, y, z) position of the block to show.
        texture : list of len 3
            The coordinates of the texture squares. Use `tex_coords()` to
            generate.

        """
        x, y, z = position
        vertex_data = cube_vertices(x, y, z, 0.5)
        texture_data = list(texture[0])
        # create vertex list
        # FIXME Maybe `add_indexed()` should be used instead
        self._shown[position] = self.batch.add(24, GL_QUADS, self.atlases[texture[1]][0],
                                               ('v3f/static', vertex_data),
                                               ('t2f/static', texture_data))

    def hide_block(self, position, immediate=True):
        """ Hide the block at the given `position`. Hiding does not remove the
        block from the world.

        Parameters
        ----------
        position : tuple of len 3
            The (x, y, z) position of the block to hide.
        immediate : bool
            Whether or not to immediately remove the block from the canvas.

        """
        self.shown.pop(position)
        if immediate:
            self._hide_block(position)
        else:
            self._enqueue(self._hide_block, position)

    def _hide_block(self, position):
        """ Private implementation of the 'hide_block()` method.

        """
        self._shown.pop(position).delete()

    def show_sector(self, sector):
        """ Ensure all blocks in the given sector that should be shown are
        drawn to the canvas.

        """
        for position in self.sectors.get(sector, []):
            if position not in self.shown and self.exposed(position):
                self.show_block(position, False)

    def hide_sector(self, sector):
        """ Ensure all blocks in the given sector that should be hidden are
        removed from the canvas.

        """
        for position in self.sectors.get(sector, []):
            if position in self.shown:
                self.hide_block(position, False)

    def change_sectors(self, before, after):
        """ Move from sector `before` to sector `after`. A sector is a
        contiguous x, y sub-region of world. Sectors are used to speed up
        world rendering.

        """
        before_set = set()
        after_set = set()
        pad = 4
        for dx in xrange(-pad, pad + 1):
            for dy in [0]:  # xrange(-pad, pad + 1):
                for dz in xrange(-pad, pad + 1):
                    if dx ** 2 + dy ** 2 + dz ** 2 > (pad + 1) ** 2:
                        continue
                    if before:
                        x, y, z = before
                        before_set.add((x + dx, y + dy, z + dz))
                    if after:
                        x, y, z = after
                        after_set.add((x + dx, y + dy, z + dz))
        show = after_set - before_set
        hide = before_set - after_set
        for sector in show:
            self.show_sector(sector)
        for sector in hide:
            self.hide_sector(sector)

    def _enqueue(self, func, *args):
        """ Add `func` to the internal queue.

        """
        self.queue.append((func, args))

    def _dequeue(self):
        """ Pop the top function from the internal queue and call it.

        """
        func, args = self.queue.popleft()
        func(*args)

    def process_queue(self):
        """ Process the entire queue while taking periodic breaks. This allows
        the game loop to run smoothly. The queue contains calls to
        _show_block() and _hide_block() so this method should be called if
        add_block() or remove_block() was called with immediate=False

        """
        td = time.time()
        while self.queue and td - self.delta < 1.0 / TICKS_PER_SEC:
            self.delta = deepcopy(td)
            self._dequeue()

    def process_entire_queue(self):
        """ Process the entire queue with no breaks.

        """
        while self.queue:
            self._dequeue()


class Window(pyglet.window.Window):

    def initModel(self, args):
        # Instance of the model that handles the world.
        self.model = Model()

    def __init__(self, *args, **kwargs):
        super(Window, self).__init__(*args, **kwargs)

        # Whether or not the window exclusively captures the mouse.
        self.exclusive = False

        # When flying gravity has no effect and speed is increased.
        self.flying = False

        # self.image_sprite = pyglet.sprite.Sprite(inven_image, x=self.width//5, y=self.height//25)
        # Strafing is moving lateral to the direction you are facing,
        # e.g. moving to the left or right while continuing to face forward.
        #
        # First element is -1 when moving forward, 1 when moving back, and 0
        # otherwise. The second element is -1 when moving left, 1 when moving
        # right, and 0 otherwise.
        self.strafe = [0, 0]

        # Current (x, y, z) position in the world, specified with floats. Note
        # that, perhaps unlike in math class, the y-axis is the vertical axis.
        self.position = (125, 50, 125)

        # First element is rotation of the player in the x-z plane (ground
        # plane) measured from the z-axis down. The second is the rotation
        # angle from the ground plane up. Rotation is in degrees.
        #
        # The vertical plane rotation ranges from -90 (looking straight down) to
        # 90 (looking straight up). The horizontal rotation range is unbounded.
        self.rotation = (0, 0)

        # Which sector the player is currently in.
        self.sector = None

        # Inventory gui
        self.bar = Sprite(image.load("textures/ui/inven.png"), x=0, y=0)
        self.togleInv = False

        # The crosshairs at the center of the screen.
        self.reticle = None

        # Velocity in the y (upward) direction.
        self.dy = 0

        # Convenience list of num keys.
        self.num_keys = [
            key._1, key._2, key._3, key._4, key._5,
            key._6, key._7, key._8, key._9, key._0]

        self.initModel([])

        # A list of blocks the player can place. Hit num keys to cycle.
        self.hotBar = ["GRASS", "SAND", "GLASS", "STONE", "OLDR", "WOOD", "BWOOD", "LEAF", "BLEAF"]
        self.inventory = [["" for i in range(9)] for z in range(5)]
        for i in range(len(self.model.blocksSprites.keys())):
            if i > 9 * 5:
                break
            else:
                self.inventory[i // 9][i % 9] = list(self.model.blocksSprites.keys())[i]

        # The current block the user can place. Hit num keys to cycle.
        self.block = self.hotBar[0]
        self.moveBlock = [0, 0, ""]

        # Opened menu
        self.openMenu = False
        # Menu
        self.menu = [Button(100, 100, 100, 20, "textures/ui/button2.png", "textures/ui/button1.png")]

        # The label that is displayed in the top left of the canvas.
        self.label = pyglet.text.Label('', font_name='MS Serif', font_size=18,
                                       x=10, y=self.height - 10, anchor_x='left', anchor_y='top',
                                       color=(0, 0, 0, 255))
        #
        # self.inven_image = pyglet.image.load('textures/ui/inven.png')
        # This call schedules the `update()` method to be called
        # TICKS_PER_SEC. This is the main game event loop.
        pyglet.clock.schedule_interval(self.update, 1.0 / TICKS_PER_SEC)

    def set_exclusive_mouse(self, exclusive):
        """ If `exclusive` is True, the game will capture the mouse, if False
        the game will ignore the mouse.

        """
        super(Window, self).set_exclusive_mouse(exclusive)
        self.exclusive = exclusive

    def get_sight_vector(self):
        """ Returns the current line of sight vector indicating the direction
        the player is looking.

        """
        x, y = self.rotation
        # y ranges from -90 to 90, or -pi/2 to pi/2, so m ranges from 0 to 1 and
        # is 1 when looking ahead parallel to the ground and 0 when looking
        # straight up or down.
        m = math.cos(math.radians(y))
        # dy ranges from -1 to 1 and is -1 when looking straight down and 1 when
        # looking straight up.
        dy = math.sin(math.radians(y))
        dx = math.cos(math.radians(x - 90)) * m
        dz = math.sin(math.radians(x - 90)) * m
        return (dx, dy, dz)

    def get_motion_vector(self):
        """ Returns the current motion vector indicating the velocity of the
        player.

        Returns
        -------
        vector : tuple of len 3
            Tuple containing the velocity in x, y, and z respectively.

        """
        if any(self.strafe):
            x, y = self.rotation
            strafe = math.degrees(math.atan2(*self.strafe))
            y_angle = math.radians(y)
            x_angle = math.radians(x + strafe)
            if self.flying:
                m = math.cos(y_angle)
                dy = math.sin(y_angle)
                if self.strafe[1]:
                    # Moving left or right.
                    dy = 0.0
                    m = 1
                if self.strafe[0] > 0:
                    # Moving backwards.
                    dy *= -1
                # When you are flying up or down, you have less left and right
                # motion.
                dx = math.cos(x_angle) * m
                dz = math.sin(x_angle) * m
            else:
                dy = 0.0
                dx = math.cos(x_angle)
                dz = math.sin(x_angle)
        else:
            dy = 0.0
            dx = 0.0
            dz = 0.0
        return (dx, dy, dz)

    def update(self, dt):
        # music = pyglet.media.load('music/' + random.choice(music_list) + '.wav')
        # player.play()
        # time
        global time_world
        global time_music
        time_world += 1
        time_music += 1
        if time_music == (21000):
            music = pyglet.media.load('music/' + random.choice(music_list) + '.wav')
            player.queue(music)
            player.play()
        if time_music == (21001):
            time_music = 0
        if time_world == (9500):
            time_world = 0
        if time_world == (2500):
            glClearColor(0.4, 0.50, 0.8, 1)
            glFogfv(GL_FOG_COLOR, (GLfloat * 4)(0.4, 0.50, 0.8, 1))
        if time_world == (1):
            glClearColor(0.7, 0.69, 1.0, 1)
            glFogfv(GL_FOG_COLOR, (GLfloat * 4)(0.7, 0.69, 1.0, 1))
        if time_world == (4000):
            glClearColor(0.3, 0.35, 0.5, 1)
            glFogfv(GL_FOG_COLOR, (GLfloat * 4)(0.3, 0.35, 0.5, 1))
        if time_world == (5000):
            glClearColor(0.2, 0.20, 0.3, 1)
            glFogfv(GL_FOG_COLOR, (GLfloat * 4)(0.2, 0.20, 0.3, 1))
        if time_world == (5500):
            glClearColor(0.1, 0.10, 0.2, 1)
            glFogfv(GL_FOG_COLOR, (GLfloat * 4)(0.1, 0.10, 0.2, 1))
        if time_world == (6000):
            glClearColor(0, 0, 0, 1)
            glFogfv(GL_FOG_COLOR, (GLfloat * 4)(0, 0, 0, 1))
        if time_world == (7000):
            glClearColor(0.1, 0.10, 0.2, 1)
            glFogfv(GL_FOG_COLOR, (GLfloat * 4)(0.1, 0.10, 0.2, 1))
        if time_world == (7500):
            glClearColor(0.2, 0.20, 0.3, 1)
            glFogfv(GL_FOG_COLOR, (GLfloat * 4)(0.2, 0.20, 0.3, 1))
        if time_world == (8500):
            glClearColor(0.3, 0.35, 0.5, 1)
            glFogfv(GL_FOG_COLOR, (GLfloat * 4)(0.3, 0.35, 0.5, 1))
        if time_world == (9200):
            glClearColor(0.4, 0.50, 0.8, 1)
            glFogfv(GL_FOG_COLOR, (GLfloat * 4)(0.4, 0.50, 0.8, 1))
            pass
        # if self.position == (0, -3, 0):
        # self.position = (125, 50, 125)
        # pass
        """ This method is scheduled to be called repeatedly by the pyglet
        clock.

        Parameters
        ----------
        dt : float
            The change in time since the last call.

        """
        self.model.process_queue()
        sector = sectorize(self.position)
        if sector != self.sector:
            self.model.change_sectors(self.sector, sector)
            if self.sector is None:
                self.model.process_entire_queue()
            self.sector = sector
        m = 8
        dt = min(dt, 0.2)
        for _ in xrange(m):
            self._update(dt / m)
        if self.moveBlock[2] != "":
            self.moveBlock[0] = self._mouse_x - 16
            self.moveBlock[1] = self._mouse_y - 16

    def _update(self, dt):
        """ Private implementation of the `update()` method. This is where most
        of the motion logic lives, along with gravity and collision detection.

        Parameters
        ----------
        dt : float
            The change in time since the last call.

        """
        # walking
        speed = FLYING_SPEED if self.flying else WALKING_SPEED
        d = dt * speed  # distance covered this tick.
        dx, dy, dz = self.get_motion_vector()
        # New position in space, before accounting for gravity.
        dx, dy, dz = dx * d, dy * d, dz * d
        # gravity
        if not self.flying:
            # Update your vertical speed: if you are falling, speed up until you
            # hit terminal velocity; if you are jumping, slow down until you
            # start falling.
            self.dy -= dt * GRAVITY
            self.dy = max(self.dy, -TERMINAL_VELOCITY)
            dy += self.dy * dt
        # collisions
        x, y, z = self.position
        x, y, z = self.collide((x + dx, y + dy, z + dz), PLAYER_HEIGHT)
        self.position = (x, y, z)

    def collide(self, position, height):
        """ Checks to see if the player at the given `position` and `height`
        is colliding with any blocks in the world.

        Parameters
        ----------
        position : tuple of len 3
            The (x, y, z) position to check for collisions at.
        height : int or float
            The height of the player.

        Returns
        -------
        position : tuple of len 3
            The new position of the player taking into account collisions.

        """
        # How much overlap with a dimension of a surrounding block you need to
        # have to count as a collision. If 0, touching terrain at all counts as
        # a collision. If .49, you sink into the ground, as if walking through
        # tall grass. If >= .5, you'll fall through the ground.
        pad = 0.25
        p = list(position)
        np = normalize(position)
        for face in FACES:  # check all surrounding blocks
            for i in xrange(3):  # check each dimension independently
                if not face[i]:
                    continue
                # How much overlap you have with this dimension.
                d = (p[i] - np[i]) * face[i]
                if d < pad:
                    continue
                for dy in xrange(height):  # check each height
                    op = list(np)
                    op[1] -= dy
                    op[i] += face[i]
                    if tuple(op) not in self.model.world:
                        continue
                    p[i] -= (d - pad) * face[i]
                    if face == (0, -1, 0) or face == (0, 1, 0):
                        # You are colliding with the ground or ceiling, so stop
                        # falling / rising.
                        self.dy = 0
                    break
        return tuple(p)

    def on_mouse_press(self, x, y, button, modifiers):
        """ Called when a mouse button is pressed. See pyglet docs for button
        amd modifier mappings.

        Parameters
        ----------
        x, y : int
            The coordinates of the mouse click. Always center of the screen if
            the mouse is captured.
        button : int
            Number representing mouse button that was clicked. 1 = left button,
            4 = right button.
        modifiers : int
            Number representing any modifying keys that were pressed when the
            mouse button was clicked.

        """
        if self.openMenu == True:
            for i in self.menu:
                i.isHit(x, y, 1, self.initModel, [])
        elif self.exclusive:
            vector = self.get_sight_vector()
            block, previous = self.model.hit_test(self.position, vector)
            if (button == mouse.RIGHT) or \
                    ((button == mouse.LEFT) and (modifiers & key.MOD_CTRL)):
                # ON OSX, control + left click = right click.
                if previous:
                    self.model.add_block(previous, self.model.blocks[self.block])
            elif button == pyglet.window.mouse.LEFT and block:
                texture = self.model.world[block]
                self.model.remove_block(block, byPlayer=True)
                sound = pyglet.media.load('sounds/break.wav')
                soundpl.queue(sound)
                soundpl.play()
        elif self.togleInv == False:
            self.set_exclusive_mouse(True)
        elif self.togleInv == True:
            if button == mouse.LEFT:
                x = x // 35
                y = abs(self.height - y) // 35
                try:
                    self.moveBlock[2] = self.inventory[y][x]
                except:
                    pass

    def on_mouse_motion(self, x, y, dx, dy):
        """ Called when the player moves the mouse.

        Parameters
        ----------
        x, y : int
            The coordinates of the mouse click. Always center of the screen if
            the mouse is captured.
        dx, dy : float
            The movement of the mouse.

        """
        if self.openMenu == True:
            for i in self.menu:
                i.isHit(x, y, 0, self.initModel, [])
        elif self.exclusive:
            m = 0.15
            x, y = self.rotation
            x, y = x + dx * m, y + dy * m
            y = max(-90, min(90, y))
            self.rotation = (x, y)

    def on_mouse_release(self, x, y, button, modifiers):
        if self.openMenu == True:
            for i in self.menu:
                i.isHit(x, y, -1, self.initModel, [])
        if self.togleInv == True:
            if button == mouse.LEFT:
                if self.moveBlock[2] != "":
                    x = abs(6 - x) // 40
                    try:
                        if y <= 41:
                            self.hotBar[x] = self.moveBlock[2]
                    except:
                        pass
                    self.moveBlock[2] = ""

    def on_key_press(self, symbol, modifiers):
        """ Called when the player presses a key. See pyglet docs for key
        mappings.

        Parameters
        ----------
        symbol : int
            Number representing the key that was pressed.
        modifiers : int
            Number representing any modifying keys that were pressed.

        """
        if symbol == key.W:
            self.strafe[0] -= 1
        elif symbol == key.S:
            self.strafe[0] += 1
        elif symbol == key.A:
            self.strafe[1] -= 1
        elif symbol == key.D:
            self.strafe[1] += 1
        elif symbol == key.SPACE:
            if self.dy == 0:
                self.dy = JUMP_SPEED
        elif symbol == key.ESCAPE:
            self.set_exclusive_mouse(False)
            self.openMenu = not self.openMenu
        elif symbol == key.TAB:
            self.flying = not self.flying
            sound = pyglet.media.load('sounds/fly.wav')
            soundpl.queue(sound)
            soundpl.play()
        elif symbol in self.num_keys:
            index = (symbol - self.num_keys[0]) % len(self.hotBar)
            self.block = self.hotBar[index]
        elif symbol == key.F11:
            # not working yet
            window = pyglet.window.Window(fullscreen=True)
        elif symbol == key.R:
            self.position = (125, 50, 125)
        elif symbol == key.E:
            self.togleInv = not self.togleInv
            self.set_exclusive_mouse(not self.togleInv)

    def on_key_release(self, symbol, modifiers):
        """ Called when the player releases a key. See pyglet docs for key
        mappings.

        Parameters
        ----------
        symbol : int
            Number representing the key that was pressed.
        modifiers : int
            Number representing any modifying keys that were pressed.

        """
        global time_world
        global flying
        if symbol == key.W:
            self.strafe[0] += 1
        elif symbol == key.S:
            self.strafe[0] -= 1
        elif symbol == key.A:
            self.strafe[1] += 1
        elif symbol == key.D:
            self.strafe[1] -= 1
        elif symbol == key.F2:
            file = str(random.randint(1, 99999999999999999999))
            f = open('screenshots/' + file + ".png", "a")
            f.close()
            pyglet.image.get_buffer_manager().get_color_buffer().save(
                'screenshots/' + file + '.png')
        elif symbol == key.Y:
            time_world += 200
        elif symbol == key.F6:
            with open('worlds\level.dat', 'wb') as f:  # Python 3: open(..., 'wb')
                pickle.dump([flying], f)
        elif symbol == key.F7:
            with open('worlds\level.dat', 'rb') as f:  # Python 3: open(..., 'rb')
                try:
                    flying = pickle.load(f)
                except:
                    print("saving failed!")
        elif symbol == key.F3:
            os.system("python minecraft.py")
            time.sleep(0.2)
            sys.exit()
        elif symbol == key.F1:
            quit()
        # self.img = pyglet.image.load("texture/ui/block1.png")

    def on_resize(self, width, height):
        """ Called when the window is resized to a new `width` and `height`.

        """
        # label
        self.label.y = height - 10
        # reticle
        if self.reticle:
            self.reticle.delete()
        x, y = self.width // 2, self.height // 2
        n = 10
        self.reticle = pyglet.graphics.vertex_list(4,
                                                   ('v2i', (x - n, y, x + n, y, x, y - n, x, y + n))
                                                   )

    def set_2d(self):
        """ Configure OpenGL to draw in 2d.

        """
        width, height = self.get_size()
        glDisable(GL_DEPTH_TEST)
        viewport = self.get_viewport_size()
        glViewport(0, 0, max(1, viewport[0]), max(1, viewport[1]))
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0, max(1, width), 0, max(1, height), -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

    def set_3d(self):
        """ Configure OpenGL to draw in 3d.

        """
        width, height = self.get_size()
        glEnable(GL_DEPTH_TEST)
        viewport = self.get_viewport_size()
        glViewport(0, 0, max(1, viewport[0]), max(1, viewport[1]))
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(65.0, width / float(height), 0.1, 60.0)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        x, y = self.rotation
        glRotatef(x, 0, 1, 0)
        glRotatef(-y, math.cos(math.radians(x)), 0, math.sin(math.radians(x)))
        x, y, z = self.position
        glTranslatef(-x, -y, -z)

    def on_draw(self):
        """ Called by pyglet to draw the canvas.

        """
        self.clear()
        # sky.blit(0, 0)
        self.set_3d()
        glColor3d(1, 1, 1)
        if self.openMenu == False:
            self.model.batch.draw()
            self.draw_focused_block()
        self.set_2d()
        self.draw_label()
        # self.draw_inven()
        self.draw_reticle()
        self.draw_inventory()
        self.draw_menu()
        # self.inven_image(anchor_x='center', anchor_y='center')
        # self.image_sprite.draw()

    def draw_menu(self):
        if self.openMenu == True:
            for i in self.menu:
                i.draw()

    def draw_focused_block(self):
        """ Draw black edges around the block that is currently under the
        crosshairs.

        """
        vector = self.get_sight_vector()
        block = self.model.hit_test(self.position, vector)[0]
        if block:
            x, y, z = block
            vertex_data = cube_vertices(x, y, z, 0.50)  # 51
            glColor3d(0, 0, 0)
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
            pyglet.graphics.draw(24, GL_QUADS, ('v3f/static', vertex_data))
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

    def draw_label(self):
        """ Draw the label in the top left of the screen.

        """
        x, y, z = self.position

        self.label.text = 'Beta 0.0.4 Fps: %02d (%.2f, %.2f, %.2f) %d / %d' % (
            pyglet.clock.get_fps(), x, y, z,
            len(self.model._shown), len(self.model.world))
        # Beta 0.0.4 Fps: %02d (%.2f, %.2f, %.2f) %d / %d
        self.label.draw()

    def draw_reticle(self):
        """ Draw the crosshairs in the center of the screen.

        """
        glColor3d(255, 225, 225)
        self.reticle.draw(GL_LINES)

    def draw_inventory(self):
        glColor3d(255, 225, 225)
        self.bar.draw()
        for i in range(len(self.hotBar)):
            t = self.model.blocksSprites[self.hotBar[i]]
            t.width = 32
            t.height = 32
            t.blit(6 + i * 40, 6)
        if self.togleInv:
            h = self.height
            for i in range(len(self.inventory)):
                for z in range(len(self.inventory[i])):
                    if self.inventory[i][z] != "":
                        img = self.model.blocksSprites[self.inventory[i][z]]
                        img.width = 32
                        img.height = 32
                        img.blit(z * 35, h - i * 35 - 35)
            if self.moveBlock[2] != "":
                img = self.model.blocksSprites[self.moveBlock[2]]
                img.width = 32
                img.height = 32
                img.blit(self.moveBlock[0], self.moveBlock[1])


def setup_fog():
    """ Configure the OpenGL fog properties.

    """
    # Enable fog. Fog "blends a fog color with each rasterized pixel fragment's
    # post-texturing color."
    glEnable(GL_FOG)
    # Set the fog color.
    glFogfv(GL_FOG_COLOR, (GLfloat * 4)(145.0, 145.0, 145.0, 1))
    # Say we have no preference between rendering speed and quality.
    glHint(GL_FOG_HINT, GL_DONT_CARE)
    # Specify the equation used to compute the blending factor.
    glFogi(GL_FOG_MODE, GL_LINEAR)
    # How close and far away fog starts and ends. The closer the start and end,
    # the denser the fog in the fog range.
    glFogf(GL_FOG_START, 40.0)
    glFogf(GL_FOG_END, 60.0)
    # for texture
    glEnable(GL_BLEND)
    glBlendFunc(GL_ONE, GL_ONE)
    glEnable(GL_LINE_SMOOTH);
    # glEnable(GL_LIGHTING)
    glHint(GL_LINE_SMOOTH_HINT, GL_DONT_CARE)


def setup():
    """ Basic OpenGL configuration.

    """
    # Set the color of "clear", i.e. the sky, in rgba.
    glClearColor(0.5, 0.69, 1.0, 1)
    # Enable culling (not rendering) of back-facing facets -- facets that aren't
    # visible to you.
    glEnable(GL_CULL_FACE)
    # Set the texture minification/magnification function to GL_NEAREST (nearest
    # in Manhattan distance) to the specified texture coordinates. GL_NEAREST
    # "is generally faster than GL_LINEAR, but it can produce textured images
    # with sharper edges because the transition between texture elements is not
    # as smooth."
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
    setup_fog()


def main():
    window = Window(width=906, height=519, caption='Minecraft python', resizable=True)  # 1280 720
    # Hide the mouse cursor and prevent the mouse from leaving the window.
    window.set_exclusive_mouse(True)
    setup()
    pyglet.app.run()


#
from mods.default import *

#
main()
