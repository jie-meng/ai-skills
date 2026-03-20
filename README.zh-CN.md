# mythril-agent-skills

面向多智能体 AI 编程助手的统一技能管理系统。本工具包（以 Python 包形式分发）提供一套精选的可复用技能集合，以及用于在 Github Copilot、Claude Code、Cursor、Codex、Gemini CLI 等工具之间安装、配置和维护技能的集中式 CLI 命令。

[English](./README.md) | 中文

## 什么是 Skill？

Skill（技能）是一个提示词/指令包，用于教 AI 助手如何处理特定类型的任务。可以把它理解为一个专用工具：它有名称、触发描述和详细的操作指令。

根据作用范围和管理方式，技能主要分为两类：

| 特性 | 用户级技能（全局） | 项目级技能（本地） |
| :--- | :--- | :--- |
| **作用范围** | 在你所有项目中均可使用 | 仅限特定项目仓库 |
| **可移植性** | 在同一台机器的不同项目间复用 | 随该项目仓库一起移动 |
| **适用场景** | 通用工具（如 Jira 集成、代码审查、Git 操作、Figma） | 项目专属规则（如自定义 UI 规范、特定构建/部署步骤） |
| **管理方式** | 安装在用户主目录（`~/.claude/skills`、`~/.cursor/skills` 等） | 存放在项目目录内（如 `.claude/skills/`、`.github/skills/`） |
| **版本控制** | 通过本工具包集中管理 | 提交到项目 Git 仓库，供团队共享 |

### 本工具包的定位

**`mythril-agent-skills` 专门用于管理用户级技能。** 它作为集中式 CLI 工具包，负责在你机器上的多个 AI 编程助手之间安装、配置并保持通用技能同步。

对于**项目级技能**，无需使用本安装器。我们推荐使用内置的 **[Skill Creator](./mythril_agent_skills/skills/skill-creator/)** 技能，在项目工作区中直接调用它来生成项目专属技能，然后提交到版本控制系统，让整个团队受益。

## 可用技能

[English](./README.md) | 中文

<details>
<summary><b>Meta</b></summary>
<br>

**[Skill Creator](./mythril_agent_skills/skills/skill-creator/)**

为任意 AI 平台创建/优化技能和提示词，含起草、测试用例生成、评估、基准测试、描述优化。

- **示例：** 帮我创建一个 Cursor skill
- **依赖：** —

</details>

<details>
<summary><b>Code Review</b></summary>
<br>

**[Code Review (Staged)](./mythril_agent_skills/skills/code-review-staged/)**

针对 Git 暂存区变更的上下文感知代码审查，读取相关文件验证，自动生成并复制 commit message。

- **示例：** 审查暂存的代码
- **依赖：** `git` CLI

**[Code Review (Local Branch Diff)](./mythril_agent_skills/skills/branch-diff-review/)**

纯本地 git 操作对比分支差异，无需平台 API，支持任意 git 仓库（GitHub、GitLab、Gitee、Bitbucket 等）。

- **示例：** Review 一下 feat/123 合到 main
- **依赖：** `git` CLI

**[Code Review (GitHub PR)](./mythril_agent_skills/skills/github-code-review-pr/)**

通过 `gh` CLI 对 Pull Request 进行上下文感知代码审查，支持 github.com 和 GitHub Enterprise（任意域名），使用 partial clone + sparse checkout 获取深层仓库上下文。

- **示例：** 审查这个 PR https://github.com/xxx/yyy/pull/100
- **依赖：** `git` CLI, `gh` CLI

</details>

<details>
<summary><b>Git & GitHub</b></summary>
<br>

**[Git Repo Reader](./mythril_agent_skills/skills/git-repo-reader/)**

克隆、缓存并阅读任意托管平台的 git 仓库（GitHub、GitLab、Gitee、Bitbucket 等），支持跨会话复用缓存。

- **示例：** 看看这个仓库 https://github.com/xxx/yyy
- **依赖：** `git` CLI

**[GH Operations](./mythril_agent_skills/skills/gh-operations/)**

使用 GitHub CLI (`gh`) 执行 GitHub issue/PR 工作流：读写 issue、查看/创建 PR、添加 PR 评论（含行内 review 评论）。

- **示例：** 看看这个 issue https://github.com/xxx/yyy/issues/18331
- **依赖：** `gh` CLI

</details>

<details>
<summary><b>API Integrations</b></summary>
<br>

**[Jira](./mythril_agent_skills/skills/jira/)**

通过 Jira REST API（内置 Python 脚本）处理 issue、sprint 和 board 工作流，无需 CLI 工具。

- **示例：** 看一下这个 Jira ticket https://yourorg.atlassian.net/browse/PROJ-123
- **依赖：** `ATLASSIAN_API_TOKEN`, `ATLASSIAN_USER_EMAIL`, `ATLASSIAN_BASE_URL`

**[Confluence](./mythril_agent_skills/skills/confluence/)**

通过 Confluence REST API（内置 Python 脚本）处理 page、space、comment 和 label 工作流，无需 CLI 工具。

- **示例：** 看一下这个 Confluence 页面 https://yourorg.atlassian.net/wiki/spaces/XX/pages/123
- **依赖：** `ATLASSIAN_API_TOKEN`, `ATLASSIAN_USER_EMAIL`, `ATLASSIAN_BASE_URL`

**[Figma](./mythril_agent_skills/skills/figma/)**

从 Figma 文件提取设计规格用于实现，涵盖布局、颜色、字体、组件规格，遇到 Figma 链接自动触发。

- **示例：** 这个 Figma 设计是什么样子 https://figma.com/file/xxx
- **依赖：** `FIGMA_ACCESS_TOKEN`

</details>

<details>
<summary><b>Media Processing</b></summary>
<br>

**[ImageMagick](./mythril_agent_skills/skills/imagemagick/)**

通过 ImageMagick CLI 处理图片，支持缩放、格式转换、裁剪、缩略图、特效、水印、批量处理和元数据提取。

- **示例：** 把 photo.jpg 缩放到 800x600
- **依赖：** `magick` CLI

**[FFmpeg](./mythril_agent_skills/skills/ffmpeg/)**

通过 FFmpeg CLI 处理视频和音频，支持转码、格式转换、裁剪、合并、缩放、压缩、提取音频/字幕、GIF 创建，以及音频格式转换（MP3、WAV、PCM、OGG、AAC、FLAC、OPUS）。

- **示例：** 把 video.mov 转成 mp4
- **依赖：** `ffmpeg` CLI

</details>

---

## 快速开始

根据需求选择适合你的方式：

### 方式 A：直接使用现有技能（通过 pip 安装）

如果只想安装并使用现成的技能，从这里开始。
从 PyPI 安装，无需克隆仓库：

```bash
pip install mythril-agent-skills
```

升级到最新版本：

```bash
pip install -U mythril-agent-skills
```

安装后提供四个命令：

| 命令 | 描述 |
|---|---|
| `skills-setup` | 交互式安装器 — 选择 AI 工具和要安装的技能 |
| `skills-cleanup` | 交互式卸载器 — 选择已安装的技能进行移除 |
| `skills-check` | 依赖检查器 — 验证并配置所需的 CLI 工具和 API 密钥 |
| `skills-clean-cache` | 缓存清理器 — 删除技能运行时产生的临时文件 |

**安装技能：**

```bash
skills-setup              # 交互式：选择工具，再选择技能
skills-setup .cursor      # 直接指定目标：跳过工具选择步骤
```

**移除技能：**

```bash
skills-cleanup
```

**检查依赖：**

```bash
skills-check                    # 交互式：选择要检查的技能
skills-check gh-operations jira figma  # 检查指定技能
```

**清理缓存临时文件：**

```bash
skills-clean-cache          # 交互式：列出缓存内容，确认后删除
skills-clean-cache --force  # 直接删除，不询问确认
skills-clean-cache --show-repos  # 可选：显示已缓存的仓库名称和大小
```

检查器将会：
- 无参数运行时启动交互式 UI 让你选择技能
- 检测缺失的 CLI 工具（如 `gh`）并提供自动安装选项
- 提示输入缺失的 API 密钥/Token 并保存到 shell 配置文件
- 验证认证状态（如 `gh auth status`）

### 方式 B：自定义技能（GitHub Fork 或独立克隆）

如果想自定义技能并维护自己的仓库，有两种等效方式：

- **GitHub fork**（保持与 github.com 上游的关联）
- **独立克隆**（完全脱离上游，可托管在任意平台）

选择以下一种方式进行初始化，然后按照后面的共用步骤操作。

**方式 A — GitHub Fork（与上游保持关联）：**

```bash
# 在 GitHub 上 Fork，然后克隆你的 Fork：
git clone https://github.com/<your-username>/mythril-agent-skills.git
cd mythril-agent-skills
```

**方式 B — 独立克隆（与上游脱钩，可用于非 GitHub 平台）：**

```bash
# 1. 克隆原始仓库
git clone https://github.com/jie-meng/mythril-agent-skills.git
cd mythril-agent-skills

# 2. 与上游脱钩（删除 .git，创建全新仓库）
python3 scripts/init-fork.py

# 3. 按照屏幕提示将代码推送到新的远程仓库
```

初始化脚本将会：
- 删除 `.git` 历史记录（切断与上游的关联）
- 执行 `git init`（空仓库 — 你自己创建第一个 commit）
- 可选：重命名根目录

> **警告**：此操作不可逆，仅执行一次。请在全新克隆的副本上运行。

**两种方式的共用步骤：**

直接运行脚本，无需安装：

```bash
python3 scripts/skills-setup.py       # 交互式安装器
python3 scripts/skills-cleanup.py     # 交互式卸载器
python3 scripts/skills-check.py       # 依赖检查器
```

**与上游保持同步（可选）：**

- **方式 A（GitHub fork）**：使用 GitHub 内置的 **"Sync fork"** 按钮
- **方式 B（独立克隆）**：使用内置同步脚本（见下方）

```bash
python3 scripts/sync-upstream.py              # 交互式同步
python3 scripts/sync-upstream.py --dry-run     # 仅预览变更
python3 scripts/sync-upstream.py --force        # 直接应用，不询问确认
```

同步脚本只处理上游已存在的技能。**你自定义的、名称唯一的技能永远不会被覆盖** — 无需任何配置。

只有当你需要防止某个**上游技能**被覆盖时，才在 `.sync-upstream.json` 中使用 `exclude_skills`（例如：你在本地修改过 `jira`，或者想保护一个自定义技能名，以防上游未来新增同名技能）：

```json
{
  "exclude_skills": ["jira"]
}
```

完整指南请参阅 **[docs/FORK-SYNC.md](./docs/FORK-SYNC.md)**。

- 如果你**只新增名称唯一的自定义技能**，效果最佳 — 不会产生冲突
- 如果你**修改过上游技能**（如自定义了 `jira`），同步时可能出现需要手动解决的合并冲突

---

## 安装器工作原理

`skills-setup` 命令会引导你完成两个交互式界面：

1. **选择 AI 工具** — 选择要将技能安装到哪些工具
2. **选择技能** — 选择要安装哪些技能

```
Select skills to install:
Up/Down move | Space toggle | a all/none | Enter confirm | q quit

  [x]  Select All / Deselect All
  ------------------------------------
  [x]  code-review-staged
  [x]  figma
  [x]  gh-operations
  [x]  jira
  [x]  skill-creator

  5/5 selected
```

未在你机器上安装的工具将以灰色显示并标注 `[-]`，无法被选中。

安装完成后，对于需要外部依赖（CLI 工具或 API Token）的技能，`skills-check` 会自动运行。

### 支持的工具及技能路径

所有配置目录均相对于用户主目录（macOS/Linux 为 `~`，Windows 为 `%USERPROFILE%`）。

| # | 工具 | 技能路径 |
|---|---|---|
| 1 | Copilot CLI / VS Code | `~/.copilot/skills/` |
| 2 | Claude Code | `~/.claude/skills/` |
| 3 | Cursor | `~/.cursor/skills/` |
| 4 | Codex | `~/.codex/skills/` |
| 5 | Gemini CLI | `~/.gemini/skills/` |
| 6 | Qwen CLI | `~/.qwen/skills/` |
| 7 | Opencode | `~/.config/opencode/skills/` |
| 8 | Grok CLI | `~/.grok/skills/` |

### 卸载已安装的技能

```bash
skills-cleanup
```

卸载命令同样引导你完成两个界面：

1. **选择 AI 工具** — 选择要扫描哪些工具目录（默认扫描所有已检测到的）
2. **选择要移除的技能** — 树形视图展示每个工具及其已安装的技能（默认不选中）

```
Select skills to remove:
Up/Down move | Space toggle | a all/none | Enter confirm | q quit

  [ ]  Select All / Deselect All
  ------------------------------------
  Copilot CLI  ~/.copilot/skills/  (0/3)
      [ ]  code-review-staged
      [ ]  figma
      [ ]  skill-creator
  Cursor  ~/.cursor/skills/  (0/2)
      [ ]  gh-operations
      [ ]  jira

  0/5 selected for removal
```

### 项目级安装

如需在项目级别安装技能，手动复制即可：

```bash
cp -r mythril_agent_skills/skills/skill-name ./your-project/.github/skills/
# 或
cp -r mythril_agent_skills/skills/skill-name ./your-project/.claude/skills/
```

---

## 项目结构

```
mythril-agent-skills/
├── mythril_agent_skills/        # Python 包
│   ├── cli/                     # CLI 入口点
│   │   ├── skills_setup.py      # 交互式安装器
│   │   ├── skills_cleanup.py    # 交互式卸载器
│   │   └── skills_check.py      # 依赖检查器与配置器
│   └── skills/                  # 内置技能定义
│       ├── skill-creator/       # 创建和改进技能
│       ├── figma/               # 从 Figma 提取设计规格
│       ├── gh-operations/       # GitHub CLI issue/PR/commit 工作流
│       ├── ffmpeg/              # 通过 FFmpeg CLI 处理视频和音频
│       ├── imagemagick/         # 通过 ImageMagick CLI 处理图片
│       ├── jira/                # Jira REST API issue/sprint/board 工作流
│       ├── code-review-staged/  # 结构化代码审查
│       └── git-repo-reader/     # 克隆并阅读任意 git 仓库
├── scripts/                     # 开发脚本及向后兼容包装器
│   ├── sync-upstream.py         # Fork 上游同步工具
│   └── init-fork.py             # 一次性 Fork 初始化（脱钩 + git 重初始化）
├── docs/
│   ├── INSTALLATION.md          # 完整依赖参考
│   ├── PUBLISHING.md            # PyPI 发布与测试指南
│   └── FORK-SYNC.md             # Fork 同步指南
├── .sync-upstream.json           # 上游同步配置（供 Fork 使用）
├── pyproject.toml               # 包配置
├── AGENTS.md                    # 面向 Agent 的开发规范
├── LICENSE                      # Apache 2.0 许可证
└── README.md                    # 英文版说明
```

### 技能目录结构

每个技能遵循以下模式：

```
mythril_agent_skills/skills/skill-name/
├── SKILL.md                  # 必需：元数据 + 指令
├── README.md                 # 可选：人类可读概览
├── scripts/                  # 可选：辅助脚本（Python/Bash）
├── references/               # 可选：文档、指南、Schema
├── agents/                   # 可选：评估用提示词
└── assets/                   # 可选：模板、图标、HTML 资源
```

---

## 开发者指南

### 新增技能

1. 在 `mythril_agent_skills/skills/` 下创建新目录：
   ```bash
   mkdir mythril_agent_skills/skills/my-skill
   ```

2. 创建带有必要 frontmatter 的 `SKILL.md`：
   ```yaml
   ---
   name: my-skill
   description: |
      What this skill does and when to use it.
     Include trigger keywords for better AI assistant activation.
   license: Apache-2.0
   ---

   # My Skill

   Detailed instructions, examples, and workflows...
   ```

3. 按以下格式提交：
   ```bash
   git add .
   git commit -m "[my-skill] Add initial skill with core workflows"
   ```

完整的开发规范和发布说明，请参阅 **[AGENTS.md](./AGENTS.md)** 和 **[docs/PUBLISHING.md](./docs/PUBLISHING.md)**。

---

## 贡献指南

1. **Fork 或创建分支**，然后新增技能
2. **遵循** [AGENTS.md](./AGENTS.md) 中的代码风格和结构规范
3. **提交**时使用描述性信息，格式为：`[skill-name] Brief description`
4. **开启 Pull Request**，并附上技能用途和使用方式的说明

---
