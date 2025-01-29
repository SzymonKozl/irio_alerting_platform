from prometheus_client import Counter, Gauge


PINGS_SENT_CTR = Counter('pings_sent_total', 'Total Pings')
SUCCESSFUL_PINGS_CTR = Counter('successful_pings_total', 'Total Pings')
HTTP_CONNS_ACTIVE_CTR = Gauge('http_conns_active_total', 'Total HTTP connections')
JOBS_ACTIVE_CTR = Gauge('jobs_active_total', 'Total Jobs')