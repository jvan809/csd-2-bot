import pyautogui
import sys

print("--- Starting Failsafe Test ---")
pyautogui.FAILSAFE = True
print("Failsafe is ON. You have 10 seconds to move your mouse to the top-left corner.")
print("If this script finishes, the failsafe did NOT work.")

try:
    for i in range(10, 0, -1):
        # displayMousePosition() can interfere with the output, so we'll use a manual print
        pos = pyautogui.position()
        sys.stdout.write(f"\rTime left: {i:02d}s | Current Position: {str(pos):<20}")
        sys.stdout.flush()
        pyautogui.sleep(1)

    print("\n\nTest finished: Failsafe did NOT trigger.")

except pyautogui.FailSafeException:
    print("\n\nSUCCESS: Failsafe triggered correctly!")
except KeyboardInterrupt:
    print("\n\nTest stopped by user.")
except Exception as e:
    print(f"\n\nAn unexpected error occurred: {e}")
