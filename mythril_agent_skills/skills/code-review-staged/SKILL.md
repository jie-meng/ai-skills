---
name: code-review-staged
description: |
  Context-aware code review for git STAGED changes (git diff --cached).
  Triggers when user mentions "暂存" (staged) with any review verb: 审查/评审/看/检查.
  Examples: '审查暂存', '评审暂存', '看看暂存', '看一下暂存', '检查暂存', '暂存区审查',
  '看一下暂存代码', '看看暂存的代码', '审查暂存代码', '检查暂存代码'.
  English triggers: 'review staged', 'staged code review', 'check staged', 'look at staged',
  'look at staged code', 'review staged code'.
  Reads related files to validate changes in context. Auto-generates and copies commit message.
  ONLY reviews staged changes, NOT unstaged or all changes.
license: Apache-2.0
---

# When to Use This Skill

**ALWAYS invoke this skill when user wants to review STAGED git changes:**

Chinese (关键词"暂存" + 动词: 审查/评审/看/检查):
- "审查暂存" / "审查暂存区" / "审查暂存的代码" / "暂存区审查" / "暂存区代码审查"
- "评审暂存" / "评审暂存区"
- "看看暂存" / "看一下暂存" / "看看暂存区" / "看一下暂存区"
- "检查暂存" / "检查暂存区"

English:
- "review staged" / "review staged changes" / "staged code review" / "staged CR"
- "check staged" / "look at staged" / "review cached changes"

**This skill is specifically for STAGED changes (git diff --cached).**
For remote GitHub PRs, use `github-code-review-pr` instead.

# Requirements

- **Working directory**: Must be inside a git repository
- **Review language**: Match the user's input language (Chinese or English)
- **Commit message**: Always in English, single line, max 72 characters

# Implementation

The skill executes these steps:

## Step 1: Get Staged Changes and Branch Info

Run these commands concurrently:

```bash
git diff --cached
git rev-parse --abbrev-ref HEAD
```

If no staged changes found, report and suggest `git add`.

## Step 2: Gather Repository Context

Since we're already inside the repository, context gathering is cheap and fast — just local file reads.

### 2a. Project structure overview

```bash
git ls-tree -r --name-only HEAD | head -200
```

This reveals the project's module organization, naming conventions, and architecture without reading any file content.

### 2b. Coding conventions and config files

Read key project files (if they exist) to understand coding standards. Prioritize by relevance to the changed files' languages.

**AI agent instruction files** (highest priority — these define project conventions explicitly):

| File | Tool |
|---|---|
| `AGENTS.md` | Cross-tool standard (Codex, Cursor, Copilot, Amp, Windsurf, Devin) |
| `CLAUDE.md` | Claude Code |
| `GEMINI.md` | Gemini CLI |
| `.github/copilot-instructions.md` | GitHub Copilot |
| `.cursorrules` / `.cursor/rules/` | Cursor |
| `.windsurfrules` / `.windsurf/rules/` | Windsurf |

**Project and build config files**:

| File | Purpose |
|---|---|
| `README.md` | Project overview |
| `CONTRIBUTING.md` | Development guidelines, contribution rules |
| `pyproject.toml` / `setup.cfg` | Python project config, linting rules |
| `package.json` | Node.js project config, lint config |
| `.editorconfig` | Editor formatting rules |
| `.eslintrc.*` / `biome.json` | JS/TS linting rules |
| `Makefile` / `Justfile` | Build conventions |
| `Cargo.toml` | Rust project config |
| `go.mod` | Go module config |
| `.clang-format` / `.clang-tidy` | C/C++ formatting rules |

**Constraints:**
- Read at most 3-5 config files — prioritize the ones most relevant to the changed files' languages
- Skim only; skip files larger than ~50KB

### 2c. Smart context retrieval for changed files

Analyze the diff to determine if related files need to be read for a high-quality review:
- **When to read context**:
    - If a function signature changes, check its usages or definition
    - If a class inherits from a base class not in diff, read the base class definition
    - If a variable type is unclear, check its declaration
    - If a config value changes, check where it's consumed if the impact is ambiguous
    - **Header/Source Pairing**: For C/C++, always check the corresponding `.h` or `.cpp` file if one is modified
    - **Tests**: Check if existing tests need updates or if new tests are consistent with existing patterns
- **Full file content**: For files with significant changes, read the entire file (not just the diff) to understand the complete context
- **Constraints**:
    - Read only 3-5 directly related files beyond the changed files themselves
    - Only read files that are strictly necessary to validate the correctness of the staged changes
    - If a file is huge, read only relevant sections

## Step 3: Detect Language

Analyze user's input to determine review output language:
- Contains Chinese characters → Chinese review
- Only English → English review
- Commit message always in English

## Step 4: Perform Code Review

Structure the review into these sections:

### If Chinese review requested:

#### 1. 变更概览
- 此 diff 主要做了什么（修复 bug、添加功能、重构、配置变更等）
- 变更规模和受影响的主要模块
- 项目的编码规范和风格（基于 config 文件和已有代码推断）
- 此变更是否符合项目整体风格和架构模式

#### 2. 代码质量 & Clean Code 评价
- 全面评估变更的代码风格、命名、注释、可读性、可维护性、设计架构、模块解耦、重复代码等
- 特别关注：变更是否与项目现有代码风格一致（命名惯例、代码组织方式、错误处理模式等）
- 发现任何易错写法、不安全代码、低效实现、反模式或不符合最佳实践的地方要具体列出
- 指出被修改的具体位置与问题描述（行号/文件名/代码片段，或足够明确的定位描述）
- 提出详细的修复/重构/优化建议，并解释理由

#### 3. 潜在的重大问题和风险
- 检查代码逻辑是否存在难以发现的 bug、异常未处理、未校验边界条件、性能瓶颈、安全隐患等
- 检查是否有遗漏的修改（如：改了接口但没改调用方，改了 schema 但没改迁移）
- 指出这些疑点，并简单说明为何值得关注

#### 4. 增量建议
- 给出进一步增强代码质量、工程可维护性、测试覆盖的建议
- 建议是否需要补充测试、文档、类型声明等

#### 5. 推荐提交信息
- 为此变更生成简洁、准确且符合规范的提交信息，**提交信息使用英文**
- **必须是单行，最多72个字符**
- **用一句话高度概括所有变更，不要列举细节**
- 如果分支名包含斜杠（如 `feat/item-definition`），使用格式：`type[scope]: message`
- 如果分支名不包含斜杠，使用常规格式：`type: message`
- 常用类型: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`

### If English review requested:

#### 1. Change Overview
- What this diff does (bug fix, feature, refactor, config change, etc.)
- Change scope and primary modules affected
- Project coding conventions and style (inferred from config files and existing code)
- Whether this change aligns with the project's overall style and architectural patterns

#### 2. Code Quality & Clean Code Evaluation
- Thoroughly assess code style, naming conventions, comments, readability, maintainability, architecture, modularity, code duplication, etc.
- Pay special attention to: whether changes are consistent with existing project code style (naming conventions, code organization, error handling patterns, etc.)
- Identify error-prone code, unsafe patterns, inefficient implementations, anti-patterns, or violations of best practices
- Clearly specify the exact location and nature of each problem (line number, filename, code snippet, or sufficiently precise description)
- Provide actionable suggestions for fixes/refactoring/optimization with explanatory reasoning

#### 3. Major Issues and Risks
- Evaluate hard-to-detect logic bugs, unhandled exceptions, missing boundary checks, performance bottlenecks, security vulnerabilities
- Check for missed changes (e.g., changed an interface but not its callers, changed a schema but not its migration)
- Point out suspicious areas and explain their potential impact

#### 4. Incremental Suggestions
- Suggestions for improving code quality, maintainability, and test coverage
- Whether additional tests, documentation, or type annotations are needed

#### 5. Recommended Commit Message
- Generate a concise, accurate, and conventional commit message, **in English**
- **MUST be a SINGLE LINE, maximum 72 characters**
- **Provide a high-level summary of all changes in ONE sentence**
- If branch name contains a slash (e.g., `feat/item-definition`), use format: `type[scope]: message`
- If branch name doesn't contain a slash, use conventional format: `type: message`
- Common types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`

## Step 5: Copy Commit Message to Clipboard

After generating the review, extract the commit message from Section 5 and copy it to clipboard:

```bash
# macOS
echo -n "commit message here" | pbcopy

# Linux (if xclip available)
echo -n "commit message here" | xclip -selection clipboard
```

If clipboard tools are unavailable, report the limitation but still display the commit message clearly for manual copying.

## Error Handling

- **No staged changes**: Report that no staged changes found and suggest using `git add`
- **Not a git repo**: Report and suggest navigating to a git repository
- **Language detection failure**: Default to English review
- **Clipboard failure**: Report error but STILL display the commit message prominently for manual copy
- **Large diff (>50 files)**: Warn the user; focus on the most critical files

## Examples

### Example 1: Chinese Request
**User input**: "审查暂存区的代码"
**Branch**: `feat/audio-support`
**Action**: Get staged diff → gather repo context locally → review in Chinese → copy commit message
**Output**: Context-aware Chinese review with commit message copied to clipboard

### Example 2: English Request
**User input**: "Review my staged changes"
**Branch**: `fix/wifi-connection`
**Action**: Get staged diff → gather repo context locally → review in English → copy commit message
**Output**: Context-aware English review with commit message copied to clipboard
