# Multi-Robot Rover - try45

The available try45 folder is an incomplete camera-processing module snapshot rather than a runnable application.

## Features
- Contains camera frame processing and object-detection logic for the modular dashboard.
- Includes perspective transformation and tracking-related state.
- Does not include the application entry point, configuration, hardware controller, template, or supporting modules.
- Preserved as a partial source stage for historical accuracy.

## Dependencies and hardware
Python 3 with OpenCV, NumPy, and Ultralytics, plus the missing application modules (`roverconf` and `utils`) required by this partial camera component.

## Setup and run
This snapshot cannot be launched by itself: it contains only `camera_processor.py` and is missing the app, configuration, and supporting modules.

## Changes from the previous available try
Available files are reduced to a camera processor module; the rest of the application tree is absent. The previous available stage in this history is try44.

## Notes
This stage is intentionally partial; no missing modules or behavior have been invented.
