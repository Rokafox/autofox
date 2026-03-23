#!/usr/bin/env python3
"""
Auto Drawer — Press a hotkey and the mouse draws a pattern on screen!

Patterns are JSON files containing stroke data (relative coordinates).
The drawing always starts centered at the current mouse position.

Usage:
    python3 fox_drawer.py                            # draws pattern_fox.json at cursor
    python3 fox_drawer.py --pattern pattern_fox.json # explicit pattern file
    python3 fox_drawer.py --hotkey ctrl+alt+f        # custom hotkey
    python3 fox_drawer.py --scale 2.0                # bigger drawing
    python3 fox_drawer.py --speed 0.005              # faster drawing

Pattern file format (JSON):
    {
        "name": "my_pattern",
        "description": "optional description",
        "strokes": [
            [[x1, y1], [x2, y2], ...],   // stroke 1 (pen down, draw, pen up)
            [[x1, y1], [x2, y2], ...],   // stroke 2
            ...
        ]
    }

    Coordinates are relative to center (0, 0) in unscaled pixels.
    Positive X = right, positive Y = down.
    Each stroke is a separate pen-down/pen-up sequence.
    Complex drawings are fully supported — just add more strokes and points.

Requirements:
    pip install pyautogui pynput

Works on: Linux (X11), macOS, Windows
"""

import argparse
import json
import os
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
# Pattern loading
# ---------------------------------------------------------------------------

def load_pattern(path):
    """Load a pattern JSON file and return its stroke data."""
    with open(path, 'r') as f:
        data = json.load(f)

    if 'strokes' not in data:
        print(f"ERROR: Pattern file '{path}' missing 'strokes' key.")
        sys.exit(1)

    strokes = data['strokes']
    name = data.get('name', os.path.basename(path))
    total_points = sum(len(s) for s in strokes)
    print(f"  Loaded pattern '{name}': {len(strokes)} strokes, {total_points} points")
    return strokes


def resolve_pattern(strokes, center_x, center_y, scale):
    """Convert relative pattern coordinates to absolute screen coordinates."""
    resolved = []
    for stroke in strokes:
        resolved.append([
            (round(center_x + pt[0] * scale), round(center_y + pt[1] * scale))
            for pt in stroke
        ])
    return resolved


# ---------------------------------------------------------------------------
# Drawing engine
# ---------------------------------------------------------------------------

_drawing = False   # prevent overlapping draws


def draw_pattern(strokes, center_x, center_y, scale, speed,
                 pause_between_strokes=0.15):
    """Execute the drawing by controlling the mouse."""
    global _drawing
    if _drawing:
        return
    _drawing = True

    pyautogui.PAUSE = 0            # we handle our own timing
    pyautogui.FAILSAFE = True      # move mouse to corner to abort

    resolved = resolve_pattern(strokes, center_x, center_y, scale)
    print(f"  Drawing: {len(resolved)} strokes, "
          f"{sum(len(s) for s in resolved)} total points ...")

    for stroke in resolved:
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

    print("  Done!")
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

def find_default_pattern():
    """Look for a default pattern file next to this script."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    for name in ('pattern_fox.json',):
        path = os.path.join(script_dir, name)
        if os.path.isfile(path):
            return path
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Auto Drawer — hotkey-triggered mouse drawing from pattern files")
    parser.add_argument('--pattern', default=None,
                        help='Path to pattern JSON file (default: pattern_fox.json)')
    parser.add_argument('--hotkey', default='ctrl+shift+f',
                        help='Hotkey combo (default: ctrl+shift+f)')
    parser.add_argument('--scale', type=float, default=1.2,
                        help='Drawing scale multiplier (default: 1.2)')
    parser.add_argument('--speed', type=float, default=0.008,
                        help='Seconds per point movement (default: 0.008)')

    args = parser.parse_args()

    # Resolve pattern file
    pattern_path = args.pattern
    if pattern_path is None:
        pattern_path = find_default_pattern()
        if pattern_path is None:
            print("ERROR: No pattern file found. Use --pattern <file.json>")
            sys.exit(1)

    strokes = load_pattern(pattern_path)

    screen_w, screen_h = pyautogui.size()
    print(f"  Screen size: {screen_w}x{screen_h}")

    hotkey_str = parse_hotkey(args.hotkey)
    print(f"\n  Auto Drawer ready!")
    print(f"  Hotkey  : {args.hotkey}  (internal: {hotkey_str})")
    print(f"  Pattern : {pattern_path}")
    print(f"  Scale   : {args.scale}")
    print(f"  Speed   : {args.speed}s per step")
    print(f"  Center  : current mouse position at time of hotkey press")
    print(f"\n  Open a drawing app (e.g. KolourPaint, GIMP, MS Paint),")
    print(f"  then press {args.hotkey} to draw!")
    print(f"  Press Ctrl+C here to quit.\n")
    print(f"  FAILSAFE: quickly move mouse to top-left corner to abort.\n")

    def on_hotkey():
        cx, cy = pyautogui.position()
        print(f"\n  Hotkey pressed! Drawing at ({cx}, {cy}) ...")
        t = threading.Thread(target=draw_pattern,
                             args=(strokes, cx, cy, args.scale, args.speed),
                             daemon=True)
        t.start()

    hotkey_dict = {hotkey_str: on_hotkey}

    try:
        with keyboard.GlobalHotKeys(hotkey_dict) as listener:
            listener.join()
    except KeyboardInterrupt:
        print("\n  Bye!")


if __name__ == '__main__':
    main()
