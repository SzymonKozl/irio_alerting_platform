from collections import namedtuple


job_id_t = int
JobData = namedtuple("JobData", ["job_id", "mail1", "mail2", "url", "period", "window", "response_time"])


ERR_MSG_CREATE_POSITIVE_INT = "fields 'period', 'alerting_window' and 'response_time' should be positive integers"
