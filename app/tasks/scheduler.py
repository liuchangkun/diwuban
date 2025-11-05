# [占位][方案A-标注] 当前未注册任何定时任务（扫描于 2025-09-24）。仅保留启动器骨架，未在生产路径使用。
# 如需启用，请在 jobs/ 下补充任务并在此注册；否则建议后续归档/删除。

from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()

# 占位：后续注册 jobs


def start_scheduler():
    if not scheduler.running:
        scheduler.start()
