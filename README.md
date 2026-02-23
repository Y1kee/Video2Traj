# video2traj

[English](#english) | [中文](#中文)

---

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
pip install -r requirements.txt
```

### 🚀 Quick Start

**Try with Example Video**

```bash
uv run python video2traj.py examples/example_in.mp4 -o examples/example_out.jpg
```

**Uniform Sampling (Default)**

```bash
uv run python video2traj.py examples/example_in.mp4 -o examples/example_out.jpg --num-frames 30
```

**Manual Frame Selection**

```bash
uv run python video2traj.py examples/example_in.mp4 -o examples/example_out.jpg --manual "30,60,90,120"
```

**Interactive Mode in Video Player**

```bash
uv run python video2traj.py examples/example_in.mp4 -o examples/example_out.jpg --interactive
```

Interactive Controls:

- `SPACE` - Play/Pause
- `S` - Mark current frame
- `D` - Undo last mark
- `←/→` - Step one frame
- Drag trackbar - Seek to frame
- `P` - Open/close preview of selected frames
- `ESC/Q` - Confirm and exit

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

**Full Example**

```bash
python video2traj.py input.mp4 -o output.jpg \
  --num-frames 50 \
  --diff-threshold 30 \
  --soft-edge 11 \
  --alpha-start 0.2 \
  --alpha-end 1.0
```

### 📄 Output

- `output.jpg` - Stroboscopic trajectory image
- `output.json` - Trajectory data with per-frame information:
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

### 🎓 Credits

This project was inspired by [videoStrobe](https://github.com/demolen/videoStrobe) by demolen. We extend our gratitude for the original concept and implementation.

### 📝 License

MIT License - feel free to use this in your research and projects!

### 🧪 Testing

Run the test suite to verify installation:

```bash
# Run all tests
python tests/run_all_tests.py

# Run specific test
python tests/test_synthetic.py
python tests/test_regression.py
```

See [tests/README.md](tests/README.md) for detailed testing documentation.

### 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## 📹 视频轨迹图生成器

**面向机器人研究者**：一个专门用于从实验视频中可视化机器人轨迹的工具，用于论文和演示。

### ⚠️ 重要限制

本工具箱专为**固定机位、静态背景**场景设计。目前**无法**处理：

- 移动/动态背景
- 移动相机或手持拍摄
- 明显的相机抖动或漂移

为获得最佳效果，请使用在受控环境中用固定相机录制的视频。

### ✨ 特性

- **🎯 多种帧选择模式**
  - 可配置间隔的均匀采样
  - 手动指定帧序号
  - 带实时预览的交互式 GUI
- **🎨 高质量渲染**
  - 逐帧 Alpha 合成实现自然混合
  - 形态学细化获得干净掩模
  - LAB 色彩空间 + 梯度分割
  - 支持软边缘实现更平滑阴影
- **📊 轨迹数据导出**
  - JSON 输出包含每帧的质心、边界框和面积
  - 可直接用于下游分析和绘图

### 📦 安装

```bash
# 克隆仓库
git clone https://github.com/yourusername/video2traj.git
cd video2traj

# 安装依赖
pip install -r requirements.txt
```

### 🚀 快速开始

**使用示例视频试用**

```bash
uv run python video2traj.py examples/example_in.mp4 -o examples/example_out.jpg
```

**均匀采样（默认）**

```bash
uv run python video2traj.py examples/example_in.mp4 -o examples/example_out.jpg --num-frames 30
```

**手动选帧**

```bash
uv run python video2traj.py examples/example_in.mp4 -o examples/example_out.jpg --manual "30,60,90,120"
```

**播放器交互模式**

```bash
uv run python video2traj.py examples/example_in.mp4 -o examples/example_out.jpg --interactive
```

交互操控键：

- `空格` - 播放/暂停
- `S` - 标记当前帧
- `D` - 撤销最近标记
- `←/→` - 单帧步进
- 拖动进度条 - 跳转到指定帧
- `P` - 打开/关闭已选帧预览
- `ESC/Q` - 确认退出

### ⚙️ 高级参数

**帧选择**

```bash
--num-frames 50                 # 采样帧数
--start-frame 100               # 从第 100 帧开始
--end-frame 500                 # 在第 500 帧结束
```

**背景提取**

```bash
--num-samples 10                # 背景采样帧数
```

**Alpha 混合**

```bash
--alpha-start 0.3               # 最早阴影不透明度 (0-1)
--alpha-end 1.0                 # 最新阴影不透明度 (0-1)
```

**分割**

```bash
--diff-threshold 20             # LAB 差分阈值 (0=自动 OTSU)
--no-gradient                   # 禁用梯度辅助分割
--grad-threshold 15             # 梯度差分阈值
```

**掩模细化**

```bash
--blur-size 5                   # 高斯模糊核大小（必须是奇数）
--close-kernel-size 21          # 形态学闭运算核大小
--open-kernel-size 5            # 形态学开运算核大小
--min-motion-area 100           # 最小掩模面积（像素）
--soft-edge 9                   # 软边缘核大小（必须是奇数，0=禁用）
```

**完整示例**

```bash
python video2traj.py input.mp4 -o output.jpg \
  --num-frames 50 \
  --diff-threshold 30 \
  --soft-edge 11 \
  --alpha-start 0.2 \
  --alpha-end 1.0
```

### 📄 输出

- `output.jpg` - 频闪轨迹图像
- `output.json` - 轨迹数据，包含每帧信息：
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

### 🎓 致谢

本项目受 demolen 的 [videoStrobe](https://github.com/demolen/videoStrobe) 启发。我们对原始概念和实现表示感谢。

### 📝 许可证

MIT 许可证 - 欢迎在您的研究和项目中使用！

### 🧪 测试

运行测试套件以验证安装：

```bash
# 运行所有测试
python tests/run_all_tests.py

# 运行特定测试
python tests/test_synthetic.py
python tests/test_regression.py
```

详细测试文档见 [tests/README.md](tests/README.md)。

### 🤝 贡献

欢迎贡献！请随时提交 Pull Request。