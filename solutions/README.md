# 方案提交指南 · Solutions

本赛题支持**多个团队、多条技术路线并行**。每个方案一个独立目录，由该团队自行维护，社区统一管理。

## 快速开始（三选一）

**方式 A · 网页直传（不会 Git 也能用）**
1. 点本仓库右上角 **Fork**（或已被邀请为组织成员的可跳过）；
2. `Add file → Create new file`，文件名输入 `solutions/队名-方案名/README.md`；
3. 写好方案说明 → Commit → **Create pull request**。也可用 `Upload files` 整个文件夹拖拽上传。

**方式 B · 命令行**
```bash
git clone https://github.com/OpenRDHub/<本赛题仓库>.git
cd <本赛题仓库>
git checkout -b solution-队名
mkdir -p solutions/队名-方案名
# 放入 README 与成果文件
git add . && git commit -m "solution: 队名-方案名 首版"
git push -u origin solution-队名   # 或推到自己 fork 后发 PR
```

**方式 C · 方案长大后独立建仓**：超过约 200MB、要发版或要商业化时，联系社区迁独立仓库，本目录保留跳转链接。

## 目录规范

```
solutions/
└── 队名-方案名/          ← 命名：中文队名-方案简称，路径即身份
    ├── README.md         ← 必须，开头带元信息（见下）
    ├── src/ 或 设计文件/  ← 代码 / CAD / 电路 / 模型
    └── docs/             ← 设计文档、测试记录、失败经验
```

**方案 README 开头请带以下元信息**（供总览表自动生成，缺省用目录名）：

```markdown
---
team: 醒伴队
solution: 语音提醒药盒
status: 原型开发中      # 构思中 / 设计中 / 原型开发中 / 测试中 / 可用 / 已迁出
summary: 一句话方案简介
repo: https://...      # 可选，已迁独立仓库时填写
---
```

## 规则（与社区共识一致）

1. **自主权**：各队只在自己目录内提交；本仓库 `CODEOWNERS` 会把目录所有权登记给对应团队，他人（含社区接待人）改动需该队批准；
2. **统一管理**：所有成果通过 PR 进入本仓库主分支；只改自己目录的 PR 由本队自行批准 + CI 通过即可合并，涉及共享区（赛题 README、docs/）或红线事项由社区接待人审批；
3. **阶段性提交**：不要憋大招——方案设计、原型、测试记录分批 PR，社区全程可见；
4. **隐私红线**：患者姓名、手机号、病历、影像等个人信息一律不得入库；测试照片需处理人脸；
5. **医疗边界**：未验证原型不得包装为诊疗工具；
6. **Fork 提示**：从 fork 发出的 PR 首次不会自动跑检查，需接待人点一下 "Approve and run"。

## 总览表

赛题 README 中的「方案总览」表格由 GitHub Actions 自动维护（扫描本目录各 README 元信息生成），无需手工更新。
