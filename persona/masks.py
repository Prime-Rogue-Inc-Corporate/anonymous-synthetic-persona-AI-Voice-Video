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
