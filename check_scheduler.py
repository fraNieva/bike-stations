"""Quick diagnostic — run inside Docker to check scheduler and logging."""
import logging
logging.basicConfig(level=logging.INFO)

from app.scheduler import start_scheduler, scheduler
start_scheduler()
print(f"Scheduler running: {scheduler.running}")
print(f"Jobs: {scheduler.get_jobs()}")