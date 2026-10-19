---
team: Albassist Team
solution: PC 端 AI 助视学习软件
status: 原型开发中
summary: 面向白化病低视力中小学生的 PC 端 AI 助视阅读工具，本地离线 OCR + 视觉增强 + 大字阅读版，零网络依赖
---

# Albassist - PC 端 AI 助视学习软件

面向白化病低视力中小学生的室内学习阅读工具。使用 PC 相机或智能眼镜摄像头输入，把课本原图放大呈现，并用本地 AI（OCR）将选中文字转换成可调字号的大字阅读版，保持与原图位置对应。

## 项目背景

白化病（Albinism）患者因基因缺陷导致黑色素合成不足，常伴随**重度畏光**和**低视力**（视力通常 0.01—0.3）。中国人群发病率约 1/18,000，患者约 10 万人，其中 >90% 伴眼球震颤。目前无根治手段，**未来 3—5 年助视需求刚性不变**。

核心病理机制：白化病低视力不是「模糊」，是「细节少」——患者保有残余视力，核心诉求是**「自己看清楚」**而非「听朗读」。唯一有效路径是**把图像放大到能辨识的程度**。

中小学阶段白化病低视力学生在室内学习阅读课本时面临三重困难：

1. **看不清** — 课本字号小（约 10pt）、对比度低，低视力学生难以辨认
2. **看不久** — 持续凑近阅读导致眼疲劳、头痛，无法长时间学习
3. **不敢看** — 教室灯光眩光严重，白化病患者畏光，强光下几乎无法睁眼

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

### 配置文件说明

| 文件 | 作用 |
|------|------|
| `pyproject.toml` | 项目元数据、依赖、mypy strict、pytest asyncio_mode、import-linter 三条分层契约 |
| `conftest.py` | pytest 全局配置：检测 asyncio 事件循环可用性，不可用时 skip async 测试 |
| `src/albassist/app/main.py` | 应用入口：配置眼镜 MJPEG 地址、创建 DI 容器并装配所有依赖 |
| `src/albassist/app/composition_root.py` | 依赖装配：`create_container(use_fake_ocr, db_path, network_camera_urls)` |
| `albassist_preferences.db` | 运行时生成：SQLite 偏好数据库（WAL 模式），不存图像/OCR 正文 |

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