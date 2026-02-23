# video2traj Test Suite | 测试套件

## 📋 Test Overview | 测试概览

This directory contains automated tests for the video2traj toolbox.

本目录包含 video2traj 工具箱的自动化测试。

### Test 1: Synthetic Video Test | 合成视频测试

**Purpose | 目的**: Verify that the toolbox correctly detects and tracks moving objects.

**Method | 方法**: 
- Creates a synthetic video with a pure color background and a moving rectangle
- 创建包含纯色背景和移动矩形的合成视频
- Runs the full video2traj pipeline
- 运行完整的 video2traj 管线
- Compares detected bounding boxes with ground truth
- 将检测到的边界框与真实值比较
- Calculates IoU (Intersection over Union) scores
- 计算 IoU（交并比）分数

**Success Criteria | 成功标准**: Average IoU > 0.7 (ideally > 0.9)

### Test 2: Regression Test | 回归测试

**Purpose | 目的**: Ensure that the toolbox produces consistent, deterministic output.

**Method | 方法**:
- Creates a deterministic test video with fixed random seed
- 使用固定随机种子创建确定性测试视频
- Runs the pipeline twice with identical parameters
- 使用相同参数运行管线两次
- Compares SHA256 hashes of output images and trajectory JSON
- 比较输出图像和轨迹 JSON 的 SHA256 哈希值
- Stores baseline hash for future comparisons
- 存储基线哈希以供将来比较

**Success Criteria | 成功标准**: Identical output hashes across runs

## 🚀 Running Tests | 运行测试

### Run All Tests | 运行所有测试

```bash
cd tests
python run_all_tests.py
```

### Run Individual Tests | 运行单个测试

**Test 1: Synthetic Video**
```bash
cd tests
python test_synthetic.py
```

**Test 2: Regression**
```bash
cd tests
python test_regression.py
```

### Update Baseline (Regression Test) | 更新基线（回归测试）

If you've made intentional changes to the algorithm and the regression test fails:

如果您对算法进行了有意的更改且回归测试失败：

```bash
cd tests
python test_regression.py --update-baseline
```

## 📊 Expected Output | 预期输出

### Successful Test Run | 成功的测试运行

```
======================================================================
                    video2traj Test Suite
                    video2traj 测试套件
======================================================================


============================================================
Test 1: Synthetic Video - Mask Coverage | 测试1：合成视频 - 掩模覆盖率
============================================================

[1/5] Generating synthetic video... | 生成合成视频...
      ...
      
Results | 结果:
  Average IoU | 平均 IoU:        0.850
  Min IoU | 最小 IoU:            0.720
  Max IoU | 最大 IoU:            0.950
  Coverage > 90% | 覆盖率 > 90%: 60.0% (6/10 frames)
============================================================

✅ PASS: Average IoU > 0.7 | 通过：平均 IoU > 0.7


============================================================
Test 2: Regression - Output Consistency | 测试2：回归 - 输出一致性
============================================================

...

Results | 结果:
  Image Match | 图像匹配: ✅ YES
  JSON Match | JSON匹配:  ✅ YES
============================================================

✅ PASS: Output is deterministic | 通过：输出是确定性的


======================================================================
                     Test Summary | 测试摘要
======================================================================
  ✅ PASS  Synthetic Video Test | 合成视频测试
  ✅ PASS  Regression Test | 回归测试

  Total | 总计: 2/2 tests passed
======================================================================
```

## 📝 Notes | 注意事项

- Tests create temporary files that are automatically cleaned up
- 测试会创建临时文件，这些文件会自动清理
- Baseline hashes are stored in `baseline_hashes.json`
- 基线哈希存储在 `baseline_hashes.json` 中
- If tests fail unexpectedly, check OpenCV and NumPy versions
- 如果测试意外失败，请检查 OpenCV 和 NumPy 版本
- Tests require the same dependencies as video2traj
- 测试需要与 video2traj 相同的依赖项

## 🐛 Troubleshooting | 故障排除

**Test fails with "module not found"**
- Make sure you run tests from the `tests/` directory
- 确保从 `tests/` 目录运行测试

**Regression test fails after code changes**
- This is expected if you've modified the algorithm
- 如果修改了算法，这是正常的
- Review changes and update baseline if intentional
- 审查更改，如果是有意的则更新基线
- Use `--update-baseline` flag to accept new output
- 使用 `--update-baseline` 标志接受新输出

**Synthetic test fails with low IoU**
- Check diff_threshold and other segmentation parameters
- 检查 diff_threshold 和其他分割参数
- Pure synthetic video should have near-perfect detection
- 纯合成视频应该有接近完美的检测
- Low IoU may indicate a bug in the segmentation pipeline
- 低 IoU 可能表明分割管线存在错误
