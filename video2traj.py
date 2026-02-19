import cv2
import numpy as np
import math
from typing import List, Tuple, Optional, Dict, Any

# ==========================================
# Module 1: Frame Selector | 关键帧选择器
# ==========================================

def auto_select_frames(
    total_frames: int, 
    start_frame: int = 0, 
    end_frame: Optional[int] = None, 
    interval: int = 300
) -> List[int]:
    """Generates a list of frame indices using uniform interval sampling. | 使用均匀间隔采样生成关键帧序号列表。

    Args:
        total_frames (int): The total number of frames in the video. | 视频的总帧数。
        start_frame (int, optional): The starting frame index. Defaults to 0. | 起始帧序号，默认为 0。
        end_frame (Optional[int], optional): The ending frame index. If None, defaults to total_frames. | 结束帧序号。如果为 None，则默认为总帧数。
        interval (int, optional): The sampling step size. Defaults to 15. | 采样步长，默认为 15。

    Returns:
        List[int]: A strictly ascending, deduplicated list of selected frame indices. | 严格递增且去重的所选关键帧序号列表。
    """
    if end_frame is None:
        end_frame = total_frames
    end_frame = min(end_frame, total_frames)
    if interval <= 0:
        raise ValueError(f"interval must be positive, got {interval}")
    return sorted(set(range(start_frame, end_frame, interval)))


def interactive_select_frames(video_path: str) -> List[int]:
    """Provides a lightweight OpenCV GUI to manually select frames for non-uniform sampling. | 提供一个轻量级的 OpenCV GUI，用于手动选择非均匀采样的关键帧。

    This function opens a video player where the user can play/pause, step forward/backward,
    and mark specific frames of interest (e.g., when the drone approaches the Sink Goal). | 该函数会打开一个视频播放器，用户可以播放/暂停、快进/后退，并标记感兴趣的特定帧（例如，无人机接近收敛目标时）。

    Args:
        video_path (str): The absolute or relative path to the input video file. | 输入视频文件的绝对或相对路径。

    Returns:
        List[int]: A strictly ascending, deduplicated list of user-selected frame indices. | 严格递增且去重的用户选择的关键帧序号列表。
    """
    pass


# ==========================================
# Module 2: Background Extractor | 背景提取器
# ==========================================

def extract_stable_background(
    video_path: str, 
    start_frame: int = 0, 
    end_frame: Optional[int] = None, 
    sample_interval: int = 30
) -> Optional[np.ndarray]:
    """Extracts a stable, moving-object-free background using temporal median filtering. | 使用时域中值滤波提取稳定且无运动物体的背景底图。
    
    This function samples frames evenly across the specified duration and computes 
    the median pixel values to eliminate dynamic foreground objects. | 该函数在指定时间段内均匀采样，并计算像素的中值以消除动态前景物体。

    Args:
        video_path (str): Path to the input video. | 输入视频路径。
        start_frame (int, optional): The frame to start sampling from. Defaults to 0. | 采样起始帧，默认为 0。
        end_frame (Optional[int], optional): The frame to stop sampling. Defaults to None. | 采样结束帧，默认为 None。
        sample_interval (int, optional): Interval between sampled frames for the median pool. 
            Larger values reduce memory usage. Defaults to 30. | 用于中值计算的采样间隔。较大的值可降低内存使用量，默认为 30。

    Returns:
        Optional[np.ndarray]: A 3-channel BGR image representing the stable background, 
            or None if extraction fails. | 代表稳定背景的 3 通道 BGR 图像，如果提取失败则返回 None。
    """
    MAX_SAMPLES_FOR_BG = 100

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if end_frame is None:
        end_frame = total_frames
    end_frame = min(end_frame, total_frames)

    if end_frame <= start_frame:
        cap.release()
        return None

    num_candidate = math.ceil((end_frame - start_frame) / sample_interval)
    if num_candidate > MAX_SAMPLES_FOR_BG:
        sample_interval = math.ceil((end_frame - start_frame) / MAX_SAMPLES_FOR_BG)

    frames = []
    for frame_idx in range(start_frame, end_frame, sample_interval):
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


# ==========================================
# Module 3: Rendering Engine | 核心渲染引擎
# ==========================================

def refine_motion_mask(
    mask: np.ndarray, 
    min_area: int = 100, 
    blur_size: int = 5, 
    morph_kernel_size: int = 5
) -> np.ndarray:
    """Refines a raw binary motion mask using morphological operations. | 使用形态学操作优化原始二值运动掩模。

    Applies Gaussian blur, morphological closing, and opening to filter noise. | 应用高斯模糊、闭运算和开运算来过滤噪声。

    Args:
        mask (np.ndarray): The raw binary mask. | 原始二值掩模。
        min_area (int, optional): Minimum connected component area. Defaults to 100. | 最小连通域面积，默认为 100。
        blur_size (int, optional): Kernel size for Gaussian blur. Defaults to 5. | 高斯模糊核大小，默认为 5。
        morph_kernel_size (int, optional): Kernel size for morphology. Defaults to 5. | 形态学操作核大小，默认为 5。

    Returns:
        np.ndarray: The purified binary mask. | 净化后的二值掩模。
    """
    # Gaussian blur to smooth edges | 高斯模糊平滑边缘
    mask = cv2.GaussianBlur(mask, (blur_size, blur_size), 0)
    
    # Threshold back to binary | 重新二值化
    _, mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)
    
    # Morphological operations | 形态学操作
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (morph_kernel_size, morph_kernel_size))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel) # Fill gaps in drone | 填补无人机内部空洞
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)  # Remove background noise | 去除背景噪声
    
    # Remove small components | 移除极小连通域 (物理过滤网)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for contour in contours:
        if cv2.contourArea(contour) < min_area:
            cv2.fillPoly(mask, [contour], 0)
            
    return mask


def render_trajectory(
    video_path: str, 
    bg_image: np.ndarray, 
    frame_indices: List[int], 
    alpha_start: float = 0.2, 
    alpha_end: float = 1.0,
    blur_size: int = 5,
    morph_kernel_size: int = 5,
    min_motion_area: int = 100
) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
    """Renders a stroboscopic trajectory image using a Z-Buffer (ID Map) architecture. | 使用深度缓冲 (ID Map) 架构渲染残影轨迹图。

    Args:
        video_path (str): Path to the input video. | 输入视频路径。
        bg_image (np.ndarray): The clean background image. | 干净的背景底图。
        frame_indices (List[int]): A list of frame indices to be rendered. | 待渲染的关键帧序号列表。
        alpha_start (float, optional): Opacity of the earliest shadow. Defaults to 0.2. | 最早残影的不透明度，默认为 0.2。
        alpha_end (float, optional): Opacity of the latest shadow. Defaults to 1.0. | 最新残影的不透明度，默认为 1.0。
        blur_size (int, optional): Blur size for mask. Defaults to 5. | 掩模模糊大小，默认为 5。
        morph_kernel_size (int, optional): Morphology kernel size. Defaults to 5. | 形态学核大小，默认为 5。
        min_motion_area (int, optional): Minimum mask area. Defaults to 100. | 最小掩模面积，默认为 100。

    Returns:
        Tuple[np.ndarray, List[Dict]]: (trajectory_image, trajectory_data).
            trajectory_data contains per-frame centroid, bbox and area. |
            返回 (轨迹合成图, 轨迹数据列表)，轨迹数据包含每帧质心、边界框和面积。
    """
    # 1. Defensive data cleaning at M3 entry | 入口防御性清洗
    sorted_indices = sorted(set(frame_indices))
    num_frames = len(sorted_indices)
    if num_frames == 0:
        return bg_image.copy(), []

    rank_map = {frame_idx: rank + 1 for rank, frame_idx in enumerate(sorted_indices)}
    
    # 2. Initialize buffers (uint16 saves half memory vs int32) | 初始化缓冲
    height, width = bg_image.shape[:2]
    id_map = np.zeros((height, width), dtype=np.uint16)
    color_buffer = np.zeros((height, width, 3), dtype=np.uint8)
    bg_gray = cv2.cvtColor(bg_image, cv2.COLOR_BGR2GRAY)
    trajectory_data: List[Dict[str, Any]] = []
    
    # 3. One-pass forward video reading with I/O fault tolerance | 单遍前向读取 + I/O 容错
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[ERROR] Cannot open video: {video_path}")
        return bg_image.copy(), []

    current_frame_idx = 0
    max_frame_needed = sorted_indices[-1]
    consecutive_failures = 0
    MAX_CONSECUTIVE_FAILURES = 5
    
    print(f"Rendering {num_frames} frames (range {sorted_indices[0]}..{max_frame_needed})...")
    
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
            rank = rank_map[current_frame_idx]
            current_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            diff = cv2.absdiff(current_gray, bg_gray)
            _, raw_mask = cv2.threshold(diff, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            refined_mask = refine_motion_mask(raw_mask, min_motion_area, blur_size, morph_kernel_size)
            
            # Z-Buffer overwrite | 深度缓冲覆盖
            valid_pixels = refined_mask > 0
            id_map[valid_pixels] = rank
            color_buffer[valid_pixels] = frame[valid_pixels]

            # Extract trajectory (centroid + bbox) — nearly free | 提取轨迹数据
            M = cv2.moments(refined_mask)
            if M["m00"] > 0:
                cx = M["m10"] / M["m00"]
                cy = M["m01"] / M["m00"]
                x, y, w, h = cv2.boundingRect(refined_mask)
                trajectory_data.append({
                    "frame": current_frame_idx,
                    "cx": round(cx, 2), "cy": round(cy, 2),
                    "bbox": [int(x), int(y), int(w), int(h)],
                    "area": round(M["m00"] / 255.0, 1),
                })
            
        current_frame_idx += 1
        
    cap.release()
    
    # 4. Vectorized alpha blending via LUT (replaces O(N*H*W*3) Python loop) | LUT 向量化混合
    print("Compositing with vectorized alpha blending...")
    alpha_lut = np.zeros(num_frames + 1, dtype=np.float32)
    for rank in range(1, num_frames + 1):
        if num_frames == 1:
            alpha_lut[rank] = alpha_end
        else:
            alpha_lut[rank] = alpha_start + (alpha_end - alpha_start) * ((rank - 1) / (num_frames - 1))

    alpha_map = alpha_lut[id_map][:, :, np.newaxis]       # H x W x 1
    fg_mask = (id_map > 0)[:, :, np.newaxis]               # H x W x 1

    bg_f = bg_image.astype(np.float32)
    cb_f = color_buffer.astype(np.float32)
    result = np.where(fg_mask, cb_f * alpha_map + bg_f * (1.0 - alpha_map), bg_f)

    return np.clip(result, 0, 255).astype(np.uint8), trajectory_data


# ==========================================
# Entry Point | 程序入口
# ==========================================

if __name__ == "__main__":
    import argparse
    import json
    import os

    parser = argparse.ArgumentParser(description="video2traj: Generate stroboscopic trajectory images from video.")
    parser.add_argument("input", type=str, help="Path to the input video file.")
    parser.add_argument("--output", "-o", type=str, default="trajectory.jpg", help="Output image path.")
    parser.add_argument("--trajectory-output", type=str, default=None,
                        help="Output trajectory JSON path. Defaults to <output>.json.")
    parser.add_argument("--interval", type=int, default=300, help="Frame sampling interval (auto mode).")
    parser.add_argument("--start-frame", type=int, default=0, help="Start frame index.")
    parser.add_argument("--end-frame", type=int, default=None, help="End frame index (None = all).")
    parser.add_argument("--sample-interval", type=int, default=30, help="Background sampling interval.")
    parser.add_argument("--alpha-start", type=float, default=0.2, help="Opacity of earliest shadow.")
    parser.add_argument("--alpha-end", type=float, default=1.0, help="Opacity of latest shadow.")
    parser.add_argument("--blur-size", type=int, default=5, help="Gaussian blur kernel size (odd).")
    parser.add_argument("--morph-kernel-size", type=int, default=5, help="Morphology kernel size.")
    parser.add_argument("--min-motion-area", type=int, default=100, help="Minimum motion mask area.")
    parser.add_argument("--frames", type=str, default=None,
                        help="Manually specify frame indices (comma-separated, e.g. '30,60,90,120').")

    args = parser.parse_args()

    if not os.path.isfile(args.input):
        print(f"[ERROR] Input file not found: {args.input}")
        exit(1)
    if args.blur_size % 2 == 0:
        raise ValueError("--blur-size must be odd.")

    out_dir = os.path.dirname(args.output)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    traj_json_path = args.trajectory_output
    if traj_json_path is None:
        traj_json_path = os.path.splitext(args.output)[0] + ".json"

    # --- Step 1: Select frames ---
    if args.frames:
        frame_indices = [int(x.strip()) for x in args.frames.split(",")]
        print(f"Manual frame selection: {frame_indices}")
    else:
        cap_probe = cv2.VideoCapture(args.input)
        total = int(cap_probe.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap_probe.get(cv2.CAP_PROP_FPS)
        cap_probe.release()
        print(f"Video: {total} frames, {fps:.1f} FPS")
        frame_indices = auto_select_frames(total, args.start_frame, args.end_frame, args.interval)
        print(f"Auto-selected {len(frame_indices)} frames (interval={args.interval})")

    # --- Step 2: Extract background ---
    print("Extracting stable background...")
    bg = extract_stable_background(args.input, args.start_frame, args.end_frame, args.sample_interval)
    if bg is None:
        print("[ERROR] Background extraction failed.")
        exit(1)

    # --- Step 3: Render trajectory ---
    result_img, traj_data = render_trajectory(
        args.input, bg, frame_indices,
        alpha_start=args.alpha_start, alpha_end=args.alpha_end,
        blur_size=args.blur_size, morph_kernel_size=args.morph_kernel_size,
        min_motion_area=args.min_motion_area,
    )

    # --- Step 4: Save outputs ---
    cv2.imwrite(args.output, result_img)
    print(f"Trajectory image saved: {args.output}")

    with open(traj_json_path, "w", encoding="utf-8") as f:
        json.dump(traj_data, f, indent=2, ensure_ascii=False)
    print(f"Trajectory data saved: {traj_json_path} ({len(traj_data)} points)")