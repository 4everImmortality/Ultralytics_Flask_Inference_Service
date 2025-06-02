# Flask Video Inference Service

This is a standalone Flask application responsible for real-time video stream processing, object detection, behavior analysis, saving alarm data to a SQLite database, and saving alarm video files.

## Project Structure (Inference Service related parts only)

```
Ultralytics_Flask_Inference_Service/      # Flask application for video processing
├── app.py              # Flask application entry point, API endpoints
├── config.py           # Flask application configuration (DB path, video paths, model)
├── utils.py            # Utility functions (DB operations, video saving, FFmpeg commands)
├── video_processor.py  # Manages detection pipelines
└── behaviors/          # Detection behavior modules
│   ├── __init__.py      # Makes it a Python package
│   ├── base_behavior.py  # Base behavior class
│   ├── renshutongji.py   # Example behavior: People Counting
│   └── zhoujieruqin.py   # Example behavior: Perimeter Intrusion
                
└── saved_videos/         # Subdirectory for saved videos (defined in Flask config)
│   └── alarm_videos/     # Subdirectory for alarm videos
├── Admin.sqlite3         # SQLite database file (Flask app writes alarm data here)
└── requirements.txt      # Project dependencies (includes libraries needed by Flask app)
```

**Note:** The `Admin.sqlite3` and `media` directories are typically part of a Django project, but the Flask application needs access to them. Please adjust path configurations according to your actual project structure.

For YOLO algorithm, You can place this project in the same directory as your modified local Ultralytics project, so that you can call your modified algorithms.

## Prerequisites

- Python 3.11+
- pip (Python package installer)
- FFmpeg (Must be installed and added to your system's PATH)

## Setup

1. Create a virtual environment (recommended):

   Execute the following in your project root directory (the directory containing the inference_service directory):

   ```
   conda create -n inference_server python=3.11 -y
   ```

2. **Activate the virtual environment:**

   - On Windows:

     ```
     conda activate inference_server
     ```

   - On macOS and Linux:

     ```
     conda activate inference_server
     ```

3. Install dependencies:

   Ensure your requirements.txt file in the project root contains the libraries required by the Flask application (e.g., Flask, ultralytics, opencv-python, numpy). Then execute:

   ```
   pip install -r requirements.txt
   ```

   - **OpenCV Note:** Depending on your system, you might need `opencv-contrib-python`.

4. **Flask Application Configuration (`inference_service`):**

   - Navigate to the `inference_service` directory.
   - Edit the `config.py` file to match your environment:
     - `MODEL_PATH`: Set the absolute or relative path to your YOLO model file (e.g., `yolov8n.pt`).
     - `SQLITE_DB_PATH`: **Very important, set this to the exact absolute path of the `Admin.sqlite3` database file used by your Django project.** For example: `r'D:\Code\PythonCurriculum\VideoAnalyze-master\Admin\Admin.sqlite3'`.
     - `ALARM_TABLE_NAME`: Ensure this matches the `db_table` name in your Django `Alarm` model's `Meta` class (you specified `'av_alarm'`).
     - `DJANGO_PROJECT_ROOT`, `DJANGO_MEDIA_ROOT`: These paths are inferred based on `SQLITE_DB_PATH`. **Please verify these paths are correct** based on your actual project structure.
     - `VIDEO_SAVE_MEDIA_RELATIVE_PATH_STRUCTURE`: Defines the relative path structure for video files within `DJANGO_MEDIA_ROOT` (e.g., `'saved_videos/alarm_videos'`). This should align with how you expect Django to serve these files.
     - `VIDEO_SAVE_FULL_PATH`: This is the absolute path where the Flask application will save the video files. It is constructed from `DJANGO_MEDIA_ROOT` and `VIDEO_SAVE_MEDIA_RELATIVE_PATH_STRUCTURE`. Ensure the user running the Flask application has write permissions to this directory.

## Running the Application

After activating the virtual environment, run the Flask application as a module from your project **root directory** (the directory containing the `inference_service` directory):

```
python -m Ultralytics_Flask_Inference_Service.app
```

The application will typically run on port `http://127.0.0.1:9002/`.

## API Endpoints

The Flask application exposes the following API endpoints:

- `POST /api/controls`: Get the status of all active control instances.
- `POST /api/control`: Get the status of a specific control instance by `code`. Requires a JSON request body with a `code` field.
- `POST /api/control/add`: Start a new detection control instance. Requires a JSON request body with `code`, `behaviorCode`, `streamUrl` fields, and optional `pushStream` and `pushStreamUrl`.
- `POST /api/control/cancel`: Stop a detection control instance by `code`. Requires a JSON request body with a `code` field.
- `GET /health`: Health check endpoint, returns the application status and number of active detection pipelines.

## Multithreading Design

To enable concurrent processing of multiple video streams, the inference service employs a multithreading design. Each active video stream processing pipeline is handled by a set of dedicated threads that communicate via queues.

The core threads include:

1. Manager Thread (`_manage_pipeline`)

   :

   - One Manager thread per video stream.
   - Coordinates the processing pipeline for its stream.
   - Responsible for starting and monitoring the `Puller`, `Detector`, and `Pusher` threads.
   - Listens for stop events (`stop_event`) or error events (`error_event`) and coordinates the stopping of child threads and resource cleanup upon receiving a signal.

2. Puller Thread (`_pull_stream`)

   :

   - Responsible for continuously reading raw video frames from the specified video stream URL (RTSP, file, etc.).
   - Uses an OpenCV `VideoCapture` object.
   - Places the read frames into the `frame_queue` for the `Detector` thread to consume.
   - Handles stream interruption and reconnection logic.

3. Detector Thread (`_detect_frames`)

   :

   - Retrieves raw video frames from the `frame_queue`.
   - Performs object detection on the frames using the YOLO model.
   - Passes the detection results and frames to the corresponding `Behavior Handler` for further analysis and processing.
   - Places the frames, potentially with additional annotations from the behavior handler, into the `annotated_frame_queue` for the `Pusher` thread to consume.
   - Triggers video saving logic (executed in a separate thread) based on signals from the behavior handler.

4. Pusher Thread (`_push_stream`)

   :

   - Retrieves annotated video frames from the `annotated_frame_queue`.
   - Uses an FFmpeg subprocess to push these frames to the specified push stream URL (RTSP, RTMP, etc.).
   - Writes the raw frame data to the FFmpeg process's standard input pipe.
   - Monitors the FFmpeg process status and error output.

**Inter-Thread Communication and Control:**

- **Queues:** `frame_queue` and `annotated_frame_queue` are used for safely passing video frame data between different threads. Queue capacity limits help control memory usage and flow.
- **Events:** `stop_event` is used to signal all threads to stop, and `error_event` is used to notify other threads to stop immediately if a critical error occurs in any thread. The Manager thread monitors these events to coordinate the lifecycle of the entire pipeline.

This multithreading architecture allows the application to process video streams from multiple sources concurrently, improving the system's responsiveness and real-time capabilities.

## Behavior Modules

Specific detection logic is implemented in behavior modules within the `inference_service/behaviors/` directory.

- Each behavior class should inherit from `base_behavior.BaseBehavior`.
- Implement the `process_frame` method to contain the specific detection and event triggering logic.
- Implement the optional `on_detection_start` and `on_detection_stop` methods for setup/cleanup during start/stop.
- Implement the optional `get_alarm_data` method to provide specific data for the alarm record when an event is triggered.
- Add your new behavior class to the `BEHAVIOR_MAP` dictionary in `inference_service/behaviors/__init__.py`, mapping a unique `behaviorCode` string to your class.

## Troubleshooting

- **`ImportError: cannot import name ... from 'config'`**: Ensure your file structure includes `__init__.py` files in package directories (`inference_service/` and `inference_service/behaviors/`) and you are running the Flask app as a module from the project root (`python -m inference_service.app`).
- **Database records not appearing:**
  - Verify that `SQLITE_DB_PATH` in `inference_service/config.py` is the **exact** path to your Django database file.
  - Verify that `ALARM_TABLE_NAME` in `inference_service/config.py` matches the `db_table` in your Django `Alarm` model (`av_alarm`).
  - Check the Flask application logs (`utils` logger) for any errors related to database initialization or insertion.
  - Use a SQLite client to open the database file and check if the `av_alarm` table exists and contains data.
- **Frontend 404 for video files:**
  - Verify that the Flask application is saving videos to the correct absolute path (`VIDEO_SAVE_FULL_PATH`), which should be located within your Django `MEDIA_ROOT`.
  - Verify that the `video_path` stored in the database is the correct relative path from Django's `MEDIA_ROOT` (e.g., `saved_videos/alarm_videos/your_video.mp4`). This is controlled by `VIDEO_SAVE_MEDIA_RELATIVE_PATH_STRUCTURE` in `config.py`.
  - Ensure Django is configured with the correct `MEDIA_ROOT` and `MEDIA_URL` and is properly serving static files under `/media/`.
- **FFmpeg errors (`Invalid data found when processing input`, `pipe broken`):**
  - This indicates an issue with the raw video data being sent from the Flask application to the FFmpeg process via the pipe.
  - Check Flask logs for specific FFmpeg error messages.
  - Try modifying the `build_ffmpeg_push_command` function to make FFmpeg save to a local file instead of pushing, to isolate the issue.
  - Verify the integrity of the `annotated_frame` data before writing to the pipe (e.g., save a few frames as images).
- **Permissions Errors:** Ensure the user running the Flask application has read/write permissions for the SQLite database file and the video save directory (`VIDEO_SAVE_FULL_PATH`).

# Future work

As OpenCV can not generate native H264 video, so I first generate avi video and then use ffmpeg to convert *.avi in to *.mp4, so that, HTML can read this local video file.

- [ ] generate native mp4 video
- [ ] add more detection algorithm in behavior package