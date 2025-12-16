# MCP 工具和技能推荐清单

> **目标**: 为复杂Python项目开发提供完整的 MCP 工具生态系统,提升开发效率、代码质量和知识管理能力

---

## 📊 当前已安装工具

根据您的配置,已安装以下 MCP 工具:

### ✅ 核心工具 (已安装并配置)
1. **Context7** - 库文档检索
2. **Sequential Thinking** - 问题分解与反思
3. **Postgres** - 数据库只读查询
4. **Time** - 时间与时区处理
5. **Memory** - 长期记忆管理
6. **Spec Workflow** - 规格工作流管理
7. **Exa** - Web搜索与代码搜索
8. **DeepWiki** - 深度文档获取

---

## 🎯 推荐安装的额外工具

基于您的项目特点(复杂Python系统、大数据量、个人开发),以下是强烈推荐的工具:

### 🔥 高优先级 (立即安装)

#### 1. **GitHub MCP Server** ⭐⭐⭐⭐⭐
**用途**: GitHub 仓库管理、Issue自动化、PR工作流

**为什么适合你**:
- ✅ 个人开发者友好,自动化日常Git操作
- ✅ Issue管理更高效 (节省30分钟/天)
- ✅ PR模板自动填充

**安装方式**:
```bash
npm install -g @modelcontextprotocol/server-github
```

**配置示例**:
```json
{
  "mcpServers": {
    "github": {
      "command": "mcp-server-github",
      "args": [],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "你的token"
      }
    }
  }
}
```

**典型用例**:
- 自动创建PR并填充模板
- 批量关闭已解决的Issue
- 搜索跨仓库代码

---

#### 2. **Firecrawl MCP Server** ⭐⭐⭐⭐⭐
**用途**: 网页抓取与数据提取,技术文档自动归档

**为什么适合你**:
- ✅ 自动抓取PostgreSQL/FastAPI最新文档
- ✅ 提取关键API示例到本地知识库
- ✅ 监控依赖库变更日志

**安装方式**:
```bash
npm install -g @mendable/firecrawl-mcp
```

**典型用例**:
- 抓取 PostgreSQL 16 新特性页面
- 自动下载 scikit-learn API 文档
- 监控 pandas 2.x 迁移指南更新

---

#### 3. **Qdrant / Chroma MCP Server** ⭐⭐⭐⭐
**用途**: 向量数据库,语义搜索代码片段和文档

**为什么适合你**:
- ✅ 用自然语言搜索代码: "如何计算泵效率"
- ✅ 相似代码模式推荐
- ✅ 减少重复造轮子

**安装方式** (Chroma更轻量):
```bash
pip install chromadb
npm install -g @chroma/mcp-server
```

**典型用例**:
```python
# AI 助手可以这样搜索
query = "SQL参数化防注入的正确写法"
results = vector_db.search(query, top_k=3)
# 返回项目中已有的3个最佳示例
```

---

#### 4. **Apifox MCP Server** ⭐⭐⭐⭐
**用途**: API文档管理,自动生成接口测试代码

**为什么适合你**:
- ✅ 管理30+计算指标的API接口
- ✅ AI自动生成API调用代码
- ✅ 接口变更自动同步文档

**安装方式**:
参考 [Apifox MCP 官方文档](https://apifox.com/docs/mcp)

**典型用例**:
- 定义 `POST /api/calculate/pump-efficiency` 接口
- AI自动生成调用代码和测试用例
- 变更接口参数时自动更新文档

---

### 💡 中优先级 (根据需求选择)

#### 5. **Playwright MCP** (已安装但可增强)
**建议用法**:
- 自动截取数据库监控界面
- 定期检查pgAdmin性能指标
- 抓取第三方系统集成页面

**增强配置**:
```json
{
  "playwright": {
    "headless": true,
    "screenshot_quality": 90,
    "max_pages": 5
  }
}
```

---

#### 6. **Notion / Obsidian MCP**
**用途**: 知识库同步,双向笔记链接

**为什么有用**:
- ✅ 将PLAYBOOKS同步到个人笔记系统
- ✅ 通过双链建立知识网络
- ✅ 移动端随时查阅

**安装方式**:
```bash
# Obsidian MCP (本地Markdown)
npm install -g @obsidian/mcp-server
```

---

#### 7. **Slack / 企业微信 MCP**
**用途**: 异常告警、日报自动发送

**典型用例**:
- 数据导入失败自动发送告警
- 每日性能报告推送到手机
- 代码审查提醒

---

### 🔧 专业工具 (高级需求)

#### 8. **LlamaCloud MCP**
**用途**: 高级RAG系统,NL2SQL查询

**为什么值得关注**:
- ✅ 自然语言查询数据库: "过去7天效率最低的泵"
- ✅ 自动生成复杂SQL
- ✅ 与现有PostgreSQL深度集成

**适用场景**: 当需要面向非技术人员提供查询界面时

---

#### 9. **MLflow / Weights & Biases MCP**
**用途**: 机器学习实验跟踪

**为什么有用**:
- ✅ 跟踪特性曲线拟合的188种方法性能
- ✅ 自动记录超参数和指标
- ✅ 可视化模型对比

**适用场景**: 优化曲线拟合算法时

---

## 🎨 推荐的 Claude Skills (技能)

### ✅ 立即创建的 Skills

#### Skill 1: `/质量检查`
```markdown
# .claude/skills/quality-check.md

运行完整的代码质量检查流程:
1. 运行 ruff check app/
2. 运行 black app/ --check
3. 运行 mypy app/
4. 运行 pytest tests/ --tb=short
5. 检查 git status 是否有未提交文件
6. 总结所有发现的问题并给出修复建议
```

#### Skill 2: `/代码审查`
```markdown
# .claude/skills/code-review.md

对最近的代码变更进行审查:
1. 运行 git diff HEAD~1 查看变更
2. 检查是否遵循编码规范 (docs/编码规范.md)
3. 验证类型注解完整性
4. 确认SQL参数化
5. 检查是否有敏感信息泄露
6. 生成审查报告
```

#### Skill 3: `/性能分析`
```markdown
# .claude/skills/performance-profile.md

分析数据库性能:
1. 连接PostgreSQL (只读)
2. 查询 pg_stat_statements 慢查询TOP10
3. 检查分区裁剪是否生效
4. 分析索引命中率
5. 查看连接池使用情况
6. 生成性能优化建议
```

#### Skill 4: `/文档同步`
```markdown
# .claude/skills/sync-docs.md

自动同步文档:
1. 扫描git diff,识别变更文件
2. 更新对应的PLAYBOOKS条目
3. 检查 CLAUDE.md 是否需要更新
4. 更新代码索引 (.code-index.json)
5. 记录关键决策到 Memory
6. 生成本次变更摘要
```

---

## 🔗 推荐的 Git Hooks

### pre-commit Hook
```bash
#!/bin/bash
# .git/hooks/pre-commit

echo "🔍 运行代码质量检查..."

# 1. 运行ruff
ruff check app/ || exit 1

# 2. 运行类型检查
mypy app/ || exit 1

# 3. 检查敏感信息
secretlint **/* || exit 1

# 4. 更新知识系统
python scripts/tools/update_knowledge_system.py

echo "✅ 所有检查通过"
```

### post-commit Hook
```bash
#!/bin/bash
# .git/hooks/post-commit

# 自动更新PLAYBOOKS
python scripts/tools/auto_update_playbooks.py

# 更新代码索引
python scripts/tools/gen_code_index.py

echo "📝 文档已自动更新"
```

---

## 🚀 实施优先级矩阵

| 工具/技能 | 投入成本 | 预期收益 | 优先级 | 建议时间 |
|----------|----------|----------|--------|----------|
| GitHub MCP | 低 (30min) | 高 (节省30min/天) | P0 | 立即 |
| 质量检查 Skill | 极低 (15min) | 中 (减少返工) | P0 | 立即 |
| Firecrawl MCP | 低 (45min) | 高 (自动化文档) | P0 | 本周 |
| 代码审查 Skill | 低 (20min) | 中 (提升代码质量) | P1 | 本周 |
| Chroma MCP | 中 (2h) | 高 (语义搜索) | P1 | 2周内 |
| 性能分析 Skill | 低 (30min) | 中 (优化决策) | P1 | 2周内 |
| Apifox MCP | 中 (1.5h) | 中 (API管理) | P2 | 按需 |
| MLflow MCP | 高 (4h) | 低 (仅ML场景) | P3 | 未来 |

---

## 📖 配置模板

### 完整 .mcp.json 示例
```json
{
  "mcpServers": {
    "context7": {
      "command": "npx",
      "args": ["-y", "@context7/mcp-server"]
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
      }
    },
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres"],
      "env": {
        "POSTGRES_CONNECTION_STRING": "postgresql://user:password@localhost:5432/diliuban"
      }
    },
    "memory": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-server-memory"]
    },
    "firecrawl": {
      "command": "npx",
      "args": ["-y", "@mendable/firecrawl-mcp"],
      "env": {
        "FIRECRAWL_API_KEY": "${FIRECRAWL_KEY}"
      }
    },
    "chroma": {
      "command": "npx",
      "args": ["-y", "@chroma/mcp-server"],
      "env": {
        "CHROMA_HOST": "localhost",
        "CHROMA_PORT": "8000"
      }
    }
  }
}
```

---

## 🎯 效率提升预测

### 实施前 vs 实施后

| 任务 | 当前耗时 | 优化后耗时 | 节省比例 |
|------|---------|-----------|---------|
| 查找API文档 | 15min (手动搜索) | 2min (Context7) | **87%** |
| 代码质量检查 | 10min (手动运行) | 1min (Skill) | **90%** |
| 创建PR | 8min (手动填写) | 2min (GitHub MCP) | **75%** |
| 搜索历史问题 | 20min (浏览代码) | 3min (Memory) | **85%** |
| 查找相似代码 | 25min (全文搜索) | 5min (Chroma) | **80%** |
| **总计** | **78min/天** | **13min/天** | **83%** |

**预计每天节省 65 分钟!**

---

## 🛠️ 安装指南

### 步骤 1: 安装 Node.js工具
```bash
# GitHub MCP
npm install -g @modelcontextprotocol/server-github

# Firecrawl MCP
npm install -g @mendable/firecrawl-mcp

# Chroma MCP
npm install -g @chroma/mcp-server
```

### 步骤 2: 配置环境变量
```bash
# .env 文件
GITHUB_TOKEN=ghp_your_token_here
FIRECRAWL_API_KEY=fc_your_key_here
POSTGRES_CONNECTION_STRING=postgresql://localhost:5432/diliuban
```

### 步骤 3: 创建 Skills
```bash
mkdir -p .claude/skills
# 复制上面的 skill 模板到对应文件
```

### 步骤 4: 配置 Git Hooks
```bash
cp hooks/pre-commit .git/hooks/
cp hooks/post-commit .git/hooks/
chmod +x .git/hooks/*
```

---

## 📚 学习资源

### 官方文档
- [MCP 协议规范](https://modelcontextprotocol.io/)
- [Claude Code 最佳实践](https://docs.anthropic.com/claude-code)
- [GitHub MCP 文档](https://github.com/modelcontextprotocol/servers)

### 社区资源
- [Awesome MCP](https://github.com/punkpeye/awesome-mcp) - 33k+ star 工具集合
- [MCP 中文社区](https://mcp.csdn.net/)
- [Claude Code Skills 库](https://github.com/anthropics/claude-code-skills)

---

## ⚠️ 注意事项

### 安全性
- ⚠️ GitHub Token 使用最小权限原则
- ⚠️ PostgreSQL 连接字符串加密存储
- ⚠️ API Key 不提交到 Git

### 性能
- 💡 Chroma 向量数据库定期清理过期索引
- 💡 Firecrawl 限制爬取频率 (避免被封)
- 💡 Memory 定期导出备份

### 维护
- 📅 每月更新 MCP 工具版本
- 📅 每季度审查 Skills 有效性
- 📅 每半年清理未使用的工具

---

## 🎉 总结

### 必装清单 (今天就做)
1. ✅ GitHub MCP - 自动化Git操作
2. ✅ 质量检查 Skill - 一键检查
3. ✅ 代码审查 Skill - 自动审查
4. ✅ Git Hooks - 自动维护知识库

### 本周完成
1. ⏳ Firecrawl MCP - 文档自动化
2. ⏳ 性能分析 Skill - 数据库优化
3. ⏳ 文档同步 Skill - 保持最新

### 未来探索
1. 🔮 Chroma MCP - 语义搜索
2. 🔮 Apifox MCP - API管理
3. 🔮 MLflow MCP - ML实验跟踪

---

**创建时间**: 2025-12-16
**维护者**: AI助手 + 个人开发者
**状态**: ✅ 活跃维护

---

## 📖 参考来源

- [开发者必看!2025年最值得掌握的10款MCP工具实战指南](https://mcp.csdn.net/68195a66e9858151797de575.html)
- [2025年 10 个热门 MCP Server 推荐](https://mcp.csdn.net/6811f5bfc89bb164988954d8.html)
- [10 个好用的 MCP Server 推荐](https://zhuanlan.zhihu.com/p/1892956102380995168)
- [2025神仙MCP工具名单](https://zhuanlan.zhihu.com/p/1938728936784790538)
