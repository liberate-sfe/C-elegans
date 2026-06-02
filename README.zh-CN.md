# C. elegans 计算机视觉试点项目

这是一个低成本、可安装在显微镜上的计算机视觉项目，用于自动化
*C. elegans* 视频计数、密度估算和后续基础行为分析。

项目的短期目标是先建立一个可运行、可验证、可复现的视频分析流程；
长期目标是把视频采集、目标检测、追踪、标注和验证经验迁移到未来
*Daphnia* 水质监测项目中。

## 第一版目标

第一版目前已经加入视频优先的 OpenCV baseline CLI，用于：

- 导入显微镜视频；
- 按固定间隔抽帧；
- 检测每个采样帧中的线虫；
- 统计每个采样帧的线虫数量；
- 根据校准数据计算每帧 worms/mm2；
- 导出 frame-level 和 detection-level CSV 结果；
- 可选保存带标注的视频；
- 与人工逐帧计数结果进行比较。

图像输入仍然保留，用于校准、阈值调参和快速测试。跨帧追踪和行为分析放在后续阶段。

## 快速运行

安装依赖：

```powershell
python -m pip install -r requirements.txt
python -m pip install -e software/c_elegans_counter
```

运行视频分析。输入目录可以直接包含 `.mp4`，也可以包含装有视频的 `.zip`：

```powershell
c-elegans-counter analyze-video `
  --input data/example_videos `
  --calibration-um-per-pixel 2.5 `
  --frame-step 5 `
  --output results/csv/video_frames.csv `
  --detections-output results/csv/video_detections.csv `
  --annotated-video results/annotated_videos
```

如果视频数据在仓库外部，直接把 `--input` 指向那个数据目录即可，不需要把原始视频复制进仓库。

默认假设浅色背景上有较深的线虫。如果视频条件不同，可以尝试
`--polarity bright` 或 `--polarity auto`，并调整面积、长宽比和长度阈值。

## 为什么先做 C. elegans

与 *Daphnia* 相比，*C. elegans* 更容易制备受控样本，也更容易在显微镜下
积累可重复的视频数据。虽然线虫和水蚤的形态、运动模式不同，但完整工作流程具有
迁移价值，包括：

- 视频采集；
- 代表性帧抽样；
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
  software/              视频分析流程与未来代码
  data/                  示例视频、示例图像和标注文件
  notebooks/             探索性分析 notebook
  results/               标注视频、标注图像和 CSV 输出
  scripts/               辅助脚本
```

## 阶段规划

1. 视频抽帧检测：标签为 `worm`，输出每帧数量、位置、密度和标注视频。
2. 虫卵检测：标签为 `worm` 和 `egg`，输出虫卵与线虫比例。
3. 发育阶段分类：标签为 `egg`、`larva`、`adult`。
4. 基础行为分析：加入跨帧追踪，提取速度、位移、轨迹长度、活动水平等特征。
5. Daphnia 迁移：用于游泳行为分析和水质胁迫评估。

## 下一步

下一步建议先加入少量真实显微镜视频，然后抽取代表性帧做人工计数，
再根据人工结果调参，验证检测、计数、密度估算、标注视频输出和 CSV 导出是否可靠。
