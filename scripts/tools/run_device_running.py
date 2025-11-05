from __future__ import annotations

"""
命令行入口：批量计算并落地 device_running（0/1）。
- 解析参数后委托 app.services.device_running_job.main 执行
"""

from app.services.device_running_job import main

if __name__ == "__main__":
    main()
