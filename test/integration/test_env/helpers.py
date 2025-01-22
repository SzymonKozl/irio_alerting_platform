import signal
from dataclasses import dataclass
from typing import List, Optional
import os
import subprocess
import requests
from sys import exit
from test_env.log import *

import threading
from aiosmtpd.controller import Controller
from aiosmtpd.handlers import Debugging
from email.message import EmailMessage
from email import message_from_bytes, policy

from test_env.log import log_net


class SMTPHandler(Debugging):
    def __init__(self, collector, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.collector = collector


    async def handle_DATA(self, server, session, envelope):
        try:
            # Convert raw email bytes to an EmailMessage object
            email_message = message_from_bytes(envelope.content)

            self.collector(email_message)

            info(f"Email received for account: {email_message['To']} from {envelope.mail_from}")
            return '250 OK'
        except Exception as e:
            warn(f"Error handling email: {e}")
            return '451 Internal Server Error'


def save_mail(msg: EmailMessage):
    with open("mail.log", "a") as mail_log:
        content = msg.as_string().replace('\n', ' ').replace('\r', ' ')
        mail_log.write(f"{msg['To']};{content}\n")


def scrap_ack_url(mail_content: str) -> str:
    try:
        ix1 = mail_content.index("Click") + len("Click")
        mail_content = mail_content[ix1:]
        ix2 = mail_content.index(" to acknowledge")
        mail_content = mail_content[:ix2]
        return mail_content
    except Exception as e:
        error(f"notification id cound not be scrapped from email {e}")
        return ""


class MailServer:
    def __init__(self, host="localhost", port=587):
        self.host = host
        self.port = port
        self.controller = Controller(handler=SMTPHandler(save_mail), hostname=self.host, port=self.port)
        self.thread = None
        self.start()


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

    def last_mail_to(self, receiver: str) -> Optional[str]:
        content = None
        with open("mail.log", "r") as mail_log:
            for line in mail_log:
                if line.strip().split(';')[0] == receiver:
                    content = line.strip().split(';', 1)[1]
        return content


class MockServiceHandle:
    def __init__(self, port):
        self.port = port
        self.log_file = open(f"service={self.port}.log", "w")
        self.child_pid = -1
        self._create()
        
    def _create(self):
        log_net(info, "Creating...", "mock service", self.port)
        self.child_pid = os.fork()
        if self.child_pid == 0:
            subprocess.run(["python", "test_env/mock_server.py", "localhost", str(self.port)], stdout=self.log_file, stderr=self.log_file)
            exit(0)

    def close(self):
        self.log_file.close()
        os.kill(self.child_pid, signal.SIGTERM)

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
    period: int
    url: str | MockServiceHandle
    alerting_window: int
    response_time: int


def handle_child_death(signum, frame):
    error("Child death detected.\n Terminating.")
    exit(1)


class AlertingServiceHandle:
    def __init__(self):
        log_net(info, "Creating...", "alerting service", 5000)
        self.port = 5000
        self.log_file = open(f"server.log", "w")
        if os.fork() == 0:
            subprocess.run(["python", "../../server/main.py", ">", "server.log"], stdout=self.log_file, stderr=self.log_file)
            exit(0)


    def add_pinging_job(self, job_data: PingingJob) -> int:
        payload = {
            "url": job_data.url if isinstance(job_data.url, str) else job_data.url.port,
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
            log_net(warn, f"failed to add ping job. Exception: {type(e).__name__}, reason: {e}, server_resp: {resp} {resp.json()}", self.__class__.__name__, self.port)
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


    def confirm_alert(self, link: str) -> bool:

        resp = requests.get(link)

        if 200 <= resp.status_code < 300:
            log_net(info, f"acknowledged alert: {link}", self.__class__.__name__, self.port)
            return True
        else:
            log_net(warn, f"failed to acknowledge alert with link {link}. response code: {resp.status_code}, reponse: {resp.text}", self.__class__.__name__, self.port)
            return False
