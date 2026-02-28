

# Video2Traj

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
uv pip install -r requirements.txt
```

### 🚀 快速开始

**单视频模式**（使用 `--input` 与 `--output`）：

**使用示例视频试用**

```bash
uv run python video2traj.py --input examples/example_1.mp4 -o examples/example_single.jpg
```

![示例输出](examples/example_single.jpg)

*数据来源：[My Paper on IEEE Trans. Robot. (T-RO)](https://ieeexplore.ieee.org/document/11300826/)*

**均匀采样（默认）**

```bash
uv run python video2traj.py --input examples/example_1.mp4 -o examples/example_single.jpg --num-frames 30
```

**手动选帧**

```bash
uv run python video2traj.py --input examples/example_1.mp4 -o examples/example_single.jpg --manual "30,60,90,120"
```

**播放器交互模式**

```bash
uv run python video2traj.py --input examples/example_1.mp4 -o examples/example_single.jpg --interactive
```

交互操控键：

- `空格` - 播放/暂停
- `S` - 标记当前帧
- `D` - 撤销最近标记
- `←/→` - 单帧步进
- 拖动进度条 - 跳转到指定帧
- `P` - 打开/关闭已选帧预览
- `ESC/Q` - 确认退出

**多视频模式**（将多个视频的轨迹合并到一张图，需使用配置文件）：

**使用示例运行**（使用 `examples/example_1.mp4` 与 `examples/example_2.mp4`，输出为 `examples/example_multi.jpg`）：

```bash
uv run python video2traj.py --config config_template.yaml
```

![多视频示例输出](examples/example_multi.jpg)

若使用自己的视频，请复制模板并编辑路径与参数：

```bash
# 1. 复制模板并编辑视频路径与参数
cp config_template.yaml my_config.yaml

# 2. 使用配置文件运行
uv run python video2traj.py --config my_config.yaml
```

配置文件格式（YAML 或 JSON）：在 `videos` 下列出各视频，每项包含 `path`、`mode`（`manual` / `uniform` / `interactive`）及对应字段（`frames`、`num_frames`、`start_frame`、`end_frame`）。共用选项放在 `defaults`。输出路径在 `output.image` 与 `output.trajectory_json`。完整示例见 [config_template.yaml](config_template.yaml)。


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
--grad-threshold 15             # 梯度差分阈值
--gradient-region 0.02          # 颜色 mask 膨胀比例，梯度仅在此邻域内生效
```

**掩模细化**

```bash
--blur-size 5                   # 高斯模糊核大小（必须是奇数）
--close-kernel-size 21          # 形态学闭运算核大小
--open-kernel-size 5            # 形态学开运算核大小
--min-motion-area 100           # 最小掩模面积（像素）
--soft-edge 9                   # 软边缘核大小（必须是奇数，0=禁用）
```

**完整示例（单视频）**

```bash
uv run python video2traj.py --input input.mp4 -o output.jpg \
  --num-frames 50 \
  --diff-threshold 30 \
  --soft-edge 11 \
  --alpha-start 0.2 \
  --alpha-end 1.0
```

### 📄 输出

**单视频模式**

- `output.jpg` - 频闪轨迹图像
- `output.json` - 轨迹数据（每帧一条的数组）：
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

**多视频模式**（使用 `--config` 时）

- 图像路径由配置中 `output.image` 指定（如 `result.png`）
- JSON 路径由 `output.trajectory_json` 指定（如 `result.json`），结构：
  ```json
  {
    "videos": [
      { "video": "video1.mp4", "trajectory": [ { "frame": 10, "cx": 100, "cy": 80, "bbox": [...], "area": 1200 } ] },
      { "video": "video2.mp4", "trajectory": [ ... ] }
    ]
  }
  ```

### 🎓 致谢

本项目受 demolen 的 [videoStrobe](https://github.com/demolen/videoStrobe) 启发。我们对原始概念和实现表示感谢。

### 📝 许可证

MIT 许可证 - 欢迎在您的研究和项目中使用！

### 🧪 测试

在项目目录下用 uv 运行测试套件以验证安装：

```bash
# 运行所有测试（单视频、回归、多视频）
uv run python tests/run_all_tests.py

# 运行特定测试
uv run python tests/test_synthetic.py
uv run python tests/test_regression.py
uv run python tests/test_multi_video.py
```

详细测试文档见 [tests/README.md](tests/README.md)。

### 🤝 贡献

欢迎贡献！请随时提交 Pull Request。