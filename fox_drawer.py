#!/usr/bin/env python3
"""
🦊 Fox Drawer — Press a hotkey and the mouse draws a fox on screen!

Usage:
    python3 fox_drawer.py                        # default: Ctrl+Shift+F
    python3 fox_drawer.py --hotkey ctrl+alt+f    # custom hotkey
    python3 fox_drawer.py --scale 2.0            # bigger fox
    python3 fox_drawer.py --speed 0.005          # faster drawing (seconds per step)
    python3 fox_drawer.py --app mspaint          # optimized for MS Paint (adds click)

Requirements:
    pip install pyautogui pynput

Works on: Linux (X11), macOS, Windows
Note: On Wayland (modern Linux), you may need X11 compatibility or xdotool fallback.
"""

import argparse
import math
import sys
import time
import threading

try:
    import pyautogui
except ImportError:
    print("ERROR: pyautogui not installed. Run: pip install pyautogui")
    sys.exit(1)

try:
    from pynput import keyboard
except ImportError:
    print("ERROR: pynput not installed. Run: pip install pynput")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Fox path generation
# ---------------------------------------------------------------------------

def generate_fox_path(center_x, center_y, scale=1.0):
    """
    Returns a list of (x, y) tuples that trace a fox outline:
    - Two pointy ears
    - Round head with puffy cheeks
    - Snout/chin
    - Oval body
    - Bushy curved tail
    - Two small legs
    - Two small eyes and a nose (lifted strokes)
    
    All coordinates are absolute screen pixels.
    """
    strokes = []          # list of stroke-lists; each stroke is a list of (x,y)
    current_stroke = []

    def flush():
        nonlocal current_stroke
        if current_stroke:
            strokes.append(current_stroke)
            current_stroke = []

    def pt(x, y):
        current_stroke.append((round(center_x + x * scale),
                               round(center_y + y * scale)))

    def arc(cx, cy, rx, ry, start_deg, end_deg, steps=30):
        for i in range(steps + 1):
            angle = math.radians(start_deg + (end_deg - start_deg) * i / steps)
            pt(cx + rx * math.cos(angle), cy + ry * math.sin(angle))

    def line(x1, y1, x2, y2, steps=12):
        for i in range(steps + 1):
            t = i / steps
            pt(x1 + (x2 - x1) * t, y1 + (y2 - y1) * t)

    # ── Outer head + ears (one continuous stroke) ──────────────────────────

    # Start at left jaw
    pt(-55, 40)

    # Left cheek up to ear base
    arc(-55, 0, 28, 45, 100, 180, steps=12)

    # LEFT EAR — sharp triangle
    line(-75, -25, -95, -140, steps=18)     # up to tip
    line(-95, -140, -45, -55, steps=18)     # back down

    # Top of head arc (between ears)
    arc(0, -50, 45, 18, 180, 0, steps=20)

    # RIGHT EAR — sharp triangle
    line(45, -55, 95, -140, steps=18)       # up to tip
    line(95, -140, 75, -25, steps=18)       # back down

    # Right cheek down to jaw
    arc(55, 0, 28, 45, 0, 80, steps=12)

    # Snout / chin (V shape)
    line(55, 38, 15, 58, steps=10)
    line(15, 58, 0, 62, steps=5)
    line(0, 62, -15, 58, steps=5)
    line(-15, 58, -55, 40, steps=10)

    flush()

    # ── Body (oval below head) ─────────────────────────────────────────────

    # Neck-left down to body
    line(-40, 50, -55, 90, steps=8)
    # Body oval
    arc(0, 145, 60, 55, 180, 520, steps=50)
    # Neck-right back up
    line(55, 90, 40, 50, steps=8)

    flush()

    # ── Tail (bushy, curves to the right & up) ────────────────────────────

    tail_bx, tail_by = 55, 120
    for i in range(50):
        t = i / 49
        # Main curve sweeping right and up
        tx = tail_bx + 90 * t + 30 * math.sin(t * math.pi)
        ty = tail_by - 100 * t * t + 15 * math.sin(t * math.pi * 2)
        pt(tx, ty)
    # Return stroke (bushy bottom edge)
    for i in range(50):
        t = 1.0 - i / 49
        tx = tail_bx + 90 * t + 30 * math.sin(t * math.pi) + 12
        ty = tail_by - 100 * t * t + 15 * math.sin(t * math.pi * 2) + 18
        pt(tx, ty)

    flush()

    # ── Left front leg ────────────────────────────────────────────────────

    line(-30, 195, -30, 230, steps=8)
    line(-30, 230, -18, 230, steps=5)

    flush()

    # ── Right front leg ───────────────────────────────────────────────────

    line(30, 195, 30, 230, steps=8)
    line(30, 230, 42, 230, steps=5)

    flush()

    # ── Left eye (small dot / circle) ─────────────────────────────────────

    arc(-25, -5, 6, 6, 0, 360, steps=16)

    flush()

    # ── Right eye ─────────────────────────────────────────────────────────

    arc(25, -5, 6, 6, 0, 360, steps=16)

    flush()

    # ── Nose (small triangle) ─────────────────────────────────────────────

    line(-6, 30, 0, 38, steps=6)
    line(0, 38, 6, 30, steps=6)
    line(6, 30, -6, 30, steps=6)

    flush()

    return strokes


# ---------------------------------------------------------------------------
# Drawing engine
# ---------------------------------------------------------------------------

_drawing = False   # prevent overlapping draws

def draw_fox(center_x, center_y, scale, speed, pause_between_strokes=0.15):
    """Execute the drawing by controlling the mouse."""
    global _drawing
    if _drawing:
        return
    _drawing = True

    pyautogui.PAUSE = 0            # we handle our own timing
    pyautogui.FAILSAFE = True      # move mouse to corner to abort

    strokes = generate_fox_path(center_x, center_y, scale)
    print(f"  Drawing fox: {len(strokes)} strokes, "
          f"{sum(len(s) for s in strokes)} total points …")

    for si, stroke in enumerate(strokes):
        if len(stroke) < 2:
            continue

        # Move to stroke start WITHOUT pressing
        pyautogui.moveTo(stroke[0][0], stroke[0][1], duration=0.05)
        time.sleep(0.02)

        # Press and drag through all points
        pyautogui.mouseDown(button='left')
        for x, y in stroke[1:]:
            pyautogui.moveTo(x, y, duration=speed)
        pyautogui.mouseUp(button='left')

        time.sleep(pause_between_strokes)

    print("  ✓ Fox drawn!")
    _drawing = False


# ---------------------------------------------------------------------------
# Hotkey parsing
# ---------------------------------------------------------------------------

MODIFIER_MAP = {
    'ctrl':  '<ctrl>',
    'control': '<ctrl>',
    'shift': '<shift>',
    'alt':   '<alt>',
    'cmd':   '<cmd>',
    'super': '<cmd>',
    'win':   '<cmd>',
}

def parse_hotkey(spec: str) -> str:
    """
    Convert user-friendly hotkey string like 'ctrl+shift+f'
    into pynput GlobalHotKeys format like '<ctrl>+<shift>+f'.
    """
    parts = [p.strip().lower() for p in spec.split('+')]
    mapped = []
    for p in parts:
        if p in MODIFIER_MAP:
            mapped.append(MODIFIER_MAP[p])
        else:
            mapped.append(p)
    return '+'.join(mapped)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="🦊 Fox Drawer — hotkey-triggered mouse drawing of a fox")
    parser.add_argument('--hotkey', default='ctrl+shift+f',
                        help='Hotkey combo (default: ctrl+shift+f)')
    parser.add_argument('--scale', type=float, default=1.2,
                        help='Drawing scale multiplier (default: 1.2)')
    parser.add_argument('--speed', type=float, default=0.008,
                        help='Seconds per point movement (default: 0.008)')
    parser.add_argument('--cx', type=int, default=None,
                        help='Center X (default: screen center)')
    parser.add_argument('--cy', type=int, default=None,
                        help='Center Y (default: screen center)')
    parser.add_argument('--at-cursor', action='store_true',
                        help='Draw at current mouse position instead of screen center')

    args = parser.parse_args()

    # Determine center
    screen_w, screen_h = pyautogui.size()
    print(f"  Screen size: {screen_w}×{screen_h}")

    def get_center():
        if args.at_cursor:
            return pyautogui.position()
        cx = args.cx if args.cx is not None else screen_w // 2
        cy = args.cy if args.cy is not None else screen_h // 2
        return cx, cy

    hotkey_str = parse_hotkey(args.hotkey)
    print(f"\n  🦊 Fox Drawer ready!")
    print(f"  Hotkey : {args.hotkey}  (internal: {hotkey_str})")
    print(f"  Scale  : {args.scale}")
    print(f"  Speed  : {args.speed}s per step")
    print(f"  Center : {'cursor position' if args.at_cursor else f'{get_center()}'}")
    print(f"\n  Open a drawing app (e.g. KolourPaint, GIMP, MS Paint),")
    print(f"  then press {args.hotkey} to draw the fox!")
    print(f"  Press Ctrl+C here to quit.\n")
    print(f"  ⚠  FAILSAFE: quickly move mouse to top-left corner to abort.\n")

    def on_hotkey():
        cx, cy = get_center()
        print(f"\n  🎨 Hotkey pressed! Drawing at ({cx}, {cy}) …")
        # Run in thread so hotkey listener isn't blocked
        t = threading.Thread(target=draw_fox,
                             args=(cx, cy, args.scale, args.speed),
                             daemon=True)
        t.start()

    hotkey_dict = {hotkey_str: on_hotkey}

    try:
        with keyboard.GlobalHotKeys(hotkey_dict) as listener:
            listener.join()
    except KeyboardInterrupt:
        print("\n  Bye bye! 🦊")


if __name__ == '__main__':
    main()
