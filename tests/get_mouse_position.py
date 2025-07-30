import pyautogui
import time

print("--- Mouse Position Finder ---")
print("Move your mouse over the game window to find coordinates.")
print("Press Ctrl-C in this terminal to quit.")

try:
    while True:
        # Get and display the current mouse position.
        x, y = pyautogui.position()
        position_str = f"X: {str(x).rjust(4)} Y: {str(y).rjust(4)}"

        # Get and display the color of the pixel under the mouse.
        pixel_color = pyautogui.screenshot().getpixel((x, y))
        color_str = f"RGB: ({str(pixel_color[0]).rjust(3)}, {str(pixel_color[1]).rjust(3)}, {str(pixel_color[2]).rjust(3)})"

        # Print the combined string.
        print(f"{position_str} | {color_str}", end='')

        # \b is a backspace character. We print backspaces to erase the line.
        print('\b' * (len(position_str) + len(color_str) + 3), end='', flush=True)

        # A small delay to prevent high CPU usage.
        time.sleep(1.0)

except KeyboardInterrupt:
    
    print("\nDone.")

