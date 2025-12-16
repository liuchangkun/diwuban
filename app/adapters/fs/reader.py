from __future__ import annotations

"""
文件系统读取适配器（adapters.fs.reader）：CSV 读取与有效性校验
- validate_header：规范列头校验（BOM/空白/大小写兼容；要求 TagName/DataTime/DataValue）
- iter_rows：返回 ValidRow/RejectRow 迭代器，上层负责填充站点/设备/指标元信息

注意：
- 统一 UTF-8 读取与 BOM 兼容
- 报错采用 RejectRow 汇报错误信息，便于数据质量统计
"""


import csv
from pathlib import Path
from typing import Iterator, Sequence

from app.core.types import RejectRow, ValidRow

# 最小必需列集合：大小写与空白差异在 normalize 后比较
REQUIRED_COLS = {"tagname", "datatime", "datavalue"}


def _normalize(name: str) -> str:
    """去除 BOM、首尾空白并小写化，用于宽松匹配列名。"""
    return name.lstrip("\ufeff").strip().lower()


def validate_header(header: Sequence[str]) -> None:
    """校验 CSV 头，确保最小必需列存在。
    - header: 来自 DictReader.fieldnames
    - 允许大小写与空白差异，自动清洗后对比 REQUIRED_COLS
    - 缺失则抛出 ValueError
    """
    cols = {_normalize(str(c)) for c in header}
    missing = REQUIRED_COLS - cols
    if missing:
        raise ValueError(f"CSV列缺失: {missing}; 需要列: TagName/DataTime/DataValue")


def iter_rows(
    csv_path: Path,
    source_hint: str,
    *,
    delimiter: str = ",",
    encoding: str = "utf-8",
    quote_char: str = '"',
    escape_char: str = "\\",
    allow_bom: bool = True,
    read_buffer_size: int | None = None,
) -> Iterator[ValidRow | RejectRow]:
    """逐行读取 CSV，产出标准化的 ValidRow 或带错误信息的 RejectRow。
    - csv_path: 待读取 CSV 路径
    - source_hint: 源信息标注，透传到 ValidRow/RejectRow
    - 可选参数：CSV 方言与缓冲设置（默认保持兼容）
    - 注意：station_name/device_name/metric_key 由上层填充
    """
    enc = encoding
    if allow_bom and encoding.lower().replace("_", "-") in ("utf-8", "utf8"):
        enc = "utf-8-sig"
    buffering = (
        read_buffer_size
        if (isinstance(read_buffer_size, int) and read_buffer_size > 0)
        else -1
    )
    with csv_path.open("r", encoding=enc, newline="", buffering=buffering) as f:
        reader = csv.DictReader(
            f,
            delimiter=delimiter,
            quotechar=quote_char,
            escapechar=escape_char,
        )
        validate_header(reader.fieldnames or [])
        for row in reader:
            try:
                yield ValidRow(
                    station_name="",  # 上层填充
                    device_name="",
                    metric_key="",
                    TagName=str(row.get("TagName") or row.get("tagname") or "").strip(),
                    DataTime=str(
                        row.get("DataTime") or row.get("datetime") or ""
                    ).strip(),
                    DataValue=str(
                        row.get("DataValue") or row.get("datavalue") or ""
                    ).strip(),
                    source_hint=source_hint,
                )
            except Exception as e:
                yield RejectRow(source_hint=source_hint, error_msg=str(e))
