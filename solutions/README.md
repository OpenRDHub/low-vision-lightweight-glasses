# 方案提交指南 · Solutions

> 🏆 **黑客松比赛提交（截止 2026-10-17 周六 12:00）**
> 请按官方 [《开源代码与 Demo 提交规则及操作方法》](https://lcnh7zi6opm8.feishu.cn/docx/IN8VdvcwMoyin4xGd0WcO65OnMg) 操作：
> **Fork 本仓库 → 在自己的 Fork 上传代码 / 项目 README / LICENSE（任一 OSI 协议）→ 在魔搭（组织：Khub罕见病开源社区）发布 Demo**。
> **无需向本仓库提交 PR，无需把代码传回官方仓库。**
> 提交后请在本仓库开一个 [「提交成果链接」Issue](../../issues/new/choose)，主办方会把你的 Fork 与 Demo 链接汇总进 README 的「方案总览」。

> 🌱 **本目录（solutions/）用于赛后社区共建**
> 比赛结束后，希望把方案沉淀进官方仓库长期维护的团队，欢迎按下面指南提交 PR；多团队、多技术路线并行，各目录由所属团队自行维护，社区统一管理。

## 社区共建提交方式（三选一）

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
├── links.json            ← 官方成果登记表（主办方维护，README 总览自动读取）
└── 队名-方案名/           ← 社区共建方案目录
    ├── README.md         ← 必须，开头带元信息（见下）
    ├── src/ 或 设计文件/
    └── docs/
```

**共建方案 README 开头请带元信息**（供总览表自动生成，缺省用目录名）：

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

1. **自主权**：各队只在自己目录内提交；本仓库 `CODEOWNERS` 把目录所有权登记给对应团队，他人（含社区接待人）改动需该队批准；
2. **统一管理**：共建成果通过 PR 进入本仓库主分支；只改自己目录的 PR 由本队批准 + CI 通过即可合并，涉及共享区或红线事项由社区接待人审批；
3. **隐私红线**：患者姓名、手机号、病历、影像等个人信息一律不得入库；测试照片需处理人脸；**API Key / Token / 未经授权的第三方代码不得上传**；
4. **医疗边界**：未验证原型不得包装为诊疗工具；
5. **Fork 提示**：从 fork 发出的 PR 首次不会自动跑检查，需接待人点一下 "Approve and run"。

## 总览表

赛题 README 中的「方案总览」表格由 GitHub Actions 自动维护，数据来源两个：
- `solutions/*/README.md` 的 frontmatter（共建方案）
- `solutions/links.json`（比赛成果登记，来自「提交成果链接」Issue，主办方录入）
