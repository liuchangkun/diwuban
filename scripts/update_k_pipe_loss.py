"""更新 K_pipe_loss 参数"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config.loader_new import load_settings
from app.adapters.db.pool import initialize_pool, close_pool, get_connection

# 初始化数据库
settings = load_settings(Path("configs"))
initialize_pool(settings)

try:
    with get_connection() as conn:
        cursor = conn.cursor()

        # 更新 K_pipe_loss 参数（从 1e-5 改为 2e-7）
        cursor.execute("""
            UPDATE calculation_parameters
            SET param_value = '0.0000002'
            WHERE param_name = 'K_pipe_loss'
              AND metric_key = 'pump_head'
            RETURNING device_id, param_name, param_value;
        """)

        results = cursor.fetchall()
        conn.commit()

        print(f"\n✅ 更新了 {len(results)} 条 K_pipe_loss 参数:")
        for row in results:
            print(f"  - device_id={row[0]}, param_name={row[1]}, param_value={row[2]}")

finally:
    close_pool()

