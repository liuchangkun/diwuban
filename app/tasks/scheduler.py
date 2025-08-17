from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()

# 占位：后续注册 jobs


def start_scheduler():
    if not scheduler.running:
        scheduler.start()
