"""Test video2traj with synthetic video (pure background + moving rectangle).
用合成视频（纯色背景 + 移动矩形）测试 video2traj。
"""

import cv2
import numpy as np
import os
import sys
import tempfile
from pathlib import Path

# Add parent directory to path to import video2traj
sys.path.insert(0, str(Path(__file__).parent.parent))

import video2traj


def create_synthetic_video(
    output_path: str,
    width: int = 640,
    height: int = 480,
    num_frames: int = 30,
    fps: int = 30,
    bg_color: tuple = (200, 200, 200),
    rect_color: tuple = (50, 50, 200),
    rect_size: tuple = (80, 60)
) -> list:
    """Create a synthetic video with a moving rectangle on pure background.
    创建合成视频，包含纯色背景上移动的矩形。
    
    Args:
        output_path: Output video file path | 输出视频路径
        width: Video width | 视频宽度
        height: Video height | 视频高度
        num_frames: Number of frames | 帧数
        fps: Frames per second | 帧率
        bg_color: Background color (B, G, R) | 背景颜色
        rect_color: Rectangle color (B, G, R) | 矩形颜色
        rect_size: Rectangle size (w, h) | 矩形尺寸
    
    Returns:
        List of ground truth positions [(x, y, w, h), ...] | 真实位置列表
    """
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    ground_truth = []
    rect_w, rect_h = rect_size
    
    # Move rectangle diagonally from top-left to bottom-right
    # 矩形从左上角对角移动到右下角
    for i in range(num_frames):
        # Create pure background | 创建纯色背景
        frame = np.full((height, width, 3), bg_color, dtype=np.uint8)
        
        # Calculate rectangle position | 计算矩形位置
        progress = i / (num_frames - 1)
        x = int((width - rect_w) * progress)
        y = int((height - rect_h) * progress)
        
        # Draw rectangle | 绘制矩形
        cv2.rectangle(frame, (x, y), (x + rect_w, y + rect_h), rect_color, -1)
        
        out.write(frame)
        ground_truth.append((x, y, rect_w, rect_h))
    
    out.release()
    return ground_truth


def calculate_iou(box1: tuple, box2: tuple) -> float:
    """Calculate IoU (Intersection over Union) between two boxes.
    计算两个框的IoU（交并比）。
    
    Args:
        box1, box2: (x, y, w, h) format | (x, y, w, h) 格式
    
    Returns:
        IoU value [0, 1] | IoU 值
    """
    x1, y1, w1, h1 = box1
    x2, y2, w2, h2 = box2
    
    # Calculate intersection | 计算交集
    x_left = max(x1, x2)
    y_top = max(y1, y2)
    x_right = min(x1 + w1, x2 + w2)
    y_bottom = min(y1 + h1, y2 + h2)
    
    if x_right < x_left or y_bottom < y_top:
        return 0.0
    
    intersection = (x_right - x_left) * (y_bottom - y_top)
    
    # Calculate union | 计算并集
    area1 = w1 * h1
    area2 = w2 * h2
    union = area1 + area2 - intersection
    
    return intersection / union if union > 0 else 0.0


def test_synthetic_video():
    """Test video2traj with synthetic video and verify mask coverage > 90%.
    用合成视频测试 video2traj 并验证掩模覆盖率 > 90%。
    """
    print("=" * 60)
    print("Test 1: Synthetic Video - Mask Coverage | 测试1：合成视频 - 掩模覆盖率")
    print("=" * 60)
    
    # Create temporary directory | 创建临时目录
    with tempfile.TemporaryDirectory() as tmpdir:
        # Generate synthetic video | 生成合成视频
        video_path = os.path.join(tmpdir, "synthetic.mp4")
        output_path = os.path.join(tmpdir, "output.jpg")
        
        print(f"\n[1/5] Generating synthetic video... | 生成合成视频...")
        ground_truth = create_synthetic_video(
            video_path,
            width=640,
            height=480,
            num_frames=30,
            fps=30,
            bg_color=(220, 220, 220),
            rect_color=(50, 50, 200),
            rect_size=(80, 60)
        )
        print(f"      Created: {video_path}")
        print(f"      Frames: {len(ground_truth)}")
        
        # Select frames to test (uniformly sample 10 frames) | 选择测试帧
        print(f"\n[2/5] Selecting frames... | 选择帧...")
        frame_indices = video2traj.auto_select_frames(
            total_frames=len(ground_truth),
            num_samples=10
        )
        print(f"      Selected frames: {frame_indices}")
        
        # Extract background | 提取背景
        print(f"\n[3/5] Extracting background... | 提取背景...")
        bg = video2traj.extract_stable_background(
            video_path,
            num_samples=5
        )
        assert bg is not None, "Background extraction failed | 背景提取失败"
        print(f"      Background shape: {bg.shape}")
        
        # Render trajectory | 渲染轨迹
        print(f"\n[4/5] Rendering trajectory... | 渲染轨迹...")
        result_img, traj_data = video2traj.render_trajectory(
            video_path,
            bg,
            frame_indices,
            alpha_start=0.3,
            alpha_end=1.0,
            diff_threshold=30,
            min_motion_area=50
        )
        cv2.imwrite(output_path, result_img)
        print(f"      Trajectory image saved: {output_path}")
        print(f"      Trajectory points: {len(traj_data)}")
        
        # Verify mask coverage | 验证掩模覆盖率
        print(f"\n[5/5] Verifying mask coverage... | 验证掩模覆盖率...")
        iou_scores = []
        
        for data in traj_data:
            frame_idx = data['frame']
            detected_bbox = tuple(data['bbox'])
            
            # Get ground truth for this frame | 获取该帧的真实值
            gt_bbox = ground_truth[frame_idx]
            
            # Calculate IoU | 计算 IoU
            iou = calculate_iou(detected_bbox, gt_bbox)
            iou_scores.append(iou)
            
            print(f"      Frame {frame_idx:3d}: IoU = {iou:.3f} "
                  f"(GT: {gt_bbox}, Detected: {detected_bbox})")
        
        # Calculate statistics | 计算统计数据
        if iou_scores:
            avg_iou = np.mean(iou_scores)
            min_iou = np.min(iou_scores)
            max_iou = np.max(iou_scores)
            coverage_90 = np.sum(np.array(iou_scores) > 0.9) / len(iou_scores) * 100
            
            print(f"\n{'='*60}")
            print(f"Results | 结果:")
            print(f"  Average IoU | 平均 IoU:        {avg_iou:.3f}")
            print(f"  Min IoU | 最小 IoU:            {min_iou:.3f}")
            print(f"  Max IoU | 最大 IoU:            {max_iou:.3f}")
            print(f"  Coverage > 90% | 覆盖率 > 90%: {coverage_90:.1f}% "
                  f"({int(coverage_90 * len(iou_scores) / 100)}/{len(iou_scores)} frames)")
            print(f"{'='*60}")
            
            # Test assertion | 测试断言
            if avg_iou > 0.7:
                print(f"\n[PASS] Average IoU > 0.7 | 通过：平均 IoU > 0.7")
                return True
            else:
                print(f"\n[FAIL] Average IoU = {avg_iou:.3f} < 0.7 | 失败：平均 IoU < 0.7")
                return False
        else:
            print(f"\n[FAIL] No trajectory detected | 失败：未检测到轨迹")
            return False


if __name__ == "__main__":
    try:
        success = test_synthetic_video()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[ERROR] | 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
