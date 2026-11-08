"""Persona masks: the head that sits on the suit.

Every mask is a function ``draw(d, amp, t)`` that paints onto a 520x520 RGBA
canvas through ``ImageDraw`` ``d``. The suit's collar sits at y=300, centre x=260.

- ``amp``: voice loudness for this frame, 0..1 (drives jaws, wings, etc.)
- ``t``:   time in seconds (for idle motion)

Register new masks with ``@mask("name")`` and pick one per episode with
``"mask": "name"`` in episode.json.
"""
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
    """The shared headless suit (static)."""
    im = Image.new("RGBA", (520, 520), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
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
