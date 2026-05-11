---
name: agent-config-maintenance
description: 在 agent_config/ 各 agent 設定檔中新增或移除指令來源（instruction source）。當新專案需要引入額外的 rules/skills 路徑、或某個來源不再適用時使用。
---

# Agent Config Maintenance

## agent_config/ 結構對照

| 檔案 | 工具 | 用途 |
|------|------|------|
| `.claude/CLAUDE.md` | Claude Code | 啟動時載入，支援 `@filepath` import（僅限存在的檔案） |
| `.claude/settings.local.json` | Claude Code | 工具權限設定 |
| `.codex/config.toml` | Codex CLI | 沙箱模式、審批政策、developer_instructions |
| `.gemini/settings.json` | Gemini CLI | 預設審批模式（yolo 只能 CLI flag，無法寫入設定） |
| `AGENTS.md` | Codex + OpenCode | 純文字指示，不支援 import，Codex/OpenCode 共用 |
| `GEMINI.md` | Gemini CLI | 支援 `@filepath` import（僅限 .md，巢狀 import 未確認） |
| `opencode.json` | OpenCode | `instructions` 陣列支援 glob，檔案不存在時自動略過 |

## 新增指令來源的更新規則

### 必須存在的來源（強制載入）

**Claude (`.claude/CLAUDE.md`)**：加入 `@path/to/file.md`
**Gemini (`GEMINI.md`)**：加入 `@path/to/file.md`，若需載入多個 rules 則逐一列出（避免依賴巢狀 import）
**Codex (`.codex/config.toml`)**：更新 `developer_instructions` 字串，加入「read X at session start」
**OpenCode (`opencode.json`)**：在 `instructions` 陣列加入路徑或 glob pattern

### 可能不存在的來源（選擇性載入）

**Claude / Gemini**：用文字指示（`If X exists, read it`），不用 `@` import，避免檔案不存在時報錯
**Codex**：同樣用文字指示
**OpenCode**：直接加入 `instructions` 陣列，glob 不存在時自動略過，最可靠

## 當前指令來源清單

### 共用來源（所有專案）
- `knowledge-base/agent_cli_file/catalogue.md` — 共用 rules/skills 索引
- `knowledge-base/agent_cli_file/rules/*.md` — 所有共用 rules（OpenCode 直接載入）

### 選擇性專案來源
- `.ai/catalogue.md` — 專案層級 rules/skills 索引（若存在則載入）
- `.ai/rules/*.md` — 專案層級 rules（OpenCode 直接載入）

## 各工具的完整設定範本

### Claude `.claude/CLAUDE.md`
```markdown
@knowledge-base/agent_cli_file/catalogue.md

If `.ai/catalogue.md` exists in this project, read it to load project-specific rules and skills.
```

### Gemini `GEMINI.md`
```markdown
@knowledge-base/agent_cli_file/catalogue.md

If `.ai/catalogue.md` exists in this project, read it to load project-specific rules and skills.
```
> 注意：Gemini `@` import 的巢狀解析（catalogue.md 內的 `@./rules/*.md`）尚未正式確認。
> 若發現 rules 未被載入，改為在此逐一列出 `@knowledge-base/agent_cli_file/rules/*.md`。

### Codex `AGENTS.md`
```markdown
At session start, read `knowledge-base/agent_cli_file/catalogue.md` to load all shared rules and skills.

If `.ai/catalogue.md` exists in this project, also read it to load project-specific rules and skills.
```

### OpenCode `opencode.json`
```json
{
  "permission": "allow",
  "instructions": [
    "knowledge-base/agent_cli_file/catalogue.md",
    "knowledge-base/agent_cli_file/rules/*.md",
    ".ai/catalogue.md",
    ".ai/rules/*.md"
  ]
}
```
