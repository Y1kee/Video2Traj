<div align="right">
  <a href="README.md"><img src="https://img.shields.io/badge/Language-English-blue.svg" alt="English"></a>
  <a href="README_zh.md"><img src="https://img.shields.io/badge/语言-简体中文-red.svg" alt="简体中文"></a>
</div>

# Video2Traj

## 📹 Video to Trajectory Figure Generator

**For Robotics Researchers**: A specialized tool to visualize robot trajectories from experimental videos for papers and presentations.

### ⚠️ Important Limitations

This toolbox is designed for **static backgrounds with fixed camera positions**. It currently does **not** handle:

- Moving/dynamic backgrounds
- Moving camera or handheld footage
- Significant camera shake or drift

For best results, use videos recorded with a stationary camera in a controlled environment.

### ✨ Features

- **🎯 Multiple Frame Selection Modes**
  - Uniform sampling with configurable intervals
  - Manual frame specification
  - Interactive GUI with real-time preview
- **🎨 High-Quality Rendering**
  - Per-frame alpha compositing for natural blending
  - Morphological refinement for clean masks
  - LAB color space + gradient-based segmentation
  - Soft edge support for smoother shadows
- **📊 Trajectory Data Export**
  - JSON output with centroid, bounding box, and area per frame
  - Ready for downstream analysis and plotting

### 📦 Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/video2traj.git
cd video2traj

# Install dependencies
uv pip install -r requirements.txt
```

### 🚀 Quick Start

**Single-video mode** (use `--input` and `--output`):

**Try with Example Video**

```bash
uv run python video2traj.py --input examples/example_in.mp4 -o examples/example_out.jpg
```

![Example output](examples/example_single.jpg)

*Source: [My Paper on IEEE Trans. Robot. (T-RO)](https://ieeexplore.ieee.org/document/11300826/)*

**Uniform Sampling (Default)**

```bash
uv run python video2traj.py --input examples/example_in.mp4 -o examples/example_out.jpg --num-frames 30
```

**Manual Frame Selection**

```bash
uv run python video2traj.py --input examples/example_in.mp4 -o examples/example_out.jpg --manual "30,60,90,120"
```

**Interactive Mode in Video Player**

```bash
uv run python video2traj.py --input examples/example_in.mp4 -o examples/example_out.jpg --interactive
```

Interactive Controls:

- `SPACE` - Play/Pause
- `S` - Mark current frame
- `D` - Undo last mark
- `←/→` - Step one frame
- Drag trackbar - Seek to frame
- `P` - Open/close preview of selected frames
- `ESC/Q` - Confirm and exit

**Multi-video mode** (merge trajectories from multiple videos onto one image; requires a config file):

**Try with Example** (uses `examples/example_1.mp4` and `examples/example_2.mp4`; output: `examples/example_multi.jpg`):

```bash
uv run python video2traj.py --config config_template.yaml
```

![Multi-video example output](examples/example_multi.jpg)

To use your own videos, copy the template and edit paths/parameters:

```bash
# 1. Copy the template and edit paths/parameters
cp config_template.yaml my_config.yaml

# 2. Run with config
uv run python video2traj.py --config my_config.yaml
```

Config format (YAML or JSON): list videos under `videos` with `path`, `mode` (`manual` / `uniform` / `interactive`), and mode-specific fields (`frames`, `num_frames`, `start_frame`, `end_frame`). Use `defaults` for shared options. Output paths go under `output.image` and `output.trajectory_json`. See [config_template.yaml](config_template.yaml) for a full example.


### ⚙️ Advanced Parameters

**Frame Selection**

```bash
--num-frames 50                 # Number of frames to sample
--start-frame 100               # Start from frame 100
--end-frame 500                 # End at frame 500
```

**Background Extraction**

```bash
--num-samples 10                # Background sampling frames
```

**Alpha Blending**

```bash
--alpha-start 0.3               # Earliest shadow opacity (0-1)
--alpha-end 1.0                 # Latest shadow opacity (0-1)
```

**Segmentation**

```bash
--diff-threshold 20             # LAB difference threshold (0=auto OTSU)
--no-gradient                   # Disable gradient-based segmentation
--grad-threshold 15             # Gradient difference threshold
```

**Mask Refinement**

```bash
--blur-size 5                   # Gaussian blur kernel (must be odd)
--close-kernel-size 21          # Morphological closing kernel
--open-kernel-size 5            # Morphological opening kernel
--min-motion-area 100           # Minimum mask area (pixels)
--soft-edge 9                   # Soft edge kernel (must be odd, 0=disabled)
```

**Full Example (single video)**

```bash
uv run python video2traj.py --input input.mp4 -o output.jpg \
  --num-frames 50 \
  --diff-threshold 30 \
  --soft-edge 11 \
  --alpha-start 0.2 \
  --alpha-end 1.0
```

### 📄 Output

**Single-video mode**

- `output.jpg` - Stroboscopic trajectory image
- `output.json` - Trajectory data (array of per-frame entries):
  ```json
  [
    {
      "frame": 30,
      "cx": 512.34,
      "cy": 384.67,
      "bbox": [450, 320, 120, 80],
      "area": 8456.2
    }
  ]
  ```

**Multi-video mode** (when using `--config`)

- Image path from `output.image` in config (e.g. `result.png`)
- JSON path from `output.trajectory_json` (e.g. `result.json`), structure:
  ```json
  {
    "videos": [
      { "video": "video1.mp4", "trajectory": [ { "frame": 10, "cx": 100, "cy": 80, "bbox": [...], "area": 1200 } ] },
      { "video": "video2.mp4", "trajectory": [ ... ] }
    ]
  }
  ```

### 🎓 Credits

This project was inspired by [videoStrobe](https://github.com/demolen/videoStrobe) by demolen. We extend our gratitude for the original concept and implementation.

### 📝 License

MIT License - feel free to use this in your research and projects!

### 🧪 Testing

Run the test suite to verify installation (with uv in project directory):

```bash
# Run all tests (single-video, regression, multi-video)
uv run python tests/run_all_tests.py

# Run specific test
uv run python tests/test_synthetic.py
uv run python tests/test_regression.py
uv run python tests/test_multi_video.py
```

See [tests/README.md](tests/README.md) for detailed testing documentation.

### 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
