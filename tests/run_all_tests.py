"""Run all tests for video2traj.
运行 video2traj 的所有测试。
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from test_synthetic import test_synthetic_video
from test_regression import test_regression


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
    print("\n")
    try:
        result1 = test_synthetic_video()
        results.append(("Synthetic Video Test | 合成视频测试", result1))
    except Exception as e:
        print(f"[FAIL] Test 1 failed with exception: {e}")
        results.append(("Synthetic Video Test | 合成视频测试", False))
    
    # Test 2: Regression
    print("\n")
    try:
        result2 = test_regression()
        results.append(("Regression Test | 回归测试", result2))
    except Exception as e:
        print(f"[FAIL] Test 2 failed with exception: {e}")
        results.append(("Regression Test | 回归测试", False))
    
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
