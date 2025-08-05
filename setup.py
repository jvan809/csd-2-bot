import cv2
import numpy as np
import pyautogui
from mss import mss
import pytesseract
from pytesseract import Output
from pathlib import Path

from src.config_manager import ConfigManager
from src.ocr_processor import OcrProcessor
# Global variable to store points from user clicks
click_points = []


def mouse_callback(event, x, y, flags, param):
    """OpenCV mouse callback function to capture click coordinates."""
    global click_points
    clone = param['image']
    window_name = param['window_name']
    max_points = param.get('max_points', 2)  # Default to 2 for rectangle selection
    
    if event == cv2.EVENT_LBUTTONDOWN:
        if len(click_points) < max_points:
            click_points.append((x, y))
            # Draw a circle to give user feedback on their click
            cv2.circle(clone, (x, y), 5, (0, 255, 0), -1)
            cv2.imshow(window_name, clone)


def get_user_clicks(screenshot, prompt_text, num_points=1):
    """
    Interactively asks the user to click on specific points on the screen.
    Returns a list of (x, y) tuples.
    """
    global click_points
    window_name = "Setup: Define Points"
    
    click_points = []  # Reset points
    clone = screenshot.copy()
    cv2.namedWindow(window_name)
    cv2.setMouseCallback(window_name, mouse_callback, {'image': clone, 'window_name': window_name, 'max_points': num_points})
    
    cv2.putText(clone, prompt_text, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 3)
    cv2.putText(clone, prompt_text, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    while len(click_points) < num_points:
        cv2.imshow(window_name, clone)
        if cv2.waitKey(1) & 0xFF == 27: # Allow escape to exit
            cv2.destroyAllWindows()
            return None
            
    cv2.destroyAllWindows()
    print(f"✅ Points captured: {click_points}")
    return click_points


def get_panel_from_user(screenshot, name="Ingredient"):
    """
    Interactively asks the user to define the a panel by clicking.
    """
    global click_points
    window_name = f"Setup: Define {name} Panel"
    
    while True:  # Main loop for retries
        click_points = []  # Reset points for each attempt
        clone = screenshot.copy()
        cv2.namedWindow(window_name)
        cv2.setMouseCallback(window_name, mouse_callback, {'image': clone, 'window_name': window_name})
        
        cv2.putText(clone, f"Click TOP-LEFT, then BOTTOM-RIGHT of the {name} panel.", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 3)
        cv2.putText(clone, f"Click TOP-LEFT, then BOTTOM-RIGHT of the {name} panel.", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        while len(click_points) < 2:
            cv2.imshow(window_name, clone)
            if cv2.waitKey(1) & 0xFF == 27:  # Allow escape to exit
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


def step_1_find_main_panels(config_manager):
    """STEP 1: Captures the full screen and finds the main UI panels using user input."""
    print("\n--- Step 1: Main Panel Calibration ---")
    screen_width, screen_height = pyautogui.size()
    print("🔍 Searching for main game panels...")
    with mss() as sct:
        monitor = {"top": 0, "left": 0, "width": screen_width, "height": screen_height}
        screenshot = np.array(sct.grab(monitor))
        screenshot_bgr = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2BGR)
        gray = cv2.cvtColor(screenshot_bgr, cv2.COLOR_BGR2GRAY)

    ingredient_panel_roi = get_panel_from_user(screenshot, "Ingredient")
    recipe_list_roi = get_panel_from_user(screenshot, "Recipe")

    # Display what was found for user confirmation
    debug_img = screenshot_bgr.copy()
    r1 = ingredient_panel_roi
    cv2.rectangle(debug_img, (r1['left'], r1['top']), (r1['left'] + r1['width'], r1['top'] + r1['height']), (0, 255, 0), 3)
    r2 = recipe_list_roi
    cv2.rectangle(debug_img, (r2['left'], r2['top']), (r2['left'] + r2['width'], r2['top'] + r2['height']), (0, 0, 255), 3)

    cv2.putText(debug_img, "Found Panels. Press any key to continue.", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.imshow("Setup: Panel Detection", debug_img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    config_manager.update_setting("ocr_regions.ingredient_panel_roi", ingredient_panel_roi)
    config_manager.update_setting("ocr_regions.recipe_list_roi", recipe_list_roi)
    return screenshot


def step_2_calibrate_recipe_layout(config_manager, screenshot):
    """STEP 2: Calibrates page indicators and recipe slot positions."""
    print("\n--- Step 2: Recipe Layout Calibration ---")
    
    # --- Get Page Indicator Positions ---

    indicator_points = get_user_clicks(screenshot, "Click 2nd page dot, then 3rd page dot", num_points=2)
    if not indicator_points or len(indicator_points) != 2:
        print("❌ Failed to get page indicator points. Aborting.")
        return False
    
    page_indicators = [
        {"x": p[0], "y": p[1]} for p in indicator_points
    ]


    # --- Programmatically find recipe slots ---
    print("\n In the game, navigate to a recipe with at least 6 normal steps (e.g. Sashimi).")
    input("Press Enter when ready to find recipe slots...")

    recipe_roi = config_manager.get_setting("ocr_regions.recipe_list_roi")
    with mss() as sct:
        # Grab a fresh screenshot of the recipe panel
        recipe_panel_img = np.array(sct.grab(recipe_roi))

    # Convert from 4-channel BGRA to 3-channel BGR for color matching
    recipe_panel_img_hsv = cv2.cvtColor(recipe_panel_img, cv2.COLOR_BGR2HSV)


    # recipe boxes are coloured boxes on greyscale background
    minimum_saturation_ratio = 0.2
    recipe_panel_height, recipe_panel_width, _ = recipe_panel_img_hsv.shape
    mask = np.zeros((recipe_panel_height, recipe_panel_width), dtype=np.uint8)

    lower_bound = np.array([0.0, minimum_saturation_ratio*255, 0.0])
    upper_bound = np.array([255.0, 255.0, 255.0])
    mask = cv2.inRange(recipe_panel_img_hsv, lower_bound, upper_bound)


    # Find contours on the mask and filter them
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    recipe_slots_relative = []
    min_area = 500  # Heuristic to filter out small noise
    for contour in contours:
        if cv2.contourArea(contour) > min_area:
            recipe_slots_relative.append(cv2.boundingRect(contour))

    recipe_slots_relative = list(set(recipe_slots_relative))
    
        # Sort boxes in reading order
    recipe_slots_relative.sort(key=lambda r: (r[1], r[0])) 


    if len(recipe_slots_relative) < 6:
        print(f"❌ ERROR: Expected to find at least 6 recipe slots, but only found {len(recipe_slots_relative)}.")
        return False
    else:
        print(f"✅ Found {len(recipe_slots_relative)} recipe slots.")

    
    y_second_line = recipe_slots_relative[-1][1]
    reciple_slot_width = recipe_slots_relative[-1][2]
    reciple_slot_height = recipe_slots_relative[-1][3]

    while len(recipe_slots_relative) < 10:
        x_ind_new_slot = len(recipe_slots_relative) - 5
        new_slot = (recipe_slots_relative[x_ind_new_slot][0], y_second_line, reciple_slot_width, reciple_slot_height)
        recipe_slots_relative.append(new_slot)



    # Convert to the required ROI format
    recipe_indicator_rois = [{"left": x, "top": y, "width": w, "height": h} for x, y, w, h in recipe_slots_relative]
    recipe_slot_rois = []
    for (i, slot) in enumerate(recipe_slots_relative):
        x, y, w, h = slot
        if i == 4 or i == 9:
            slot_right = recipe_panel_width
        else: 
            slot_right =  recipe_indicator_rois[i+1]['left']

        recipe_slot = {"left": x+w, "top": y, "width": slot_right - (x+w), "height":h+2}
        recipe_slot_rois.append(recipe_slot)


    # Calculate vertical coordinates based on the found slots
    vertical_coords = {
        "panel_top": recipe_slots_relative[0][1],
        "line_one_bottom": recipe_slots_relative[0][1] + recipe_slots_relative[0][3],
        "line_two_bottom": recipe_slots_relative[5][1] + recipe_slots_relative[5][3],
        "panel_bottom": recipe_panel_height
    }
    print(f"✅ Calculated vertical coordinates: {vertical_coords}")
    # --- Save to config ---
    print("\n Saving new recipe layout configuration...")
    config_manager.update_setting("recipe_layout.page_indicators", page_indicators)
    config_manager.update_setting("recipe_layout.recipe_slot_rois", recipe_slot_rois)
    config_manager.update_setting("recipe_layout.recipe_indicator_rois", recipe_indicator_rois)
    config_manager.update_setting("recipe_layout.vertical_coords", vertical_coords)
    
    return True


def find_ingredient_slots(panel_roi):
    """
    Finds the 8 individual ingredient slots within the main ingredient panel.
    """
    print("\n--- Next Step: Ingredient Slot Detection ---") 
    # initial setup screen should be valid for this function, so no input() is needed


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

def step_3_process_ingredient_slots(config_manager):
    ingredient_panel_roi = config_manager.get_setting("ocr_regions.ingredient_panel_roi", None)

    if not ingredient_panel_roi:
        print("Ingredient panel failed to save to config. Exiting")
        return False

    slots, first_slot_contour = find_ingredient_slots(ingredient_panel_roi)
    if not slots:
        return False

    ingredient_slot_rois = []
    # panel_x, panel_y = ingredient_panel_roi['left'], ingredient_panel_roi['top']
    for rect in slots:
        x, y, w, h = rect
        relative_roi = {"top": y, "left": x, "width": w, "height": h}
        ingredient_slot_rois.append(relative_roi)

    mask_path = Path("assets/masks/ingredient_mask.png")
    create_corner_mask(first_slot_contour, mask_path)

    print("\n💾 Saving configuration...")
    config_manager.update_setting("ocr_regions.ingredient_slot_rois", ingredient_slot_rois)
    config_manager.update_setting("bot_settings.ingredient_mask_path", str(mask_path))
    return True    


def main():
    """Main setup script execution."""
    print("--- CSD2 Bot Setup Script ---")
    print("This script will calibrate the bot by finding key areas on your screen.")
    print("Please make sure the game is running and visible.")
    input("Press Enter to begin...")

    config_manager = ConfigManager()

    # --- Run Setup Steps ---
    # The first step also captures the initial screenshot we need for subsequent steps.
    screenshot = step_1_find_main_panels(config_manager)
    if screenshot is None:
        print("\n❌ Setup failed during main panel detection. Exiting.")
        return

    success = step_2_calibrate_recipe_layout(config_manager, screenshot)
    if not success:
        print("\n❌ Setup failed during recipe layout calibration. Exiting.")
        return

    success = step_3_process_ingredient_slots(config_manager)
    if not success:
        print("\n❌ Setup failed during recipe layout calibration. Exiting.")
        return



    # The config is saved by `update_setting` within each step, so we just need a final message.
    print("\n" + "="*40)
    print("✅ Configuration saved successfully to config.json.")
    print("Setup complete! You can now run the main bot.")
    print("="*40)


if __name__ == "__main__":
    main()
