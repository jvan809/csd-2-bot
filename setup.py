import time
from pathlib import Path

import cv2
import numpy as np
import pyautogui
from mss import mss

from src.config_manager import ConfigManager

# Global variable to store points from user clicks
click_points = []

def mouse_callback(event, x, y, flags, param):
    """OpenCV mouse callback function to capture click coordinates."""
    global click_points
    clone = param['image']
    window_name = param['window_name']
    
    if event == cv2.EVENT_LBUTTONDOWN:
        if len(click_points) < 2:
            click_points.append((x, y))
            # Draw a circle to give user feedback on their click
            cv2.circle(clone, (x, y), 5, (0, 255, 0), -1)
            cv2.imshow(window_name, clone)

def get_panel_from_user(screenshot, name = "Ingredient"):
    """
    Interactively asks the user to define the a panel by clicking.
    """
    global click_points
    window_name = f"Setup: Define {name} Panel"
    
    while True: # Main loop for retries
        click_points = [] # Reset points for each attempt
        clone = screenshot.copy()
        cv2.namedWindow(window_name)
        cv2.setMouseCallback(window_name, mouse_callback, {'image': clone, 'window_name': window_name})
        
        cv2.putText(clone, f"Click TOP-LEFT, then BOTTOM-RIGHT of the {name} panel.", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 3)
        cv2.putText(clone, f"Click TOP-LEFT, then BOTTOM-RIGHT of the {name} panel.", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        while len(click_points) < 2:
            cv2.imshow(window_name, clone)
            if cv2.waitKey(1) & 0xFF == 27: # Allow escape to exit
                cv2.destroyAllWindows()
                return None

        p1_raw, p2_raw = click_points[0], click_points[1]
        p1 = (min(p1_raw[0], p2_raw[0]), min(p1_raw[1], p2_raw[1]))
        p2 = (max(p1_raw[0], p2_raw[0]), max(p1_raw[1], p2_raw[1]))
        roi = {"top": p1[1], "left": p1[0], "width": p2[0] - p1[0], "height": p2[1] - p1[1]}

        confirm_img = screenshot.copy()
        cv2.rectangle(confirm_img, p1, p2, (0, 255, 0), 3)
        cv2.putText(confirm_img, "Is this correct? (y/n)", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 3)
        cv2.putText(confirm_img, "Is this correct? (y/n)", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.imshow(window_name, confirm_img)
        
        key = cv2.waitKey(0) & 0xFF
        cv2.destroyAllWindows()
        if key == ord('y'):
            print(f"✅ {name} Panel defined.")
            return roi
        elif key == ord('n'):
            print("❌ User rejected selection. Retrying...")
        else:
            print("⚠️ Invalid input. Please press 'y' or 'n'. Retrying...")

def find_main_panels(screen_width, screen_height):
    """
    Captures the full screen and finds the main UI panels using user input.
    """
    print("🔍 Searching for main game panels...")
    with mss() as sct:
        monitor = {"top": 0, "left": 0, "width": screen_width, "height": screen_height}
        screenshot = np.array(sct.grab(monitor))
        screenshot_bgr = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2BGR)
        gray = cv2.cvtColor(screenshot_bgr, cv2.COLOR_BGR2GRAY)


    ingredient_panel_roi = get_panel_from_user(screenshot, "Ingredient")

    recipe_list_roi = get_panel_from_user(screenshot, "Recipe")

    # Optional: Display what was found for user confirmation
    debug_img = screenshot_bgr.copy()
    r1 = ingredient_panel_roi
    cv2.rectangle(debug_img, (r1['left'], r1['top']), (r1['left'] + r1['width'], r1['top'] + r1['height']), (0, 255, 0), 3)
    r2 = recipe_list_roi
    cv2.rectangle(debug_img, (r2['left'], r2['top']), (r2['left'] + r2['width'], r2['top'] + r2['height']), (0, 0, 255), 3)

    cv2.putText(debug_img, "Found Panels. Press any key to continue.", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.imshow("Setup: Panel Detection", debug_img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    return ingredient_panel_roi, recipe_list_roi


def find_ingredient_slots(panel_roi):
    """
    Finds the 8 individual ingredient slots within the main ingredient panel.
    """
    print("\n--- Next Step: Ingredient Slot Detection ---")
    print("Please ensure the game is showing a food with at least 5 ingredient slots visible.")
    input("Press Enter when you are ready...")

    with mss() as sct:
        panel_screenshot = np.array(sct.grab(panel_roi))

    gray = cv2.cvtColor(panel_screenshot, cv2.COLOR_BGRA2GRAY)
    _, thresh = cv2.threshold(gray, 250, 255, cv2.THRESH_BINARY)


    # Debug - show thresholded image for verification
    # cv2.imshow("Thresholded Ingredient panel:", thresh)
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    width = 0
    height = 0

    boxes = []
    first_contour = None

    for contour in contours:
        rect = cv2.boundingRect(contour)
        x, y, w, h = rect
        area = w * h
        aspect_ratio = w / float(h) if h > 0 else 0
        # Use similar heuristics as the original bot to find the boxes
        if 1000 < area < 50000 and aspect_ratio > 2.0:
            boxes.append(rect)

            if width == 0:
                width = w
                height = h
                first_contour = contour
            else:
                assert abs(width - w) < 2, "Inconsistent box widths, This shouldn't happen - please talk to dev"
                assert abs(height - h) < 2, "Inconsistent box heights, Please select a different food as the ingredient pictures are too bright"

    # Sort boxes in column reading order (left side top to bottom then right side top to bottom)
    boxes.sort(key=lambda b: (b[0], b[1]))

    if len(boxes) < 5:
        print(f"❌ ERROR: Expected to find 5 or more ingredient slots, but only found {len(boxes)} slots.")
        print("Please make sure a food with 5 or more ingredients is on screen and try again.")
        return None

    print(f"✅ Successfully found {len(boxes)} ingredient slots.")

    if len(boxes) == 8:
        return boxes, first_contour
    
    y_values = [box[1] for box in boxes]
    x_value_right_column = boxes[-1][0]
    
    while len(boxes) < 8:
        new_box_y_ind = len(boxes) - 4
        new_box = (x_value_right_column, y_values[new_box_y_ind], width, height)
        # new_box = {"top": y_values[new_box_y_ind], "left" : x_value_right_column, "width" : width, "height" : height}
        boxes.append(new_box)

    return boxes, first_contour
        


def create_corner_mask(first_slot_contour, mask_path):
    """
    Creates and saves a mask image to handle the rounded corners of ingredient slots.
    """
     # Calculate the bounding rectangle directly from the contour
    x, y, w, h = cv2.boundingRect(first_slot_contour)


    # Create a blank image for the mask
    mask = np.zeros((h, w), dtype=np.uint8)

    # The contour is relative to the panel, but we need it relative to its own bounding box.
    # We need to shift the contour to be relative to the rect's origin (0,0).
    shifted_contour = first_slot_contour - (x, y)

    # Use convex hull to create a solid shape
    hull = cv2.convexHull(shifted_contour)

    # Draw the filled hull onto the mask
    cv2.drawContours(mask, [hull], -1, 255, -1)

    # Ensure the directory exists
    mask_path.parent.mkdir(parents=True, exist_ok=True)


    # Save the mask
    cv2.imwrite(str(mask_path), mask)
    print(f"✅ Corner mask created and saved to '{mask_path}'")


def main():
    """Main setup script execution."""
    print("--- CSD2 Bot Setup Script ---")
    print("This script will calibrate the bot by finding key areas on your screen.")
    print("Please make sure the game is running in full-screen mode.")
    print("Navigate to any save file, Food Catalog then Soup on the top row, and start making stew")
    input("Press Enter to begin...")



    try:
        screen_width, screen_height = pyautogui.size()
        print(f"Detected screen resolution: {screen_width}x{screen_height}")
    except Exception as e:
        print(f"Could not get screen size. Error: {e}")
        return


    config_manager = ConfigManager()
    # config_manager.get_setting("ocr_regions.ingredient_panel_roi", None)
    # config_manager.get_setting("ocr_regions.recipe_list_roi", None)

    # ingredient_panel_roi, recipe_list_roi = find_main_panels(screen_width, screen_height)


    # if not ingredient_panel_roi or not recipe_list_roi:
    #     print("\nSetup failed. Exiting.")
    #     return

    recipe_list_roi = {
            "top": 884,
            "left": 452,
            "width": 1012,
            "height": 97
        }
    ingredient_panel_roi = {
            "top": 146,
            "left": 1610,
            "width": 305,
            "height": 364
        }


    slots, first_slot_contour = find_ingredient_slots(ingredient_panel_roi)
    if not slots:
        print("\nSetup failed. Exiting.")
        return

    ingredient_slot_rois = []
    # panel_x, panel_y = ingredient_panel_roi['left'], ingredient_panel_roi['top']
    for rect in slots:
        x, y, w, h = rect
        absolute_roi = {"top": y, "left": x, "width": w, "height": h}
        ingredient_slot_rois.append(absolute_roi)

    mask_path = Path("assets/masks/ingredient_mask.png")
    create_corner_mask(first_slot_contour, mask_path)

    print("\n💾 Saving configuration...")

    config_manager.update_setting("ocr_regions.ingredient_panel_roi", ingredient_panel_roi)
    config_manager.update_setting("ocr_regions.recipe_list_roi", recipe_list_roi)
    config_manager.update_setting("ocr_regions.ingredient_slot_rois", ingredient_slot_rois)
    config_manager.update_setting("bot_settings.ingredient_mask_path", str(mask_path))

    config_manager.save_config()
    print("✅ Configuration saved successfully to config.json.")
    print("\nSetup complete! You can now run the main bot.")


if __name__ == "__main__":
    main()
