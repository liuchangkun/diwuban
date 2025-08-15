---
description: CLI 返回码与输出（阶段化返回码、机器可读摘要、人类提示）
---
# CLI 返回码与输出

## 返回码
- 0：成功；1：配置/参数错误；2：Schema/映射校验失败；3：文件路径错误；4：DB 连接失败；5：导入/对齐失败；6：门禁/性能不达标终止；99：未知错误。

## 机器可读摘要（JSON Schema）
```json
{
  "type": "object",
  "required": ["trace_id", "status", "rows_loaded", "rows_deduped", "rows_merged", "batch_cost_ms", "p95_ms"],
  "properties": {
    "trace_id": {"type": "string"},
    "status": {"type": "string", "enum": ["success", "partial", "failed"]},
    "rows_loaded": {"type": "integer"},
    "rows_deduped": {"type": "integer"},
    "rows_merged": {"type": "integer"},
    "rows_failed": {"type": "integer"},
    "batch_cost_ms": {"type": "integer"},
    "p95_ms": {"type": "integer"},
    "guardrail": {"type": "string"},
    "hint": {"type": "string"}
  }
}
```

## 样例
```json
{"trace_id":"t-...","status":"success","rows_loaded":120000,"rows_deduped":110500,"rows_merged":109900,"rows_failed":600,"batch_cost_ms":1850,"p95_ms":1900}
```