from dataclasses import dataclass
from typing import List


class MockServiceHandle:
    def __init__(self, port):
        self.port = port
        self._create()
        
    def _create(self):
        pass # todo

    def respond_timeout(self):
        pass # todo
    
    def respond_normal(self):
        pass # todo
    
    def respond_404(self):
        pass # todo


@dataclass
class PingingJob:
    mail1: str
    mail2: str
    period: str
    service: str | MockServiceHandle
    alerting_window: int
    response_time: int


def handle_mock_death(signum, frame):
    pass # todo


def add_pinging_job(job_data: PingingJob) -> int:
    pass # todo


def remove_pinging_job(
        job_id: int
) -> bool:
    pass # todo


def get_pinging_jobs(
        mail: str,
) -> List[PingingJob]:
    pass # todo
