"""Regression test: Fixed input -> Fixed output hash.
回归测试：固定输入 -> 固定输出哈希。
"""

import cv2
import numpy as np
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

# Add parent directory to path to import video2traj
sys.path.insert(0, str(Path(__file__).parent.parent))

import video2traj


def create_test_video(output_path: str, seed: int = 42) -> None:
    """Create a deterministic test video for regression testing.
    创建确定性测试视频用于回归测试。
    
    Args:
        output_path: Output video file path | 输出视频路径
        seed: Random seed for reproducibility | 可重现性的随机种子
    """
    np.random.seed(seed)
    
    width, height = 320, 240
    num_frames = 20
    fps = 30
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    # Create video with deterministic random noise and moving blob
    # 创建带有确定性随机噪声和移动斑点的视频
    for i in range(num_frames):
        # Base frame with noise | 带噪声的基础帧
        frame = np.random.randint(180, 200, (height, width, 3), dtype=np.uint8)
        
        # Add a moving blob | 添加移动斑点
        cx = int(width * (0.2 + 0.6 * i / (num_frames - 1)))
        cy = int(height * 0.5)
        cv2.circle(frame, (cx, cy), 20, (50, 100, 150), -1)
        
        out.write(frame)
    
    out.release()


def compute_image_hash(image: np.ndarray) -> str:
    """Compute SHA256 hash of an image.
    计算图像的 SHA256 哈希值。
    
    Args:
        image: Input image | 输入图像
    
    Returns:
        Hex string of hash | 哈希的十六进制字符串
    """
    return hashlib.sha256(image.tobytes()).hexdigest()


def compute_json_hash(data: list) -> str:
    """Compute SHA256 hash of trajectory JSON data.
    计算轨迹 JSON 数据的 SHA256 哈希值。
    
    Args:
        data: Trajectory data | 轨迹数据
    
    Returns:
        Hex string of hash | 哈希的十六进制字符串
    """
    # Convert to deterministic JSON string
    # 转换为确定性 JSON 字符串
    json_str = json.dumps(data, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(json_str.encode('utf-8')).hexdigest()


def test_regression():
    """Test that fixed input produces consistent output.
    测试固定输入产生一致的输出。
    """
    print("=" * 60)
    print("Test 2: Regression - Output Consistency | 测试2：回归 - 输出一致性")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test video | 创建测试视频
        video_path = os.path.join(tmpdir, "test_regression.mp4")
        
        print(f"\n[1/6] Creating test video... | 创建测试视频...")
        create_test_video(video_path, seed=42)
        print(f"      Created: {video_path}")
        
        # Fixed parameters for regression test | 回归测试的固定参数
        FIXED_PARAMS = {
            'num_frames': 10,
            'num_bg_samples': 5,
            'alpha_start': 0.2,
            'alpha_end': 1.0,
            'diff_threshold': 25,
            'blur_size': 5,
            'close_kernel_size': 21,
            'open_kernel_size': 5,
            'min_motion_area': 100,
        }
        
        print(f"\n[2/6] Fixed parameters | 固定参数:")
        for key, value in FIXED_PARAMS.items():
            print(f"      {key}: {value}")
        
        # Run pipeline twice to verify consistency | 运行管线两次验证一致性
        results = []
        
        for run in range(1, 3):
            print(f"\n[{2+run}/6] Run #{run} | 运行 #{run}...")
            
            # Select frames | 选择帧
            frame_indices = video2traj.auto_select_frames(
                total_frames=20,
                num_samples=FIXED_PARAMS['num_frames']
            )
            
            # Extract background | 提取背景
            bg = video2traj.extract_stable_background(
                video_path,
                num_samples=FIXED_PARAMS['num_bg_samples']
            )
            
            # Render trajectory | 渲染轨迹
            result_img, traj_data = video2traj.render_trajectory(
                video_path,
                bg,
                frame_indices,
                alpha_start=FIXED_PARAMS['alpha_start'],
                alpha_end=FIXED_PARAMS['alpha_end'],
                diff_threshold=FIXED_PARAMS['diff_threshold'],
                blur_size=FIXED_PARAMS['blur_size'],
                close_kernel_size=FIXED_PARAMS['close_kernel_size'],
                open_kernel_size=FIXED_PARAMS['open_kernel_size'],
                min_motion_area=FIXED_PARAMS['min_motion_area'],
            )
            
            # Compute hashes | 计算哈希
            img_hash = compute_image_hash(result_img)
            json_hash = compute_json_hash(traj_data)
            
            print(f"      Image hash: {img_hash[:16]}...")
            print(f"      JSON hash:  {json_hash[:16]}...")
            
            results.append({
                'run': run,
                'img_hash': img_hash,
                'json_hash': json_hash,
                'traj_data': traj_data
            })
        
        # Compare results | 比较结果
        print(f"\n[5/6] Comparing results... | 比较结果...")
        
        img_match = results[0]['img_hash'] == results[1]['img_hash']
        json_match = results[0]['json_hash'] == results[1]['json_hash']
        
        print(f"\n{'='*60}")
        print(f"Results | 结果:")
        print(f"  Run #1 Image Hash | 运行1图像哈希: {results[0]['img_hash'][:32]}...")
        print(f"  Run #2 Image Hash | 运行2图像哈希: {results[1]['img_hash'][:32]}...")
        print(f"  Image Match | 图像匹配: {'[YES]' if img_match else '[NO]'}")
        print(f"")
        print(f"  Run #1 JSON Hash | 运行1 JSON哈希:  {results[0]['json_hash'][:32]}...")
        print(f"  Run #2 JSON Hash | 运行2 JSON哈希:  {results[1]['json_hash'][:32]}...")
        print(f"  JSON Match | JSON匹配:  {'[YES]' if json_match else '[NO]'}")
        print(f"{'='*60}")
        
        # Store baseline hash (first time) or compare with baseline
        # 存储基线哈希（首次）或与基线比较
        baseline_file = Path(__file__).parent / "baseline_hashes.json"
        
        print(f"\n[6/6] Checking baseline... | 检查基线...")
        
        if baseline_file.exists():
            # Load and compare with baseline | 加载并与基线比较
            with open(baseline_file, 'r') as f:
                baseline = json.load(f)
            
            baseline_img_match = results[0]['img_hash'] == baseline.get('img_hash')
            baseline_json_match = results[0]['json_hash'] == baseline.get('json_hash')
            
            print(f"      Baseline file found: {baseline_file}")
            print(f"      Baseline image match: {'[YES]' if baseline_img_match else '[NO]'}")
            print(f"      Baseline JSON match:  {'[YES]' if baseline_json_match else '[NO]'}")
            
            if not baseline_img_match or not baseline_json_match:
                print(f"\n[WARNING] Output differs from baseline!")
                print(f"          If this is expected (code improvement), update baseline:")
                print(f"          python tests/test_regression.py --update-baseline")
        else:
            # Create baseline for first time | 首次创建基线
            baseline = {
                'img_hash': results[0]['img_hash'],
                'json_hash': results[0]['json_hash'],
                'params': FIXED_PARAMS
            }
            with open(baseline_file, 'w') as f:
                json.dump(baseline, f, indent=2)
            
            print(f"      Baseline file created: {baseline_file}")
            print(f"      Use this as reference for future runs.")
        
        # Final verdict | 最终结论
        print(f"\n{'='*60}")
        if img_match and json_match:
            print(f"[PASS] Output is deterministic | 通过：输出是确定性的")
            print(f"{'='*60}")
            return True
        else:
            print(f"[FAIL] Output is NOT deterministic | 失败：输出不是确定性的")
            print(f"{'='*60}")
            return False


if __name__ == "__main__":
    # Check for --update-baseline flag | 检查 --update-baseline 标志
    update_baseline = "--update-baseline" in sys.argv
    
    if update_baseline:
        print("Updating baseline hashes... | 更新基线哈希...")
        baseline_file = Path(__file__).parent / "baseline_hashes.json"
        if baseline_file.exists():
            baseline_file.unlink()
            print(f"Removed old baseline: {baseline_file}")
    
    try:
        success = test_regression()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[ERROR] | 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
