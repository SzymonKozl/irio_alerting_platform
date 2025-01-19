from dataclasses import dataclass
from typing import List, Optional
import os
import subprocess
import requests
from sys import exit
from log import *

import threading
from aiosmtpd.controller import Controller
from aiosmtpd.handlers import Debugging
from email.message import EmailMessage


class SMTPHandler(Debugging):
    def __init__(self, collector, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.collector = collector


    async def handle_DATA(self, server, session, envelope):
        try:
            # Convert raw email bytes to an EmailMessage object
            email_message = EmailMessage()
            email_message.set_content(envelope.content.decode('utf-8', errors='replace'))

            for header, value in envelope.headers:
                email_message[header] = value

            self.collector(email_message)

            info(f"Email received: {email_message['Subject']} from {email_message['From']}")
            return '250 OK'
        except Exception as e:
            warn(f"Error handling email: {e}")
            return '451 Internal Server Error'

class MailServer:
    def __init__(self, host="127.0.0.1", port=1025):
        self.host = host
        self.port = port
        self.messages = []
        self.controller = Controller(handler=SMTPHandler(lambda msg: self.messages.append(msg)), hostname=self.host, port=self.port)
        self.thread = None

    def start(self):
        if self.thread is not None:
            warn("Mail server is already running.")
            return

        def run():
            self.controller.start()

        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()
        info(f"Mail server started on {self.host}:{self.port}")

    def stop(self):
        if self.thread is None:
            warn("Mail server is not running.")
            return

        self.controller.stop()
        self.thread = None
        info("Mail server stopped.")



class MockServiceHandle:
    def __init__(self, port):
        self.port = port
        self._create()
        
    def _create(self):
        log_net(info, "Creating...", "mock service", self.port)
        if os.fork() != 0:
            subprocess.run(["python", "mock_server.py", "localhost", str(self.port)])
            exit(0)

    def _set_mode(self, mode: str):
        resp = requests.post(f"http://localhost:{self.port}/set_response_mode?mode={mode}")
        success = 200 <= resp.status_code < 300
        if not success:
            log_net(warn, f"failed to set resp mode to {mode}", "mock_service", self.port)
        else:
            log_net(info, f"set resp mode to {mode}", "mock_service", self.port)
        return success

    def respond_timeout(self):
        self._set_mode("timeout")
    
    def respond_normal(self):
        self._set_mode("normal")
    
    def respond_404(self):
        self._set_mode("404")


@dataclass
class PingingJob:
    mail1: str
    mail2: str
    period: str
    url: str | MockServiceHandle
    alerting_window: int
    response_time: int


def handle_child_death(signum, frame):
    error("Child death detected.\n Terminating.")
    exit(1)


class AlertingServiceHandle:
    def __init__(self, port):
        self.port = port
        if os.fork() != 0:
            subprocess.run(["python", "repo/server/main.py", "localhost", str(self.port)])
            exit(0)

    def add_pinging_job(self, job_data: PingingJob) -> int:
        payload = {
            "url": job_data.url,
            "alerting_window": job_data.alerting_window,
            "period": job_data.period,
            "primary_email": job_data.mail1,
            "secondary_email": job_data.mail2,
            "response_time": job_data.response_time
        }
        resp = requests.post(f"http://localhost:{self.port}/add_service", json=payload)
        try:
            job_id = resp.json()["job_id"]
            log_net(info, f"added ping job {job_id}", self.__class__.__name__, self.port)
            return job_id
        except (requests.exceptions.JSONDecodeError, KeyError) as e:
            log_net(warn, f"failed to add ping job. Exception: {type(e).__name__}, reason: {e}", self.__class__.__name__, self.port)
            return -1


    def remove_pinging_job(
            self, job_id: int
    ) -> bool:
        payload = {
            "job_id": job_id,
        }
        resp = requests.delete(f"http://localhost:{self.port}/del_job", json=payload)
        success = 200 <= resp.status_code < 300
        if not success:
            log_net(warn, f"failed to delete ping job with id {job_id}. response code: {resp.status_code}", self.__class__.__name__, self.port)
        else:
            log_net(info, f"deleted ping job with id {job_id}", self.__class__.__name__, self.port)
        return success


    def get_pinging_jobs(
            self, mail: str,
    ) -> Optional[List[PingingJob]]:
        payload = {
            "primary_admin_email": mail,
        }
        resp = requests.get(f"http://localhost:{self.port}/alerting_jobs", payload)
        if resp.status_code != 200:
            log_net(warn, f"failed to get pinging for mail {mail}. response code: {resp.status_code}", self.__class__.__name__, self.port)
            return None
        res = []
        try:
            for entry in resp.json():
                res.append(PingingJob(**entry))
        except (requests.exceptions.JSONDecodeError, Exception) as e:
            log_net(warn, f"failed to get pinging jobs. Exception: {type(e).__name__}, reason: {e}", self.__class__.__name__, self.port)
            return None
        log_net(info, f"get pinging jobs for mail {mail}", self.__class__.__name__, self.port)
        return res
