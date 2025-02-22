from collections import namedtuple
import os


job_id_t = int
notification_id_t = int
JobData = namedtuple("JobData", ["job_id", "mail1", "mail2", "url", "period", "window", "response_time", "is_active"])
NotificationData = namedtuple("NotificationData", ["notification_id", "time_sent", "admin_responded", "notification_num", "job_id"])


DB_HOST = os.environ.get("DB_HOST")
DB_PORT = 5432

APP_HOST = os.environ.get("APP_HOST")
APP_PORT = 8080

ERR_MSG_CREATE_POSITIVE_INT = "fields 'period', 'alerting_window' and 'response_time' should be positive integers"
