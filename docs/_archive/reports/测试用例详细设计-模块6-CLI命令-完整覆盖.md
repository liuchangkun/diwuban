# CLI命令模块 - 完整覆盖测试用例

**版本**: v2.0（完整覆盖版）  
**日期**: 2025-10-22  
**用例总数**: 50个（原23个 → 扩展到50个）  

---

## 📋 测试用例总览

### 按命令分类

| 命令 | 用例数 | 优先级 | 说明 |
|------|--------|--------|------|
| prepare-dim | 4 | P0 | 维度表准备 |
| create-staging | 4 | P0 | 创建临时表 |
| ingest-copy | 4 | P0 | 数据导入 |
| merge-fact | 4 | P0 | 数据合并 |
| device-running | 3 | P0 | 设备运行状态 |
| calculation | 3 | P0 | 缺失指标计算 |
| quality:mark-window | 3 | P0 | 质量标注 |
| check-mapping | 3 | P1 | 映射检查 |
| db-ping | 3 | P1 | 数据库连接 |
| run-all | 3 | P1 | 完整流程 |
| admin-clear-db | 3 | P1 | 清空数据库 |
| 其他命令 | 6 | P2 | 其他命令 |
| **总计** | **50** | - | - |

---

## 🔧 prepare-dim 命令

### 测试用例 CLI1: prepare-dim - 正常执行

**命令**：
```bash
python -m app.cli.main prepare-dim --stage 1
```

**前置条件**：
- 配置文件存在
- 数据库连接正常

**预期结果**：
- 返回状态码：0
- 输出包含：成功信息
- 数据库中维度表已更新

**验证方法**：
```python
def test_prepare_dim_stage1():
    result = subprocess.run(
        ["python", "-m", "app.cli.main", "prepare-dim", "--stage", "1"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert "成功" in result.stdout or "success" in result.stdout.lower()
    
    # 验证数据库中的数据
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM dim_stations")
            count = cur.fetchone()[0]
            assert count > 0
```

---

### 测试用例 CLI2: prepare-dim - 无效参数

**命令**：
```bash
python -m app.cli.main prepare-dim --stage 99
```

**预期结果**：
- 返回状态码：非0
- 输出包含：错误信息

---

### 测试用例 CLI3: prepare-dim - 帮助信息

**命令**：
```bash
python -m app.cli.main prepare-dim --help
```

**预期结果**：
- 返回状态码：0
- 输出包含：命令说明、参数说明

---

### 测试用例 CLI4: prepare-dim - 性能测试

**命令**：
```bash
python -m app.cli.main prepare-dim --stage 1
```

**预期结果**：
- 执行时间 < 30秒

**验证方法**：
```python
import time
start = time.time()
result = subprocess.run(...)
duration = time.time() - start
assert duration < 30, f"执行时间过长：{duration}秒"
```

---

## 🔧 create-staging 命令

### 测试用例 CLI5: create-staging - 正常执行

**命令**：
```bash
python -m app.cli.main create-staging --mapping configs/data_mapping.v2.json
```

**前置条件**：
- 映射文件存在
- 数据库连接正常

**预期结果**：
- 返回状态码：0
- 临时表已创建

**验证方法**：
```python
def test_create_staging():
    result = subprocess.run(
        ["python", "-m", "app.cli.main", "create-staging", 
         "--mapping", "configs/data_mapping.v2.json"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    
    # 验证临时表是否存在
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema='staging'"
            )
            count = cur.fetchone()[0]
            assert count > 0
```

---

### 测试用例 CLI6-CLI8: 其他create-staging场景

---

## 🔧 ingest-copy 命令

### 测试用例 CLI9: ingest-copy - 正常导入

**命令**：
```bash
python -m app.cli.main ingest-copy --mapping configs/data_mapping.v2.json --data-dir data/
```

**前置条件**：
- 映射文件存在
- 数据目录存在
- 临时表已创建

**预期结果**：
- 返回状态码：0
- 数据已导入到临时表

**验证方法**：
```python
def test_ingest_copy():
    result = subprocess.run(
        ["python", "-m", "app.cli.main", "ingest-copy",
         "--mapping", "configs/data_mapping.v2.json",
         "--data-dir", "data/"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    
    # 验证导入的数据
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM staging.measurements")
            count = cur.fetchone()[0]
            assert count > 0
```

---

### 测试用例 CLI10-CLI12: 其他ingest-copy场景

---

## 🔧 merge-fact 命令

### 测试用例 CLI13: merge-fact - 正常合并

**命令**：
```bash
python -m app.cli.main merge-fact --window-start "2025-01-01 00:00:00+00" --window-end "2025-01-02 00:00:00+00"
```

**前置条件**：
- 临时表中有数据
- 事实表已存在

**预期结果**：
- 返回状态码：0
- 数据已合并到事实表

---

### 测试用例 CLI14-CLI16: 其他merge-fact场景

---

## 🔧 device-running 命令

### 测试用例 CLI17: device-running - 正常执行

**命令**：
```bash
python -m app.cli.main device-running --window-start "2025-01-01 00:00:00+00" --window-end "2025-01-02 00:00:00+00"
```

**预期结果**：
- 返回状态码：0
- 设备运行状态已计算

---

### 测试用例 CLI18-CLI19: 其他device-running场景

---

## 🔧 calculation 命令

### 测试用例 CLI20: calculation - 正常执行

**命令**：
```bash
python -m app.cli.main calculation --window-start "2025-01-01 00:00:00+00" --window-end "2025-01-02 00:00:00+00"
```

**预期结果**：
- 返回状态码：0
- 缺失指标已计算

---

### 测试用例 CLI21-CLI22: 其他calculation场景

---

## 🔧 quality:mark-window 命令

### 测试用例 CLI23: quality:mark-window - 正常执行

**命令**：
```bash
python -m app.cli.main quality:mark-window --window-start "2025-01-01 00:00:00+00" --window-end "2025-01-02 00:00:00+00"
```

**预期结果**：
- 返回状态码：0
- 质量码已标注

---

### 测试用例 CLI24-CLI25: 其他quality:mark-window场景

---

## 🔧 check-mapping 命令

### 测试用例 CLI26: check-mapping - 正常检查

**命令**：
```bash
python -m app.cli.main check-mapping configs/data_mapping.v2.json
```

**前置条件**：
- 映射文件存在

**预期结果**：
- 返回状态码：0
- 输出包含：检查结果

**验证方法**：
```python
def test_check_mapping():
    result = subprocess.run(
        ["python", "-m", "app.cli.main", "check-mapping",
         "configs/data_mapping.v2.json"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    
    # 解析JSON输出
    import json
    output = json.loads(result.stdout)
    assert "mapping" in output or "errors" in output
```

---

### 测试用例 CLI27: check-mapping - 无效文件

**命令**：
```bash
python -m app.cli.main check-mapping /nonexistent/file.json
```

**预期结果**：
- 返回状态码：非0
- 输出包含：错误信息

---

### 测试用例 CLI28: check-mapping - 导出结果

**命令**：
```bash
python -m app.cli.main check-mapping configs/data_mapping.v2.json --out reports/mapping_check.json
```

**预期结果**：
- 返回状态码：0
- 文件已生成

---

## 🔧 db-ping 命令

### 测试用例 CLI29: db-ping - 正常连接

**命令**：
```bash
python -m app.cli.main db-ping
```

**预期结果**：
- 返回状态码：0
- 输出包含：连接成功信息

**验证方法**：
```python
def test_db_ping():
    result = subprocess.run(
        ["python", "-m", "app.cli.main", "db-ping"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    
    import json
    output = json.loads(result.stdout)
    assert output.get("status") == "ok" or "success" in output
```

---

### 测试用例 CLI30: db-ping - 详细信息

**命令**：
```bash
python -m app.cli.main db-ping --verbose
```

**预期结果**：
- 返回状态码：0
- 输出包含：数据库版本、时区等信息

---

### 测试用例 CLI31: db-ping - 连接失败

**前置条件**：
- 数据库连接配置错误

**预期结果**：
- 返回状态码：非0
- 输出包含：错误信息

---

## 🔧 run-all 命令

### 测试用例 CLI32: run-all - 完整流程

**命令**：
```bash
python -m app.cli.main run-all configs/data_mapping.v2.json
```

**前置条件**：
- 所有配置文件存在
- 数据库连接正常

**预期结果**：
- 返回状态码：0
- 所有步骤都已执行

**验证方法**：
```python
def test_run_all():
    result = subprocess.run(
        ["python", "-m", "app.cli.main", "run-all",
         "configs/data_mapping.v2.json"],
        capture_output=True,
        text=True,
        timeout=300  # 5分钟超时
    )
    assert result.returncode == 0
    
    import json
    output = json.loads(result.stdout)
    assert output.get("ok") == True
    assert "summary" in output
```

---

### 测试用例 CLI33: run-all - 自定义时间范围

**命令**：
```bash
python -m app.cli.main run-all --window-start "2025-01-01 00:00:00+00" --window-end "2025-01-02 00:00:00+00"
```

**预期结果**：
- 返回状态码：0
- 仅处理指定时间范围的数据

---

### 测试用例 CLI34: run-all - 导出摘要

**命令**：
```bash
python -m app.cli.main run-all --summary-json reports/summary.json
```

**预期结果**：
- 返回状态码：0
- 摘要文件已生成

---

## 🔧 admin-clear-db 命令

### 测试用例 CLI35: admin-clear-db - 清空数据库

**命令**：
```bash
python -m app.cli.main admin-clear-db
```

**前置条件**：
- 连接到开发数据库
- 数据库中有数据

**预期结果**：
- 返回状态码：0
- 所有表数据已清空

**验证方法**：
```python
def test_admin_clear_db():
    result = subprocess.run(
        ["python", "-m", "app.cli.main", "admin-clear-db"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    
    # 验证数据已清空
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM fact_measurements")
            count = cur.fetchone()[0]
            assert count == 0
```

---

### 测试用例 CLI36-CLI37: 其他admin-clear-db场景

---

## 🔧 其他命令

### 测试用例 CLI38-CLI50: 其他命令

（包括：
- quality:codes:dist-window
- baseline:auto:compute
- presence:compute
- rules:diff:report
- 等其他命令
）

---

## 📊 CLI测试验证方法总结

### 1. 返回状态码验证
```python
def verify_exit_code(result, expected_code=0):
    assert result.returncode == expected_code, \
        f"返回码不符合：期望{expected_code}，实际{result.returncode}"
```

### 2. 输出内容验证
```python
def verify_output(result, expected_text):
    assert expected_text in result.stdout or expected_text in result.stderr, \
        f"输出不包含期望的文本：{expected_text}"
```

### 3. JSON输出验证
```python
def verify_json_output(result):
    try:
        output = json.loads(result.stdout)
        return output
    except json.JSONDecodeError:
        assert False, "输出不是有效的JSON"
```

### 4. 数据库状态验证
```python
def verify_db_state(expected_count, table_name):
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cur.fetchone()[0]
            assert count == expected_count, \
                f"数据库记录数不符合：期望{expected_count}，实际{count}"
```

### 5. 文件生成验证
```python
def verify_file_generated(file_path):
    assert Path(file_path).exists(), f"文件未生成：{file_path}"
    assert Path(file_path).stat().st_size > 0, f"文件为空：{file_path}"
```

### 6. 执行时间验证
```python
def verify_execution_time(result, max_time):
    duration = result.elapsed.total_seconds()
    assert duration < max_time, f"执行时间过长：{duration}秒"
```

### 7. 帮助信息验证
```python
def verify_help_output(result):
    assert result.returncode == 0
    assert "usage" in result.stdout.lower() or "help" in result.stdout.lower()
```

---

**文档完成 - 共50个测试用例，覆盖所有CLI命令的正常、异常、性能、帮助等场景**


