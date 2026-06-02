# C. elegans 计算机视觉试点项目

这是一个低成本、可安装在显微镜上的计算机视觉项目，用于自动化
*C. elegans* 计数、密度估算和基础行为分析。

项目的短期目标是先建立一个可运行、可验证、可复现的线虫分析流程；
长期目标是把图像采集、目标检测、追踪、标注和验证经验迁移到未来
*Daphnia* 水质监测项目中。

## 第一版目标

第一版目前已经加入 OpenCV baseline CLI，用于：

- 导入显微镜图像或短视频；
- 检测视野中的线虫；
- 统计线虫数量；
- 根据校准数据计算 worms/mm2；
- 导出 CSV 结果；
- 保存带标注的图像；
- 与人工计数结果进行比较。

当前代码先支持图像输入。视频追踪和行为分析放在后续阶段。

## 快速运行

安装依赖：

```powershell
python -m pip install -r requirements.txt
python -m pip install -e software/c_elegans_counter
```

运行图像文件夹分析：

```powershell
c-elegans-counter analyze `
  --input data/example_images `
  --calibration-um-per-pixel 2.5 `
  --output results/csv/results.csv `
  --detections-output results/csv/detections.csv `
  --annotated-dir results/annotated_images
```

默认假设浅色背景上有较深的线虫。如果图像条件不同，可以尝试
`--polarity bright` 或 `--polarity auto`，并调整面积、长宽比和长度阈值。

## 为什么先做 C. elegans

与 *Daphnia* 相比，*C. elegans* 更容易制备受控样本，也更容易在显微镜下
积累大量图像。虽然线虫和水蚤的形态、运动模式不同，但完整工作流程具有
迁移价值，包括：

- 图像或视频采集；
- 数据标注；
- 目标检测；
- 密度估算；
- 目标追踪；
- 行为特征提取；
- 人工结果与自动结果的验证；
- 错误来源分析。

## 项目结构

```text
C_elegans_CV_Pilot_Project/
  README.md              英文项目首页
  README.zh-CN.md        中文摘要
  docs/                  实验方案、标注规范、验证计划
  hardware/              3D 打印转接器与硬件说明
  software/              图像分析流程与未来代码
  data/                  示例图像和标注文件
  notebooks/             探索性分析 notebook
  results/               标注图像和 CSV 输出
  scripts/               辅助脚本
```

## 阶段规划

1. 线虫检测：标签为 `worm`，输出数量、位置、密度和标注图。
2. 虫卵检测：标签为 `worm` 和 `egg`，输出虫卵与线虫比例。
3. 发育阶段分类：标签为 `egg`、`larva`、`adult`。
4. 基础行为分析：提取速度、位移、轨迹长度、活动水平等特征。
5. Daphnia 迁移：用于游泳行为分析和水质胁迫评估。

## 下一步

下一步建议先加入少量真实或示例显微镜图像，然后根据人工计数结果调参，
验证检测、计数、密度估算、标注图输出和 CSV 导出是否可靠。
