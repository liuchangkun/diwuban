# Git 快捷别名使用指南

> 已配置的Git全局别名,大幅提升Git操作效率

**创建时间**: 2025-12-16
**状态**: ✅ 已生效

---

## 📋 基础别名

### 状态和导航
```bash
# 查看状态(简洁格式)
git st
# 等同于: git status -sb

# 切换分支
git co <branch-name>
# 等同于: git checkout <branch-name>

# 查看分支
git br
# 等同于: git branch

# 提交
git ci -m "提交信息"
# 等同于: git commit -m "提交信息"
```

---

## 🔧 实用操作

### 撤销和修改
```bash
# 取消暂存
git unstage <file>
# 等同于: git reset HEAD -- <file>

# 查看最后一次提交
git last
# 等同于: git log -1 HEAD

# 修正最后一次提交(不改消息)
git amend
# 等同于: git commit --amend --no-edit

# 撤销最后一次提交(保留更改)
git undo
# 等同于: git reset --soft HEAD^
```

### 清理
```bash
# 清理未跟踪的文件和目录
git cleanup
# 等同于: git clean -fd
# ⚠️ 警告: 会删除未跟踪的文件,谨慎使用!
```

---

## 📊 可视化和信息

```bash
# 图形化查看提交历史
git visual
# 等同于: git log --graph --oneline --decorate --all

# 查看所有分支(包括远程)
git branches
# 等同于: git branch -a

# 查看所有标签
git tags
# 等同于: git tag -l

# 查看远程仓库
git remotes
# 等同于: git remote -v

# 查看所有别名
git aliases
# 列出所有已配置的Git别名
```

---

## 🚀 高级组合命令

### 快速保存
```bash
# 快速提交所有更改
git save "提交信息"
# 等同于: git add -A && git commit -m "提交信息"

# 示例:
git save "修复BUG: 泵效率计算异常"
```

### 快速推送
```bash
# 快速提交并推送
git quickpush "提交信息"
# 等同于: git add -A && git commit -m "提交信息" && git push

# 示例:
git quickpush "feat: 添加泵扭矩计算功能"
```

### 同步远程
```bash
# 同步所有远程分支并rebase
git sync
# 等同于: git fetch --all && git pull --rebase

# 使用场景: 开始工作前同步最新代码
```

---

## 💡 典型工作流示例

### 场景1: 日常开发
```bash
# 1. 同步远程代码
git sync

# 2. 创建功能分支
git co -b feature/new-metric

# 3. 修改代码...

# 4. 查看状态
git st

# 5. 快速提交
git save "实现新指标计算"

# 6. 推送到远程
git push origin feature/new-metric
```

### 场景2: 快速修复
```bash
# 1. 切换到主分支
git co main

# 2. 同步最新代码
git sync

# 3. 创建修复分支
git co -b fix/bug-123

# 4. 修改代码...

# 5. 快速提交并推送
git quickpush "fix: 修复泵效率计算异常"
```

### 场景3: 提交失误修正
```bash
# 1. 发现上次提交有问题
git last  # 查看上次提交

# 2. 修改代码

# 3. 修正提交(不改消息)
git amend

# 或者: 撤销提交重新来
git undo
git save "正确的提交信息"
```

### 场景4: 清理工作区
```bash
# 1. 查看状态
git st

# 2. 取消暂存某个文件
git unstage app/config/test.py

# 3. 清理未跟踪的文件
git cleanup  # ⚠️ 谨慎使用!
```

---

## 📈 效率提升

使用这些别名可以节省:

| 操作 | 原命令 | 别名 | 节省字符 |
|------|--------|------|---------|
| 查看状态 | `git status` (11字符) | `git st` (6字符) | **45%** |
| 切换分支 | `git checkout` (13字符) | `git co` (6字符) | **54%** |
| 快速提交 | `git add -A && git commit -m` (27字符) | `git save` (8字符) | **70%** |
| 图形日志 | `git log --graph --oneline --decorate --all` (43字符) | `git visual` (10字符) | **77%** |

**平均节省 60% 的输入时间!**

---

## 🔍 查看和管理别名

### 查看所有别名
```bash
git aliases
```

### 查看特定别名定义
```bash
git config --global alias.st
```

### 删除别名
```bash
git config --global --unset alias.st
```

### 修改别名
```bash
git config --global alias.st "status -s"
```

---

## 🎓 最佳实践

### 推荐使用频率
- 🔥 **每天必用**: `git st`, `git save`, `git sync`
- ⭐ **经常使用**: `git co`, `git br`, `git last`
- 💡 **偶尔使用**: `git amend`, `git undo`, `git visual`
- ⚠️ **谨慎使用**: `git cleanup` (会删除未跟踪文件)

### 记忆技巧
- `st` = **St**atus
- `co` = **C**heck**o**ut
- `br` = **Br**anch
- `ci` = **C**heck **i**n (提交)
- `save` = 保存所有更改
- `sync` = 同步远程

---

## ⚠️ 注意事项

### git cleanup
```bash
# ⚠️ 危险操作! 会永久删除未跟踪的文件和目录
git cleanup

# 建议先预览:
git clean -nfd  # -n 表示dry-run(预览)
```

### git undo
```bash
# 只撤销提交,保留更改
git undo

# 如果要彻底撤销(包括更改):
git reset --hard HEAD^  # ⚠️ 危险! 会丢失更改
```

### git quickpush
```bash
# 会自动推送到远程,确保:
# 1. 当前分支有远程跟踪分支
# 2. 有推送权限
# 3. 没有冲突
```

---

## 🔗 相关文档

- [开发工作流程规范](开发工作流程规范.md#阶段七-提交与发布)
- [编码规范](编码规范.md#14-提交与评审)
- [Git官方文档](https://git-scm.com/book/zh/v2)

---

## 📝 自定义扩展

如果您想添加更多别名:

```bash
# 添加新别名
git config --global alias.your-alias "your command"

# 示例: 添加一个查看贡献者的别名
git config --global alias.contributors "shortlog -sn"

# 使用:
git contributors
```

---

**提示**: 这些别名是全局配置,适用于您的所有Git仓库!

**维护者**: AI助手
**状态**: ✅ 已配置并测试通过
