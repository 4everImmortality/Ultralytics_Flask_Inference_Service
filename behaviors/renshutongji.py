# inference_service/behaviors/renshutongji.py (Standalone with SQLite)

import cv2
import numpy as np
from .base_behavior import BaseBehavior

class RenShuTongJiBehavior(BaseBehavior):
    """
    Behavior to count the number of people detected in a frame and display the count.
    """
    def __init__(self, control_code):
        """
        Initializes the RENSHUTONGJI behavior handler.

        Args:
            control_code (str): The unique code for the control instance.
        """
        super().__init__(control_code)
        self.logger.info("RENSHUTONGJI behavior handler initialized.")

    def process_frame(self, frame: np.ndarray, detections: list, control_state: dict) -> tuple[np.ndarray, bool]:
        """
        Counts people and draws the count on the frame.

        Args:
            frame (np.ndarray): The current frame (already has general detections drawn).
            detections (list): Raw detection results.
            control_state (dict): The mutable state dictionary for this control code.

        Returns:
            tuple[np.ndarray, bool]:
                - np.ndarray: The frame with the people count drawn.
                - bool: Always False, as this behavior doesn't trigger specific events like video save.
        """
        # Assuming class 0 in detections is 'person' in the YOLO model
        person_detections = [det for det in detections if int(det[5]) == 0]
        num_people = len(person_detections)

        # Draw the count on a copy of the frame to avoid modifying the buffer frame directly
        annotated_frame = frame.copy()
        # Define text properties
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1
        color = (0, 255, 0)  # Green color (BGR format)
        thickness = 2
        text = f"People Count: {num_people}"
        position = (10, 30) # Top-left corner

        # Draw the text on the frame
        # Ensure position is within frame bounds if needed, but (10, 30) is usually safe
        cv2.putText(annotated_frame, text, position, font, font_scale, color, thickness)

        # This behavior does not trigger specific events
        event_triggered = False

        return annotated_frame, event_triggered

    # This behavior does not trigger alarms, so get_alarm_data is not needed
    # or can return None as per the BaseBehavior default.

