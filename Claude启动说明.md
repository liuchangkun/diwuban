# Claude Code 快速启动指南

## 方式1: VSCode扩展（已配置自动批准）

1. 重启VSCode窗口：`Ctrl+Shift+P` → `Developer: Reload Window`
2. MCP工具应该可以自动执行，不再需要确认

**配置位置**: `settings.json` 已添加：
- `claude.permissions.autoApprove: true`
- `claude.workspace.skipApprovalForKnownTools: true`

---

## 方式2: CLI模式（完全无权限确认）

如果VSCode扩展仍然需要确认，使用CLI模式：

### Windows:
```bash
# 双击运行
启动Claude-无权限确认.bat
```

### 手动启动:
```bash
cd d:\Augment\diliuban
claude-code --dangerously-skip-permissions
```

---

## 对比

| 方式 | 优点 | 缺点 |
|------|------|------|
| VSCode扩展 | 集成IDE，界面友好 | 可能仍需部分确认 |
| CLI模式 | 完全无确认，MCP工具自由调用 | 需要终端操作 |

---

## 推荐使用流程

1. **优先使用VSCode扩展**（已配置好）
2. **如遇到确认提示**，使用 `启动Claude-无权限确认.bat`
3. **日常开发**：CLI模式效率最高

---

**配置文件位置**：
- 全局配置: `C:\Users\Administrator\AppData\Roaming\Code\User\settings.json`
- 项目配置: `d:\Augment\diliuban\.claude\claude-settings.json`
