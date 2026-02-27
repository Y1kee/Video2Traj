"""Run all tests for video2traj.
运行 video2traj 的所有测试。
"""

import os
import sys
from pathlib import Path

# Disable tqdm progress bars during tests to avoid hang when stdout is not a TTY
# 测试时关闭 tqdm 进度条，避免在非 TTY 下卡住
os.environ["TQDM_DISABLE"] = "1"

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from test_synthetic import test_synthetic_video
from test_regression import test_regression
from test_multi_video import test_multi_video_mode, test_multi_video_config_validation


def main():
    """Run all tests and report results.
    运行所有测试并报告结果。
    """
    print("\n" + "=" * 70)
    print(" " * 20 + "video2traj Test Suite")
    print(" " * 20 + "video2traj 测试套件")
    print("=" * 70)
    
    results = []
    
    # Test 1: Synthetic video
    print("\n[Run] Test 1: Synthetic Video ...", flush=True)
    try:
        result1 = test_synthetic_video()
        results.append(("Synthetic Video Test | 合成视频测试", result1))
    except Exception as e:
        print(f"[FAIL] Test 1 failed with exception: {e}", flush=True)
        results.append(("Synthetic Video Test | 合成视频测试", False))

    # Test 2: Regression
    print("\n[Run] Test 2: Regression ...", flush=True)
    try:
        result2 = test_regression()
        results.append(("Regression Test | 回归测试", result2))
    except Exception as e:
        print(f"[FAIL] Test 2 failed with exception: {e}", flush=True)
        results.append(("Regression Test | 回归测试", False))

    # Test 3: Multi-video mode
    print("\n[Run] Test 3: Multi-Video Mode ...", flush=True)
    try:
        result3 = test_multi_video_mode()
        results.append(("Multi-Video Mode Test | 多视频模式测试", result3))
    except Exception as e:
        print(f"[FAIL] Test 3 failed with exception: {e}", flush=True)
        results.append(("Multi-Video Mode Test | 多视频模式测试", False))

    # Test 4: Multi-video config validation
    print("\n[Run] Test 4: Multi-Video Config Validation ...", flush=True)
    try:
        result4 = test_multi_video_config_validation()
        results.append(("Multi-Video Config Validation | 多视频配置校验", result4))
    except Exception as e:
        print(f"[FAIL] Test 4 failed with exception: {e}", flush=True)
        results.append(("Multi-Video Config Validation | 多视频配置校验", False))

    # Summary
    print("\n" + "=" * 70)
    print(" " * 25 + "Test Summary | 测试摘要")
    print("=" * 70)
    
    for test_name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status}  {test_name}")
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    print(f"\n  Total | 总计: {passed_count}/{total_count} tests passed")
    print("=" * 70 + "\n")
    
    return all(passed for _, passed in results)


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[ERROR] Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
