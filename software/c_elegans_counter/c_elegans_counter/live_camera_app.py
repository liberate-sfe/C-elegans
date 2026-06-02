from __future__ import annotations

import argparse
from dataclasses import dataclass, asdict
from pathlib import Path
import threading
import time
from typing import Any

import cv2
import numpy as np
from flask import Flask, Response, jsonify, request

from .analysis import DetectorConfig, analyze_frame_array, draw_annotations


DEFAULT_WEIGHTS = Path(
    "runs/segment/runs/wormswin/yolo_seg_md_to_csb1_gpu_5e_frac025/weights/best.pt"
)


PROJECT_PRESETS = {
    "c_elegans_yolo": {
        "label": "C. elegans - YOLO segmentation",
        "mode": "yolo",
        "weights": str(DEFAULT_WEIGHTS),
        "conf": 0.25,
        "imgsz": 640,
    },
    "c_elegans_opencv": {
        "label": "C. elegans - OpenCV baseline",
        "mode": "opencv",
        "weights": "",
        "conf": 0.25,
        "imgsz": 640,
    },
    "daphnia_preview": {
        "label": "Daphnia - camera preview",
        "mode": "preview",
        "weights": "",
        "conf": 0.25,
        "imgsz": 640,
    },
    "focus_check": {
        "label": "Focus and illumination check",
        "mode": "preview",
        "weights": "",
        "conf": 0.25,
        "imgsz": 640,
    },
}


@dataclass
class LiveConfig:
    project: str = "c_elegans_yolo"
    source_type: str = "camera"
    camera_index: int = 0
    video_path: str = ""
    mode: str = "yolo"
    weights: str = str(DEFAULT_WEIGHTS)
    conf: float = 0.25
    imgsz: int = 640
    device: str = "0"
    process_every_n: int = 1
    display_scale: float = 1.0
    opencv_polarity: str = "dark"
    opencv_contrast_mode: str = "clahe"
    opencv_threshold_scale: float = 0.65
    opencv_min_area_px: float = 10.0
    opencv_min_length_px: float = 6.0
    opencv_min_aspect_ratio: float = 1.1


@dataclass
class LiveStats:
    running: bool = False
    project: str = "c_elegans_yolo"
    mode: str = "yolo"
    source: str = "camera:0"
    frame_index: int = 0
    worm_count: int = 0
    fps: float = 0.0
    inference_ms: float = 0.0
    width: int = 0
    height: int = 0
    status: str = "idle"
    error: str = ""
    weights: str = ""


class LiveCounter:
    def __init__(self, repo_root: Path, config: LiveConfig) -> None:
        self.repo_root = repo_root
        self.config = config
        self.stats = LiveStats()
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._latest_jpeg: bytes | None = None
        self._model: Any | None = None
        self._model_key: tuple[str, str] | None = None
        self._last_detections: tuple[Any, ...] = ()
        self._last_processed_frame: np.ndarray | None = None

    def start(self) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop_event.clear()
            self.stats.running = True
            self.stats.status = "starting"
            self.stats.error = ""
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        thread = self._thread
        if thread is not None:
            thread.join(timeout=2.0)
        with self._lock:
            self.stats.running = False
            self.stats.status = "stopped"

    def update_config(self, config: LiveConfig) -> None:
        restart_source = (
            config.source_type != self.config.source_type
            or config.camera_index != self.config.camera_index
            or config.video_path != self.config.video_path
        )
        self.config = config
        if restart_source and self.stats.running:
            self.stop()
            self.start()

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            return asdict(self.stats)

    def get_config(self) -> dict[str, Any]:
        return asdict(self.config)

    def get_latest_jpeg(self) -> bytes:
        with self._lock:
            if self._latest_jpeg is not None:
                return self._latest_jpeg
        return make_placeholder_frame("No camera frame yet")

    def stream(self):
        while True:
            frame = self.get_latest_jpeg()
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
            time.sleep(1 / 30)

    def _run_loop(self) -> None:
        capture = self._open_capture()
        if capture is None:
            return

        last_time = time.perf_counter()
        frame_index = 0
        cached_count = 0
        cached_inference_ms = 0.0
        cached_annotated: np.ndarray | None = None

        try:
            while not self._stop_event.is_set():
                ok, frame = capture.read()
                if not ok:
                    if self.config.source_type == "video":
                        capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        continue
                    self._set_error("Could not read from camera.")
                    time.sleep(0.1)
                    continue

                process_frame = frame_index % max(1, self.config.process_every_n) == 0
                processing_error = ""
                if process_frame:
                    start = time.perf_counter()
                    try:
                        cached_annotated, cached_count = self._process_frame(frame)
                    except Exception as exc:
                        cached_annotated = frame.copy()
                        cached_count = 0
                        processing_error = str(exc)
                    cached_inference_ms = (time.perf_counter() - start) * 1000
                elif cached_annotated is None:
                    cached_annotated = frame.copy()

                now = time.perf_counter()
                fps = 1.0 / max(1e-6, now - last_time)
                last_time = now
                output_frame = self._overlay_status(
                    cached_annotated.copy(),
                    count=cached_count,
                    fps=fps,
                    inference_ms=cached_inference_ms,
                )
                jpeg = encode_jpeg(output_frame)

                with self._lock:
                    self._latest_jpeg = jpeg
                    self.stats.running = True
                    self.stats.project = self.config.project
                    self.stats.mode = self.config.mode
                    self.stats.source = self._source_label()
                    self.stats.frame_index = frame_index
                    self.stats.worm_count = cached_count
                    self.stats.fps = round(fps, 2)
                    self.stats.inference_ms = round(cached_inference_ms, 2)
                    self.stats.width = int(frame.shape[1])
                    self.stats.height = int(frame.shape[0])
                    self.stats.status = "error" if processing_error else "running"
                    self.stats.error = processing_error
                    self.stats.weights = self.config.weights

                frame_index += 1
        finally:
            capture.release()
            with self._lock:
                self.stats.running = False
                if not self.stats.error:
                    self.stats.status = "stopped"

    def _open_capture(self) -> cv2.VideoCapture | None:
        if self.config.source_type == "video" and self.config.video_path:
            capture = cv2.VideoCapture(str(Path(self.config.video_path)))
            source = self.config.video_path
        else:
            capture = cv2.VideoCapture(int(self.config.camera_index), cv2.CAP_DSHOW)
            source = f"camera:{self.config.camera_index}"

        if not capture.isOpened():
            self._set_error(f"Could not open {source}.")
            return None

        with self._lock:
            self.stats.source = source
            self.stats.status = "running"
            self.stats.error = ""
        return capture

    def _source_label(self) -> str:
        if self.config.source_type == "video" and self.config.video_path:
            return Path(self.config.video_path).name
        return f"camera:{self.config.camera_index}"

    def _process_frame(self, frame: np.ndarray) -> tuple[np.ndarray, int]:
        mode = self.config.mode
        if mode == "yolo":
            return self._process_yolo(frame)
        if mode == "opencv":
            return self._process_opencv(frame)
        return frame.copy(), 0

    def _process_yolo(self, frame: np.ndarray) -> tuple[np.ndarray, int]:
        weights = resolve_path(self.repo_root, self.config.weights)
        if not weights.exists():
            annotated = frame.copy()
            cv2.putText(
                annotated,
                "YOLO weights not found",
                (20, 42),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (0, 0, 255),
                2,
                cv2.LINE_AA,
            )
            return annotated, 0

        model = self._load_yolo_model(str(weights), self.config.device)
        result = model.predict(
            frame,
            imgsz=self.config.imgsz,
            conf=self.config.conf,
            device=self.config.device,
            verbose=False,
        )[0]
        count = 0 if result.boxes is None else len(result.boxes)
        annotated = result.plot()
        return annotated, int(count)

    def _load_yolo_model(self, weights: str, device: str):
        key = (weights, device)
        if self._model is not None and self._model_key == key:
            return self._model

        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise RuntimeError("ultralytics is required for YOLO live mode.") from exc

        self._model = YOLO(weights)
        self._model_key = key
        return self._model

    def _process_opencv(self, frame: np.ndarray) -> tuple[np.ndarray, int]:
        config = DetectorConfig(
            polarity=self.config.opencv_polarity,
            min_area_px=self.config.opencv_min_area_px,
            max_area_px=50000.0,
            min_aspect_ratio=self.config.opencv_min_aspect_ratio,
            min_length_px=self.config.opencv_min_length_px,
            blur_kernel=5,
            background_kernel=51,
            morph_kernel=3,
            roi_mode="auto",
            roi_margin_px=30,
            contrast_mode=self.config.opencv_contrast_mode,
            clahe_clip_limit=2.5,
            clahe_tile_size=8,
            threshold_scale=self.config.opencv_threshold_scale,
        )
        result = analyze_frame_array(
            image=frame,
            calibration_um_per_pixel=1.0,
            config=config,
        )
        annotated = draw_annotations(
            frame,
            result["detections"],
            roi_mask=result["roi_mask"],
        )
        return annotated, int(result["worm_count"])

    def _overlay_status(
        self,
        frame: np.ndarray,
        count: int,
        fps: float,
        inference_ms: float,
    ) -> np.ndarray:
        project_label = PROJECT_PRESETS.get(self.config.project, {}).get(
            "label",
            self.config.project,
        )
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (frame.shape[1], 82), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.45, frame, 0.55, 0, frame)
        line_1 = f"{project_label} | Count: {count}"
        line_2 = (
            f"{self._source_label()} | {self.config.mode} | "
            f"FPS {fps:.1f} | inference {inference_ms:.1f} ms"
        )
        cv2.putText(
            frame,
            line_1,
            (18, 32),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
        cv2.putText(
            frame,
            line_2,
            (18, 64),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.58,
            (210, 240, 255),
            1,
            cv2.LINE_AA,
        )
        return frame

    def _set_error(self, message: str) -> None:
        with self._lock:
            self.stats.running = False
            self.stats.status = "error"
            self.stats.error = message
            self._latest_jpeg = make_placeholder_frame(message)


def create_app(repo_root: Path, initial_config: LiveConfig) -> Flask:
    app = Flask(__name__)
    counter = LiveCounter(repo_root=repo_root, config=initial_config)

    @app.get("/")
    def index():
        return INDEX_HTML

    @app.get("/video_feed")
    def video_feed():
        return Response(counter.stream(), mimetype="multipart/x-mixed-replace; boundary=frame")

    @app.get("/api/projects")
    def api_projects():
        return jsonify(PROJECT_PRESETS)

    @app.get("/api/cameras")
    def api_cameras():
        return jsonify(enumerate_cameras())

    @app.get("/api/state")
    def api_state():
        return jsonify({"config": counter.get_config(), "stats": counter.get_stats()})

    @app.post("/api/config")
    def api_config():
        payload = request.get_json(force=True) or {}
        config = build_config(payload, counter.config)
        counter.update_config(config)
        return jsonify({"config": counter.get_config(), "stats": counter.get_stats()})

    @app.post("/api/start")
    def api_start():
        counter.start()
        return jsonify(counter.get_stats())

    @app.post("/api/stop")
    def api_stop():
        counter.stop()
        return jsonify(counter.get_stats())

    return app


def build_config(payload: dict[str, Any], current: LiveConfig) -> LiveConfig:
    data = asdict(current)
    project = payload.get("project", data["project"])
    preset = PROJECT_PRESETS.get(project)
    if preset:
        data["project"] = project
        data["mode"] = preset["mode"]
        data["weights"] = preset["weights"]
        data["conf"] = preset["conf"]
        data["imgsz"] = preset["imgsz"]

    for key in data:
        if key in payload and payload[key] not in (None, ""):
            data[key] = payload[key]

    data["camera_index"] = int(data["camera_index"])
    data["conf"] = float(data["conf"])
    data["imgsz"] = int(data["imgsz"])
    data["process_every_n"] = max(1, int(data["process_every_n"]))
    data["display_scale"] = float(data["display_scale"])
    data["opencv_threshold_scale"] = float(data["opencv_threshold_scale"])
    data["opencv_min_area_px"] = float(data["opencv_min_area_px"])
    data["opencv_min_length_px"] = float(data["opencv_min_length_px"])
    data["opencv_min_aspect_ratio"] = float(data["opencv_min_aspect_ratio"])
    return LiveConfig(**data)


def enumerate_cameras(max_index: int = 8) -> list[dict[str, Any]]:
    cameras: list[dict[str, Any]] = []
    for index in range(max_index):
        capture = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        if capture.isOpened():
            width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cameras.append({"index": index, "label": f"Camera {index}", "width": width, "height": height})
        capture.release()
    return cameras


def resolve_path(repo_root: Path, path: str) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return repo_root / candidate


def encode_jpeg(frame: np.ndarray) -> bytes:
    ok, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 82])
    if not ok:
        return make_placeholder_frame("Could not encode frame")
    return buffer.tobytes()


def make_placeholder_frame(message: str) -> bytes:
    frame = np.full((720, 1280, 3), (245, 245, 245), dtype=np.uint8)
    cv2.putText(
        frame,
        message,
        (40, 360),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (60, 60, 60),
        2,
        cv2.LINE_AA,
    )
    return encode_jpeg(frame)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Live microscope camera worm counter.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7860)
    parser.add_argument("--camera-index", type=int, default=0)
    parser.add_argument("--weights", default=str(DEFAULT_WEIGHTS))
    parser.add_argument("--device", default="0")
    parser.add_argument("--source-type", choices=["camera", "video"], default="camera")
    parser.add_argument("--video-path", default="")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args(argv)

    repo_root = Path.cwd()
    config = LiveConfig(
        camera_index=args.camera_index,
        weights=args.weights,
        device=args.device,
        source_type=args.source_type,
        video_path=args.video_path,
    )
    app = create_app(repo_root=repo_root, initial_config=config)
    print(f"Live camera app: http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug, threaded=True)
    return 0


INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>C. elegans Live Counter</title>
  <style>
    :root {
      color-scheme: light;
      --ink: #1d2329;
      --muted: #5e6975;
      --line: #cfd6dd;
      --panel: #f4f6f8;
      --accent: #116466;
      --danger: #9f2a2a;
      font-family: Inter, Segoe UI, Arial, sans-serif;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: #e7ebef;
      color: var(--ink);
      min-height: 100vh;
      display: grid;
      grid-template-columns: minmax(280px, 340px) 1fr;
    }
    aside {
      border-right: 1px solid var(--line);
      background: #f9fafb;
      padding: 18px;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }
    main {
      min-width: 0;
      display: grid;
      grid-template-rows: auto 1fr;
    }
    header {
      min-height: 64px;
      border-bottom: 1px solid var(--line);
      background: #ffffff;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 12px 18px;
    }
    h1 {
      font-size: 18px;
      line-height: 1.2;
      margin: 0;
      font-weight: 650;
      letter-spacing: 0;
    }
    label {
      display: grid;
      gap: 6px;
      font-size: 13px;
      color: var(--muted);
      font-weight: 600;
    }
    select, input, button {
      width: 100%;
      min-height: 38px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 8px 10px;
      background: #fff;
      color: var(--ink);
      font: inherit;
    }
    button {
      cursor: pointer;
      background: var(--accent);
      border-color: var(--accent);
      color: #fff;
      font-weight: 650;
    }
    button.secondary {
      background: #fff;
      color: var(--ink);
      border-color: var(--line);
    }
    .controls {
      display: grid;
      gap: 12px;
    }
    .row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }
    .stats {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
      margin-top: 4px;
    }
    .stat {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px;
      min-height: 62px;
    }
    .stat span {
      display: block;
      color: var(--muted);
      font-size: 12px;
      font-weight: 650;
    }
    .stat strong {
      display: block;
      margin-top: 4px;
      font-size: 24px;
      line-height: 1.1;
    }
    .status {
      font-size: 13px;
      color: var(--muted);
      word-break: break-word;
    }
    .status.error { color: var(--danger); }
    .viewer {
      min-height: 0;
      padding: 18px;
      display: grid;
      place-items: center;
    }
    .feed {
      width: min(100%, 1280px);
      max-height: calc(100vh - 104px);
      object-fit: contain;
      border: 1px solid #aeb8c2;
      background: #111;
    }
    .actions {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }
    @media (max-width: 860px) {
      body { grid-template-columns: 1fr; }
      aside { border-right: 0; border-bottom: 1px solid var(--line); }
      .viewer { padding: 10px; }
      .feed { max-height: 62vh; }
    }
  </style>
</head>
<body>
  <aside>
    <h1>Live Microscope Counter</h1>
    <div class="controls">
      <label>Project
        <select id="project"></select>
      </label>
      <div class="row">
        <label>Source
          <select id="sourceType">
            <option value="camera">Camera</option>
            <option value="video">Video test</option>
          </select>
        </label>
        <label>Camera
          <select id="cameraIndex"></select>
        </label>
      </div>
      <label>Video test path
        <input id="videoPath" placeholder="Optional local video path">
      </label>
      <label>Weights
        <input id="weights">
      </label>
      <div class="row">
        <label>Confidence
          <input id="conf" type="number" min="0" max="1" step="0.01">
        </label>
        <label>Image size
          <input id="imgsz" type="number" min="160" step="32">
        </label>
      </div>
      <div class="row">
        <label>Device
          <input id="device">
        </label>
        <label>Process N
          <input id="processEvery" type="number" min="1" step="1">
        </label>
      </div>
      <div class="actions">
        <button id="start">Start</button>
        <button id="stop" class="secondary">Stop</button>
      </div>
    </div>
    <div class="stats">
      <div class="stat"><span>Count</span><strong id="wormCount">0</strong></div>
      <div class="stat"><span>FPS</span><strong id="fps">0</strong></div>
      <div class="stat"><span>Inference</span><strong id="infer">0</strong></div>
      <div class="stat"><span>Frame</span><strong id="frameIndex">0</strong></div>
    </div>
    <div id="status" class="status">idle</div>
  </aside>
  <main>
    <header>
      <div>
        <h1 id="activeProject">C. elegans - YOLO segmentation</h1>
        <div id="activeSource" class="status">camera:0</div>
      </div>
      <div id="resolution" class="status">0 x 0</div>
    </header>
    <section class="viewer">
      <img class="feed" src="/video_feed" alt="live microscope feed">
    </section>
  </main>
  <script>
    const controls = {
      project: document.getElementById('project'),
      sourceType: document.getElementById('sourceType'),
      cameraIndex: document.getElementById('cameraIndex'),
      videoPath: document.getElementById('videoPath'),
      weights: document.getElementById('weights'),
      conf: document.getElementById('conf'),
      imgsz: document.getElementById('imgsz'),
      device: document.getElementById('device'),
      processEvery: document.getElementById('processEvery')
    };
    let projects = {};

    async function loadProjects() {
      projects = await fetch('/api/projects').then(r => r.json());
      controls.project.innerHTML = '';
      for (const [key, preset] of Object.entries(projects)) {
        const option = document.createElement('option');
        option.value = key;
        option.textContent = preset.label;
        controls.project.appendChild(option);
      }
    }

    async function loadCameras() {
      const cameras = await fetch('/api/cameras').then(r => r.json());
      controls.cameraIndex.innerHTML = '';
      if (!cameras.length) {
        const option = document.createElement('option');
        option.value = 0;
        option.textContent = 'Camera 0';
        controls.cameraIndex.appendChild(option);
        return;
      }
      for (const camera of cameras) {
        const option = document.createElement('option');
        option.value = camera.index;
        option.textContent = `${camera.label} (${camera.width}x${camera.height})`;
        controls.cameraIndex.appendChild(option);
      }
    }

    async function loadState() {
      const state = await fetch('/api/state').then(r => r.json());
      fillControls(state.config);
      renderStats(state.stats);
    }

    function fillControls(config) {
      controls.project.value = config.project;
      controls.sourceType.value = config.source_type;
      controls.cameraIndex.value = config.camera_index;
      controls.videoPath.value = config.video_path;
      controls.weights.value = config.weights;
      controls.conf.value = config.conf;
      controls.imgsz.value = config.imgsz;
      controls.device.value = config.device;
      controls.processEvery.value = config.process_every_n;
    }

    function collectConfig() {
      return {
        project: controls.project.value,
        source_type: controls.sourceType.value,
        camera_index: Number(controls.cameraIndex.value),
        video_path: controls.videoPath.value,
        weights: controls.weights.value,
        conf: Number(controls.conf.value),
        imgsz: Number(controls.imgsz.value),
        device: controls.device.value,
        process_every_n: Number(controls.processEvery.value)
      };
    }

    async function applyConfig() {
      const response = await fetch('/api/config', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(collectConfig())
      });
      const state = await response.json();
      renderStats(state.stats);
    }

    function renderStats(stats) {
      document.getElementById('wormCount').textContent = stats.worm_count;
      document.getElementById('fps').textContent = stats.fps;
      document.getElementById('infer').textContent = `${stats.inference_ms} ms`;
      document.getElementById('frameIndex').textContent = stats.frame_index;
      document.getElementById('status').textContent = stats.error || stats.status;
      document.getElementById('status').className = stats.error ? 'status error' : 'status';
      document.getElementById('activeProject').textContent =
        projects[stats.project]?.label || stats.project;
      document.getElementById('activeSource').textContent = stats.source;
      document.getElementById('resolution').textContent = `${stats.width} x ${stats.height}`;
    }

    controls.project.addEventListener('change', async () => {
      const preset = projects[controls.project.value];
      if (preset) {
        controls.weights.value = preset.weights;
        controls.conf.value = preset.conf;
        controls.imgsz.value = preset.imgsz;
      }
      await applyConfig();
    });
    for (const el of Object.values(controls)) {
      if (el.id !== 'project') el.addEventListener('change', applyConfig);
    }
    document.getElementById('start').addEventListener('click', async () => {
      await applyConfig();
      const stats = await fetch('/api/start', {method: 'POST'}).then(r => r.json());
      renderStats(stats);
    });
    document.getElementById('stop').addEventListener('click', async () => {
      const stats = await fetch('/api/stop', {method: 'POST'}).then(r => r.json());
      renderStats(stats);
    });

    async function boot() {
      await loadProjects();
      await loadCameras();
      await loadState();
      setInterval(async () => {
        const state = await fetch('/api/state').then(r => r.json());
        renderStats(state.stats);
      }, 500);
    }
    boot();
  </script>
</body>
</html>
"""


if __name__ == "__main__":
    raise SystemExit(main())
