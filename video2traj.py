import cv2
import numpy as np
import math
from typing import List, Tuple, Optional, Dict, Any
from tqdm import tqdm
from screeninfo import get_monitors

# ==========================================
# Shared Utilities | 公共工具
# ==========================================

def _open_video(path: str) -> cv2.VideoCapture:
    """Open video with auto-orientation so portrait videos display correctly. | 打开视频并自动旋转使竖屏视频正确显示。"""
    cap = cv2.VideoCapture(path)
    if cap.isOpened() and hasattr(cv2, "CAP_PROP_ORIENTATION_AUTO"):
        cap.set(cv2.CAP_PROP_ORIENTATION_AUTO, 1)
    return cap


def _get_primary_display_bounds() -> Optional[Tuple[int, int, int, int]]:
    """Return (x, y, width, height) of the primary monitor, or None on failure. | 返回主显示器的 (x, y, width, height)，失败则返回 None。"""
    try:
        monitors = get_monitors()
        if not monitors:
            return None
        for m in monitors:
            if getattr(m, "is_primary", False):
                return (m.x, m.y, m.width, m.height)
        m = monitors[0]
        return (m.x, m.y, m.width, m.height)
    except Exception:
        return None


def _get_display_max_size() -> Tuple[int, int]:
    """Return (max_w, max_h) for window sizing: primary monitor * 0.8 to leave margin (e.g. taskbar). | 返回窗口尺寸 (max_w, max_h)：主显示器 * 0.8 以留出边距（如任务栏）。"""
    SCALE = 0.8
    MIN_W, MIN_H = 800, 600
    FALLBACK_W, FALLBACK_H = 1600, 900
    bounds = _get_primary_display_bounds()
    if bounds is not None:
        _x, _y, w, h = bounds
        max_w = max(MIN_W, int(w * SCALE))
        max_h = max(MIN_H, int(h * SCALE))
        return (max_w, max_h)
    try:
        import tkinter as _tk
        root = _tk.Tk()
        root.withdraw()
        w = root.winfo_screenwidth()
        h = root.winfo_screenheight()
        root.destroy()
        if w > 0 and h > 0:
            return (max(MIN_W, int(w * SCALE)), max(MIN_H, int(h * SCALE)))
    except Exception:
        pass
    return (FALLBACK_W, FALLBACK_H)


# ==========================================
# Module 1: Frame Selector | 关键帧选择器
# ==========================================

def auto_select_frames(
    total_frames: int, 
    start_frame: int = 0, 
    end_frame: Optional[int] = None, 
    num_samples: int = 30
) -> List[int]:
    """Generates a list of frame indices by uniformly sampling a fixed number of frames. | 按采样数目在范围内均匀选取关键帧序号。

    Args:
        total_frames (int): The total number of frames in the video. | 视频的总帧数。
        start_frame (int, optional): The starting frame index. Defaults to 0. | 起始帧序号，默认为 0。
        end_frame (Optional[int], optional): The ending frame index. If None, defaults to total_frames. | 结束帧序号。如果为 None，则默认为总帧数。
        num_samples (int, optional): Number of frames to sample, uniformly distributed in [start, end). Defaults to 10. | 采样帧数，在 [start, end) 内均匀选取，默认为 10。

    Returns:
        List[int]: A strictly ascending, deduplicated list of selected frame indices. | 严格递增且去重的所选关键帧序号列表。
    """
    if end_frame is None:
        end_frame = total_frames
    end_frame = min(end_frame, total_frames)
    if num_samples <= 0:
        raise ValueError(f"num_samples must be positive, got {num_samples}")
    n = min(num_samples, end_frame - start_frame)
    if n <= 0:
        return []
    if n == 1:
        return [start_frame]
    step = (end_frame - start_frame - 1) / (n - 1)
    return [start_frame + round(i * step) for i in range(n)]


def interactive_select_frames(video_path: str) -> List[int]:
    """Provides a lightweight OpenCV GUI to manually select frames. | 提供轻量级 OpenCV GUI 手动选帧。

    Controls | 操控:
        Space   = play / pause | 播放/暂停
        S       = mark current frame | 标记当前帧
        D       = undo last mark | 撤销最近标记
        Left/Right = step one frame | 单帧步进
        ESC / Q = confirm & exit | 确认退出

    Args:
        video_path (str): Path to the input video file. | 输入视频文件路径。

    Returns:
        List[int]: Strictly ascending, deduplicated list of selected frame indices. | 严格递增去重的选帧列表。
    """
    cap = _open_video(video_path)
    if not cap.isOpened():
        print(f"[ERROR] Cannot open video: {video_path}")
        return []

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    import time as _time
    import sys as _sys

    # Windows: Set DPI awareness to prevent system scaling of OpenCV windows | Windows: 声明 DPI 感知，避免 OpenCV 窗口被系统缩放放大
    if _sys.platform == "win32":
        try:
            import ctypes
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except Exception:
                try:
                    ctypes.windll.shcore.SetProcessDpiAwareness(1)
                except Exception:
                    ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

    selected: List[int] = []
    current_pos = 0
    playing = False
    need_seek = False
    last_seek_done = 0.0
    SEEK_THROTTLE_S = 0.03  # Throttle seeks to once per 30ms when dragging to balance responsiveness and decode performance | 拖动时每 30ms 最多 seek 一次，既跟手又不拖垮解码
    WINDOW = "video2traj - Interactive Frame Selector"
    cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)

    ret, frame = cap.read()
    if not ret:
        print("[ERROR] Cannot read first frame.")
        cap.release()
        cv2.destroyAllWindows()
        return []

    frame_h, frame_w = frame.shape[:2]
    primary_bounds = _get_primary_display_bounds()
    MAX_WIN_W, MAX_WIN_H = _get_display_max_size()
    disp_scale = min(MAX_WIN_W / frame_w, MAX_WIN_H / frame_h, 0.7)
    disp_w = int(frame_w * disp_scale)
    disp_h = int(frame_h * disp_scale)
    print(f"Display size: {disp_w}x{disp_h}")
    print(f"Frame size: {frame_w}x{frame_h}")
    print(f"Scale: {disp_scale}")

    # Must resize before createTrackbar, otherwise trackbar will force expand window width | 必须在 createTrackbar 之前 resize，否则 trackbar 会强行扩展窗口宽度
    TRACKBAR_ROW_H = 45
    cv2.resizeWindow(WINDOW, disp_w, disp_h + TRACKBAR_ROW_H)

    def _on_trackbar(val: int) -> None:
        nonlocal current_pos, need_seek
        if val != current_pos:
            current_pos = val
            need_seek = True

    cv2.createTrackbar("Frame", WINDOW, 0, max(total_frames - 1, 0), _on_trackbar)

    # Preview overlay related | 叠加预览相关
    selected_frame_cache: List[np.ndarray] = []
    PREVIEW_W = 200
    PREVIEW_H = int(PREVIEW_W * frame_h / frame_w)
    preview_dirty = True
    preview_composite: Optional[np.ndarray] = None
    show_preview = True

    hud_font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = max(disp_w / 1280.0, 0.5)
    thickness = max(int(font_scale * 2), 1)
    line_h = int(40 * font_scale)
    TIMELINE_H = int(40 * font_scale)
    first_show = True

    while True:
        if cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:
            break

        if need_seek and not playing:
            now = _time.monotonic()
            if now - last_seek_done >= SEEK_THROTTLE_S:
                cap.set(cv2.CAP_PROP_POS_FRAMES, current_pos)
                ret, f = cap.read()
                if ret:
                    frame = f
                last_seek_done = now
                need_seek = False

        # --- Resize to display size, then draw HUD on it | 调整到显示尺寸，然后绘制 HUD ---
        disp = cv2.resize(frame, (disp_w, disp_h), interpolation=cv2.INTER_AREA)
        h, w = disp.shape[:2]

        marked_str = "  [MARKED]" if current_pos in selected else ""
        status_str = "PLAYING" if playing else "PAUSED"
        fs = font_scale * 0.8
        hud_lines = [
            f"Frame: {current_pos}/{total_frames - 1}  |  FPS: {fps:.1f}  |  Selected: {len(selected)}",
            f"Status: {status_str}{marked_str}",
            "",
            "[SPACE] Play/Pause    [S] Mark Frame    [P] Toggle Preview",
            "[D] Undo Last Mark    [Left/Right] Step 1 Frame",
            "[ESC/Q] Confirm & Exit",
        ]

        pad = int(10 * font_scale)
        box_h = len(hud_lines) * line_h + pad * 2
        max_text_w = max(cv2.getTextSize(l, hud_font, fs, thickness)[0][0] for l in hud_lines if l)
        box_w = max_text_w + pad * 2

        overlay = disp.copy()
        cv2.rectangle(overlay, (0, 0), (box_w, box_h), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, disp, 0.4, 0, disp)

        for i, line_text in enumerate(hud_lines):
            if not line_text:
                continue
            y = pad + (i + 1) * line_h
            if i == 0:
                color = (0, 255, 0)
            elif i == 1:
                color = (0, 255, 255)
            else:
                color = (220, 220, 220)
            if "[MARKED]" in line_text:
                base = line_text.replace("  [MARKED]", "")
                cv2.putText(disp, base, (pad, y), hud_font, fs, (0, 255, 255), thickness)
                base_w = cv2.getTextSize(base, hud_font, fs, thickness)[0][0]
                cv2.putText(disp, "  [MARKED]", (pad + base_w, y), hud_font, fs, (0, 0, 255), thickness)
            else:
                cv2.putText(disp, line_text, (pad, y), hud_font, fs, color, thickness)

        # --- Rebuild preview composite if selection changed | 如果选择变化则重建预览合成 ---
        if preview_dirty:
            if selected_frame_cache:
                n = len(selected_frame_cache)
                if n == 1:
                    preview_composite = selected_frame_cache[0].copy()
                else:
                    comp = selected_frame_cache[0].astype(np.float32)
                    for i in range(1, n):
                        a = 0.3 + 0.7 * (i / (n - 1))
                        comp = comp * (1.0 - a) + selected_frame_cache[i].astype(np.float32) * a
                    preview_composite = np.clip(comp, 0, 255).astype(np.uint8)
            else:
                preview_composite = None
            preview_dirty = False

        # --- Mini timeline | 迷你时间线 ---
        bar_y = h - TIMELINE_H
        cv2.rectangle(disp, (0, bar_y), (w, h), (40, 40, 40), -1)
        if total_frames > 1:
            cx = int(current_pos / (total_frames - 1) * (w - 1))
            cv2.line(disp, (cx, bar_y), (cx, h), (255, 255, 255), 2)
            for sf in selected:
                sx = int(sf / (total_frames - 1) * (w - 1))
                cv2.line(disp, (sx, bar_y), (sx, h), (0, 255, 0), 2)

        # --- Preview overlay (bottom-right, above timeline, semi-transparent) | 预览叠加层（右下角，时间线上方，半透明） ---
        if show_preview and preview_composite is not None:
            ph, pw = preview_composite.shape[:2]
            margin = 8
            x1 = w - pw - margin
            y1 = bar_y - ph - margin
            if x1 >= 0 and y1 >= 0:
                roi = disp[y1:y1 + ph, x1:x1 + pw]
                cv2.addWeighted(preview_composite, 0.75, roi, 0.25, 0, roi)
                cv2.rectangle(disp, (x1 - 2, y1 - 2), (x1 + pw + 1, y1 + ph + 1), (255, 255, 255), 1)
                label = f"Preview [{len(selected_frame_cache)}]"
                cv2.putText(disp, label, (x1, y1 - 6), hud_font, fs * 0.8, (255, 255, 255), 1)

        cv2.imshow(WINDOW, disp)
        if first_show:
            first_show = False
            if primary_bounds is not None:
                px, py, pw, ph = primary_bounds
                win_x = px + max(0, (pw - disp_w) // 2)
                win_y = py + max(0, (ph - disp_h - TRACKBAR_ROW_H) // 2)
                cv2.moveWindow(WINDOW, win_x, win_y)
        cv2.setTrackbarPos("Frame", WINDOW, current_pos)

        if need_seek:
            delay = 1
        elif playing:
            delay = max(1, int(1000 / fps))
        else:
            delay = 30
        key = cv2.waitKeyEx(delay)

        # Key handling (waitKeyEx returns extended codes for arrow keys) | 按键处理（waitKeyEx 返回方向键的扩展代码）
        if key == 27 or key == ord('q') or key == ord('Q'):
            break
        elif key == 32:  # Space | 空格键
            playing = not playing
        elif key == ord('s') or key == ord('S'):
            if current_pos not in selected:
                selected.append(current_pos)
                thumb = cv2.resize(frame, (PREVIEW_W, PREVIEW_H), interpolation=cv2.INTER_AREA)
                selected_frame_cache.append(thumb)
                preview_dirty = True
                print(f"  [+] Marked frame {current_pos} (total: {len(selected)})")
            else:
                print(f"  [=] Frame {current_pos} already marked")
        elif key == ord('d') or key == ord('D'):
            if selected:
                removed = selected.pop()
                selected_frame_cache.pop()
                preview_dirty = True
                print(f"  [-] Unmarked frame {removed} (total: {len(selected)})")
        elif key in (2424832, 65361):  # Left arrow (Win / Linux) | 左箭头（Win / Linux）
            playing = False
            current_pos = max(0, current_pos - 1)
            need_seek = True
        elif key in (2555904, 65363):  # Right arrow (Win / Linux) | 右箭头（Win / Linux）
            playing = False
            current_pos = min(total_frames - 1, current_pos + 1)
            need_seek = True
        elif key == ord('p') or key == ord('P'):
            show_preview = not show_preview

        if playing:
            ret, new_frame = cap.read()
            if ret:
                frame = new_frame
                current_pos += 1
                if current_pos >= total_frames:
                    current_pos = total_frames - 1
                    playing = False
            else:
                playing = False
            need_seek = False

    cap.release()
    cv2.destroyAllWindows()

    result = sorted(set(selected))
    print(f"Interactive selection complete: {len(result)} frames selected")
    return result


# ==========================================
# Module 2: Background Extractor | 背景提取器
# ==========================================

def extract_stable_background(
    video_path: str, 
    start_frame: int = 0, 
    end_frame: Optional[int] = None, 
    num_samples: int = 10
) -> Optional[np.ndarray]:
    """Extracts a stable, moving-object-free background using temporal median filtering. | 使用时域中值滤波提取稳定且无运动物体的背景底图。

    Uniformly samples a fixed number of frames across the specified range and computes
    the median pixel values to eliminate dynamic foreground objects. | 在指定范围内按采样数目均匀选取帧，计算像素中值以消除动态前景。

    Args:
        video_path (str): Path to the input video. | 输入视频路径。
        start_frame (int, optional): The frame to start sampling from. Defaults to 0. | 采样起始帧，默认为 0。
        end_frame (Optional[int], optional): The frame to stop sampling. Defaults to None. | 采样结束帧，默认为 None。
        num_samples (int, optional): Number of frames to sample for the median. Uniformly distributed in [start, end). Defaults to 10. | 参与中值计算的采样帧数，在 [start, end) 内均匀选取，默认为 10。

    Returns:
        Optional[np.ndarray]: A 3-channel BGR image representing the stable background, 
            or None if extraction fails. | 代表稳定背景的 3 通道 BGR 图像，如果提取失败则返回 None。
    """
    MAX_SAMPLES_FOR_BG = 500  # upper bound to avoid OOM | 上限以避免内存溢出

    if num_samples <= 0:
        return None
    n = min(num_samples, MAX_SAMPLES_FOR_BG)

    cap = _open_video(video_path)
    if not cap.isOpened():
        return None

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if end_frame is None:
        end_frame = total_frames
    end_frame = min(end_frame, total_frames)

    if end_frame <= start_frame:
        cap.release()
        return None

    # Uniformly pick n frame indices in [start_frame, end_frame) | 在 [start_frame, end_frame) 内均匀选取 n 个帧索引
    if n == 1:
        frame_indices = [start_frame]
    else:
        step = (end_frame - start_frame - 1) / (n - 1)
        frame_indices = [start_frame + round(i * step) for i in range(n)]

    frames = []
    for frame_idx in tqdm(frame_indices, desc="Sampling background", unit="frame"):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if ret:
            frames.append(frame)

    cap.release()

    if not frames:
        return None

    print(f"Computing median background from {len(frames)} sampled frames...")
    frames_array = np.array(frames)
    background = np.median(frames_array, axis=0).astype(np.uint8)
    return background


def extract_background_from_multiple_videos(
    video_paths: List[str],
    num_samples_per_video: int = 5
) -> Optional[np.ndarray]:
    """Extracts a unified clean background by sampling frames from multiple videos and taking the median. | 从多个视频采样帧并取中值得到统一干净背景。

    Each video is uniformly sampled for N frames; all samples are merged (capped at 500 frames
    to avoid OOM), then temporal median is computed to obtain a single background. |
    每个视频均匀采样 N 帧，合并后取中值（总帧数上限 500 以防 OOM）。

    Args:
        video_paths (List[str]): Paths to input videos. | 输入视频路径列表。
        num_samples_per_video (int, optional): Number of frames to sample per video for background. Defaults to 5. | 每个视频用于背景的采样帧数，默认 5。

    Returns:
        Optional[np.ndarray]: Unified BGR background image, or None if extraction fails. | 统一的 BGR 背景图，失败则返回 None。
    """
    MAX_TOTAL_SAMPLES = 500  # Upper bound to avoid OOM | 上限以避免内存溢出

    all_frame_indices: List[Tuple[str, List[int]]] = []
    for path in video_paths:
        cap = _open_video(path)
        if not cap.isOpened():
            print(f"[WARN] Cannot open video for background: {path}, skipping.")
            continue
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()
        if total <= 0:
            continue
        indices = auto_select_frames(total, 0, None, num_samples_per_video)
        all_frame_indices.append((path, indices))

    if not all_frame_indices:
        return None

    # Collect frames from all videos until cap | 从所有视频收集帧直至上限
    frames: List[np.ndarray] = []
    for path, indices in all_frame_indices:
        if len(frames) >= MAX_TOTAL_SAMPLES:
            break
        cap = _open_video(path)
        if not cap.isOpened():
            continue
        n_to_take = min(len(indices), MAX_TOTAL_SAMPLES - len(frames))
        for i in range(n_to_take):
            cap.set(cv2.CAP_PROP_POS_FRAMES, indices[i])
            ret, frame = cap.read()
            if ret:
                frames.append(frame)
        cap.release()

    if not frames:
        return None
    print(f"Computing median background from {len(frames)} sampled frames (multi-video)...")
    frames_array = np.array(frames)
    background = np.median(frames_array, axis=0).astype(np.uint8)
    return background


# ==========================================
# Module 3: Rendering Engine | 核心渲染引擎
# ==========================================

def refine_motion_mask(
    mask: np.ndarray, 
    min_area: int = 100, 
    blur_size: int = 5, 
    close_kernel_size: int = 21,
    open_kernel_size: int = 5
) -> np.ndarray:
    """Refines a raw binary motion mask using morphological operations. | 使用形态学操作优化原始二值运动掩模。

    Uses a large closing kernel to bridge gaps (e.g. body-wheel disconnect),
    then a small opening kernel to remove true noise. | 先用大核闭运算粘合断裂部分，再用小核开运算去除真实噪点。

    Args:
        mask (np.ndarray): The raw binary mask. | 原始二值掩模。
        min_area (int, optional): Minimum connected component area. Defaults to 100. | 最小连通域面积，默认为 100。
        blur_size (int, optional): Kernel size for Gaussian blur. Defaults to 5. | 高斯模糊核大小，默认为 5。
        close_kernel_size (int, optional): Kernel size for morphological closing. Defaults to 21. | 闭运算核大小，默认为 21。
        open_kernel_size (int, optional): Kernel size for morphological opening. Defaults to 5. | 开运算核大小，默认为 5。

    Returns:
        np.ndarray: The purified binary mask. | 净化后的二值掩模。
    """
    mask = cv2.GaussianBlur(mask, (blur_size, blur_size), 0)
    _, mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)

    close_k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (close_kernel_size, close_kernel_size))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, close_k)

    open_k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (open_kernel_size, open_kernel_size))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, open_k)

    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
    if num_labels > 1:
        areas = stats[:, cv2.CC_STAT_AREA]
        keep = np.zeros(num_labels, dtype=bool)
        keep[1:] = areas[1:] >= min_area
        mask = np.where(keep[labels], np.uint8(255), np.uint8(0))

    return mask


def render_trajectory(
    video_path: str, 
    bg_image: np.ndarray, 
    frame_indices: List[int], 
    alpha_start: float = 0.2, 
    alpha_end: float = 1.0,
    blur_size: int = 5,
    close_kernel_size: int = 21,
    open_kernel_size: int = 5,
    min_motion_area: int = 100,
    diff_threshold: int = 20,
    use_gradient: bool = True,
    grad_threshold: int = 15,
    soft_edge_size: int = 0
) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
    """Renders a stroboscopic trajectory image via per-frame alpha compositing. | 通过逐帧 Alpha 合成渲染残影轨迹图。

    Each keyframe is independently segmented and alpha-blended onto the running
    composite buffer, so overlapping regions blend naturally instead of hard
    overwriting. | 每帧独立分割并 Alpha 混合到累积缓冲上，重叠区域自然融合而非硬覆盖。

    Args:
        video_path (str): Path to the input video. | 输入视频路径。
        bg_image (np.ndarray): The clean background image. | 干净的背景底图。
        frame_indices (List[int]): A list of frame indices to be rendered. | 待渲染的关键帧序号列表。
        alpha_start (float, optional): Opacity of the earliest shadow. Defaults to 0.2. | 最早残影的不透明度，默认为 0.2。
        alpha_end (float, optional): Opacity of the latest shadow. Defaults to 1.0. | 最新残影的不透明度，默认为 1.0。
        blur_size (int, optional): Blur size for mask refinement. Defaults to 5. | 掩模模糊大小，默认为 5。
        close_kernel_size (int, optional): Kernel size for morphological closing. Defaults to 21. | 闭运算核大小，默认为 21。
        open_kernel_size (int, optional): Kernel size for morphological opening. Defaults to 5. | 开运算核大小，默认为 5。
        min_motion_area (int, optional): Minimum mask area. Defaults to 100. | 最小掩模面积，默认为 100。
        diff_threshold (int, optional): Fixed threshold for LAB diff. 0 = fallback to OTSU. Defaults to 20. | LAB 差分固定阈值，0 则回退 OTSU，默认为 20。
        use_gradient (bool, optional): Enable gradient-based diff as auxiliary mask. Defaults to True. | 启用梯度差分辅助路径，默认开启。
        grad_threshold (int, optional): Threshold for gradient diff. Defaults to 15. | 梯度差分阈值，默认为 15。
        soft_edge_size (int, optional): Gaussian blur kernel size for soft mask edges. 0 = disabled (binary mask). Defaults to 0. | 软边缘高斯核大小，0 为关闭，默认为 0。

    Returns:
        Tuple[np.ndarray, List[Dict]]: (trajectory_image, trajectory_data).
            trajectory_data contains per-frame centroid, bbox and area. |
            返回 (轨迹合成图, 轨迹数据列表)，轨迹数据包含每帧质心、边界框和面积。
    """
    # 1. Defensive data cleaning at M3 entry | 在 M3 入口进行防御性数据清洗
    sorted_indices = sorted(set(frame_indices))
    num_frames = len(sorted_indices)
    if num_frames == 0:
        return bg_image.copy(), []

    rank_map = {frame_idx: rank for rank, frame_idx in enumerate(sorted_indices)}
    
    # 2. Initialize composite buffer | 初始化合成缓冲
    height, width = bg_image.shape[:2]
    result = bg_image.astype(np.float32)
    trajectory_data: List[Dict[str, Any]] = []

    # Pre-compute background representations outside the frame loop | 在帧循环外预计算背景表示
    bg_lab = cv2.cvtColor(bg_image, cv2.COLOR_BGR2LAB)
    bg_gray: Optional[np.ndarray] = None
    bg_grad: Optional[np.ndarray] = None
    if use_gradient or diff_threshold == 0:
        bg_gray = cv2.cvtColor(bg_image, cv2.COLOR_BGR2GRAY)
    if use_gradient:
        bg_grad = cv2.magnitude(
            cv2.Sobel(bg_gray, cv2.CV_32F, 1, 0, ksize=3),
            cv2.Sobel(bg_gray, cv2.CV_32F, 0, 1, ksize=3))
    
    # 3. Read frames: seek for sparse keyframes, sequential for dense | 读取帧：稀疏关键帧用 seek，密集帧用顺序读取
    cap = _open_video(video_path)
    if not cap.isOpened():
        print(f"[ERROR] Cannot open video: {video_path}")
        return bg_image.copy(), []

    max_frame_needed = sorted_indices[-1]
    frame_span = max_frame_needed - sorted_indices[0] + 1
    use_seek = num_frames < frame_span * 0.3

    print(f"Rendering {num_frames} frames (range {sorted_indices[0]}..{max_frame_needed}), "
          f"strategy={'seek' if use_seek else 'sequential'}...")

    def _process_frame(frame: np.ndarray, frame_idx: int, rank: int) -> None:
        """Process a single keyframe: diff → mask → alpha composite → trajectory extract. | 处理单个关键帧：差分 → 掩模 → Alpha 合成 → 轨迹提取。"""
        # --- LAB color diff (primary path) | LAB 颜色差分（主路径） ---
        frame_lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        diff_lab = cv2.absdiff(frame_lab, bg_lab)
        diff_max = np.max(diff_lab, axis=2)

        if diff_threshold > 0:
            _, mask_color = cv2.threshold(diff_max, diff_threshold, 255, cv2.THRESH_BINARY)
        else:
            _, mask_color = cv2.threshold(diff_max, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        raw_mask = mask_color

        # --- Gradient diff (auxiliary path) | 梯度差分（辅助路径） ---
        if use_gradient:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            grad_frame = cv2.magnitude(
                cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3),
                cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3))
            diff_grad = np.abs(grad_frame - bg_grad)
            diff_grad_u8 = np.clip(diff_grad, 0, 255).astype(np.uint8)
            _, mask_grad = cv2.threshold(diff_grad_u8, grad_threshold, 255, cv2.THRESH_BINARY)
            raw_mask = cv2.bitwise_or(raw_mask, mask_grad)

        refined_mask = refine_motion_mask(raw_mask, min_motion_area, blur_size,
                                          close_kernel_size, open_kernel_size)

        # Per-frame alpha compositing | 逐帧 Alpha 合成
        alpha = alpha_start + (alpha_end - alpha_start) * (rank / max(num_frames - 1, 1))
        if soft_edge_size > 0:
            mask_f = cv2.GaussianBlur(refined_mask.astype(np.float32) / 255.0, (soft_edge_size, soft_edge_size), 0)
        else:
            mask_f = (refined_mask > 0).astype(np.float32)
        alpha_mask = (mask_f * alpha)[:, :, np.newaxis]
        frame_f = frame.astype(np.float32)
        result[:] = result * (1.0 - alpha_mask) + frame_f * alpha_mask

        # Extract trajectory (centroid + bbox) | 提取轨迹（质心 + 边界框）
        M = cv2.moments(refined_mask)
        if M["m00"] > 0:
            cx = M["m10"] / M["m00"]
            cy = M["m01"] / M["m00"]
            x, y, w, h = cv2.boundingRect(refined_mask)
            trajectory_data.append({
                "frame": frame_idx,
                "cx": round(cx, 2), "cy": round(cy, 2),
                "bbox": [int(x), int(y), int(w), int(h)],
                "area": round(M["m00"] / 255.0, 1),
            })

    if use_seek:
        for frame_idx in tqdm(sorted_indices, desc="Rendering (seek)", unit="frame"):
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret:
                print(f"[WARN] Failed to read frame {frame_idx}, skipping.")
                continue
            _process_frame(frame, frame_idx, rank_map[frame_idx])
    else:
        pbar = tqdm(total=num_frames, desc="Rendering (sequential)", unit="frame")
        current_frame_idx = 0
        consecutive_failures = 0
        MAX_CONSECUTIVE_FAILURES = 5
        while cap.isOpened() and current_frame_idx <= max_frame_needed:
            ret, frame = cap.read()
            if not ret:
                consecutive_failures += 1
                if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                    print(f"[WARN] {MAX_CONSECUTIVE_FAILURES} consecutive decode failures at frame {current_frame_idx}, stopping.")
                    break
                current_frame_idx += 1
                continue
            consecutive_failures = 0
            if current_frame_idx in rank_map:
                _process_frame(frame, current_frame_idx, rank_map[current_frame_idx])
                pbar.update(1)
            current_frame_idx += 1
        pbar.close()

    cap.release()

    return np.clip(result, 0, 255).astype(np.uint8), trajectory_data


def render_multi_video_trajectory(
    video_paths: List[str],
    bg_image: np.ndarray,
    frame_indices_per_video: List[List[int]],
    alpha_start: float = 0.2,
    alpha_end: float = 1.0,
    blur_size: int = 5,
    close_kernel_size: int = 21,
    open_kernel_size: int = 5,
    min_motion_area: int = 100,
    diff_threshold: int = 20,
    use_gradient: bool = True,
    grad_threshold: int = 15,
    soft_edge_size: int = 0,
) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
    """Renders trajectory from multiple videos onto a single canvas. | 将多个视频的轨迹渲染到同一画布。

    All frames are segmented against the unified background, then alpha-blended
    onto the accumulating canvas. Each video has independent alpha gradient. |
    所有帧都与统一背景做差分，然后 alpha 混合到累积画布。每个视频独立渐变。

    Args:
        video_paths (List[str]): Paths to input videos. | 输入视频路径列表。
        bg_image (np.ndarray): The unified clean background. | 统一的干净背景。
        frame_indices_per_video (List[List[int]]): Frame indices for each video. | 每个视频的帧索引列表。
        alpha_start (float, optional): Opacity of earliest shadow. Defaults to 0.2. | 最早残影的不透明度，默认 0.2。
        alpha_end (float, optional): Opacity of latest shadow. Defaults to 1.0. | 最新残影的不透明度，默认 1.0。
        blur_size (int, optional): Gaussian blur kernel size for mask. Defaults to 5. | 掩模高斯模糊核大小，默认 5。
        close_kernel_size (int, optional): Morphological closing kernel size. Defaults to 21. | 闭运算核大小，默认 21。
        open_kernel_size (int, optional): Morphological opening kernel size. Defaults to 5. | 开运算核大小，默认 5。
        min_motion_area (int, optional): Minimum motion mask area. Defaults to 100. | 最小运动掩模面积，默认 100。
        diff_threshold (int, optional): LAB diff threshold (0 = OTSU). Defaults to 20. | LAB 差分阈值，0 为 OTSU，默认 20。
        use_gradient (bool, optional): Use gradient-based diff. Defaults to True. | 是否使用梯度差分，默认 True。
        grad_threshold (int, optional): Gradient diff threshold. Defaults to 15. | 梯度差分阈值，默认 15。
        soft_edge_size (int, optional): Soft edge kernel size (0 = disabled). Defaults to 0. | 软边缘核大小，0 为关闭，默认 0。

    Returns:
        Tuple[np.ndarray, List[Dict[str, Any]]]: (canvas, grouped_trajectory_data).
            grouped_trajectory_data = [{"video": path, "trajectory": [...]}, ...] |
            返回 (画布, 分组轨迹数据)。轨迹数据按视频分组。
    """
    height, width = bg_image.shape[:2]
    canvas = bg_image.astype(np.float32)  # Initialize composite buffer | 初始化合成缓冲
    grouped_trajectory_data: List[Dict[str, Any]] = []

    # Pre-compute background representations | 预计算背景表示
    bg_lab = cv2.cvtColor(bg_image, cv2.COLOR_BGR2LAB)
    bg_gray: Optional[np.ndarray] = None
    bg_grad: Optional[np.ndarray] = None
    if use_gradient or diff_threshold == 0:
        bg_gray = cv2.cvtColor(bg_image, cv2.COLOR_BGR2GRAY)
    if use_gradient:
        bg_grad = cv2.magnitude(
            cv2.Sobel(bg_gray, cv2.CV_32F, 1, 0, ksize=3),
            cv2.Sobel(bg_gray, cv2.CV_32F, 0, 1, ksize=3))

    for v_idx, (video_path, frame_indices) in enumerate(zip(video_paths, frame_indices_per_video)):
        sorted_indices = sorted(set(frame_indices))
        num_frames = len(sorted_indices)
        if num_frames == 0:
            grouped_trajectory_data.append({"video": video_path, "trajectory": []})
            continue

        rank_map = {frame_idx: rank for rank, frame_idx in enumerate(sorted_indices)}
        video_trajectory: List[Dict[str, Any]] = []

        cap = _open_video(video_path)
        if not cap.isOpened():
            print(f"[ERROR] Cannot open video: {video_path}")
            grouped_trajectory_data.append({"video": video_path, "trajectory": []})
            continue

        max_frame_needed = sorted_indices[-1]
        frame_span = max_frame_needed - sorted_indices[0] + 1
        use_seek = num_frames < frame_span * 0.3
        print(f"Processing video {v_idx + 1}/{len(video_paths)}: {video_path} ({num_frames} frames, "
              f"strategy={'seek' if use_seek else 'sequential'})...")

        def _process_frame(frame: np.ndarray, frame_idx: int, rank: int) -> None:
            frame_lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
            diff_lab = cv2.absdiff(frame_lab, bg_lab)
            diff_max = np.max(diff_lab, axis=2)
            if diff_threshold > 0:
                _, mask_color = cv2.threshold(diff_max, diff_threshold, 255, cv2.THRESH_BINARY)
            else:
                _, mask_color = cv2.threshold(diff_max, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            raw_mask = mask_color
            if use_gradient and bg_gray is not None and bg_grad is not None:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                grad_frame = cv2.magnitude(
                    cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3),
                    cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3))
                diff_grad = np.abs(grad_frame - bg_grad)
                diff_grad_u8 = np.clip(diff_grad, 0, 255).astype(np.uint8)
                _, mask_grad = cv2.threshold(diff_grad_u8, grad_threshold, 255, cv2.THRESH_BINARY)
                raw_mask = cv2.bitwise_or(raw_mask, mask_grad)
            refined_mask = refine_motion_mask(
                raw_mask, min_motion_area, blur_size, close_kernel_size, open_kernel_size)
            # Per-video alpha gradient: first frame = alpha_start, last = alpha_end | 每视频独立 alpha 渐变
            alpha = alpha_start + (alpha_end - alpha_start) * (rank / max(num_frames - 1, 1))
            if soft_edge_size > 0:
                mask_f = cv2.GaussianBlur(
                    refined_mask.astype(np.float32) / 255.0,
                    (soft_edge_size, soft_edge_size), 0)
            else:
                mask_f = (refined_mask > 0).astype(np.float32)
            alpha_mask = (mask_f * alpha)[:, :, np.newaxis]
            frame_f = frame.astype(np.float32)
            canvas[:] = canvas * (1.0 - alpha_mask) + frame_f * alpha_mask
            M = cv2.moments(refined_mask)
            if M["m00"] > 0:
                cx = M["m10"] / M["m00"]
                cy = M["m01"] / M["m00"]
                x, y, w, h = cv2.boundingRect(refined_mask)
                video_trajectory.append({
                    "frame": frame_idx,
                    "cx": round(cx, 2), "cy": round(cy, 2),
                    "bbox": [int(x), int(y), int(w), int(h)],
                    "area": round(M["m00"] / 255.0, 1),
                })

        if use_seek:
            for frame_idx in tqdm(sorted_indices, desc="Rendering (seek)", unit="frame"):
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                if not ret:
                    continue
                _process_frame(frame, frame_idx, rank_map[frame_idx])
        else:
            pbar = tqdm(total=num_frames, desc="Rendering (sequential)", unit="frame")
            current_frame_idx = 0
            consecutive_failures = 0
            MAX_CONSECUTIVE_FAILURES = 5
            while cap.isOpened() and current_frame_idx <= max_frame_needed:
                ret, frame = cap.read()
                if not ret:
                    consecutive_failures += 1
                    if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                        break
                    current_frame_idx += 1
                    continue
                consecutive_failures = 0
                if current_frame_idx in rank_map:
                    _process_frame(frame, current_frame_idx, rank_map[current_frame_idx])
                    pbar.update(1)
                current_frame_idx += 1
            pbar.close()
        cap.release()
        grouped_trajectory_data.append({"video": video_path, "trajectory": video_trajectory})

    return np.clip(canvas, 0, 255).astype(np.uint8), grouped_trajectory_data


# ==========================================
# Entry Point | 程序入口
# ==========================================

if __name__ == "__main__":
    import argparse
    import json
    import os
    import sys

    def _load_yaml_or_json(config_path: str) -> Dict[str, Any]:
        """Loads configuration from YAML or JSON file. | 从 YAML 或 JSON 文件加载配置。"""
        with open(config_path, "r", encoding="utf-8") as f:
            raw = f.read()
        if config_path.lower().endswith(".json"):
            return json.loads(raw)
        if config_path.lower().endswith((".yaml", ".yml")):
            try:
                import yaml
            except ImportError:
                raise ImportError(
                    "YAML config requires PyYAML. Install with: uv pip install pyyaml"
                ) from None
            return yaml.safe_load(raw) or {}
        return json.loads(raw)

    def _validate_multi_video_config(config: Dict[str, Any], config_path: str) -> None:
        """Validates multi-video config: videos list, mode fields, required fields per mode, path existence. | 校验多视频配置。"""
        if "videos" not in config or not config["videos"]:
            raise ValueError("Config must contain non-empty 'videos' list. | 配置必须包含非空 'videos' 列表。")
        defaults = config.get("defaults", {})
        config_dir = os.path.dirname(os.path.abspath(config_path))
        for i, v in enumerate(config["videos"]):
            if "path" not in v:
                raise ValueError(f"videos[{i}] missing 'path'. | videos[{i}] 缺少 'path'。")
            path = v["path"]
            if not os.path.isabs(path):
                path = os.path.join(config_dir, path)
            if not os.path.isfile(path):
                raise ValueError(f"Video file not found: {v['path']} | 视频文件不存在: {v['path']}")
            mode = v.get("mode", defaults.get("mode", "uniform"))
            if mode == "manual":
                if "frames" not in v:
                    raise ValueError(f"{v['path']}: mode='manual' requires 'frames'. | 需要 'frames'。")
            elif mode == "uniform":
                if "num_frames" not in v and "num_frames" not in defaults:
                    raise ValueError(f"{v['path']}: mode='uniform' requires 'num_frames' (or in defaults). | 需要 num_frames。")
            elif mode != "interactive":
                raise ValueError(f"Unknown mode: {mode} | 未知模式: {mode}")

    parser = argparse.ArgumentParser(description="video2traj: Generate robots' trajectory figure from video.")
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--input", type=str,
                             help="Single video path (single-video mode).")
    input_group.add_argument("--config", type=str,
                             help="YAML/JSON config file for multi-video mode.")

    parser.add_argument("--output", "-o", type=str, default=None,
                        help="Output image path (required in single-video mode).")
    parser.add_argument("--trajectory-output", type=str, default=None,
                        help="Output trajectory JSON path. Default: <output>.json in single-video mode.")
    parser.add_argument("--num-frames", type=int, default=10,
                        help="Number of keyframes to sample uniformly (single-video only).")
    parser.add_argument("--start-frame", type=int, default=0,
                        help="Start frame index (single-video only).")
    parser.add_argument("--end-frame", type=int, default=None,
                        help="End frame index (None = all, single-video only).")
    parser.add_argument("--num-samples", type=int, default=5,
                        help="Number of frames to sample for median background (single-video only).")
    parser.add_argument("--alpha-start", type=float, default=0.2,
                        help="Opacity of earliest shadow.")
    parser.add_argument("--alpha-end", type=float, default=1.0,
                        help="Opacity of latest shadow.")
    parser.add_argument("--blur-size", type=int, default=5,
                        help="Gaussian blur kernel size (must be odd).")
    parser.add_argument("--close-kernel-size", type=int, default=21,
                        help="Morphological closing kernel size.")
    parser.add_argument("--open-kernel-size", type=int, default=5,
                        help="Morphological opening kernel size.")
    parser.add_argument("--min-motion-area", type=int, default=100,
                        help="Minimum motion mask area.")
    parser.add_argument("--diff-threshold", type=int, default=20,
                        help="LAB diff threshold (0 = fallback to OTSU).")
    parser.add_argument("--no-gradient", action="store_true",
                        help="Disable gradient-based segmentation (enabled by default).")
    parser.add_argument("--grad-threshold", type=int, default=15,
                        help="Gradient difference threshold.")
    parser.add_argument("--soft-edge", type=int, default=0,
                        help="Soft edge kernel size (0 = disabled, must be odd if > 0).")

    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--uniform", action="store_true",
                            help="Uniformly sample N frames (default, single-video only).")
    mode_group.add_argument("--manual", type=str, metavar="FRAMES", default=None,
                            help="Specify frame indices, comma-separated (single-video only).")
    mode_group.add_argument("-i", "--interactive", action="store_true",
                            help="Open interactive GUI to select frames (single-video only).")

    args, unknown = parser.parse_known_args()
    if unknown:
        # Build a clear error for config mode | 为配置模式给出明确提示
        msg = f"Unrecognized arguments: {', '.join(unknown)}."
        if args.config:
            msg += (
                " In multi-video mode (--config) all parameters (e.g. alpha_start, alpha_end) "
                "are read from the config file. Edit the YAML under 'render:' instead of passing "
                "them on the command line."
            )
        parser.error(msg)

    if args.blur_size % 2 == 0:
        raise ValueError("--blur-size must be odd.")
    if args.soft_edge > 0 and args.soft_edge % 2 == 0:
        raise ValueError("--soft-edge must be odd (or 0 to disable).")

    # === Multi-video mode (config file) | 多视频模式（配置文件）===
    if args.config:
        # Reject render/frame CLI options in config mode so user edits YAML instead of silent ignore
        # 多视频模式下拒绝通过命令行传入渲染/选帧参数，提示在配置文件中修改
        render_cli_flags = [
            "--alpha-start", "--alpha-end", "--blur-size", "--diff-threshold",
            "--close-kernel-size", "--open-kernel-size", "--min-motion-area",
            "--no-gradient", "--grad-threshold", "--soft-edge",
            "--num-frames", "--start-frame", "--end-frame", "--num-samples",
        ]
        argv_str = " ".join(sys.argv)
        passed_render = [f for f in render_cli_flags if f in argv_str]
        if passed_render:
            parser.error(
                "Multi-video mode (--config) reads all parameters from the config file. "
                "Do not pass these on the command line: " + ", ".join(passed_render) + ". "
                "Set them in the YAML under 'render:', 'defaults:', or 'background:' instead."
            )
        if not os.path.isfile(args.config):
            print(f"[ERROR] Config file not found: {args.config}")
            exit(1)
        config = _load_yaml_or_json(args.config)
        _validate_multi_video_config(config, args.config)
        videos_config = config["videos"]
        defaults = config.get("defaults", {})
        render_config = config.get("render", {})
        bg_config = config.get("background", {})
        output_config = config.get("output", {})
        config_dir = os.path.dirname(os.path.abspath(args.config))

        video_paths = []
        for v in videos_config:
            p = v["path"]
            if not os.path.isabs(p):
                p = os.path.join(config_dir, p)
            video_paths.append(p)

        print("Extracting unified background from all videos...")
        bg = extract_background_from_multiple_videos(
            video_paths,
            num_samples_per_video=bg_config.get("num_samples_per_video", 5),
        )
        if bg is None:
            print("[ERROR] Background extraction failed.")
            exit(1)

        frame_indices_per_video = []
        for video_config in videos_config:
            path = video_config["path"]
            if not os.path.isabs(path):
                path = os.path.join(config_dir, path)
            mode = video_config.get("mode", defaults.get("mode", "uniform"))
            if mode == "manual":
                indices = video_config["frames"]
            elif mode == "interactive":
                print(f"\n=== Interactive frame selection for {path} ===")
                indices = interactive_select_frames(path)
            else:
                cap = _open_video(path)
                total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                cap.release()
                end_f = video_config.get("end_frame", defaults.get("end_frame"))
                end_val = None if end_f is None else min(end_f, total)  # null = video end | null = 视频结尾
                indices = auto_select_frames(
                    total,
                    video_config.get("start_frame", defaults.get("start_frame", 0)),
                    end_val,
                    video_config.get("num_frames", defaults.get("num_frames", 15)),
                )
            frame_indices_per_video.append(indices)
            print(f"  {video_config['path']}: {len(indices)} frames (mode={mode})")

        result_img, traj_data = render_multi_video_trajectory(
            video_paths,
            bg,
            frame_indices_per_video,
            alpha_start=render_config.get("alpha_start", 0.2),
            alpha_end=render_config.get("alpha_end", 1.0),
            blur_size=render_config.get("blur_size", 5),
            close_kernel_size=render_config.get("close_kernel_size", 21),
            open_kernel_size=render_config.get("open_kernel_size", 5),
            min_motion_area=render_config.get("min_motion_area", 100),
            diff_threshold=render_config.get("diff_threshold", 20),
            use_gradient=render_config.get("use_gradient", True),
            grad_threshold=render_config.get("grad_threshold", 15),
            soft_edge_size=render_config.get("soft_edge", 0),
        )

        output_image = output_config.get("image", "result.png")
        if not os.path.isabs(output_image):
            output_image = os.path.join(config_dir, output_image)
        out_dir = os.path.dirname(output_image)
        if out_dir and not os.path.exists(out_dir):
            os.makedirs(out_dir, exist_ok=True)
        cv2.imwrite(output_image, result_img)
        print(f"Saved: {output_image}")

        if output_config.get("trajectory_json"):
            traj_path = output_config["trajectory_json"]
            if not os.path.isabs(traj_path):
                traj_path = os.path.join(config_dir, traj_path)
            with open(traj_path, "w", encoding="utf-8") as f:
                json.dump({"videos": traj_data}, f, indent=2, ensure_ascii=False)
            print(f"Trajectory JSON saved: {traj_path}")
        exit(0)

    # === Single-video mode (unchanged) | 单视频模式（保持原有逻辑）===
    if not args.output:
        parser.error("--output / -o is required when using --input.")
    if not os.path.isfile(args.input):
        print(f"[ERROR] Input file not found: {args.input}")
        exit(1)

    out_dir = os.path.dirname(args.output)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)
    traj_json_path = args.trajectory_output
    if traj_json_path is None:
        traj_json_path = os.path.splitext(args.output)[0] + ".json"

    # --- Step 1: Select frames | 步骤 1：选择帧 ---
    if args.interactive:
        frame_indices = interactive_select_frames(args.input)
        if not frame_indices:
            print("[ERROR] No frames selected in interactive mode.")
            exit(1)
        print(f"Interactive selection: {len(frame_indices)} frames → {frame_indices}")
    elif args.manual is not None:
        frame_indices = [int(x.strip()) for x in args.manual.split(",")]
        print(f"Manual frame selection: {frame_indices}")
    else:
        cap_probe = _open_video(args.input)
        total = int(cap_probe.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap_probe.get(cv2.CAP_PROP_FPS)
        cap_probe.release()
        print(f"Video: {total} frames, {fps:.1f} FPS")
        frame_indices = auto_select_frames(total, args.start_frame, args.end_frame, args.num_frames)
        print(f"Uniform sampling: {len(frame_indices)} frames (num_samples={args.num_frames})")

    # --- Step 2: Extract background | 步骤 2：提取背景 ---
    print("Extracting stable background...")
    bg = extract_stable_background(args.input, args.start_frame, args.end_frame, args.num_samples)
    if bg is None:
        print("[ERROR] Background extraction failed.")
        exit(1)

    # --- Step 3: Render trajectory | 步骤 3：渲染轨迹 ---
    result_img, traj_data = render_trajectory(
        args.input, bg, frame_indices,
        alpha_start=args.alpha_start, alpha_end=args.alpha_end,
        blur_size=args.blur_size,
        close_kernel_size=args.close_kernel_size,
        open_kernel_size=args.open_kernel_size,
        min_motion_area=args.min_motion_area,
        diff_threshold=args.diff_threshold,
        use_gradient=not args.no_gradient,
        grad_threshold=args.grad_threshold,
        soft_edge_size=args.soft_edge,
    )

    # --- Step 4: Save outputs | 步骤 4：保存输出 ---
    cv2.imwrite(args.output, result_img)
    print(f"Trajectory image saved: {args.output}")
    with open(traj_json_path, "w", encoding="utf-8") as f:
        json.dump(traj_data, f, indent=2, ensure_ascii=False)
    print(f"Trajectory data saved: {traj_json_path} ({len(traj_data)} points)")