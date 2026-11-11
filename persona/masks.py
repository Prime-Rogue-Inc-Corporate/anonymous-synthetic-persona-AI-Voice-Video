"""Persona masks: the head that sits on the suit.

Every mask is a function ``draw(d, amp, t)`` that paints onto a 520x520 RGBA
canvas through ``ImageDraw`` ``d``. The suit's collar sits at y=300, centre x=260.

- ``amp``: voice loudness for this frame, 0..1 (drives jaws, wings, etc.)
- ``t``:   time in seconds (for idle motion)

Register new masks with ``@mask("name")`` and pick one per episode with
``"mask": "name"`` in episode.json.
"""
import numpy as np
import math

from PIL import Image, ImageDraw

CX = 260
MASKS = {}


def mask(name, tie=True):
    def reg(fn):
        fn.tie = tie
        MASKS[name] = fn
        return fn
    return reg


def suit(tie=True):
    """The shared headless suit (static). tie=None: no suit at all (animals)."""
    im = Image.new("RGBA", (520, 520), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    if tie is None:
        return im
    cx = CX
    d.polygon([(cx - 190, 520), (cx - 170, 360), (cx - 70, 300), (cx + 70, 300), (cx + 170, 360), (cx + 190, 520)], fill=(14, 14, 18, 255))
    d.polygon([(cx - 40, 300), (cx + 40, 300), (cx, 420)], fill=(225, 225, 225, 255))
    d.polygon([(cx - 70, 300), (cx - 40, 300), (cx, 420), (cx - 55, 380), (cx - 95, 330)], fill=(32, 32, 38, 255))
    d.polygon([(cx + 70, 300), (cx + 40, 300), (cx, 420), (cx + 55, 380), (cx + 95, 330)], fill=(32, 32, 38, 255))
    if tie:
        d.polygon([(cx - 12, 312), (cx + 12, 312), (cx + 18, 420), (cx, 445), (cx - 18, 420)], fill=(20, 20, 24, 255))
    return im


@mask("moth")
def moth(d, amp, t):
    """The original Prime Rogue moth. Wings flutter with the voice."""
    mc, my = CX, 195
    wing, wing2 = (205, 200, 185, 255), (150, 145, 132, 255)
    k = 1 - 0.12 * amp - 0.02 * math.sin(t * 5)      # wing span squeeze
    lift = -8 * amp                                   # wingtips rise
    for s in (-1, 1):
        d.polygon([(mc, my - 10), (mc + s * 150 * k, my - 95 + lift), (mc + s * 175 * k, my - 30 + lift),
                   (mc + s * 120 * k, my + 25), (mc, my + 15)], fill=wing)
        d.polygon([(mc, my + 5), (mc + s * 110 * k, my + 30), (mc + s * 95 * k, my + 95), (mc + s * 25, my + 70)], fill=wing2)
        ex = mc + s * 95 * k
        d.ellipse([ex - 18, my - 55 + lift, ex + 18, my - 19 + lift], fill=(60, 55, 50, 255))
        d.ellipse([ex - 7, my - 44 + lift, ex + 7, my - 30 + lift], fill=(220, 215, 200, 255))
        tip = 4 * math.sin(t * 3 + s)
        d.line([(mc + s * 6, my - 58), (mc + s * 45, my - 120 + tip), (mc + s * 70, my - 128 + tip)], fill=(90, 82, 72, 255), width=4)
    d.ellipse([mc - 16, my - 40, mc + 16, my + 85], fill=(70, 62, 55, 255))
    d.ellipse([mc - 18, my - 62, mc + 18, my - 28], fill=(80, 72, 64, 255))


@mask("lincoln", tie=False)
def lincoln(d, amp, t):
    """Pale Lincoln mask: stovepipe hat, hollow eyes, chin-curtain beard, talking jaw."""
    cx = CX
    skin, shade, dark = (232, 226, 210, 255), (196, 188, 170, 255), (24, 22, 22, 255)
    jaw = 9 * amp                                     # how far the jaw drops

    # ears and side hair
    for s in (-1, 1):
        d.ellipse([cx + s * 80 - 13, 188, cx + s * 80 + 13, 240], fill=shade)
        d.polygon([(cx + s * 58, 128), (cx + s * 80, 140), (cx + s * 84, 185), (cx + s * 70, 178)], fill=dark)
    # face
    d.ellipse([cx - 72, 124, cx + 72, 304 + jaw], fill=skin)
    # gaunt cheeks
    for s in (-1, 1):
        d.polygon([(cx + s * 34, 232), (cx + s * 62, 222), (cx + s * 58, 262), (cx + s * 40, 268)], fill=(220, 213, 196, 255))
    # brows and hollow eyes
    for s in (-1, 1):
        d.polygon([(cx + s * 12, 182), (cx + s * 50, 172), (cx + s * 54, 180), (cx + s * 14, 190)], fill=dark)
        d.ellipse([cx + s * 31 - 17, 193, cx + s * 31 + 17, 213], fill=(150, 142, 128, 255))
        d.ellipse([cx + s * 31 - 11, 197, cx + s * 31 + 11, 210], fill=(10, 10, 12, 255))
    # nose
    d.polygon([(cx - 5, 196), (cx + 5, 196), (cx + 12, 246), (cx, 252), (cx - 12, 246)], fill=shade)
    d.line([(cx - 12, 246), (cx - 22, 262)], fill=(150, 142, 128, 255), width=3)
    d.line([(cx + 12, 246), (cx + 22, 262)], fill=(150, 142, 128, 255), width=3)
    # mole
    d.ellipse([cx - 40, 246, cx - 33, 253], fill=(110, 92, 80, 255))
    # mouth: a line when quiet, opens with the voice
    my = 272 + jaw * 0.3
    if amp > 0.08:
        d.ellipse([cx - 17, my - 2, cx + 17, my + 3 + 11 * amp], fill=(40, 22, 22, 255))
    else:
        d.line([(cx - 17, my), (cx + 17, my)], fill=(90, 70, 62, 255), width=3)
    # chin-curtain beard (no moustache), follows the jaw
    j = jaw
    d.polygon([(cx - 74, 214), (cx - 72, 262 + j), (cx - 50, 306 + j), (cx - 20, 330 + j), (cx, 336 + j),
               (cx + 20, 330 + j), (cx + 50, 306 + j), (cx + 72, 262 + j), (cx + 74, 214),
               (cx + 60, 226), (cx + 54, 266 + j), (cx + 32, 288 + j), (cx, 293 + j),
               (cx - 32, 288 + j), (cx - 54, 266 + j), (cx - 60, 226)], fill=dark)
    # bow tie over the suit's tie knot
    d.polygon([(cx, 318), (cx - 26, 306), (cx - 26, 332)], fill=dark)
    d.polygon([(cx, 318), (cx + 26, 306), (cx + 26, 332)], fill=dark)
    d.rectangle([cx - 5, 312, cx + 5, 325], fill=(40, 38, 40, 255))
    # stovepipe hat
    d.polygon([(cx - 62, 8), (cx + 62, 8), (cx + 58, 120), (cx - 58, 120)], fill=(16, 16, 20, 255))
    d.rectangle([cx - 59, 96, cx + 59, 114], fill=(40, 40, 46, 255))
    d.ellipse([cx - 98, 110, cx + 98, 134], fill=(12, 12, 16, 255))
    d.line([(cx - 40, 14), (cx - 38, 92)], fill=(46, 46, 54, 255), width=3)  # sheen


def render_head(name, amp, t, base=None):
    """Suit + mask for one frame. Pass a cached ``suit(MASKS[name].tie)`` as base to save time."""
    im = (base or suit(MASKS[name].tie)).copy()
    MASKS[name](ImageDraw.Draw(im), amp, t)
    return im


@mask("anchor", tie=False)
def anchor(d, amp, t):
    """News anchor: pale mask, sleek dark bob, earpiece, composed mouth."""
    cx = CX
    skin, dark = (234, 228, 216, 255), (30, 24, 22, 255)
    jaw = 6 * amp
    # hair back layer (bob)
    d.polygon([(cx - 92, 150), (cx - 80, 100), (cx - 40, 70), (cx + 40, 70), (cx + 80, 100), (cx + 92, 150),
               (cx + 96, 268), (cx + 70, 276), (cx - 70, 276), (cx - 96, 268)], fill=dark)
    # face
    d.ellipse([cx - 66, 110, cx + 66, 292 + jaw], fill=skin)
    # side-swept fringe
    d.polygon([(cx - 70, 150), (cx - 50, 96), (cx + 10, 84), (cx + 74, 110), (cx + 30, 118), (cx - 20, 140)], fill=dark)
    # brows and hollow almond eyes
    for s in (-1, 1):
        d.line([(cx + s * 14, 176), (cx + s * 48, 170)], fill=dark, width=5)
        d.ellipse([cx + s * 31 - 18, 186, cx + s * 31 + 18, 204], fill=(160, 150, 140, 255))
        d.ellipse([cx + s * 31 - 11, 189, cx + s * 31 + 11, 201], fill=(12, 10, 12, 255))
    # nose
    d.polygon([(cx - 3, 200), (cx + 3, 200), (cx + 8, 236), (cx - 8, 236)], fill=(214, 206, 192, 255))
    # mouth
    my = 262 + jaw * 0.4
    if amp > 0.08:
        d.ellipse([cx - 16, my - 2, cx + 16, my + 3 + 10 * amp], fill=(110, 40, 46, 255))
    else:
        d.line([(cx - 15, my), (cx + 15, my)], fill=(130, 60, 64, 255), width=4)
    # earpiece + coil
    d.ellipse([cx + 62, 196, cx + 74, 210], fill=(200, 200, 205, 255))
    d.line([(cx + 68, 210), (cx + 76, 250), (cx + 70, 300)], fill=(170, 170, 176, 255), width=2)
    # blouse collar
    d.polygon([(cx - 40, 300), (cx, 330), (cx + 40, 300), (cx + 30, 296), (cx, 318), (cx - 30, 296)], fill=(245, 245, 245, 255))


@mask("expert", tie=True)
def expert(d, amp, t):
    """Government expert: bald dome, round wire glasses, grey goatee, permanent smile."""
    cx = CX
    skin, grey = (232, 224, 208, 255), (150, 148, 144, 255)
    jaw = 7 * amp
    for s in (-1, 1):
        d.ellipse([cx + s * 76 - 12, 186, cx + s * 76 + 12, 232], fill=(206, 198, 182, 255))
    # head (tall bald dome)
    d.ellipse([cx - 70, 96, cx + 70, 296 + jaw], fill=skin)
    d.arc([cx - 46, 108, cx + 30, 160], 200, 290, fill=(250, 248, 240, 255), width=5)   # shine
    # grey fringe
    for s in (-1, 1):
        d.polygon([(cx + s * 70, 170), (cx + s * 74, 200), (cx + s * 64, 226), (cx + s * 58, 190)], fill=grey)
    # brows, raised (eternally upbeat)
    for s in (-1, 1):
        d.arc([cx + s * 31 - 22, 160, cx + s * 31 + 22, 186], 200, 340, fill=grey, width=5)
    # hollow eyes behind round wire glasses
    for s in (-1, 1):
        d.ellipse([cx + s * 31 - 11, 186, cx + s * 31 + 11, 202], fill=(14, 12, 14, 255))
        d.ellipse([cx + s * 31 - 24, 176, cx + s * 31 + 24, 212], outline=(60, 60, 66, 255), width=3)
    d.line([(cx - 7, 192), (cx + 7, 192)], fill=(60, 60, 66, 255), width=3)
    # nose
    d.polygon([(cx - 4, 200), (cx + 4, 200), (cx + 11, 238), (cx, 243), (cx - 11, 238)], fill=(210, 200, 182, 255))
    # moustache + goatee, follow the jaw
    d.polygon([(cx - 28, 252), (cx, 246), (cx + 28, 252), (cx + 22, 258), (cx, 254), (cx - 22, 258)], fill=grey)
    d.polygon([(cx - 22, 274 + jaw), (cx + 22, 274 + jaw), (cx + 14, 300 + jaw), (cx, 306 + jaw), (cx - 14, 300 + jaw)], fill=grey)
    # smile that opens with the voice
    my = 262 + jaw * 0.4
    if amp > 0.08:
        d.chord([cx - 22, my - 8, cx + 22, my + 8 + 12 * amp], 0, 180, fill=(70, 30, 30, 255))
    else:
        d.arc([cx - 22, my - 10, cx + 22, my + 6], 20, 160, fill=(110, 70, 64, 255), width=4)


def _mouth(d, cx, my, amp, w=16, lip=(110, 70, 64, 255), inner=(50, 24, 24, 255)):
    if amp > 0.08:
        d.ellipse([cx - w, my - 2, cx + w, my + 3 + 11 * amp], fill=inner)
    else:
        d.line([(cx - w, my), (cx + w, my)], fill=lip, width=4)


def _eyes(d, cx, y=196, gap=31, socket=(156, 148, 136, 255)):
    for s in (-1, 1):
        d.ellipse([cx + s * gap - 17, y - 9, cx + s * gap + 17, y + 9], fill=socket)
        d.ellipse([cx + s * gap - 10, y - 6, cx + s * gap + 10, y + 6], fill=(12, 10, 12, 255))


@mask("rancher", tie=False)
def rancher(d, amp, t):
    """Prairie organizer: cowboy hat, big moustache, bolo tie."""
    cx = CX
    skin, dark, hat = (230, 222, 206, 255), (60, 46, 36, 255), (92, 68, 46, 255)
    jaw = 7 * amp
    for s in (-1, 1):
        d.ellipse([cx + s * 76 - 12, 190, cx + s * 76 + 12, 234], fill=(206, 196, 180, 255))
    d.ellipse([cx - 70, 118, cx + 70, 300 + jaw], fill=skin)
    for s in (-1, 1):
        d.line([(cx + s * 14, 178), (cx + s * 50, 174)], fill=dark, width=6)
    _eyes(d, cx, 194)
    d.polygon([(cx - 5, 200), (cx + 5, 200), (cx + 12, 240), (cx - 12, 240)], fill=(212, 200, 182, 255))
    _mouth(d, cx, 266 + jaw * 0.4, amp)
    # handlebar moustache over the mouth
    d.polygon([(cx - 40, 258), (cx - 30, 246), (cx, 244), (cx + 30, 246), (cx + 40, 258), (cx + 24, 254), (cx, 252), (cx - 24, 254)], fill=dark)
    # bolo tie
    d.line([(cx - 10, 300), (cx - 3, 360)], fill=(30, 30, 30, 255), width=3)
    d.line([(cx + 10, 300), (cx + 3, 360)], fill=(30, 30, 30, 255), width=3)
    d.ellipse([cx - 12, 318, cx + 12, 338], fill=(150, 170, 180, 255), outline=(200, 180, 120, 255), width=3)
    # cowboy hat
    d.ellipse([cx - 120, 112, cx + 120, 148], fill=hat)
    d.polygon([(cx - 66, 130), (cx - 58, 56), (cx - 20, 44), (cx, 56), (cx + 20, 44), (cx + 58, 56), (cx + 66, 130)], fill=hat)
    d.rectangle([cx - 64, 110, cx + 64, 124], fill=(52, 38, 28, 255))


@mask("organizer", tie=False)
def organizer(d, amp, t):
    """Movement finance lead: curly grey-blonde hair, cat-eye glasses, earrings."""
    cx = CX
    skin, hair = (234, 226, 214, 255), (196, 182, 150, 255)
    jaw = 6 * amp
    for (x, y, r) in [(-70, 150, 34), (-50, 112, 34), (-14, 96, 34), (22, 96, 34), (56, 112, 34), (74, 150, 34),
                      (-80, 196, 30), (80, 196, 30), (-74, 236, 26), (74, 236, 26)]:
        d.ellipse([cx + x - r, y - r, cx + x + r, y + r], fill=hair)
    d.ellipse([cx - 64, 120, cx + 64, 294 + jaw], fill=skin)
    for (x, y, r) in [(-40, 126, 22), (-6, 116, 22), (30, 122, 22)]:
        d.ellipse([cx + x - r, y - r, cx + x + r, y + r], fill=hair)
    _eyes(d, cx, 196, 28)
    for s in (-1, 1):   # cat-eye frames
        d.polygon([(cx + s * 6, 186), (cx + s * 52, 180), (cx + s * 56, 196), (cx + s * 46, 208), (cx + s * 10, 208)],
                  outline=(120, 40, 60, 255), width=3)
        d.ellipse([cx + s * 66 - 5, 238, cx + s * 66 + 5, 250], fill=(210, 180, 90, 255))
    d.polygon([(cx - 4, 204), (cx + 4, 204), (cx + 8, 238), (cx - 8, 238)], fill=(214, 204, 190, 255))
    _mouth(d, cx, 262 + jaw * 0.4, amp, 15, (150, 70, 80, 255), (110, 40, 50, 255))
    # scarf
    d.polygon([(cx - 56, 300), (cx + 56, 300), (cx + 30, 336), (cx - 30, 336)], fill=(150, 40, 46, 255))


@mask("official", tie=True)
def official(d, amp, t):
    """Mid-level official: grey side part, heavy brows, square jaw, flag pin."""
    cx = CX
    skin, grey = (232, 224, 210, 255), (170, 168, 164, 255)
    jaw = 7 * amp
    for s in (-1, 1):
        d.ellipse([cx + s * 76 - 12, 188, cx + s * 76 + 12, 232], fill=(206, 198, 184, 255))
    d.rounded_rectangle([cx - 70, 116, cx + 70, 300 + jaw], radius=48, fill=skin)
    d.polygon([(cx - 74, 170), (cx - 70, 120), (cx - 30, 100), (cx + 40, 100), (cx + 74, 126), (cx + 74, 168),
               (cx + 60, 140), (cx - 20, 128), (cx - 28, 140), (cx - 60, 146)], fill=grey)
    d.line([(cx - 28, 104), (cx - 26, 140)], fill=(240, 240, 240, 255), width=3)   # the part
    for s in (-1, 1):
        d.rectangle([cx + s * 31 - 22, 172, cx + s * 31 + 22, 180], fill=(96, 94, 92, 255))
    _eyes(d, cx, 196)
    d.polygon([(cx - 5, 200), (cx + 5, 200), (cx + 11, 242), (cx - 11, 242)], fill=(212, 202, 188, 255))
    _mouth(d, cx, 268 + jaw * 0.4, amp, 18)
    # flag pin on the lapel
    px, py = cx - 82, 344
    d.rectangle([px, py, px + 20, py + 12], fill=(230, 230, 230, 255))
    for k in range(0, 12, 4):
        d.line([(px, py + k), (px + 20, py + k)], fill=(190, 40, 50, 255), width=2)
    d.rectangle([px, py, px + 8, py + 6], fill=(40, 60, 140, 255))


@mask("aide", tie=False)
def aide(d, amp, t):
    """Junior note-taker: dark ponytail, lanyard and badge."""
    cx = CX
    skin, hair = (236, 228, 218, 255), (52, 36, 30, 255)
    jaw = 6 * amp
    sway = 6 * math.sin(t * 2.2)
    d.polygon([(cx + 52, 150), (cx + 98 + sway, 190), (cx + 92 + sway, 280), (cx + 70, 230)], fill=hair)   # ponytail
    d.ellipse([cx - 66, 104, cx + 66, 180], fill=hair)
    d.ellipse([cx - 62, 122, cx + 62, 294 + jaw], fill=skin)
    d.polygon([(cx - 62, 168), (cx - 56, 122), (cx, 108), (cx + 56, 122), (cx + 62, 168), (cx + 20, 134), (cx - 30, 140)], fill=hair)
    _eyes(d, cx, 198, 28)
    for s in (-1, 1):
        d.line([(cx + s * 14, 180), (cx + s * 44, 176)], fill=hair, width=4)
    d.polygon([(cx - 4, 206), (cx + 4, 206), (cx + 8, 238), (cx - 8, 238)], fill=(216, 206, 194, 255))
    _mouth(d, cx, 262 + jaw * 0.4, amp, 14, (150, 80, 86, 255), (110, 44, 52, 255))
    # lanyard + badge
    d.line([(cx - 36, 300), (cx - 6, 396)], fill=(40, 70, 150, 255), width=5)
    d.line([(cx + 36, 300), (cx + 6, 396)], fill=(40, 70, 150, 255), width=5)
    d.rectangle([cx - 24, 394, cx + 24, 450], fill=(240, 240, 240, 255))
    d.rectangle([cx - 24, 394, cx + 24, 406], fill=(40, 70, 150, 255))
    d.rectangle([cx - 14, 414, cx + 14, 438], fill=(180, 180, 186, 255))


@mask("chief", tie=False)
def chief(d, amp, t):
    """Senate chief of staff: silver pixie cut, readers pushed up on her head, pearls."""
    cx = CX
    skin, hair = (234, 226, 214, 255), (186, 184, 182, 255)
    jaw = 6 * amp
    d.ellipse([cx - 70, 100, cx + 70, 200], fill=hair)
    d.ellipse([cx - 64, 118, cx + 64, 294 + jaw], fill=skin)
    d.polygon([(cx - 66, 170), (cx - 60, 116), (cx - 10, 100), (cx + 50, 108), (cx + 68, 150), (cx + 40, 132), (cx - 10, 136), (cx - 46, 150)], fill=hair)
    for s in (-1, 1):   # readers parked on the head
        d.ellipse([cx + s * 26 - 18, 108, cx + s * 26 + 18, 128], outline=(40, 40, 46, 255), width=3)
    d.line([(cx - 8, 118), (cx + 8, 118)], fill=(40, 40, 46, 255), width=3)
    for s in (-1, 1):
        d.line([(cx + s * 14, 180), (cx + s * 46, 172)], fill=(110, 108, 106, 255), width=4)
    _eyes(d, cx, 198, 28)
    d.polygon([(cx - 4, 204), (cx + 4, 204), (cx + 9, 240), (cx - 9, 240)], fill=(214, 204, 190, 255))
    _mouth(d, cx, 264 + jaw * 0.4, amp, 15, (140, 70, 76, 255), (100, 40, 48, 255))
    for k in range(9):  # pearls
        a = math.pi * (0.15 + 0.7 * k / 8)
        px, py = cx - 46 * math.cos(a), 300 + 30 * math.sin(a)
        d.ellipse([px - 5, py - 5, px + 5, py + 5], fill=(240, 236, 226, 255))


@mask("counsel", tie=True)
def counsel(d, amp, t):
    """Young senior counsel: dark curls, five o'clock shadow, permanently loosened tie."""
    cx = CX
    skin, hair = (232, 222, 206, 255), (34, 28, 26, 255)
    jaw = 7 * amp
    for s in (-1, 1):
        d.ellipse([cx + s * 72 - 12, 190, cx + s * 72 + 12, 234], fill=(206, 196, 180, 255))
    d.ellipse([cx - 68, 116, cx + 68, 298 + jaw], fill=skin)
    d.chord([cx - 58, 228 + jaw, cx + 58, 302 + jaw], 0, 180, fill=(200, 190, 176, 255))   # stubble
    for (x, y, r) in [(-56, 132, 22), (-30, 112, 24), (0, 104, 24), (30, 110, 24), (56, 130, 22), (-66, 158, 16), (66, 156, 16)]:
        d.ellipse([cx + x - r, y - r, cx + x + r, y + r], fill=hair)
    for s in (-1, 1):
        d.line([(cx + s * 12, 178), (cx + s * 48, 176)], fill=hair, width=6)
    _eyes(d, cx, 198)
    d.polygon([(cx - 5, 204), (cx + 5, 204), (cx + 11, 244), (cx - 11, 244)], fill=(212, 200, 184, 255))
    _mouth(d, cx, 268 + jaw * 0.4, amp, 17)
    d.polygon([(cx - 22, 304), (cx + 22, 304), (cx + 14, 318), (cx - 14, 318)], fill=(225, 225, 225, 255))   # open collar


@mask("clerk", tie=True)
def clerk(d, amp, t):
    """Cloakroom floor aide: buzz cut, round face, headset, perpetually out of breath."""
    cx = CX
    skin, hair = (236, 220, 204, 255), (120, 96, 70, 255)
    jaw = 7 * amp
    for s in (-1, 1):
        d.ellipse([cx + s * 80 - 13, 190, cx + s * 80 + 13, 236], fill=(214, 194, 178, 255))
    d.ellipse([cx - 78, 126, cx + 78, 300 + jaw], fill=skin)
    d.chord([cx - 76, 124, cx + 76, 220], 180, 360, fill=hair)
    for s in (-1, 1):   # flushed cheeks
        d.ellipse([cx + s * 46 - 16, 232, cx + s * 46 + 16, 252], fill=(232, 180, 170, 255))
        d.line([(cx + s * 14, 182), (cx + s * 44, 180)], fill=hair, width=5)
    _eyes(d, cx, 200, 30)
    d.ellipse([cx - 10, 214, cx + 10, 244], fill=(222, 202, 186, 255))
    _mouth(d, cx, 270 + jaw * 0.4, amp, 16)
    # headset band + mic
    d.arc([cx - 86, 120, cx + 86, 260], 190, 350, fill=(40, 40, 44, 255), width=6)
    d.ellipse([cx - 92, 196, cx - 72, 226], fill=(40, 40, 44, 255))
    d.line([(cx - 82, 222), (cx - 50, 262), (cx - 26, 268)], fill=(40, 40, 44, 255), width=4)
    d.ellipse([cx - 30, 263, cx - 20, 273], fill=(70, 70, 76, 255))


@mask("congressman", tie=True)
def congressman(d, amp, t):
    """Lame-duck libertarian congressman: grey hair, short grey beard, rectangular glasses, unimpressed brows."""
    cx = CX
    skin, grey, dgrey = (230, 222, 208, 255), (160, 158, 154, 255), (110, 108, 104, 255)
    jaw = 7 * amp
    for s in (-1, 1):
        d.ellipse([cx + s * 74 - 12, 188, cx + s * 74 + 12, 232], fill=(206, 196, 182, 255))
    d.ellipse([cx - 68, 112, cx + 68, 296 + jaw], fill=skin)
    d.polygon([(cx - 70, 172), (cx - 66, 122), (cx - 20, 100), (cx + 30, 102), (cx + 68, 124), (cx + 70, 168),
               (cx + 54, 136), (cx + 10, 126), (cx - 40, 132), (cx - 56, 150)], fill=grey)
    # short beard and moustache, following the jaw
    d.polygon([(cx - 64, 222), (cx - 60, 262 + jaw), (cx - 36, 294 + jaw), (cx, 304 + jaw), (cx + 36, 294 + jaw), (cx + 60, 262 + jaw),
               (cx + 64, 222), (cx + 50, 240), (cx + 40, 276 + jaw), (cx, 286 + jaw), (cx - 40, 276 + jaw), (cx - 50, 240)], fill=grey)
    d.polygon([(cx - 30, 256), (cx, 250), (cx + 30, 256), (cx + 24, 262), (cx - 24, 262)], fill=dgrey)
    # flat, unimpressed brows + rectangular glasses
    for s in (-1, 1):
        d.line([(cx + s * 12, 178), (cx + s * 50, 178)], fill=dgrey, width=6)
    _eyes(d, cx, 196)
    for s in (-1, 1):
        d.rectangle([cx + s * 31 - 24, 184, cx + s * 31 + 24, 208], outline=(50, 50, 56, 255), width=3)
    d.line([(cx - 7, 192), (cx + 7, 192)], fill=(50, 50, 56, 255), width=3)
    d.polygon([(cx - 5, 204), (cx + 5, 204), (cx + 11, 242), (cx - 11, 242)], fill=(212, 200, 186, 255))
    my = 272 + jaw * 0.4
    if amp > 0.08:
        d.ellipse([cx - 15, my - 2, cx + 15, my + 3 + 10 * amp], fill=(50, 24, 24, 255))
    else:
        d.line([(cx - 15, my), (cx + 15, my)], fill=(90, 70, 62, 255), width=4)


@mask("presiding", tie=False)
def presiding(d, amp, t):
    """Speaker pro tempore: white hair, half-moon glasses on the end of the nose."""
    cx = CX
    skin, hair = (234, 226, 214, 255), (238, 236, 232, 255)
    jaw = 6 * amp
    d.ellipse([cx - 76, 100, cx + 76, 236], fill=hair)
    d.ellipse([cx - 62, 122, cx + 62, 294 + jaw], fill=skin)
    d.chord([cx - 66, 104, cx + 66, 190], 180, 360, fill=hair)
    for s in (-1, 1):
        d.line([(cx + s * 12, 182), (cx + s * 44, 180)], fill=(170, 166, 160, 255), width=4)
    _eyes(d, cx, 198, 28)
    d.polygon([(cx - 4, 204), (cx + 4, 204), (cx + 9, 240), (cx - 9, 240)], fill=(214, 204, 190, 255))
    for s in (-1, 1):   # half-moons low on the nose
        d.chord([cx + s * 24 - 18, 214, cx + s * 24 + 18, 244], 0, 180, outline=(60, 50, 40, 255), width=3)
    _mouth(d, cx, 266 + jaw * 0.4, amp, 14, (140, 80, 86, 255), (100, 44, 52, 255))
    d.polygon([(cx - 44, 300), (cx, 326), (cx + 44, 300)], fill=(60, 40, 90, 255))   # purple blouse


@mask("whip", tie=True)
def whip(d, amp, t):
    """Deputy whip: slicked-back dark hair, too many teeth, pocket square."""
    cx = CX
    skin, hair = (232, 220, 204, 255), (26, 22, 22, 255)
    jaw = 7 * amp
    for s in (-1, 1):
        d.ellipse([cx + s * 72 - 12, 188, cx + s * 72 + 12, 232], fill=(206, 194, 178, 255))
    d.ellipse([cx - 66, 112, cx + 66, 298 + jaw], fill=skin)
    d.chord([cx - 68, 96, cx + 68, 196], 180, 360, fill=hair)
    d.arc([cx - 50, 104, cx + 40, 150], 200, 330, fill=(80, 80, 90, 255), width=3)   # comb lines
    for s in (-1, 1):
        d.line([(cx + s * 12, 176), (cx + s * 46, 170)], fill=hair, width=5)
    _eyes(d, cx, 196)
    d.polygon([(cx - 5, 202), (cx + 5, 202), (cx + 10, 240), (cx - 10, 240)], fill=(212, 198, 182, 255))
    my = 262 + jaw * 0.4
    d.chord([cx - 26, my - 10, cx + 26, my + 14 + 10 * amp], 0, 180, fill=(250, 250, 248, 255))   # the grin
    d.line([(cx - 24, my + 1), (cx + 24, my + 1)], fill=(200, 196, 190, 255), width=2)
    d.polygon([(cx + 66, 346), (cx + 92, 346), (cx + 86, 334), (cx + 78, 340), (cx + 72, 332)], fill=(230, 230, 236, 255))


@mask("pundit", tie=False)
def pundit(d, amp, t):
    """Ex-cable anchor turned barn podcaster: swept preppy hair with a cowlick, one eyebrow permanently cocked,
    outdoorsman vest over an open collar."""
    cx = CX
    skin, hair = (236, 224, 206, 255), (150, 112, 70, 255)
    jaw = 7 * amp
    # vest over the suit jacket area
    d.polygon([(cx - 120, 330), (cx - 40, 300), (cx - 30, 520), (cx - 150, 520)], fill=(70, 86, 60, 255))
    d.polygon([(cx + 120, 330), (cx + 40, 300), (cx + 30, 520), (cx + 150, 520)], fill=(70, 86, 60, 255))
    for s in (-1, 1):
        d.rectangle([cx + s * 80 - 18, 390, cx + s * 80 + 18, 412], outline=(50, 62, 42, 255), width=3)   # pockets
    d.polygon([(cx - 40, 300), (cx + 40, 300), (cx + 22, 334), (cx - 22, 334)], fill=(170, 196, 226, 255))    # blue oxford
    for s in (-1, 1):
        d.ellipse([cx + s * 74 - 12, 188, cx + s * 74 + 12, 232], fill=(214, 198, 180, 255))
    d.ellipse([cx - 68, 114, cx + 68, 298 + jaw], fill=skin)
    # swept-back hair + the cowlick that will not lie down
    d.polygon([(cx - 70, 170), (cx - 66, 120), (cx - 30, 98), (cx + 30, 96), (cx + 66, 114), (cx + 72, 160),
               (cx + 50, 132), (cx + 10, 124), (cx - 30, 128), (cx - 54, 146)], fill=hair)
    d.polygon([(cx + 10, 100), (cx + 26, 66 + 4 * math.sin(t * 3)), (cx + 34, 102)], fill=hair)
    # one brow up (the quizzical look), one brow down
    d.line([(cx - 50, 170), (cx - 14, 162)], fill=(110, 80, 50, 255), width=6)
    d.arc([cx + 8, 150, cx + 58, 186], 200, 330, fill=(110, 80, 50, 255), width=6)
    _eyes(d, cx, 196)
    d.polygon([(cx - 5, 202), (cx + 5, 202), (cx + 11, 242), (cx - 11, 242)], fill=(216, 202, 184, 255))
    # lopsided half-smirk; opens with the voice
    my = 266 + jaw * 0.4
    if amp > 0.08:
        d.chord([cx - 20, my - 6, cx + 24, my + 8 + 12 * amp], 0, 180, fill=(70, 30, 30, 255))
    else:
        d.line([(cx - 18, my + 2), (cx + 20, my - 3)], fill=(130, 80, 70, 255), width=4)


@mask("orator", tie=True)
def orator(d, amp, t):
    """A gilded statue bust come to life: polished gold face, blank sculpted eyes, a laurel wreath, a jaw that
    works on a hinge. Grandeur, not a likeness."""
    cx = CX
    gold, shade, hi = (204, 160, 62, 255), (150, 110, 36, 255), (246, 214, 128, 255)
    jaw = 9 * amp
    d.ellipse([cx - 70, 100, cx + 70, 290], fill=shade)                       # head (shadow side)
    d.ellipse([cx - 64, 100, cx + 66, 284], fill=gold)
    d.ellipse([cx - 40, 112, cx + 6, 170], fill=hi)                           # polish highlight
    d.rectangle([cx - 46, 250, cx + 46, 288 + jaw], fill=gold)                # hinged jaw block
    d.line([(cx - 46, 252), (cx + 46, 252)], fill=shade, width=2)
    d.line([(cx - 64, 176), (cx + 64, 176)], fill=shade, width=5)             # heavy sculpted brow
    for s in (-1, 1):                                                         # blank statue eyes
        d.ellipse([cx + s * 30 - 18, 184, cx + s * 30 + 18, 206], fill=(230, 196, 104, 255), outline=shade, width=3)
    d.polygon([(cx - 6, 196), (cx + 6, 196), (cx + 14, 236), (cx - 14, 236)], fill=shade)    # nose
    my = 252 + jaw * 0.3
    if amp > 0.08:
        d.rectangle([cx - 24, my - 4, cx + 24, my + 4 + 14 * amp], fill=(60, 36, 12, 255))
    else:
        d.line([(cx - 24, my), (cx + 24, my)], fill=shade, width=4)
    sway = 2 * math.sin(t * 1.7)
    for s in (-1, 1):                                                         # laurel wreath
        for k in range(6):
            a = math.radians(200 - k * 18) if s < 0 else math.radians(-20 + k * 18)
            lx, ly = cx + s * abs(70 * math.cos(a)), 150 - 50 * abs(math.sin(a)) + k * 4 + sway
            d.ellipse([lx - 16, ly - 7, lx + 16, ly + 7], fill=(90, 140, 70, 255), outline=(60, 100, 46, 255))
    d.polygon([(cx - 12, 312), (cx + 12, 312), (cx + 18, 420), (cx, 445), (cx - 18, 420)], fill=(190, 150, 60, 255))  # gold tie


@mask("bulldog", tie=False)
def bulldog(d, amp, t):
    """A British bulldog in a bow tie: jowls, an underbite with two teeth, heavy-lidded eyes, an unlit cigar
    parked in the corner of the mouth. The underjaw drops with the voice."""
    cx = CX
    fawn, dark, pale = (196, 150, 104, 255), (140, 98, 62, 255), (232, 210, 180, 255)
    drop = 12 * amp
    for s in (-1, 1):                                                          # rose ears
        d.polygon([(cx + s * 70, 132), (cx + s * 112, 118), (cx + s * 104, 160)], fill=dark)
    d.ellipse([cx - 104, 118, cx + 104, 300], fill=fawn)                       # broad skull
    d.ellipse([cx - 46, 126, cx + 46, 214], fill=pale)                         # blaze
    for k in range(3):                                                         # brow wrinkles
        d.arc([cx - 50, 150 + k * 10, cx + 50, 190 + k * 10], 200, 340, fill=dark, width=3)
    for s in (-1, 1):                                                          # heavy-lidded eyes
        ex = cx + s * 50
        d.ellipse([ex - 15, 188, ex + 15, 210], fill=(30, 22, 18, 255))
        d.chord([ex - 17, 184, ex + 17, 206], 180, 360, fill=fawn)             # drooping lids
        d.line([(ex - 17, 196), (ex + 17, 196)], fill=dark, width=3)
    d.ellipse([cx - 30, 214, cx + 30, 246], fill=(40, 30, 28, 255))            # flat nose
    for s in (-1, 1):                                                          # jowls
        d.ellipse([cx + s * 62 - 50, 230, cx + s * 62 + 50, 300 + drop * 0.4], fill=fawn)
        d.line([(cx + s * 4, 246), (cx + s * 30, 262), (cx + s * 70, 268)], fill=dark, width=3)
    d.chord([cx - 46, 262 + drop, cx + 46, 312 + drop], 0, 180, fill=(120, 60, 56, 255))   # underjaw
    for s in (-1, 1):                                                          # the two teeth
        d.polygon([(cx + s * 24 - 6, 272 + drop), (cx + s * 24 + 6, 272 + drop), (cx + s * 24, 258 + drop)], fill=(246, 240, 226, 255))
    tip = 1.5 * math.sin(t * 1.1)                                              # unlit cigar
    d.line([(cx + 52, 270 + drop * 0.5), (cx + 118, 252 + tip)], fill=(110, 70, 40, 255), width=11)
    d.line([(cx + 92, 259), (cx + 100, 257)], fill=(200, 60, 50, 255), width=11)          # band
    d.ellipse([cx + 112, 246 + tip, cx + 124, 258 + tip], fill=(90, 70, 60, 255))
    # polka-dot bow tie
    d.polygon([(cx, 318), (cx - 40, 300), (cx - 40, 336)], fill=(28, 40, 96, 255))
    d.polygon([(cx, 318), (cx + 40, 300), (cx + 40, 336)], fill=(28, 40, 96, 255))
    d.ellipse([cx - 9, 309, cx + 9, 327], fill=(36, 50, 110, 255))
    for x, y in ((-28, 310), (-20, 324), (-32, 326), (26, 312), (20, 326), (32, 322)):
        d.ellipse([cx + x - 3, y - 3, cx + x + 3, y + 3], fill=(236, 236, 236, 255))


@mask("shadow", tie=False)
def shadow(d, amp, t):
    """Leader of the Opposition: a sharp silver bob, half-moon reading glasses pushed down the nose, pearls."""
    cx = CX
    skin, hair = (232, 210, 192, 255), (196, 198, 204, 255)
    jaw = 6 * amp
    d.polygon([(cx - 40, 300), (cx + 40, 300), (cx + 24, 336), (cx - 24, 336)], fill=(150, 30, 46, 255))   # blouse
    d.polygon([(cx - 84, 150), (cx - 72, 104), (cx, 84), (cx + 72, 104), (cx + 84, 150), (cx + 88, 268), (cx - 88, 268)], fill=hair)
    d.ellipse([cx - 60, 116, cx + 60, 290 + jaw], fill=skin)
    d.polygon([(cx - 70, 116), (cx + 40, 104), (cx + 76, 150), (cx + 20, 132), (cx - 66, 150)], fill=hair)   # fringe
    for s in (-1, 1):
        d.line([(cx + s * 44, 176), (cx + s * 14, 170)], fill=(120, 112, 110, 255), width=4)
    _eyes(d, cx, 190, gap=27, socket=(214, 194, 176, 255))
    for s in (-1, 1):                                                          # half-moon glasses, low
        d.chord([cx + s * 27 - 20, 196, cx + s * 27 + 20, 226], 0, 180, outline=(60, 60, 64, 255), width=3)
    d.line([(cx - 7, 210), (cx + 7, 210)], fill=(60, 60, 64, 255), width=3)
    d.polygon([(cx - 4, 200), (cx + 4, 200), (cx + 9, 236), (cx - 9, 236)], fill=(214, 192, 172, 255))
    _mouth(d, cx, 260 + jaw * 0.5, amp, w=17, lip=(150, 70, 80, 255))
    for k in range(9):                                                         # pearls
        a = math.pi * (0.15 + 0.7 * k / 8)
        px, py = cx - 46 * math.cos(a), 300 + 26 * math.sin(a)
        d.ellipse([px - 5, py - 5, px + 5, py + 5], fill=(240, 236, 226, 255))


@mask("maple", tie=False)
def maple(d, amp, t):
    """A red maple-leaf mask over a hockey sweater (no crest, no numbers): an invented rally figure, not a
    likeness. The leaf's lower lobes part with the voice."""
    cx = CX
    red, dark, white = (200, 30, 40, 255), (140, 18, 26, 255), (240, 240, 236, 255)
    # sweater over the suit: red body, white shoulder yoke stripe, lace-up collar
    d.polygon([(cx - 190, 520), (cx - 172, 356), (cx - 70, 300), (cx + 70, 300), (cx + 172, 356), (cx + 190, 520)], fill=red)
    d.polygon([(cx - 176, 390), (cx - 150, 350), (cx - 70, 318), (cx + 70, 318), (cx + 150, 350), (cx + 176, 390),
               (cx + 168, 410), (cx + 140, 372), (cx + 70, 342), (cx - 70, 342), (cx - 140, 372), (cx - 168, 410)], fill=white)
    d.rectangle([cx - 180, 470, cx + 180, 490], fill=white)
    d.polygon([(cx - 30, 300), (cx + 30, 300), (cx, 352)], fill=dark)
    for k in range(3):
        y = 312 + k * 12; d.line([(cx - 12 + k * 3, y), (cx + 12 - k * 3, y + 6)], fill=white, width=2)
    # the leaf: 11-point maple silhouette, drawn as a polygon around (cx, 200)
    open_ = 10 * amp
    pts = [(0, -110), (16, -70), (34, -82), (28, -30), (64, -56), (58, -40), (96, -46), (84, -20), (104, -6),
           (60, 24), (70, 46), (20, 36 + open_), (10, 70 + open_), (-10, 70 + open_), (-20, 36 + open_), (-70, 46),
           (-60, 24), (-104, -6), (-84, -20), (-96, -46), (-58, -40), (-64, -56), (-28, -30), (-34, -82), (-16, -70)]
    sway = 1.5 * math.sin(t * 1.4)
    d.polygon([(cx + x * 1.15, 196 + y * 1.15 + sway) for x, y in pts], fill=red, outline=dark)
    d.rectangle([cx - 5, 196 + 70 * 1.15 + open_, cx + 5, 196 + 70 * 1.15 + 24 + open_], fill=dark)   # stem
    for s in (-1, 1):                                                          # eye holes
        d.ellipse([cx + s * 30 - 14, 176, cx + s * 30 + 14, 194], fill=(20, 10, 12, 255))
    if amp > 0.08:                                                             # mouth slot
        d.rectangle([cx - 20, 232, cx + 20, 238 + 12 * amp], fill=(40, 8, 12, 255))
    else:
        d.line([(cx - 20, 234), (cx + 20, 234)], fill=dark, width=4)


@mask("deputy", tie=False)
def deputy(d, amp, t):
    """Agency deputy chief: tight low bun, rimless glasses, blazer, a lanyard with a badge turned backwards."""
    cx = CX
    skin, hair = (226, 196, 170, 255), (70, 52, 40, 255)
    jaw = 6 * amp
    d.ellipse([cx - 64, 96, cx + 64, 200], fill=hair)
    d.ellipse([cx + 30, 200, cx + 82, 250], fill=hair)                          # bun
    d.ellipse([cx - 58, 112, cx + 58, 290 + jaw], fill=skin)
    d.chord([cx - 62, 100, cx + 62, 190], 180, 360, fill=hair)
    for s in (-1, 1):
        d.line([(cx + s * 44, 172), (cx + s * 14, 168)], fill=(80, 60, 50, 255), width=4)
    _eyes(d, cx, 192, gap=27, socket=(206, 176, 152, 255))
    for s in (-1, 1):
        d.rounded_rectangle([cx + s * 27 - 19, 180, cx + s * 27 + 19, 204], radius=6, outline=(190, 190, 196, 255), width=2)
    d.polygon([(cx - 4, 200), (cx + 4, 200), (cx + 9, 236), (cx - 9, 236)], fill=(206, 176, 152, 255))
    _mouth(d, cx, 260 + jaw * 0.5, amp, w=16, lip=(150, 80, 80, 255))
    d.line([(cx - 34, 300), (cx, 410), (cx + 34, 300)], fill=(30, 60, 140, 255), width=5)   # lanyard
    d.rectangle([cx - 20, 408, cx + 20, 456], fill=(236, 236, 236, 255), outline=(120, 120, 120, 255))


@mask("analyst", tie=False)
def analyst(d, amp, t):
    """Junior analyst: overgrown side-swept hair, earnest eyebrows, a quarter-zip pullover."""
    cx = CX
    skin, hair = (238, 214, 194, 255), (180, 140, 90, 255)
    jaw = 6 * amp
    d.polygon([(cx - 70, 340), (cx - 40, 300), (cx + 40, 300), (cx + 70, 340), (cx + 150, 520), (cx - 150, 520)], fill=(70, 80, 96, 255))  # quarter-zip
    d.line([(cx, 300), (cx, 380)], fill=(190, 190, 196, 255), width=3)
    d.ellipse([cx - 60, 110, cx + 60, 288 + jaw], fill=skin)
    d.polygon([(cx - 64, 160), (cx - 60, 110), (cx - 10, 92), (cx + 50, 100), (cx + 72, 140), (cx + 10, 130), (cx - 40, 150)], fill=hair)
    for s in (-1, 1):                                                         # earnest, slightly worried brows
        d.line([(cx + s * 44, 170 + 4), (cx + s * 12, 164)], fill=(140, 100, 60, 255), width=5)
    _eyes(d, cx, 192, gap=27, socket=(218, 194, 174, 255))
    d.polygon([(cx - 4, 200), (cx + 4, 200), (cx + 9, 236), (cx - 9, 236)], fill=(218, 194, 174, 255))
    _mouth(d, cx, 260 + jaw * 0.5, amp, w=15)


@mask("caseofficer", tie=True)
def caseofficer(d, amp, t):
    """Old-school case officer: tinted aviators, a heavy moustache, a five-o'clock shadow, tie yanked loose,
    a cigarette parked behind one ear."""
    cx = CX
    skin, hair = (214, 180, 150, 255), (40, 36, 34, 255)
    jaw = 8 * amp
    d.ellipse([cx - 66, 104, cx + 66, 296 + jaw], fill=skin)
    d.chord([cx - 70, 92, cx + 70, 200], 180, 360, fill=hair)                    # thick dark hair
    d.chord([cx - 56, 220, cx + 56, 300 + jaw], 0, 180, fill=(170, 146, 124, 255))   # stubble
    for s in (-1, 1):                                                         # aviators
        d.polygon([(cx + s * 8, 180), (cx + s * 58, 176), (cx + s * 54, 212), (cx + s * 30, 220), (cx + s * 12, 206)],
                  fill=(80, 60, 30, 220), outline=(200, 170, 80, 255))
    d.line([(cx - 8, 182), (cx + 8, 182)], fill=(200, 170, 80, 255), width=3)
    d.polygon([(cx - 5, 206), (cx + 5, 206), (cx + 12, 240), (cx - 12, 240)], fill=(196, 160, 130, 255))
    d.polygon([(cx - 40, 248), (cx + 40, 248), (cx + 34, 262), (cx - 34, 262)], fill=hair)  # moustache
    my = 270 + jaw * 0.4
    if amp > 0.08:
        d.ellipse([cx - 18, my - 4, cx + 18, my + 4 + 12 * amp], fill=(60, 24, 24, 255))
    d.line([(cx + 62, 150), (cx + 92, 140)], fill=(240, 236, 226, 255), width=6)   # cigarette behind the ear
    d.line([(cx + 88, 141), (cx + 92, 140)], fill=(200, 120, 60, 255), width=6)
    d.polygon([(cx - 20, 330), (cx + 4, 330), (cx + 20, 430), (cx + 2, 452), (cx - 14, 432)], fill=(120, 30, 34, 255))  # loose tie, askew


@mask("vicparka", tie=False)
def vicparka(d, amp, t):
    """Vic in costume: the same aviators and moustache, now inside a brand-new orange expedition parka with a
    fur-ruffed hood, a fake grey beard hooked over his ears, and the store tag still dangling from the zip."""
    cx = CX
    orange, dark = (226, 110, 30, 255), (170, 76, 18, 255)
    d.polygon([(cx - 200, 520), (cx - 180, 340), (cx - 90, 290), (cx + 90, 290), (cx + 180, 340), (cx + 200, 520)], fill=orange)
    d.line([(cx, 300), (cx, 520)], fill=dark, width=5)
    d.line([(cx + 4, 360), (cx + 30, 410)], fill=(240, 240, 240, 255), width=2)          # the tag string
    d.rectangle([cx + 22, 410, cx + 50, 446], fill=(250, 250, 250, 255), outline=(150, 150, 150, 255))
    d.ellipse([cx - 104, 80, cx + 104, 330], fill=(186, 170, 150, 255))                   # fur ruff
    for k in range(28):
        a = 2 * math.pi * k / 28
        d.line([(cx + 96 * math.cos(a), 205 + 118 * math.sin(a)), (cx + 110 * math.cos(a), 205 + 132 * math.sin(a))],
               fill=(210, 196, 176, 255), width=4)
    d.ellipse([cx - 80, 100, cx + 80, 312], fill=orange)                                  # hood
    skin = (214, 180, 150, 255); jaw = 8 * amp
    d.ellipse([cx - 56, 126, cx + 56, 292 + jaw], fill=skin)
    for s in (-1, 1):                                                                    # aviators, still
        d.polygon([(cx + s * 8, 180), (cx + s * 52, 176), (cx + s * 48, 208), (cx + s * 28, 214), (cx + s * 12, 202)],
                  fill=(80, 60, 30, 220), outline=(200, 170, 80, 255))
    d.polygon([(cx - 5, 204), (cx + 5, 204), (cx + 11, 234), (cx - 11, 234)], fill=(196, 160, 130, 255))
    d.polygon([(cx - 36, 242), (cx + 36, 242), (cx + 30, 254), (cx - 30, 254)], fill=(40, 36, 34, 255))   # real moustache
    beard = [(cx - 54, 236), (cx + 54, 236), (cx + 48, 300 + jaw), (cx + 20, 330 + jaw), (cx - 20, 330 + jaw), (cx - 48, 300 + jaw)]
    d.polygon(beard, fill=(200, 200, 204, 255))                                           # fake beard
    d.line([(cx - 54, 236), (cx - 58, 200)], fill=(180, 180, 184, 255), width=2)          # its elastic
    d.line([(cx + 54, 236), (cx + 58, 200)], fill=(180, 180, 184, 255), width=2)
    if amp > 0.08:
        d.ellipse([cx - 14, 262, cx + 14, 266 + 12 * amp], fill=(60, 24, 24, 255))


def _ranger_hoodie(d, cx):
    """The red Canadian Ranger sweatshirt (plain: no crest drawn) under an open dark parka."""
    red = (196, 32, 40, 255)
    d.polygon([(cx - 200, 520), (cx - 180, 340), (cx - 90, 290), (cx + 90, 290), (cx + 180, 340), (cx + 200, 520)], fill=(40, 46, 52, 255))
    d.polygon([(cx - 70, 300), (cx + 70, 300), (cx + 96, 520), (cx - 96, 520)], fill=red)
    d.arc([cx - 50, 270, cx + 50, 330], 0, 180, fill=(150, 20, 28, 255), width=8)       # hood collar
    d.line([(cx - 24, 330), (cx - 20, 380)], fill=(240, 240, 240, 255), width=3)        # drawstrings
    d.line([(cx + 24, 330), (cx + 20, 380)], fill=(240, 240, 240, 255), width=3)


@mask("rangersgt", tie=False)
def rangersgt(d, amp, t):
    """Ranger patrol sergeant: an older woman, round glasses, a knitted toque with a pompom, the red hoodie."""
    cx = CX
    _ranger_hoodie(d, cx)
    skin = (196, 150, 116, 255); jaw = 6 * amp
    d.ellipse([cx - 60, 118, cx + 60, 290 + jaw], fill=skin)
    d.chord([cx - 66, 86, cx + 66, 196], 180, 360, fill=(60, 90, 140, 255))               # toque
    d.rectangle([cx - 66, 136, cx + 66, 160], fill=(230, 230, 230, 255))
    d.ellipse([cx - 18, 62, cx + 18, 96], fill=(230, 230, 230, 255))                      # pompom
    d.polygon([(cx - 60, 160), (cx - 66, 240), (cx - 50, 250), (cx - 46, 170)], fill=(70, 70, 76, 255))   # dark grey hair
    d.polygon([(cx + 60, 160), (cx + 66, 240), (cx + 50, 250), (cx + 46, 170)], fill=(70, 70, 76, 255))
    for s in (-1, 1):
        d.ellipse([cx + s * 26 - 17, 182, cx + s * 26 + 17, 208], outline=(60, 50, 40, 255), width=3)
        d.ellipse([cx + s * 26 - 6, 190, cx + s * 26 + 6, 200], fill=(30, 20, 16, 255))
        d.arc([cx + s * 26 - 14, 204, cx + s * 26 + 14, 216], 20, 160, fill=(160, 116, 86, 255), width=2)   # smile lines
    d.polygon([(cx - 5, 206), (cx + 5, 206), (cx + 10, 236), (cx - 10, 236)], fill=(176, 132, 100, 255))
    _mouth(d, cx, 258 + jaw * 0.5, amp, w=16, lip=(140, 80, 70, 255))


@mask("rangerjonah", tie=False)
def rangerjonah(d, amp, t):
    """Young Ranger: a flat-brim ball cap, a thin moustache, deadpan eyes, the red hoodie."""
    cx = CX
    _ranger_hoodie(d, cx)
    skin = (190, 144, 110, 255); jaw = 6 * amp
    d.ellipse([cx - 58, 118, cx + 58, 290 + jaw], fill=skin)
    d.chord([cx - 64, 98, cx + 64, 200], 180, 360, fill=(30, 30, 34, 255))                # cap crown
    d.rectangle([cx - 80, 146, cx + 80, 160], fill=(30, 30, 34, 255))                      # flat brim
    for s in (-1, 1):                                                                     # half-lidded, deadpan
        d.ellipse([cx + s * 26 - 14, 186, cx + s * 26 + 14, 202], fill=(240, 236, 230, 255))
        d.ellipse([cx + s * 26 - 6, 188, cx + s * 26 + 6, 200], fill=(26, 18, 14, 255))
        d.rectangle([cx + s * 26 - 15, 183, cx + s * 26 + 15, 192], fill=skin)
    d.polygon([(cx - 5, 204), (cx + 5, 204), (cx + 10, 234), (cx - 10, 234)], fill=(170, 126, 96, 255))
    d.line([(cx - 20, 244), (cx + 20, 244)], fill=(40, 30, 26, 255), width=3)              # thin moustache
    _mouth(d, cx, 258 + jaw * 0.5, amp, w=14)


@mask("rangerdoug", tie=False)
def rangerdoug(d, amp, t):
    """Ranger and long-time resident from Newfoundland: a big ginger beard, a striped toque, the red hoodie."""
    cx = CX
    _ranger_hoodie(d, cx)
    skin = (236, 196, 170, 255); beard = (176, 96, 46, 255); jaw = 7 * amp
    d.ellipse([cx - 60, 116, cx + 60, 290 + jaw], fill=skin)
    d.chord([cx - 66, 84, cx + 66, 194], 180, 360, fill=(30, 110, 70, 255))                 # striped toque
    for k, col in enumerate([(240, 240, 240, 255), (200, 40, 40, 255), (240, 240, 240, 255)]):
        d.rectangle([cx - 66, 112 + k * 10, cx + 66, 120 + k * 10], fill=col)
    _eyes(d, cx, 188, gap=27, socket=(220, 180, 156, 255))
    d.polygon([(cx - 5, 198), (cx + 5, 198), (cx + 11, 230), (cx - 11, 230)], fill=(220, 176, 150, 255))
    d.polygon([(cx - 60, 220), (cx + 60, 220), (cx + 54, 300 + jaw), (cx + 20, 334 + jaw), (cx - 20, 334 + jaw), (cx - 54, 300 + jaw)], fill=beard)
    if amp > 0.08:
        d.ellipse([cx - 14, 252, cx + 14, 256 + 12 * amp], fill=(70, 30, 24, 255))
    else:
        d.line([(cx - 14, 254), (cx + 14, 254)], fill=(120, 60, 30, 255), width=3)


@mask("trucker", tie=False)
def trucker(d, amp, t):
    """Long-haul trucker: a mesh-back cap, a big salt-and-pepper beard, a plaid flannel shirt."""
    cx = CX
    plaid = (150, 40, 40, 255)
    d.polygon([(cx - 200, 520), (cx - 180, 340), (cx - 90, 290), (cx + 90, 290), (cx + 180, 340), (cx + 200, 520)], fill=plaid)
    for k in range(-180, 200, 40):
        d.line([(cx + k, 300), (cx + k, 520)], fill=(90, 20, 24, 255), width=8)
    for y in range(320, 520, 40):
        d.line([(cx - 190, y), (cx + 190, y)], fill=(90, 20, 24, 255), width=8)
    skin, jaw = (226, 186, 156, 255), 7 * amp
    d.ellipse([cx - 62, 116, cx + 62, 290 + jaw], fill=skin)
    d.chord([cx - 68, 90, cx + 68, 200], 180, 360, fill=(40, 70, 120, 255))                # cap front panel
    d.chord([cx - 68, 90, cx + 68, 200], 180, 250, fill=(230, 230, 230, 255))              # mesh back
    d.rectangle([cx - 70, 140, cx + 92, 156], fill=(40, 70, 120, 255))                     # brim
    _eyes(d, cx, 188, gap=28, socket=(206, 168, 140, 255))
    d.polygon([(cx - 5, 198), (cx + 5, 198), (cx + 11, 230), (cx - 11, 230)], fill=(206, 166, 136, 255))
    d.polygon([(cx - 62, 214), (cx + 62, 214), (cx + 58, 300 + jaw), (cx + 24, 340 + jaw), (cx - 24, 340 + jaw), (cx - 58, 300 + jaw)],
              fill=(120, 116, 112, 255))
    if amp > 0.08:
        d.ellipse([cx - 14, 250, cx + 14, 254 + 12 * amp], fill=(60, 24, 24, 255))
    else:
        d.line([(cx - 14, 252), (cx + 14, 252)], fill=(70, 66, 62, 255), width=3)


@mask("truckerdarcy", tie=False)
def truckerdarcy(d, amp, t):
    """Owner-operator: a ponytail pulled through the back of a cap, sunglasses pushed up on it, a work jacket."""
    cx = CX
    d.polygon([(cx - 200, 520), (cx - 180, 340), (cx - 90, 290), (cx + 90, 290), (cx + 180, 340), (cx + 200, 520)], fill=(150, 116, 60, 255))
    d.polygon([(cx - 60, 300), (cx + 60, 300), (cx + 40, 350), (cx - 40, 350)], fill=(110, 80, 40, 255))   # collar
    skin, jaw = (236, 204, 180, 255), 6 * amp
    d.polygon([(cx + 40, 170), (cx + 110, 230), (cx + 96, 300), (cx + 70, 240)], fill=(150, 90, 50, 255))   # ponytail
    d.ellipse([cx - 58, 118, cx + 58, 288 + jaw], fill=skin)
    d.chord([cx - 64, 92, cx + 64, 198], 180, 360, fill=(60, 60, 64, 255))
    d.rectangle([cx - 66, 140, cx + 88, 154], fill=(60, 60, 64, 255))
    for s in (-1, 1):                                                                       # sunglasses up on the cap
        d.ellipse([cx + s * 24 - 18, 108, cx + s * 24 + 18, 128], fill=(20, 20, 24, 255))
    _eyes(d, cx, 188, gap=27, socket=(220, 190, 166, 255))
    d.polygon([(cx - 5, 198), (cx + 5, 198), (cx + 10, 230), (cx - 10, 230)], fill=(220, 188, 164, 255))
    _mouth(d, cx, 256 + jaw * 0.5, amp, w=15, lip=(160, 90, 86, 255))


@mask("premier", tie=False)
def premier(d, amp, t):
    """A provincial premier: a big blonde blowout, a pastel blazer with a large brooch, and eyes that slide left
    and right as if checking which way the room is leaning."""
    cx = CX
    d.polygon([(cx - 200, 520), (cx - 180, 340), (cx - 90, 290), (cx + 90, 290), (cx + 180, 340), (cx + 200, 520)], fill=(110, 170, 200, 255))
    d.polygon([(cx - 40, 300), (cx + 40, 300), (cx, 360)], fill=(250, 250, 250, 255))
    d.ellipse([cx + 60, 340, cx + 92, 372], fill=(220, 180, 60, 255))                          # brooch
    skin, hair, jaw = (240, 210, 190, 255), (232, 206, 140, 255), 6 * amp
    d.ellipse([cx - 92, 86, cx + 92, 290], fill=hair)                                         # blowout
    d.ellipse([cx - 58, 116, cx + 58, 290 + jaw], fill=skin)
    d.chord([cx - 70, 96, cx + 70, 200], 180, 360, fill=hair)
    look = 8 * math.sin(t * 0.9)                                                              # which way is the wind blowing
    for s in (-1, 1):
        d.ellipse([cx + s * 27 - 16, 182, cx + s * 27 + 16, 202], fill=(250, 246, 240, 255))
        d.ellipse([cx + s * 27 - 6 + look, 186, cx + s * 27 + 6 + look, 198], fill=(40, 60, 90, 255))
        d.line([(cx + s * 27 - 18, 174), (cx + s * 27 + 18, 172)], fill=(150, 120, 80, 255), width=4)
    d.polygon([(cx - 4, 200), (cx + 4, 200), (cx + 9, 232), (cx - 9, 232)], fill=(224, 192, 172, 255))
    _mouth(d, cx, 256 + jaw * 0.5, amp, w=17, lip=(190, 70, 90, 255))


@mask("zoomertyson", tie=False)
def zoomertyson(d, amp, t):
    """Nineteen: a mullet, ear protection pushed down around the neck, a camo jacket, a faint moustache attempt."""
    cx = CX
    d.polygon([(cx - 200, 520), (cx - 180, 340), (cx - 90, 290), (cx + 90, 290), (cx + 180, 340), (cx + 200, 520)], fill=(96, 104, 70, 255))
    rng = [(cx - 150, 400), (cx - 60, 460), (cx + 40, 380), (cx + 120, 470), (cx - 110, 500), (cx + 150, 410)]
    for x, y in rng:
        d.ellipse([x - 30, y - 16, x + 30, y + 16], fill=(70, 76, 50, 255))
    d.arc([cx - 80, 270, cx + 80, 330], 0, 180, fill=(40, 40, 44, 255), width=10)               # earmuffs around the neck
    for s in (-1, 1):
        d.ellipse([cx + s * 78 - 22, 280, cx + s * 78 + 22, 320], fill=(230, 120, 30, 255))
    skin, hair, jaw = (240, 210, 186, 255), (170, 120, 70, 255), 6 * amp
    d.polygon([(cx - 56, 200), (cx - 70, 300), (cx + 70, 300), (cx + 56, 200)], fill=hair)       # mullet, business in front
    d.ellipse([cx - 56, 120, cx + 56, 286 + jaw], fill=skin)
    d.chord([cx - 62, 104, cx + 62, 190], 180, 360, fill=hair)
    _eyes(d, cx, 190, gap=26, socket=(224, 196, 172, 255))
    d.polygon([(cx - 4, 200), (cx + 4, 200), (cx + 9, 230), (cx - 9, 230)], fill=(224, 194, 170, 255))
    d.line([(cx - 16, 242), (cx + 16, 242)], fill=(200, 160, 120, 255), width=2)                 # the moustache attempt
    _mouth(d, cx, 256 + jaw * 0.5, amp, w=14)


@mask("zoomermac", tie=False)
def zoomermac(d, amp, t):
    """Twenty: amber shooting glasses, a long braid over one shoulder, a toque, a puffer vest over a hoodie."""
    cx = CX
    d.polygon([(cx - 200, 520), (cx - 180, 340), (cx - 90, 290), (cx + 90, 290), (cx + 180, 340), (cx + 200, 520)], fill=(110, 110, 120, 255))
    d.polygon([(cx - 160, 520), (cx - 140, 350), (cx - 60, 300), (cx - 30, 520)], fill=(40, 60, 90, 255))   # puffer vest
    d.polygon([(cx + 160, 520), (cx + 140, 350), (cx + 60, 300), (cx + 30, 520)], fill=(40, 60, 90, 255))
    skin, hair, jaw = (226, 190, 160, 255), (60, 40, 30, 255), 6 * amp
    d.ellipse([cx - 58, 118, cx + 58, 288 + jaw], fill=skin)
    for k in range(6):                                                                         # braid
        d.ellipse([cx + 40 + k * 4, 230 + k * 30, cx + 70 + k * 4, 262 + k * 30], fill=hair)
    d.chord([cx - 64, 92, cx + 64, 196], 180, 360, fill=(190, 40, 50, 255))                     # toque
    d.rectangle([cx - 64, 142, cx + 64, 160], fill=(220, 220, 220, 255))
    d.rounded_rectangle([cx - 56, 176, cx + 56, 208], radius=12, fill=(240, 180, 60, 170), outline=(60, 60, 60, 255), width=3)  # amber glasses
    d.polygon([(cx - 4, 206), (cx + 4, 206), (cx + 9, 234), (cx - 9, 234)], fill=(210, 176, 148, 255))
    _mouth(d, cx, 256 + jaw * 0.5, amp, w=15, lip=(170, 90, 90, 255))


def _uniform(d, cx, col, braid=False):
    """Dress tunic: the suit shape recoloured, with shoulder boards and medal ribbons."""
    d.polygon([(cx - 200, 520), (cx - 180, 340), (cx - 90, 290), (cx + 90, 290), (cx + 180, 340), (cx + 200, 520)], fill=col)
    d.polygon([(cx - 40, 300), (cx + 40, 300), (cx, 380)], fill=(236, 236, 236, 255))
    d.polygon([(cx - 12, 312), (cx + 12, 312), (cx + 16, 400), (cx, 420), (cx - 16, 400)], fill=(20, 20, 24, 255))
    for s in (-1, 1):
        d.rectangle([cx + s * 150 - 30, 330, cx + s * 150 + 30, 346], fill=(20, 20, 30, 255) if not braid else (200, 170, 70, 255))
    for k, c in enumerate([(200, 40, 40, 255), (40, 80, 160, 255), (220, 190, 60, 255), (40, 130, 70, 255)]):
        d.rectangle([cx - 140 + (k % 2) * 30, 380 + (k // 2) * 12, cx - 112 + (k % 2) * 30, 390 + (k // 2) * 12], fill=c)


@mask("minister", tie=True)
def minister(d, amp, t):
    """A defence minister: a tidy grey part, a flag lapel pin, a very practised smile."""
    cx = CX
    skin, jaw = (232, 200, 178, 255), 6 * amp
    d.ellipse([cx - 60, 114, cx + 60, 290 + jaw], fill=skin)
    d.chord([cx - 66, 96, cx + 66, 196], 180, 360, fill=(170, 170, 176, 255))
    d.polygon([(cx - 66, 146), (cx + 10, 120), (cx + 66, 146), (cx + 66, 130), (cx - 66, 130)], fill=(170, 170, 176, 255))
    _eyes(d, cx, 190, gap=27, socket=(214, 184, 164, 255))
    d.polygon([(cx - 5, 200), (cx + 5, 200), (cx + 10, 232), (cx - 10, 232)], fill=(214, 184, 164, 255))
    my = 256 + jaw * 0.5
    if amp > 0.08:
        d.chord([cx - 22, my - 6, cx + 22, my + 8 + 12 * amp], 0, 180, fill=(70, 30, 30, 255))
    else:
        d.arc([cx - 22, my - 12, cx + 22, my + 6], 20, 160, fill=(150, 80, 80, 255), width=4)   # the smile
    d.rectangle([cx - 74, 344, cx - 60, 352], fill=(220, 40, 40, 255))                             # flag pin
    d.rectangle([cx - 70, 344, cx - 64, 352], fill=(240, 240, 240, 255))


@mask("general", tie=False)
def general(d, amp, t):
    """Chief of the Defence Staff: a dark green tunic with ribbons, a cropped grey moustache, tired eyes."""
    cx = CX
    _uniform(d, cx, (60, 74, 54, 255))
    skin, jaw = (224, 190, 166, 255), 6 * amp
    d.ellipse([cx - 60, 114, cx + 60, 290 + jaw], fill=skin)
    d.chord([cx - 64, 100, cx + 64, 180], 180, 360, fill=(120, 120, 124, 255))                    # cropped grey
    _eyes(d, cx, 190, gap=27, socket=(204, 170, 148, 255))
    for s in (-1, 1):
        d.arc([cx + s * 27 - 15, 198, cx + s * 27 + 15, 214], 20, 160, fill=(170, 130, 110, 255), width=2)   # bags
    d.polygon([(cx - 5, 200), (cx + 5, 200), (cx + 10, 232), (cx - 10, 232)], fill=(204, 170, 148, 255))
    d.rectangle([cx - 26, 240, cx + 26, 250], fill=(130, 130, 134, 255))                            # moustache
    _mouth(d, cx, 262 + jaw * 0.5, amp, w=15)


@mask("admiral", tie=False)
def admiral(d, amp, t):
    """Commander of the Navy: a navy tunic with gold shoulder boards, a short dark bob, a calm, flat stare."""
    cx = CX
    _uniform(d, cx, (24, 30, 54, 255), braid=True)
    skin, hair, jaw = (236, 206, 186, 255), (50, 40, 36, 255), 6 * amp
    d.ellipse([cx - 76, 100, cx + 76, 270], fill=hair)
    d.ellipse([cx - 58, 114, cx + 58, 288 + jaw], fill=skin)
    d.chord([cx - 66, 100, cx + 66, 190], 180, 360, fill=hair)
    for s in (-1, 1):
        d.ellipse([cx + s * 27 - 14, 184, cx + s * 27 + 14, 200], fill=(240, 236, 230, 255))
        d.ellipse([cx + s * 27 - 6, 186, cx + s * 27 + 6, 198], fill=(30, 40, 60, 255))
        d.line([(cx + s * 27 - 16, 178), (cx + s * 27 + 16, 178)], fill=(60, 50, 44, 255), width=4)    # flat brows
    d.polygon([(cx - 4, 200), (cx + 4, 200), (cx + 9, 232), (cx - 9, 232)], fill=(220, 190, 170, 255))
    _mouth(d, cx, 258 + jaw * 0.5, amp, w=15, lip=(160, 90, 90, 255))


@mask("sofcom", tie=False)
def sofcom(d, amp, t):
    """Commander of special forces: a black balaclava, dark glasses, and a face that is pixelated anyway."""
    cx = CX
    _uniform(d, cx, (46, 50, 40, 255))
    d.ellipse([cx - 62, 110, cx + 62, 292], fill=(26, 26, 30, 255))                                  # balaclava
    for y in range(140, 290, 18):                                                                    # pixelation
        for x in range(cx - 54, cx + 54, 18):
            v = 30 + int(20 * math.sin(x * 0.3 + y * 0.7 + t * 0.5) ** 2)
            d.rectangle([x, y, x + 16, y + 16], fill=(v, v, v + 4, 255))
    d.rectangle([cx - 50, 180, cx + 50, 204], fill=(10, 10, 12, 255))                                # glasses band
    if amp > 0.08:
        d.rectangle([cx - 16, 252, cx + 16, 256 + 10 * amp], fill=(10, 10, 12, 255))


@mask("rangerjosie", tie=False)
def rangerjosie(d, amp, t):
    """The eldest Ranger: white hair under a hood with a fur ruff, deep smile lines, the red hoodie."""
    cx = CX
    _ranger_hoodie(d, cx)
    d.ellipse([cx - 92, 96, cx + 92, 312], fill=(150, 130, 110, 255))                               # fur ruff
    d.ellipse([cx - 76, 110, cx + 76, 304], fill=(120, 30, 36, 255))                                # hood
    skin, jaw = (186, 140, 108, 255), 5 * amp
    d.ellipse([cx - 56, 126, cx + 56, 290 + jaw], fill=skin)
    d.chord([cx - 58, 120, cx + 58, 186], 180, 360, fill=(236, 236, 236, 255))                       # white hair
    for s in (-1, 1):
        d.arc([cx + s * 26 - 14, 182, cx + s * 26 + 14, 200], 200, 340, fill=(40, 30, 24, 255), width=4)   # smiling eyes
        for k in range(3):
            d.line([(cx + s * 44, 188 + k * 5), (cx + s * 54, 184 + k * 7)], fill=(150, 106, 80, 255), width=2)
    d.polygon([(cx - 5, 198), (cx + 5, 198), (cx + 10, 230), (cx - 10, 230)], fill=(168, 124, 94, 255))
    for s in (-1, 1):
        d.arc([cx + s * 30 - 16, 230, cx + s * 30 + 16, 262], 90 - s * 60, 90 + s * 60, fill=(150, 106, 80, 255), width=2)
    _mouth(d, cx, 256 + jaw * 0.5, amp, w=16, lip=(130, 70, 60, 255))


@mask("mandarin", tie=False)
def mandarin(d, amp, t):
    """The Clerk: silver swept-back hair, half-moon glasses on a chain, a bow tie, an expression of infinite patience."""
    cx = CX
    skin, jaw = (230, 204, 186, 255), 5 * amp
    d.ellipse([cx - 60, 112, cx + 60, 290 + jaw], fill=skin)
    d.chord([cx - 66, 92, cx + 66, 190], 180, 360, fill=(214, 214, 220, 255))
    d.polygon([(cx - 66, 150), (cx - 40, 112), (cx + 50, 108), (cx + 66, 150), (cx + 30, 128)], fill=(214, 214, 220, 255))
    for s in (-1, 1):
        d.arc([cx + s * 27 - 16, 180, cx + s * 27 + 16, 200], 200, 340, fill=(40, 34, 30, 255), width=3)   # patient, half-closed
        d.chord([cx + s * 27 - 18, 196, cx + s * 27 + 18, 222], 180, 360, outline=(150, 130, 60, 255), width=3)
    d.line([(cx - 45, 210), (cx - 70, 300)], fill=(180, 160, 80, 255), width=2)                    # glasses chain
    d.line([(cx + 45, 210), (cx + 70, 300)], fill=(180, 160, 80, 255), width=2)
    d.polygon([(cx - 4, 204), (cx + 4, 204), (cx + 9, 236), (cx - 9, 236)], fill=(214, 186, 168, 255))
    _mouth(d, cx, 260 + jaw * 0.5, amp, w=14)
    d.polygon([(cx, 316), (cx - 34, 302), (cx - 34, 330)], fill=(120, 20, 40, 255))                 # bow tie
    d.polygon([(cx, 316), (cx + 34, 302), (cx + 34, 330)], fill=(120, 20, 40, 255))


@mask("deputyclerk", tie=False)
def deputyclerk(d, amp, t):
    """Deputy secretary: a severe chin-length grey bob, reading glasses, a scarf knotted exactly right."""
    cx = CX
    skin, hair, jaw = (236, 210, 192, 255), (150, 150, 156, 255), 5 * amp
    d.polygon([(cx - 76, 140), (cx - 66, 100), (cx, 86), (cx + 66, 100), (cx + 76, 140), (cx + 74, 258), (cx - 74, 258)], fill=hair)
    d.ellipse([cx - 56, 116, cx + 56, 288 + jaw], fill=skin)
    d.rectangle([cx - 66, 112, cx + 66, 150], fill=hair)
    for s in (-1, 1):
        d.rectangle([cx + s * 27 - 17, 184, cx + s * 27 + 17, 204], outline=(40, 40, 44, 255), width=3)
        d.ellipse([cx + s * 27 - 5, 189, cx + s * 27 + 5, 199], fill=(30, 30, 34, 255))
    d.polygon([(cx - 4, 204), (cx + 4, 204), (cx + 9, 236), (cx - 9, 236)], fill=(220, 192, 174, 255))
    _mouth(d, cx, 260 + jaw * 0.5, amp, w=14, lip=(150, 80, 80, 255))
    d.polygon([(cx - 60, 300), (cx + 60, 300), (cx + 30, 340), (cx - 30, 340)], fill=(160, 40, 60, 255))   # scarf
    d.polygon([(cx + 10, 330), (cx + 30, 330), (cx + 26, 400), (cx + 6, 396)], fill=(160, 40, 60, 255))


@mask("atipcoord", tie=False)
def atipcoord(d, amp, t):
    """Access-to-information coordinator: frizzed hair with a pencil in it, sticky notes on the cardigan, eyes
    that have read every page."""
    cx = CX
    d.polygon([(cx - 200, 520), (cx - 180, 340), (cx - 90, 290), (cx + 90, 290), (cx + 180, 340), (cx + 200, 520)], fill=(120, 96, 130, 255))
    for k, (x, y) in enumerate([(-130, 380), (-90, 430), (100, 400), (130, 460), (-60, 480)]):
        d.rectangle([cx + x - 18, y - 18, cx + x + 18, y + 18], fill=[(250, 230, 90, 255), (250, 160, 190, 255), (150, 220, 250, 255)][k % 3])
    skin, hair, jaw = (236, 206, 182, 255), (120, 70, 40, 255), 6 * amp
    for k in range(14):
        a = math.pi * (1.0 + k / 13)
        d.ellipse([cx + 70 * math.cos(a) - 26, 170 + 80 * math.sin(a) - 26, cx + 70 * math.cos(a) + 26, 170 + 80 * math.sin(a) + 26], fill=hair)
    d.ellipse([cx - 58, 116, cx + 58, 288 + jaw], fill=skin)
    d.line([(cx + 30, 90), (cx + 80, 150)], fill=(240, 200, 60, 255), width=6)                    # pencil
    for s in (-1, 1):
        d.ellipse([cx + s * 27 - 15, 182, cx + s * 27 + 15, 204], fill=(244, 240, 236, 255))
        d.ellipse([cx + s * 27 - 5, 188, cx + s * 27 + 5, 198], fill=(40, 30, 26, 255))
        d.arc([cx + s * 27 - 15, 200, cx + s * 27 + 15, 214], 20, 160, fill=(170, 130, 120, 255), width=2)   # bags
    d.polygon([(cx - 4, 204), (cx + 4, 204), (cx + 9, 234), (cx - 9, 234)], fill=(220, 190, 166, 255))
    _mouth(d, cx, 258 + jaw * 0.5, amp, w=15)


@mask("comms", tie=False)
def comms(d, amp, t):
    """Communications director: an immaculate fade, a quarter-smile, a phone already in hand."""
    cx = CX
    d.polygon([(cx - 200, 520), (cx - 180, 340), (cx - 90, 290), (cx + 90, 290), (cx + 180, 340), (cx + 200, 520)], fill=(30, 34, 44, 255))
    d.polygon([(cx - 40, 300), (cx + 40, 300), (cx, 360)], fill=(200, 220, 240, 255))
    skin, jaw = (176, 130, 100, 255), 6 * amp
    d.ellipse([cx - 58, 116, cx + 58, 288 + jaw], fill=skin)
    d.chord([cx - 60, 104, cx + 60, 176], 180, 360, fill=(30, 26, 24, 255))
    _eyes(d, cx, 188, gap=27, socket=(160, 116, 90, 255))
    d.polygon([(cx - 4, 200), (cx + 4, 200), (cx + 9, 232), (cx - 9, 232)], fill=(160, 116, 90, 255))
    my = 258 + jaw * 0.5
    if amp > 0.08:
        d.chord([cx - 18, my - 6, cx + 22, my + 8 + 12 * amp], 0, 180, fill=(60, 26, 26, 255))
    else:
        d.arc([cx - 18, my - 10, cx + 22, my + 6], 20, 120, fill=(110, 60, 50, 255), width=4)
    d.rounded_rectangle([cx + 110, 360, cx + 150, 430], radius=6, fill=(20, 20, 24, 255), outline=(120, 120, 130, 255), width=2)  # phone


@mask("pcoanalyst", tie=True)
def pcoanalyst(d, amp, t):
    """Junior analyst: round glasses, a cowlick, a too-big suit, a lanyard; the only one who read the transcript."""
    cx = CX
    skin, hair, jaw = (240, 214, 196, 255), (60, 44, 34, 255), 6 * amp
    d.ellipse([cx - 56, 120, cx + 56, 286 + jaw], fill=skin)
    d.chord([cx - 62, 104, cx + 62, 190], 180, 360, fill=hair)
    d.polygon([(cx + 10, 108), (cx + 24, 76 + 3 * math.sin(t * 2)), (cx + 32, 110)], fill=hair)        # cowlick
    for s in (-1, 1):
        d.ellipse([cx + s * 26 - 18, 178, cx + s * 26 + 18, 210], outline=(40, 40, 44, 255), width=3)
        d.ellipse([cx + s * 26 - 6, 188, cx + s * 26 + 6, 200], fill=(30, 30, 34, 255))
    d.polygon([(cx - 4, 206), (cx + 4, 206), (cx + 9, 234), (cx - 9, 234)], fill=(224, 196, 178, 255))
    _mouth(d, cx, 258 + jaw * 0.5, amp, w=14)
    d.line([(cx - 34, 300), (cx - 10, 420), (cx + 34, 300)], fill=(200, 40, 40, 255), width=4)
    d.rectangle([cx - 30, 418, cx + 10, 456], fill=(236, 236, 236, 255))


def _back_suit(d, cx, col=(28, 28, 32, 255)):
    """A suit seen from behind: shoulders, a centre seam, a collar."""
    d.polygon([(cx - 200, 520), (cx - 180, 340), (cx - 90, 290), (cx + 90, 290), (cx + 180, 340), (cx + 200, 520)], fill=col)
    d.line([(cx, 330), (cx, 520)], fill=tuple(max(0, c - 12) for c in col[:3]) + (255,), width=3)
    d.polygon([(cx - 60, 292), (cx + 60, 292), (cx + 40, 318), (cx - 40, 318)], fill=tuple(min(255, c + 14) for c in col[:3]) + (255,))


@mask("mandarin_back", tie=False)
def mandarin_back(d, amp, t):
    """The Clerk, followed from behind: silver hair, ears, a pink neck above the collar. The head bobs when he talks."""
    cx = CX
    _back_suit(d, cx)
    nod = 3 * amp
    d.rectangle([cx - 30, 260, cx + 30, 300], fill=(222, 190, 170, 255))                       # neck
    for s in (-1, 1):
        d.ellipse([cx + s * 62 - 10, 186 + nod, cx + s * 62 + 10, 226 + nod], fill=(222, 190, 170, 255))   # ears
    d.ellipse([cx - 62, 110 + nod, cx + 62, 280 + nod], fill=(214, 214, 220, 255))             # silver back of head
    for k in range(5):
        d.arc([cx - 50 + k * 4, 130 + nod + k * 6, cx + 50 - k * 4, 270 + nod], 200, 340, fill=(190, 190, 198, 255), width=2)


@mask("official_back", tie=False)
def official_back(d, amp, t):
    """A senior official nobody names, followed from behind: a dark overcoat, a grey crew cut, a fedora brim."""
    cx = CX
    _back_suit(d, cx, (36, 34, 30, 255))
    nod = 3 * amp
    d.polygon([(cx - 70, 300), (cx - 30, 292), (cx - 50, 360)], fill=(60, 56, 50, 255))          # coat collar up
    d.polygon([(cx + 70, 300), (cx + 30, 292), (cx + 50, 360)], fill=(60, 56, 50, 255))
    d.rectangle([cx - 28, 262, cx + 28, 300], fill=(200, 170, 150, 255))
    d.ellipse([cx - 60, 130 + nod, cx + 60, 284 + nod], fill=(120, 120, 124, 255))
    d.ellipse([cx - 92, 132 + nod, cx + 92, 160 + nod], fill=(30, 30, 34, 255))                # hat brim
    d.chord([cx - 62, 70 + nod, cx + 62, 190 + nod], 180, 360, fill=(40, 40, 44, 255))         # crown
    d.rectangle([cx - 62, 128 + nod, cx + 62, 140 + nod], fill=(90, 70, 50, 255))             # band


@mask("cseliaison", tie=False)
def cseliaison(d, amp, t):
    """A signals-intelligence liaison: a hoodie under a blazer, one earbud in, a badge on a retractable reel."""
    cx = CX
    d.polygon([(cx - 200, 520), (cx - 180, 340), (cx - 90, 290), (cx + 90, 290), (cx + 180, 340), (cx + 200, 520)], fill=(46, 52, 64, 255))
    d.polygon([(cx - 70, 300), (cx + 70, 300), (cx + 60, 520), (cx - 60, 520)], fill=(110, 116, 124, 255))     # hoodie
    d.arc([cx - 60, 270, cx + 60, 340], 0, 180, fill=(90, 96, 104, 255), width=12)
    skin, hair, jaw = (226, 196, 172, 255), (90, 70, 50, 255), 6 * amp
    d.ellipse([cx - 56, 118, cx + 56, 286 + jaw], fill=skin)
    d.chord([cx - 62, 102, cx + 62, 172], 180, 360, fill=hair)
    d.polygon([(cx - 56, 236), (cx + 56, 236), (cx + 40, 290 + jaw), (cx - 40, 290 + jaw)], fill=(120, 96, 70, 255))   # short beard
    _eyes(d, cx, 188, gap=26, socket=(210, 180, 158, 255))
    d.polygon([(cx - 4, 200), (cx + 4, 200), (cx + 9, 230), (cx - 9, 230)], fill=(210, 180, 158, 255))
    if amp > 0.08:
        d.ellipse([cx - 14, 252, cx + 14, 256 + 12 * amp], fill=(60, 26, 26, 255))
    else:
        d.line([(cx - 14, 254), (cx + 14, 254)], fill=(80, 60, 40, 255), width=3)
    d.ellipse([cx + 52, 200, cx + 62, 212], fill=(240, 240, 240, 255))                          # earbud
    d.ellipse([cx - 120, 400, cx - 96, 424], fill=(40, 40, 44, 255))                            # badge reel
    d.rectangle([cx - 126, 424, cx - 90, 470], fill=(236, 236, 236, 255))


@mask("tbsanalyst", tie=False)
def tbsanalyst(d, amp, t):
    """Treasury Board analyst: a tight high ponytail, cat-eye glasses, a binder clutched to the chest."""
    cx = CX
    d.polygon([(cx - 200, 520), (cx - 180, 340), (cx - 90, 290), (cx + 90, 290), (cx + 180, 340), (cx + 200, 520)], fill=(70, 90, 80, 255))
    d.rectangle([cx - 110, 380, cx + 30, 520], fill=(30, 60, 140, 255), outline=(220, 220, 230, 255), width=3)   # binder
    d.rectangle([cx - 100, 400, cx + 20, 420], fill=(240, 240, 240, 255))
    skin, hair, jaw = (210, 170, 140, 255), (34, 26, 24, 255), 6 * amp
    d.ellipse([cx - 20, 50, cx + 20, 110], fill=hair)                                            # high ponytail
    d.ellipse([cx - 56, 116, cx + 56, 288 + jaw], fill=skin)
    d.chord([cx - 62, 100, cx + 62, 186], 180, 360, fill=hair)
    for s in (-1, 1):
        d.polygon([(cx + s * 8, 186), (cx + s * 48, 178), (cx + s * 50, 200), (cx + s * 12, 204)], outline=(30, 30, 34, 255), fill=None)
        d.ellipse([cx + s * 28 - 5, 187, cx + s * 28 + 5, 197], fill=(30, 24, 20, 255))
    d.polygon([(cx - 4, 202), (cx + 4, 202), (cx + 9, 232), (cx - 9, 232)], fill=(196, 156, 126, 255))
    _mouth(d, cx, 256 + jaw * 0.5, amp, w=15, lip=(170, 80, 90, 255))


@mask("cirnac", tie=False)
def cirnac(d, amp, t):
    """A director from another department: shoulder-length dark hair, rectangular glasses, a cardigan, a lanyard."""
    cx = CX
    d.polygon([(cx - 200, 520), (cx - 180, 340), (cx - 90, 290), (cx + 90, 290), (cx + 180, 340), (cx + 200, 520)], fill=(120, 60, 70, 255))
    skin, hair, jaw = (200, 156, 124, 255), (36, 28, 26, 255), 6 * amp
    d.polygon([(cx - 70, 150), (cx - 60, 100), (cx, 88), (cx + 60, 100), (cx + 70, 150), (cx + 72, 300), (cx - 72, 300)], fill=hair)
    d.ellipse([cx - 56, 116, cx + 56, 288 + jaw], fill=skin)
    d.chord([cx - 62, 102, cx + 62, 176], 180, 360, fill=hair)
    for s in (-1, 1):
        d.rectangle([cx + s * 27 - 18, 182, cx + s * 27 + 18, 204], outline=(40, 40, 44, 255), width=3)
        d.ellipse([cx + s * 27 - 5, 188, cx + s * 27 + 5, 198], fill=(30, 22, 18, 255))
    d.polygon([(cx - 4, 204), (cx + 4, 204), (cx + 9, 234), (cx - 9, 234)], fill=(184, 140, 110, 255))
    _mouth(d, cx, 258 + jaw * 0.5, amp, w=15, lip=(150, 80, 80, 255))
    d.line([(cx - 34, 300), (cx, 410), (cx + 34, 300)], fill=(30, 110, 90, 255), width=4)
    d.rectangle([cx - 18, 408, cx + 18, 446], fill=(236, 236, 236, 255))


@mask("heritage", tie=False)
def heritage(d, amp, t):
    """A policy officer from another department: a trimmed beard, round tortoiseshell glasses, a wool scarf."""
    cx = CX
    d.polygon([(cx - 200, 520), (cx - 180, 340), (cx - 90, 290), (cx + 90, 290), (cx + 180, 340), (cx + 200, 520)], fill=(60, 60, 70, 255))
    skin, hair, jaw = (232, 200, 176, 255), (70, 46, 30, 255), 6 * amp
    d.ellipse([cx - 56, 116, cx + 56, 288 + jaw], fill=skin)
    d.chord([cx - 62, 100, cx + 62, 180], 180, 360, fill=hair)
    d.polygon([(cx - 56, 232), (cx + 56, 232), (cx + 46, 292 + jaw), (cx - 46, 292 + jaw)], fill=hair)
    for s in (-1, 1):
        d.ellipse([cx + s * 26 - 17, 180, cx + s * 26 + 17, 208], outline=(120, 70, 30, 255), width=4)
        d.ellipse([cx + s * 26 - 5, 189, cx + s * 26 + 5, 199], fill=(30, 22, 18, 255))
    d.polygon([(cx - 4, 204), (cx + 4, 204), (cx + 9, 230), (cx - 9, 230)], fill=(214, 180, 156, 255))
    if amp > 0.08:
        d.ellipse([cx - 14, 250, cx + 14, 254 + 12 * amp], fill=(60, 26, 26, 255))
    d.polygon([(cx - 80, 300), (cx + 80, 300), (cx + 70, 340), (cx - 70, 340)], fill=(170, 40, 50, 255))   # scarf
    d.polygon([(cx + 20, 330), (cx + 50, 330), (cx + 44, 430), (cx + 16, 426)], fill=(170, 40, 50, 255))


@mask("diplomat", tie=True)
def diplomat(d, amp, t):
    """Global Affairs: close-cropped hair with grey at the temples, a pocket square, a diplomatic half-smile."""
    cx = CX
    skin, jaw = (120, 82, 60, 255), 6 * amp
    d.ellipse([cx - 58, 116, cx + 58, 288 + jaw], fill=skin)
    d.chord([cx - 62, 104, cx + 62, 170], 180, 360, fill=(30, 26, 24, 255))
    for s in (-1, 1):
        d.rectangle([cx + s * 58 - 6, 150, cx + s * 58 + 4, 176], fill=(150, 150, 150, 255))
    _eyes(d, cx, 188, gap=27, socket=(104, 70, 50, 255))
    d.polygon([(cx - 5, 200), (cx + 5, 200), (cx + 10, 232), (cx - 10, 232)], fill=(104, 70, 50, 255))
    my = 258 + jaw * 0.5
    if amp > 0.08:
        d.chord([cx - 18, my - 6, cx + 20, my + 8 + 12 * amp], 0, 180, fill=(50, 20, 20, 255))
    else:
        d.arc([cx - 18, my - 10, cx + 20, my + 4], 30, 150, fill=(70, 40, 30, 255), width=4)
    d.polygon([(cx + 100, 360), (cx + 140, 360), (cx + 130, 380), (cx + 110, 380)], fill=(230, 200, 60, 255))   # pocket square


@mask("finance", tie=False)
def finance(d, amp, t):
    """Finance: shirtsleeves and suspenders, a pencil behind the ear, reading glasses on the forehead."""
    cx = CX
    d.polygon([(cx - 200, 520), (cx - 180, 340), (cx - 90, 290), (cx + 90, 290), (cx + 180, 340), (cx + 200, 520)], fill=(220, 226, 236, 255))
    for s in (-1, 1):
        d.line([(cx + s * 70, 300), (cx + s * 60, 520)], fill=(140, 30, 40, 255), width=12)
    d.polygon([(cx - 12, 306), (cx + 12, 306), (cx + 16, 400), (cx, 420), (cx - 16, 400)], fill=(40, 60, 100, 255))
    skin, jaw = (236, 206, 186, 255), 6 * amp
    d.ellipse([cx - 58, 116, cx + 58, 288 + jaw], fill=skin)
    d.chord([cx - 62, 104, cx + 62, 150], 180, 360, fill=(160, 120, 90, 255))
    for s in (-1, 1):
        d.ellipse([cx + s * 24 - 16, 130, cx + s * 24 + 16, 150], outline=(40, 40, 44, 255), width=3)   # glasses up top
    d.line([(cx + 52, 170), (cx + 86, 130)], fill=(240, 200, 60, 255), width=6)
    _eyes(d, cx, 192, gap=27, socket=(220, 190, 170, 255))
    d.polygon([(cx - 5, 204), (cx + 5, 204), (cx + 10, 234), (cx - 10, 234)], fill=(220, 190, 170, 255))
    _mouth(d, cx, 258 + jaw * 0.5, amp, w=15)


@mask("nrcan", tie=True)
def nrcan(d, amp, t):
    """Natural Resources: a white hard hat worn with a business suit, safety glasses pushed up, a hi-vis lanyard."""
    cx = CX
    skin, hair, jaw = (226, 190, 160, 255), (110, 70, 40, 255), 6 * amp
    d.polygon([(cx - 70, 160), (cx - 74, 260), (cx + 74, 260), (cx + 70, 160)], fill=hair)
    d.ellipse([cx - 56, 120, cx + 56, 288 + jaw], fill=skin)
    d.chord([cx - 66, 76, cx + 66, 186], 180, 360, fill=(246, 246, 246, 255))                   # hard hat
    d.rectangle([cx - 80, 128, cx + 80, 140], fill=(230, 230, 230, 255))
    d.rectangle([cx - 52, 146, cx + 52, 160], fill=(40, 40, 44, 200))                            # safety glasses up
    _eyes(d, cx, 192, gap=27, socket=(210, 174, 146, 255))
    d.polygon([(cx - 4, 204), (cx + 4, 204), (cx + 9, 234), (cx - 9, 234)], fill=(210, 174, 146, 255))
    _mouth(d, cx, 258 + jaw * 0.5, amp, w=15, lip=(160, 80, 80, 255))
    d.line([(cx - 40, 300), (cx, 400), (cx + 40, 300)], fill=(220, 240, 40, 255), width=6)


@mask("pubsafety", tie=True)
def pubsafety(d, amp, t):
    """Public Safety: a buzz cut, a radio earpiece with a coiled cord, a square jaw."""
    cx = CX
    skin, jaw = (236, 200, 176, 255), 6 * amp
    d.rounded_rectangle([cx - 60, 112, cx + 60, 290 + jaw], radius=40, fill=skin)
    d.rounded_rectangle([cx - 62, 104, cx + 62, 150], radius=20, fill=(170, 140, 110, 255))
    _eyes(d, cx, 190, gap=27, socket=(220, 184, 160, 255))
    d.polygon([(cx - 5, 202), (cx + 5, 202), (cx + 10, 232), (cx - 10, 232)], fill=(220, 184, 160, 255))
    _mouth(d, cx, 258 + jaw * 0.5, amp, w=16)
    d.ellipse([cx + 56, 196, cx + 66, 210], fill=(30, 30, 34, 255))
    for k in range(8):
        d.arc([cx + 58, 210 + k * 12, cx + 70, 224 + k * 12], 270, 90, fill=(30, 30, 34, 255), width=2)


@mask("dpm", tie=False)
def dpm(d, amp, t):
    """A deputy prime minister in the chair: a silver bob, reading glasses on a chain, a pearl brooch."""
    cx = CX
    skin, hair, jaw = (238, 208, 190, 255), (196, 196, 202, 255), 6 * amp
    d.chord([cx - 74, 104, cx + 74, 320], 180, 360, fill=hair)
    d.rectangle([cx - 74, 210, cx - 52, 300], fill=hair); d.rectangle([cx + 52, 210, cx + 74, 300], fill=hair)
    d.ellipse([cx - 58, 118, cx + 58, 290 + jaw], fill=skin)
    d.chord([cx - 62, 110, cx + 62, 190], 180, 360, fill=hair)
    _eyes(d, cx, 196, gap=27, socket=(222, 190, 172, 255))
    for s in (-1, 1):
        d.ellipse([cx + s * 27 - 18, 184, cx + s * 27 + 18, 208], outline=(120, 90, 60, 255), width=3)
    d.line([(cx - 45, 200), (cx - 66, 300)], fill=(200, 170, 90, 255), width=2)
    d.line([(cx + 45, 200), (cx + 66, 300)], fill=(200, 170, 90, 255), width=2)
    d.polygon([(cx - 5, 206), (cx + 5, 206), (cx + 9, 234), (cx - 9, 234)], fill=(222, 190, 172, 255))
    _mouth(d, cx, 260 + jaw * 0.5, amp, w=15, lip=(170, 70, 80, 255))
    d.ellipse([cx - 82, 350, cx - 64, 368], fill=(244, 240, 230, 255), outline=(200, 190, 170, 255))


@mask("finmin", tie=True)
def finmin(d, amp, t):
    """A finance minister: bald on top, a dark fringe, rimless glasses, a pocket calculator in the breast pocket."""
    cx = CX
    skin, jaw = (226, 188, 160, 255), 6 * amp
    d.ellipse([cx - 62, 112, cx + 62, 292 + jaw], fill=skin)
    for s in (-1, 1):
        d.chord([cx + s * 60 - 14, 160, cx + s * 60 + 14, 240], 90 - s * 90, 270 - s * 90, fill=(60, 46, 40, 255))
    _eyes(d, cx, 192, gap=28, socket=(210, 172, 146, 255))
    for s in (-1, 1):
        d.rounded_rectangle([cx + s * 28 - 17, 182, cx + s * 28 + 17, 204], radius=6, outline=(200, 200, 210, 255), width=2)
    d.polygon([(cx - 6, 202), (cx + 6, 202), (cx + 11, 236), (cx - 11, 236)], fill=(210, 172, 146, 255))
    _mouth(d, cx, 262 + jaw * 0.5, amp, w=14)
    d.rectangle([cx + 58, 346, cx + 82, 378], fill=(40, 40, 44, 255))
    d.rectangle([cx + 61, 349, cx + 79, 357], fill=(150, 190, 140, 255))


@mask("psmin", tie=True)
def psmin(d, amp, t):
    """A public safety minister: young, slicked-back hair, very white teeth, permanently about to do a press scrum."""
    cx = CX
    skin, jaw = (218, 176, 142, 255), 6 * amp
    d.ellipse([cx - 58, 116, cx + 58, 290 + jaw], fill=skin)
    d.chord([cx - 62, 98, cx + 62, 180], 180, 360, fill=(30, 24, 22, 255))
    for k in range(4):
        d.arc([cx - 50 + k * 22, 104, cx - 10 + k * 22, 150], 200, 330, fill=(70, 60, 56, 255), width=2)
    _eyes(d, cx, 192, gap=26, socket=(200, 160, 128, 255))
    d.polygon([(cx - 5, 202), (cx + 5, 202), (cx + 10, 232), (cx - 10, 232)], fill=(200, 160, 128, 255))
    my = 258 + jaw * 0.5
    d.chord([cx - 24, my - 8, cx + 24, my + 10 + 10 * amp], 0, 180, fill=(250, 250, 250, 255))
    d.arc([cx - 24, my - 8, cx + 24, my + 10 + 10 * amp], 0, 180, fill=(150, 80, 80, 255), width=3)


@mask("cirnacmin", tie=False)
def cirnacmin(d, amp, t):
    """A Crown-Indigenous Relations minister: long dark braid, beaded earrings, a ribbon-skirt-trimmed blazer."""
    cx = CX
    skin, hair, jaw = (200, 152, 116, 255), (26, 22, 22, 255), 6 * amp
    d.chord([cx - 66, 102, cx + 66, 260], 180, 360, fill=hair)
    for k in range(6):
        d.ellipse([cx + 54, 200 + k * 26, cx + 78, 228 + k * 26], fill=hair)
    d.ellipse([cx - 58, 118, cx + 58, 290 + jaw], fill=skin)
    d.chord([cx - 62, 108, cx + 62, 186], 180, 360, fill=hair)
    for s in (-1, 1):
        for k, c in enumerate([(200, 40, 50), (240, 200, 60), (40, 120, 180)]):
            d.ellipse([cx + s * 62 - 5, 232 + k * 10, cx + s * 62 + 5, 242 + k * 10], fill=c + (255,))
    _eyes(d, cx, 194, gap=26, socket=(182, 136, 102, 255))
    d.polygon([(cx - 5, 204), (cx + 5, 204), (cx + 9, 232), (cx - 9, 232)], fill=(182, 136, 102, 255))
    _mouth(d, cx, 260 + jaw * 0.5, amp, w=14)
    for k, c in enumerate([(200, 40, 50), (240, 200, 60), (40, 120, 180), (240, 240, 240)]):
        d.rectangle([cx - 110, 360 + k * 6, cx + 110, 364 + k * 6], fill=c + (255,))


@mask("nsasenior", tie=False)
def nsasenior(d, amp, t):
    """A senior signals analyst: thirty years at the Fort, short grey curls, half-moon readers, a lanyard full of badges."""
    cx = CX
    skin, hair, jaw = (226, 186, 160, 255), (176, 172, 168, 255), 6 * amp
    for k in range(9):
        a = k / 8 * np.pi
        d.ellipse([cx - 70 * np.cos(a) - 20, 120 - 30 * np.sin(a) - 4, cx - 70 * np.cos(a) + 20, 120 - 30 * np.sin(a) + 36], fill=hair)
    d.ellipse([cx - 58, 116, cx + 58, 290 + jaw], fill=skin)
    _eyes(d, cx, 192, gap=27, socket=(208, 170, 146, 255))
    for s in (-1, 1):
        d.chord([cx + s * 27 - 18, 196, cx + s * 27 + 18, 222], 180, 360, outline=(60, 60, 60, 255), width=3)
    d.polygon([(cx - 5, 204), (cx + 5, 204), (cx + 9, 232), (cx - 9, 232)], fill=(208, 170, 146, 255))
    _mouth(d, cx, 260 + jaw * 0.5, amp, w=15, lip=(150, 80, 80, 255))
    d.line([(cx - 40, 300), (cx, 380)], fill=(40, 60, 140, 255), width=5); d.line([(cx + 40, 300), (cx, 380)], fill=(40, 60, 140, 255), width=5)
    for k in range(3):
        d.rectangle([cx - 18 + k * 4, 380 + k * 6, cx + 18 + k * 4, 404 + k * 6], fill=(240, 240, 240, 255), outline=(90, 90, 90, 255))


@mask("nsajunior", tie=False)
def nsajunior(d, amp, t):
    """A junior signals analyst: big over-ear headset, a grey hoodie, an energy-drink pallor."""
    cx = CX
    skin, jaw = (240, 214, 196, 255), 6 * amp
    d.polygon([(cx - 120, 420), (cx - 70, 320), (cx + 70, 320), (cx + 120, 420)], fill=(120, 124, 130, 255))
    d.ellipse([cx - 56, 118, cx + 56, 288 + jaw], fill=skin)
    d.chord([cx - 60, 104, cx + 60, 184], 180, 360, fill=(110, 80, 50, 255))
    d.arc([cx - 72, 96, cx + 72, 230], 190, 350, fill=(30, 30, 34, 255), width=10)
    for s in (-1, 1):
        d.rounded_rectangle([cx + s * 66 - 16, 180, cx + s * 66 + 16, 240], radius=10, fill=(30, 30, 34, 255))
    d.line([(cx - 66, 236), (cx - 30, 268)], fill=(30, 30, 34, 255), width=4); d.ellipse([cx - 34, 262, cx - 24, 274], fill=(30, 30, 34, 255))
    _eyes(d, cx, 194, gap=25, socket=(214, 180, 168, 255))
    d.polygon([(cx - 5, 204), (cx + 5, 204), (cx + 9, 230), (cx - 9, 230)], fill=(214, 180, 168, 255))
    _mouth(d, cx, 258 + jaw * 0.5, amp, w=13)


@mask("ngaanalyst", tie=False)
def ngaanalyst(d, amp, t):
    """An imagery analyst: dark hair in a high ponytail, glasses pushed up on her head, a fleece vest."""
    cx = CX
    skin, hair, jaw = (196, 146, 110, 255), (30, 24, 22, 255), 6 * amp
    d.polygon([(cx - 120, 420), (cx - 70, 320), (cx + 70, 320), (cx + 120, 420)], fill=(40, 70, 80, 255))
    d.rectangle([cx - 30, 320, cx + 30, 420], fill=(220, 220, 214, 255))
    d.ellipse([cx + 36, 70, cx + 70, 140], fill=hair)
    d.ellipse([cx - 56, 118, cx + 56, 288 + jaw], fill=skin)
    d.chord([cx - 60, 106, cx + 60, 180], 180, 360, fill=hair)
    for s in (-1, 1):
        d.ellipse([cx + s * 24 - 16, 112, cx + s * 24 + 16, 132], outline=(200, 60, 60, 255), width=3)
    _eyes(d, cx, 194, gap=25, socket=(176, 128, 96, 255))
    d.polygon([(cx - 5, 204), (cx + 5, 204), (cx + 9, 230), (cx - 9, 230)], fill=(176, 128, 96, 255))
    _mouth(d, cx, 258 + jaw * 0.5, amp, w=14, lip=(150, 70, 70, 255))


@mask("ngachief", tie=True)
def ngachief(d, amp, t):
    """An imagery division chief: a shaved head, a short red beard, a golf-shirt-under-a-blazer energy."""
    cx = CX
    skin, jaw = (238, 200, 176, 255), 6 * amp
    d.ellipse([cx - 60, 110, cx + 60, 290 + jaw], fill=skin)
    d.chord([cx - 58, 200 + jaw, cx + 58, 300 + jaw], 0, 180, fill=(170, 80, 40, 255))
    _eyes(d, cx, 190, gap=27, socket=(220, 180, 156, 255))
    d.polygon([(cx - 5, 200), (cx + 5, 200), (cx + 10, 230), (cx - 10, 230)], fill=(220, 180, 156, 255))
    _mouth(d, cx, 252 + jaw * 0.5, amp, w=15)


@mask("raven", tie=None)
def raven(d, amp, t):
    """A raven: glossy black, thick beak, absolutely no respect. The beak opens with the voice."""
    cx = CX
    d.ellipse([cx - 90, 260, cx + 70, 470], fill=(16, 16, 22, 255))                          # body
    d.polygon([(cx + 40, 420), (cx + 150, 470), (cx + 50, 470)], fill=(12, 12, 18, 255))        # tail
    d.ellipse([cx - 110, 180, cx + 10, 300], fill=(20, 20, 28, 255))                          # head
    d.ellipse([cx - 76, 216, cx - 58, 234], fill=(230, 230, 230, 255)); d.ellipse([cx - 71, 221, cx - 63, 229], fill=(0, 0, 0, 255))
    o = 22 * amp
    d.polygon([(cx - 104, 236), (cx - 190, 250), (cx - 104, 256)], fill=(40, 40, 46, 255))
    d.polygon([(cx - 104, 258 + o * 0.3), (cx - 180, 258 + o), (cx - 104, 270 + o * 0.3)], fill=(40, 40, 46, 255))
    for k in range(3):
        d.line([(cx - 20, 470), (cx - 30 + k * 10, 500)], fill=(30, 30, 30, 255), width=4)


@mask("arcticfox", tie=None)
def arcticfox(d, amp, t):
    """An arctic fox in its winter white: small, round, judging you with black eyes."""
    cx = CX
    w = (246, 246, 244, 255)
    d.ellipse([cx - 120, 330, cx + 120, 500], fill=w)                                         # body
    d.ellipse([cx + 80, 380, cx + 230, 470], fill=w)                                          # tail
    d.ellipse([cx - 80, 200, cx + 80, 350], fill=w)                                           # head
    for s in (-1, 1):
        d.polygon([(cx + s * 70, 230), (cx + s * 40, 150), (cx + s * 20, 220)], fill=w)
        d.polygon([(cx + s * 60, 224), (cx + s * 42, 170), (cx + s * 30, 220)], fill=(220, 200, 200, 255))
        d.ellipse([cx + s * 30 - 9, 256, cx + s * 30 + 9, 274], fill=(10, 10, 10, 255))
    d.ellipse([cx - 10, 300, cx + 10, 316], fill=(20, 20, 20, 255))
    d.chord([cx - 16, 312, cx + 16, 324 + 14 * amp], 0, 180, fill=(80, 40, 40, 255))


@mask("muskox", tie=None)
def muskox(d, amp, t):
    """A muskox: a haystack with horns. Has seen the ice age. Has seen you."""
    cx = CX
    hair = (70, 52, 38, 255)
    d.ellipse([cx - 200, 220, cx + 200, 520], fill=hair)
    for k in range(18):
        x = cx - 190 + k * 22
        d.line([(x, 400), (x - 6, 520)], fill=(50, 36, 26, 255), width=6)
    d.ellipse([cx - 80, 220, cx + 80, 400], fill=(60, 44, 32, 255))
    d.chord([cx - 110, 170, cx + 110, 280], 180, 360, fill=(220, 210, 180, 255))              # the horn boss
    for s in (-1, 1):
        d.arc([cx + s * 110 - 60, 200, cx + s * 110 + 60, 330], 180 if s < 0 else 270, 270 if s < 0 else 360, fill=(220, 210, 180, 255), width=18)
        d.ellipse([cx + s * 44 - 8, 286, cx + s * 44 + 8, 300], fill=(10, 10, 10, 255))
    d.ellipse([cx - 40, 350, cx + 40, 400], fill=(40, 34, 30, 255))
    d.chord([cx - 22, 380, cx + 22, 392 + 12 * amp], 0, 180, fill=(20, 14, 12, 255))


@mask("villagekid", tie=None)
def villagekid(d, amp, t):
    """A kid on a fat-tire bike: a toque with a pom-pom, a puffy red jacket, a gap-toothed grin."""
    cx = CX
    skin, jaw = (196, 146, 110, 255), 5 * amp
    d.rounded_rectangle([cx - 120, 320, cx + 120, 520], radius=50, fill=(200, 40, 40, 255))
    d.ellipse([cx - 56, 150, cx + 56, 310 + jaw], fill=skin)
    d.chord([cx - 62, 120, cx + 62, 230], 180, 360, fill=(40, 120, 200, 255))
    d.rectangle([cx - 62, 168, cx + 62, 184], fill=(240, 240, 240, 255))
    d.ellipse([cx - 18, 96, cx + 18, 130], fill=(240, 240, 240, 255))
    _eyes(d, cx, 220, gap=24, socket=(176, 128, 96, 255))
    my = 270 + jaw * 0.5
    d.chord([cx - 20, my - 8, cx + 20, my + 10 + 10 * amp], 0, 180, fill=(250, 250, 250, 255))
    d.rectangle([cx - 4, my - 2, cx + 4, my + 8], fill=(60, 30, 30, 255))


@mask("elderisaac", tie=None)
def elderisaac(d, amp, t):
    """An elder ice fishing: a caribou-skin hat, deep smile lines, a wooden jigging stick over one shoulder."""
    cx = CX
    skin, jaw = (176, 128, 92, 255), 5 * amp
    d.rounded_rectangle([cx - 150, 320, cx + 150, 520], radius=40, fill=(60, 80, 70, 255))
    d.line([(cx + 120, 330), (cx + 200, 120)], fill=(150, 110, 60, 255), width=8)
    d.line([(cx + 200, 120), (cx + 210, 260)], fill=(200, 200, 200, 255), width=1)
    d.ellipse([cx - 58, 130, cx + 58, 300 + jaw], fill=skin)
    d.chord([cx - 76, 90, cx + 76, 230], 180, 360, fill=(150, 120, 90, 255))
    d.rectangle([cx - 76, 156, cx + 76, 176], fill=(230, 220, 200, 255))
    _eyes(d, cx, 206, gap=26, socket=(150, 104, 72, 255))
    for s in (-1, 1):
        for k in range(3):
            d.line([(cx + s * 44, 202 + k * 6), (cx + s * 58, 196 + k * 8)], fill=(140, 96, 66, 255), width=2)
    _mouth(d, cx, 262 + jaw * 0.5, amp, w=16)


@mask("nellie", tie=None)
def nellie(d, amp, t):
    """A woman at the char racks: a flowered amauti-style cover, a black bun, flour on one cheek, no patience for you."""
    cx = CX
    skin, jaw = (190, 140, 104, 255), 5 * amp
    d.rounded_rectangle([cx - 150, 310, cx + 150, 520], radius=40, fill=(60, 110, 160, 255))
    for k in range(7):
        x = cx - 120 + k * 40
        d.ellipse([x - 8, 380, x + 8, 396], fill=(250, 200, 80, 255)); d.ellipse([x + 10, 440, x + 26, 456], fill=(230, 90, 120, 255))
    d.ellipse([cx - 30, 92, cx + 30, 140], fill=(24, 20, 20, 255))
    d.ellipse([cx - 58, 124, cx + 58, 296 + jaw], fill=skin)
    d.chord([cx - 62, 116, cx + 62, 196], 180, 360, fill=(24, 20, 20, 255))
    d.ellipse([cx + 20, 236, cx + 44, 252], fill=(236, 226, 214, 255))
    _eyes(d, cx, 204, gap=26, socket=(166, 118, 86, 255))
    _mouth(d, cx, 262 + jaw * 0.5, amp, w=15, lip=(150, 70, 70, 255))


@mask("sousministre", tie=False)
def sousministre(d, amp, t):
    """A sous-ministre: a sharp black bob with one silver streak, red-framed glasses, a navy jacket, a fleur-de-lis pin."""
    cx = CX
    skin, hair, jaw = (236, 204, 182, 255), (24, 22, 24, 255), 6 * amp
    d.polygon([(cx - 130, 420), (cx - 80, 320), (cx + 80, 320), (cx + 130, 420)], fill=(26, 36, 70, 255))
    d.rectangle([cx - 24, 320, cx + 24, 420], fill=(236, 236, 240, 255))
    d.chord([cx - 70, 104, cx + 70, 300], 180, 360, fill=hair)
    d.rectangle([cx - 70, 200, cx - 50, 290], fill=hair); d.rectangle([cx + 50, 200, cx + 70, 290], fill=hair)
    d.line([(cx - 30, 108), (cx - 60, 280)], fill=(190, 190, 196, 255), width=8)
    d.ellipse([cx - 56, 118, cx + 56, 288 + jaw], fill=skin)
    d.chord([cx - 60, 110, cx + 60, 176], 180, 360, fill=hair)
    _eyes(d, cx, 194, gap=26, socket=(218, 184, 162, 255))
    for s in (-1, 1):
        d.rectangle([cx + s * 26 - 18, 184, cx + s * 26 + 18, 206], outline=(200, 30, 40, 255), width=3)
    d.polygon([(cx - 5, 206), (cx + 5, 206), (cx + 9, 232), (cx - 9, 232)], fill=(218, 184, 162, 255))
    _mouth(d, cx, 258 + jaw * 0.5, amp, w=14, lip=(170, 60, 70, 255))
    d.rectangle([cx + 60, 344, cx + 80, 360], fill=(30, 80, 170, 255)); d.line([(cx + 70, 346), (cx + 70, 358)], fill=(255, 255, 255, 255), width=2)


@mask("normand", tie=False)
def normand(d, amp, t):
    """Normand, a lifer: a grey horseshoe of hair, a walrus moustache, a brown cardigan with leather elbow patches."""
    cx = CX
    skin, jaw = (230, 190, 166, 255), 6 * amp
    d.polygon([(cx - 140, 420), (cx - 84, 316), (cx + 84, 316), (cx + 140, 420)], fill=(120, 84, 50, 255))
    for k in range(5):
        d.ellipse([cx - 6, 334 + k * 18, cx + 6, 346 + k * 18], fill=(70, 50, 30, 255))
    d.ellipse([cx - 62, 112, cx + 62, 292 + jaw], fill=skin)
    for s in (-1, 1):
        d.chord([cx + s * 60 - 16, 150, cx + s * 60 + 16, 250], 90 - s * 90, 270 - s * 90, fill=(190, 190, 190, 255))
    _eyes(d, cx, 192, gap=28, socket=(212, 172, 148, 255))
    d.polygon([(cx - 6, 202), (cx + 6, 202), (cx + 12, 234), (cx - 12, 234)], fill=(212, 172, 148, 255))
    _mouth(d, cx, 264 + jaw * 0.6, amp, w=14)
    d.chord([cx - 40, 232, cx + 40, 270], 180, 360, fill=(200, 200, 200, 255))


@mask("felix", tie=False)
def felix(d, amp, t):
    """Félix, a political attaché: a short dark beard, a tuque worn indoors, a blazer over a band T-shirt."""
    cx = CX
    skin, jaw = (214, 170, 136, 255), 6 * amp
    d.polygon([(cx - 130, 420), (cx - 80, 320), (cx + 80, 320), (cx + 130, 420)], fill=(50, 50, 56, 255))
    d.rectangle([cx - 34, 320, cx + 34, 420], fill=(30, 30, 30, 255)); d.ellipse([cx - 16, 350, cx + 16, 382], outline=(220, 220, 220, 255), width=3)
    d.ellipse([cx - 56, 120, cx + 56, 290 + jaw], fill=skin)
    d.chord([cx - 56, 220 + jaw, cx + 56, 300 + jaw], 0, 180, fill=(50, 36, 28, 255))
    d.chord([cx - 62, 92, cx + 62, 200], 180, 360, fill=(30, 90, 160, 255))
    d.rectangle([cx - 62, 140, cx + 62, 160], fill=(24, 70, 130, 255))
    _eyes(d, cx, 196, gap=25, socket=(196, 152, 120, 255))
    d.polygon([(cx - 5, 206), (cx + 5, 206), (cx + 9, 232), (cx - 9, 232)], fill=(196, 152, 120, 255))
    _mouth(d, cx, 252 + jaw * 0.5, amp, w=13)


@mask("annie", tie=False)
def annie(d, amp, t):
    """Annie, government efficiency: a tight blonde ponytail, a stopwatch on a lanyard, a fleece with a logo nobody has explained."""
    cx = CX
    skin, hair, jaw = (240, 210, 190, 255), (220, 190, 110, 255), 6 * amp
    d.polygon([(cx - 130, 420), (cx - 80, 320), (cx + 80, 320), (cx + 130, 420)], fill=(90, 130, 90, 255))
    d.line([(cx - 34, 322), (cx, 380)], fill=(20, 20, 20, 255), width=3); d.line([(cx + 34, 322), (cx, 380)], fill=(20, 20, 20, 255), width=3)
    d.ellipse([cx - 16, 376, cx + 16, 408], fill=(200, 200, 206, 255), outline=(60, 60, 60, 255), width=3)
    d.line([(cx, 392), (cx + 8, 384)], fill=(20, 20, 20, 255), width=2)
    d.ellipse([cx - 20, 82, cx + 20, 128], fill=hair)
    d.ellipse([cx - 56, 118, cx + 56, 288 + jaw], fill=skin)
    d.chord([cx - 58, 108, cx + 58, 180], 180, 360, fill=hair)
    _eyes(d, cx, 194, gap=25, socket=(222, 190, 172, 255))
    d.polygon([(cx - 5, 204), (cx + 5, 204), (cx + 9, 230), (cx - 9, 230)], fill=(222, 190, 172, 255))
    _mouth(d, cx, 258 + jaw * 0.5, amp, w=13, lip=(170, 80, 90, 255))


@mask("rugeneral", tie=False)
def rugeneral(d, amp, t):
    """A general of the General Staff: a vast peaked cap, a grey-green tunic, a wall of ribbons, a jowl of pure procedure."""
    cx = CX
    skin, jaw = (232, 190, 166, 255), 6 * amp
    _uniform(d, cx, (84, 96, 80, 255), braid=True)
    for r in range(4):
        for k in range(5):
            d.rectangle([cx - 150 + k * 22, 370 + r * 14, cx - 132 + k * 22, 380 + r * 14], fill=[(200, 40, 40, 255), (40, 90, 170, 255), (220, 180, 60, 255), (60, 140, 80, 255)][(r + k) % 4])
    d.ellipse([cx - 64, 128, cx + 64, 300 + jaw], fill=skin)
    d.chord([cx - 70, 230 + jaw, cx + 70, 320 + jaw], 0, 180, fill=(220, 178, 154, 255))
    d.ellipse([cx - 130, 70, cx + 130, 160], fill=(84, 96, 80, 255))
    d.rectangle([cx - 76, 110, cx + 76, 168], fill=(84, 96, 80, 255)); d.rectangle([cx - 78, 150, cx + 78, 166], fill=(160, 30, 30, 255))
    d.chord([cx - 80, 156, cx + 80, 196], 0, 180, fill=(20, 20, 20, 255))
    d.ellipse([cx - 12, 116, cx + 12, 140], fill=(220, 180, 60, 255))
    _eyes(d, cx, 206, gap=28, socket=(212, 172, 148, 255))
    d.polygon([(cx - 6, 212), (cx + 6, 212), (cx + 12, 244), (cx - 12, 244)], fill=(212, 172, 148, 255))
    _mouth(d, cx, 268 + jaw * 0.5, amp, w=16)


@mask("ruadmiral", tie=False)
def ruadmiral(d, amp, t):
    """An admiral of the Northern Fleet: a black tunic with gold braid, a white-topped cap, a beard like a breakwater."""
    cx = CX
    skin, jaw = (236, 200, 178, 255), 6 * amp
    _uniform(d, cx, (20, 22, 34, 255), braid=True)
    for k in range(4):
        d.line([(cx - 190, 470 + k * 10), (cx - 140, 470 + k * 10)], fill=(220, 180, 60, 255), width=4)
    d.ellipse([cx - 60, 126, cx + 60, 296 + jaw], fill=skin)
    d.chord([cx - 62, 210 + jaw, cx + 62, 320 + jaw], 0, 180, fill=(210, 210, 214, 255))
    d.ellipse([cx - 110, 82, cx + 110, 156], fill=(244, 244, 246, 255))
    d.rectangle([cx - 70, 118, cx + 70, 166], fill=(20, 22, 34, 255))
    d.chord([cx - 76, 152, cx + 76, 190], 0, 180, fill=(10, 10, 14, 255))
    d.ellipse([cx - 14, 124, cx + 14, 150], fill=(220, 180, 60, 255))
    _eyes(d, cx, 204, gap=27, socket=(214, 178, 156, 255))
    d.polygon([(cx - 5, 210), (cx + 5, 210), (cx + 10, 238), (cx - 10, 238)], fill=(214, 178, 156, 255))
    _mouth(d, cx, 262 + jaw * 0.5, amp, w=15)


@mask("ruanalyst", tie=False)
def ruanalyst(d, amp, t):
    """A foreign-intelligence analyst, Canada desk: a severe grey suit, a blonde chignon, a tablet held like a shield."""
    cx = CX
    skin, hair, jaw = (242, 214, 196, 255), (214, 190, 140, 255), 6 * amp
    d.polygon([(cx - 140, 420), (cx - 84, 316), (cx + 84, 316), (cx + 140, 420)], fill=(110, 112, 118, 255))
    d.rectangle([cx - 60, 360, cx + 60, 440], fill=(20, 20, 24, 255)); d.rectangle([cx - 52, 368, cx + 52, 432], fill=(60, 120, 180, 255))
    d.ellipse([cx - 30, 86, cx + 30, 136], fill=hair)
    d.ellipse([cx - 56, 118, cx + 56, 288 + jaw], fill=skin)
    d.chord([cx - 58, 108, cx + 58, 176], 180, 360, fill=hair)
    _eyes(d, cx, 194, gap=25, socket=(224, 192, 176, 255))
    d.polygon([(cx - 5, 204), (cx + 5, 204), (cx + 9, 230), (cx - 9, 230)], fill=(224, 192, 176, 255))
    _mouth(d, cx, 258 + jaw * 0.5, amp, w=13, lip=(170, 70, 80, 255))


@mask("ruinterp", tie=True)
def ruinterp(d, amp, t):
    """An interpreter: round wire glasses, a nervous side part, a single earpiece, the face of a man translating the word 'eh'."""
    cx = CX
    skin, jaw = (236, 206, 186, 255), 6 * amp
    d.ellipse([cx - 56, 120, cx + 56, 290 + jaw], fill=skin)
    d.chord([cx - 60, 104, cx + 60, 184], 180, 360, fill=(120, 90, 60, 255))
    d.line([(cx - 20, 108), (cx - 30, 150)], fill=(236, 206, 186, 255), width=3)
    _eyes(d, cx, 194, gap=25, socket=(218, 186, 168, 255))
    for s in (-1, 1):
        d.ellipse([cx + s * 25 - 15, 180, cx + s * 25 + 15, 208], outline=(160, 160, 160, 255), width=2)
    d.ellipse([cx + 52, 196, cx + 64, 212], fill=(30, 30, 30, 255)); d.line([(cx + 58, 212), (cx + 70, 300)], fill=(200, 200, 200, 255), width=2)
    d.polygon([(cx - 5, 204), (cx + 5, 204), (cx + 9, 230), (cx - 9, 230)], fill=(218, 186, 168, 255))
    _mouth(d, cx, 258 + jaw * 0.5, amp, w=12)


# ---- soldiers in the field: one factory, many faces --------------------------------------------------------------
from PIL import ImageFont as _IF
_SLIDE_FONT = None


def _slide_font():
    global _SLIDE_FONT
    if _SLIDE_FONT is None:
        try:
            _SLIDE_FONT = _IF.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 26)
        except OSError:
            _SLIDE_FONT = _IF.load_default()
    return _SLIDE_FONT


_FLAGS = {"ca": [(214, 40, 40), (250, 250, 250), (214, 40, 40)],
          "lv": [(158, 48, 57), (250, 250, 250), (158, 48, 57)],
          "sk": [(250, 250, 250), (11, 78, 162), (238, 28, 37)]}


def _soldier(name, skin, rank, flag="ca", moustache=False, beard=False, glasses=False, hair=None, doc=""):
    @mask(name, tie=None)
    def f(d, amp, t):
        cx = CX; jaw = 6 * amp
        rng = np.random.default_rng(sum(map(ord, name)))
        d.polygon([(cx - 200, 520), (cx - 180, 340), (cx - 90, 296), (cx + 90, 296), (cx + 180, 340), (cx + 200, 520)], fill=(92, 100, 74, 255))
        for _ in range(40):                                                     # disruptive pattern, roughly
            x, y = rng.integers(cx - 190, cx + 190), rng.integers(320, 510)
            c = [(60, 70, 50), (120, 112, 84), (40, 44, 36)][int(rng.integers(0, 3))]
            d.ellipse([x - 14, y - 8, x + 14, y + 8], fill=c + (255,))
        d.rounded_rectangle([cx - 34, 360, cx + 34, 430], radius=6, fill=(70, 76, 56, 255), outline=(30, 30, 26, 255), width=2)
        d.text((cx, 395), rank, font=_slide_font(), fill=(20, 20, 18, 255), anchor="mm")
        for k, c in enumerate(_FLAGS[flag]):                                    # shoulder flag
            if flag == "sk":
                d.rectangle([cx - 170, 350 + k * 9, cx - 120, 359 + k * 9], fill=c + (255,))
                if k == 2:                                                      # the arms: red shield, white double cross
                    d.rounded_rectangle([cx - 162, 349, cx - 146, 371], radius=4, fill=(238, 28, 37, 255), outline=(250, 250, 250, 255))
                    d.line([(cx - 154, 352), (cx - 154, 368)], fill=(250, 250, 250, 255), width=2)
                    d.line([(cx - 159, 356), (cx - 149, 356)], fill=(250, 250, 250, 255), width=2)
                    d.line([(cx - 160, 361), (cx - 148, 361)], fill=(250, 250, 250, 255), width=2)
            else:
                w = (12, 26, 12)[k]
                d.rectangle([cx - 170 + sum((12, 26, 12)[:k]), 350, cx - 170 + sum((12, 26, 12)[:k + 1]), 377], fill=c + (255,))
                if flag == "ca" and k == 1:                                     # the maple leaf
                    lx, ly = cx - 145, 362
                    leaf = [(0, -11), (3, -6), (7, -8), (5, -2), (10, -3), (8, 1), (11, 4), (4, 4), (5, 8), (1, 6),
                            (1, 11), (-1, 11), (-1, 6), (-5, 8), (-4, 4), (-11, 4), (-8, 1), (-10, -3), (-5, -2), (-7, -8), (-3, -6)]
                    d.polygon([(lx + a, ly + b) for a, b in leaf], fill=(214, 40, 40, 255))
        d.ellipse([cx - 56, 126, cx + 56, 292 + jaw], fill=skin)
        if hair:
            d.rectangle([cx - 58, 160, cx - 44, 230], fill=hair); d.rectangle([cx + 44, 160, cx + 58, 230], fill=hair)
        if beard:
            d.chord([cx - 56, 214 + jaw, cx + 56, 300 + jaw], 0, 180, fill=(70, 50, 36, 255))
        d.chord([cx - 82, 86, cx + 82, 236], 180, 360, fill=(84, 92, 66, 255))   # helmet
        d.rectangle([cx - 82, 156, cx + 82, 168], fill=(70, 78, 56, 255))
        d.line([(cx - 60, 166), (cx - 40, 286)], fill=(30, 30, 26, 255), width=3); d.line([(cx + 60, 166), (cx + 40, 286)], fill=(30, 30, 26, 255), width=3)
        sock = tuple(max(0, v - 22) for v in skin[:3]) + (255,)
        _eyes(d, cx, 204, gap=25, socket=sock)
        if glasses:
            for s in (-1, 1):
                d.rectangle([cx + s * 25 - 16, 194, cx + s * 25 + 16, 214], outline=(30, 30, 30, 255), width=3)
        d.polygon([(cx - 5, 212), (cx + 5, 212), (cx + 9, 238), (cx - 9, 238)], fill=sock)
        if moustache:
            d.chord([cx - 30, 240, cx + 30, 266], 180, 360, fill=(80, 60, 44, 255))
        _mouth(d, cx, 262 + jaw * 0.5, amp, w=13)
    f.__doc__ = doc
    return f


_soldier("pte", (240, 206, 182, 255), "PTE", doc="A private: young, cold, has a cousin who's a welder.")
_soldier("sgt", (222, 182, 156, 255), "SGT", hair=(60, 40, 30, 255), doc="A section sergeant: dark hair under the helmet, no patience.")
_soldier("wo", (232, 190, 166, 255), "WO", moustache=True, doc="A warrant officer from Cape Breton: the moustache is regulation and also load-bearing.")
_soldier("lt", (236, 200, 176, 255), "LT", glasses=True, doc="A lieutenant with a political science degree and glasses.")
_soldier("capt", (150, 104, 76, 255), "CAPT", doc="A captain: calm, quick, unimpressed by podcasts.")
_soldier("maj", (226, 186, 160, 255), "MAJ", beard=True, doc="A major with a beard he's allowed to have.")
_soldier("lcol", (238, 204, 184, 255), "LCOL", hair=(200, 160, 90, 255), doc="A lieutenant-colonel commanding the battle group.")
_soldier("col", (222, 184, 160, 255), "COL", moustache=True, glasses=True, doc="The brigade commander: fourteen nations, one question.")
_soldier("slovakcpl", (236, 200, 178, 255), "DES", flag="sk", doc="A Slovak desiatnik (corporal), cold, drinking coffee.")
_soldier("latviansgt", (242, 214, 196, 255), "SRŽ", flag="lv", hair=(210, 180, 120, 255), doc="A Latvian seržants: blonde, entirely unconfused.")


@mask("calgaryguy", tie=None)
def calgaryguy(d, amp, t):
    """The guy from Calgary: a plain white mask (no face but the eye holes and a slot that opens when he talks),
    a massive beard coming out from under it, a black toque, a charcoal parka with the hood down, a red scarf.
    Tall. Unnamed, on purpose."""
    cx = CX; jaw = 5 * amp
    d.polygon([(cx - 210, 520), (cx - 190, 330), (cx - 100, 290), (cx + 100, 290), (cx + 190, 330), (cx + 210, 520)], fill=(52, 54, 60, 255))
    d.chord([cx - 130, 250, cx + 130, 360], 180, 360, fill=(70, 72, 80, 255))                 # the hood, down
    d.line([(cx, 330), (cx, 520)], fill=(30, 30, 34, 255), width=4)
    for k in range(6):
        d.line([(cx - 8, 340 + k * 30), (cx + 8, 340 + k * 30)], fill=(150, 150, 150, 255), width=2)
    d.rounded_rectangle([cx - 80, 270, cx + 80, 320], radius=20, fill=(180, 30, 40, 255))      # scarf
    d.polygon([(cx + 30, 300), (cx + 70, 300), (cx + 80, 420), (cx + 44, 420)], fill=(160, 26, 36, 255))
    rng = np.random.default_rng(7)                                                             # the beard: massive
    bc, bd = (128, 82, 48, 255), (92, 58, 34, 255)
    d.polygon([(cx - 40, 300), (cx + 40, 300), (cx + 54, 360), (cx - 54, 360)], fill=(86, 100, 64, 255))   # olive shirt collar
    d.ellipse([cx - 100, 200, cx + 100, 430], fill=bc)
    d.polygon([(cx - 96, 300), (cx + 96, 300), (cx + 50, 452), (cx, 470), (cx - 50, 452)], fill=bc)
    for _ in range(70):
        x = int(rng.integers(cx - 84, cx + 84)); y = int(rng.integers(260, 440))
        d.arc([x - 10, y - 14, x + 10, y + 14], 60, 200, fill=bd, width=2)
    d.ellipse([cx - 60, 120, cx + 60, 296], fill=(244, 244, 240, 255))                         # the mask
    for s in (-1, 1):
        d.ellipse([cx + s * 26 - 14, 188, cx + s * 26 + 14, 206], fill=(16, 16, 18, 255))
    d.polygon([(cx - 4, 204), (cx + 4, 204), (cx + 7, 236), (cx - 7, 236)], fill=(226, 226, 222, 255))
    d.rounded_rectangle([cx - 20, 256, cx + 20, 260 + 3 + 14 * amp], radius=3, fill=(20, 20, 22, 255))
    for k in range(9):                                                                          # hair escaping the toque
        a = -60 + k * 15
        d.ellipse([cx + a - 12, 148 + (k % 3) * 4, cx + a + 14, 186 + (k % 3) * 6], fill=(122, 80, 48, 255))
    for s_ in (-1, 1):
        d.ellipse([cx + s_ * 70 - 18, 150, cx + s_ * 70 + 18, 220], fill=(122, 80, 48, 255))
    d.chord([cx - 68, 88, cx + 68, 210], 180, 360, fill=(22, 22, 26, 255))                     # toque
    d.rectangle([cx - 68, 140, cx + 68, 166], fill=(34, 34, 40, 255))
    for k in range(9):
        d.line([(cx - 60 + k * 15, 142), (cx - 60 + k * 15, 164)], fill=(22, 22, 26, 255), width=2)


@mask("farmerearl", tie=None)
def farmerearl(d, amp, t):
    """Earl: seventies, a faded green seed cap with no logo, bib overalls over a flannel shirt, a sunburnt neck."""
    cx = CX; jaw = 6 * amp
    skin = (226, 168, 136, 255)
    d.polygon([(cx - 200, 520), (cx - 180, 330), (cx - 90, 294), (cx + 90, 294), (cx + 180, 330), (cx + 200, 520)], fill=(170, 40, 40, 255))
    for k in range(-6, 7):                                                       # flannel
        d.line([(cx + k * 30, 300), (cx + k * 30, 520)], fill=(110, 20, 24, 255), width=4)
    for y in range(320, 520, 30):
        d.line([(cx - 200, y), (cx + 200, y)], fill=(110, 20, 24, 255), width=4)
    d.rectangle([cx - 110, 380, cx + 110, 520], fill=(60, 84, 120, 255))         # bib
    for s in (-1, 1):
        d.line([(cx + s * 100, 384), (cx + s * 80, 296)], fill=(60, 84, 120, 255), width=22)
        d.ellipse([cx + s * 96 - 9, 380, cx + s * 96 + 9, 398], fill=(200, 190, 150, 255))
    d.ellipse([cx - 60, 124, cx + 60, 292 + jaw], fill=skin)
    d.chord([cx - 60, 220 + jaw, cx + 60, 300 + jaw], 0, 180, fill=(200, 196, 190, 255))   # grey stubble
    _eyes(d, cx, 196, gap=27, socket=(204, 146, 116, 255))
    for s in (-1, 1):
        for k in range(3):
            d.line([(cx + s * 44, 192 + k * 6), (cx + s * 58, 186 + k * 8)], fill=(190, 130, 100, 255), width=2)
    d.polygon([(cx - 6, 204), (cx + 6, 204), (cx + 12, 236), (cx - 12, 236)], fill=(204, 146, 116, 255))
    _mouth(d, cx, 262 + jaw * 0.5, amp, w=15)
    d.chord([cx - 68, 96, cx + 68, 200], 180, 360, fill=(70, 110, 60, 255))     # cap
    d.rectangle([cx - 68, 146, cx + 68, 152], fill=(60, 96, 52, 255))
    d.chord([cx - 70, 136, cx + 110, 176], 180, 360, fill=(60, 96, 52, 255))


@mask("farmergary", tie=None)
def farmergary(d, amp, t):
    """Gary: fifties, a canvas work jacket, a mesh-back seed cap, a moustache, reading glasses on a cord."""
    cx = CX; jaw = 6 * amp
    skin = (232, 186, 156, 255)
    d.polygon([(cx - 200, 520), (cx - 180, 330), (cx - 90, 294), (cx + 90, 294), (cx + 180, 330), (cx + 200, 520)], fill=(176, 130, 70, 255))
    d.polygon([(cx - 90, 294), (cx, 360), (cx + 90, 294), (cx + 70, 290), (cx, 336), (cx - 70, 290)], fill=(80, 52, 30, 255))   # corduroy collar
    d.line([(cx, 360), (cx, 520)], fill=(120, 86, 44, 255), width=4)
    d.ellipse([cx - 58, 124, cx + 58, 292 + jaw], fill=skin)
    _eyes(d, cx, 196, gap=26, socket=(212, 164, 134, 255))
    d.polygon([(cx - 6, 204), (cx + 6, 204), (cx + 11, 234), (cx - 11, 234)], fill=(212, 164, 134, 255))
    d.chord([cx - 34, 236, cx + 34, 262], 180, 360, fill=(110, 80, 52, 255))
    _mouth(d, cx, 266 + jaw * 0.5, amp, w=13)
    d.line([(cx - 40, 214), (cx - 60, 320)], fill=(40, 40, 40, 255), width=2); d.line([(cx + 40, 214), (cx + 60, 320)], fill=(40, 40, 40, 255), width=2)
    for s in (-1, 1):
        d.ellipse([cx + s * 28 - 16, 316, cx + s * 28 + 16, 334], outline=(40, 40, 40, 255), width=3)
    d.chord([cx - 66, 96, cx + 66, 200], 180, 360, fill=(240, 240, 236, 255))   # cap: white front, mesh back
    for k in range(6):
        d.line([(cx - 60 + k * 10, 110), (cx - 66 + k * 10, 148)], fill=(120, 120, 120, 255))
    d.rectangle([cx - 66, 146, cx + 66, 152], fill=(200, 60, 40, 255))
    d.chord([cx - 70, 136, cx + 110, 176], 180, 360, fill=(200, 60, 40, 255))
