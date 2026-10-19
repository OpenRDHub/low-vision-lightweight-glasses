---
team: Albassist Team
solution: PC 端 AI 助视学习软件
status: 原型开发中
summary: 面向白化病低视力中小学生的 PC 端 AI 助视阅读工具，本地离线 OCR + 视觉增强 + 大字阅读版，零网络依赖
---

# Albassist - PC 端 AI 助视学习软件

面向白化病低视力中小学生的室内学习阅读工具。使用 PC 相机或智能眼镜摄像头输入，把课本原图放大呈现，并用本地 AI（OCR）将选中文字转换成可调字号的大字阅读版，保持与原图位置对应。

## 团队成员

| 成员 | 角色 |
|------|------|
| 田媛 | 产品设计 / 需求分析 / 视觉增强方案 |
| 刘宏彬 | 架构设计 / 核心开发 / 质量守护 |
| 邹展彤 | OCR 集成 / 相机采集 / 测试覆盖 |

## 解决的问题

白化病低视力学生室内学习阅读面临三重困难：

1. **看不清** — 课本字号小、对比度低，低视力学生难以辨认
2. **看不久** — 持续凑近阅读导致眼疲劳，无法长时间学习
3. **不敢看** — 教室灯光眩光严重，白化病患者畏光

现有方案不足：光学放大镜手持不稳无 OCR；电子助视器昂贵不便携；手机拍照屏幕小无原图对应；通用 OCR App 需联网有隐私风险。

## 主要功能

- **实时相机预览**：本地摄像头 + 智能眼镜 MJPEG 流，统一选择
- **数字缩放**：1×—8× Lanczos 插值放大
- **视觉增强**：灰度、反色、对比度、二值化、局部对比度增强（CLAHE）、边缘、护眼模式
- **离线 OCR**：RapidOCR + ONNX Runtime，零网络依赖，中文识别
- **大字阅读版**：可调字号（24—96pt）、行距，文字块导航，原图位置对应
- **人脸提醒**：OpenCV Haar 级联离线检测 + 语音播报
- **偏好持久化**：SQLite 存储视觉配置，不存图像/OCR 正文

## 技术方案

| 技术 | 用途 |
|------|------|
| Python 3.13 + PySide6 | GUI 框架（Signal/Slot MVVM） |
| OpenCV 4.10 | 相机采集 + 图像处理 |
| RapidOCR + ONNX Runtime | 本地离线 OCR（PaddleOCR v4 ONNX 模型） |
| SQLite | 偏好持久化（WAL 模式） |
| DDD 分层架构 | domain ← application ← adapters，端口-适配器可替换 |

### 架构

```
src/albassist/
├── domain/           # 领域模型（纯 Python，零外部依赖）
├── application/      # 端口 + 用例 + 会话管理
├── vision/           # OpenCV 图像处理适配器
├── ocr_runtime/      # OCR 引擎适配器（RapidOCR / Fake）
├── infrastructure/   # 相机、SQLite、线程基础设施
├── presentation/     # PySide6 视图与 ViewModel
└── app/              # 组合根与入口
```

依赖契约由 import-linter 强制：domain 禁引外部库，application 禁引适配器，layers 单向依赖。

## 运行

```bash
# 安装依赖
pip install -e ".[dev]"

# 启动应用
PYTHONPATH=src python -m albassist.app.main

# 测试
PYTHONPATH=src python -m pytest

# 类型检查
PYTHONPATH=src python -m mypy src/albassist
```

### 配置智能眼镜摄像头

编辑 `src/albassist/app/main.py` 中 `network_camera_urls`：

```python
container = create_container(
    use_fake_ocr=False,
    network_camera_urls=("http://<眼镜IP>:<端口>/stream.mjpg",),
)
```

## 质量指标

- mypy strict：57 源文件零错误
- pytest：89 passed + 17 skipped（async 沙箱 skip）
- import-linter：3 条分层契约全通过

## 隐私与可信

- 本地优先：OCR 使用本地 ONNX 模型，零网络请求
- 不存敏感数据：SQLite 仅存视觉偏好
- 原图不可变：视觉增强在副本上执行
- 非生成式增强：仅做亮度/对比度映射

## 许可证

MIT