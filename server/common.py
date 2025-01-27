from collections import namedtuple


job_id_t = int
notification_id_t = int
JobData = namedtuple("JobData", ["job_id", "mail1", "mail2", "url", "period", "window", "response_time"])
NotificationData = namedtuple("NotificationData", ["notification_id", "time_sent", "admin_responded", "notification_num"])


DB_HOST = 'localhost'
DB_PORT = 5432

APP_HOST = '127.0.0.1'
APP_PORT = 5000

ERR_MSG_CREATE_POSITIVE_INT = "fields 'period', 'alerting_window' and 'response_time' should be positive integers"
