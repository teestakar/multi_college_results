from celery import Celery

celery_app = Celery(
    "multi_college_results",           # name of your app (just a label)
    broker="redis://localhost:6379/0", # where task messages get queued
    backend="redis://localhost:6379/0" # where task RESULTS get stored
)