import pyautogui
import time
import colorsys

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
        hsv = colorsys.rgb_to_hsv(pixel_color[0]/255, pixel_color[1]/255, pixel_color[2]/255)
        hsv = [round(x, 2) for x in hsv]

        output_line = f"{position_str} | {color_str} | {hsv}"

        # Print the combined string.
        print(output_line, end='')

        # \b is a backspace character. We print backspaces to erase the line.
        print('\b' * len(output_line), end='', flush=True)

        # A small delay to prevent high CPU usage.
        time.sleep(1.0)

except KeyboardInterrupt:
    
    print("\nDone.")

    # target_color_bgr = [[196, 67, 121], [67, 67, 196], [46, 138, 186]] 

except IndexError:
    print("\n Cursor on other screen. Exiting Script.")