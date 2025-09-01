#!/usr/bin/env python3
"""
简单数据库连接测试脚本
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径（修正为仓库根目录）
repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo_root))


def test_database_connection():
    """pytest 风格：使用 assert，不返回值。"""
    from app.adapters.db.gateway import get_conn
    from app.core.config.loader_new import load_settings

    settings = load_settings(Path("configs"))
    with get_conn(settings) as conn:
        with conn.cursor() as cur:
            # 连接可用性：选择可用表进行简单查询，这里用 dim_metric_config 作为存在性检查
            cur.execute("SELECT COUNT(*) FROM public.dim_metric_config")
            count = cur.fetchone()[0]
            assert count >= 0


if __name__ == "__main__":
    success = test_database_connection()
    sys.exit(0 if success else 1)
