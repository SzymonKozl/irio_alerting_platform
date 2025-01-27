import asyncio
import time
import smtplib
import os
import threading
from queue import PriorityQueue
from aiohttp import ClientSession
from typing import Tuple, Optional
from email.mime.text import MIMEText
from datetime import datetime
import logging


import db_access
from common import *


deleted_jobs_cache = set()
deleted_jobs_lock = asyncio.Lock()

smtp_server = os.environ.get("SMTP_SERVER")
smtp_server = 'smtp.gmail.com' if not smtp_server else smtp_server
smtp_port = os.environ.get("SMTP_PORT")
smtp_port = 587 if not smtp_port else int(smtp_port)
smtp_username = os.environ.get('SMTP_USERNAME')
smtp_password = os.environ.get('SMTP_PASSWORD')
smtp = smtplib.SMTP(smtp_server, smtp_port)
smtp_lock = threading.Lock()


def init_smtp():
    log_data = {"function_name": "init_smtp"}
    logging.info("Init SMTP called", extra={"json_fields": log_data})
    
    try:
        smtp.starttls()
        smtp.login(smtp_username, smtp_password)
    except Exception as e:
        logging.error("Error initializing SMTP connection: %s", e,
                      extra={"json_fields": log_data})
        raise e
    logging.info("SMTP connection initialized", extra={"json_fields": log_data})

def send_email(to: str, subject: str, body: str):
    log_data = {"function_name": "send_email", "to": to, "subject": subject}
    logging.info("Send email called", extra={"json_fields": log_data})

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = smtp_username
    msg['To'] = to
    try:
        with smtp_lock:
            smtp.sendmail(smtp_username, to, msg.as_string())
        logging.info("Email sent", extra={"json_fields": log_data})
    except Exception as e:
        logging.error(f"Error sending email: {e}", extra={"json_fields": log_data})


def send_alert(to: str, url: str, notification_id: int, primary_admin: bool):
    log_data = {"function_name": "send_alert", "to": to, "url": url,
                "notification_id": notification_id, "primary_admin": primary_admin}
    logging.info("Send alert called", extra={"json_fields": log_data})
    
    link = f"http://{APP_HOST}:{APP_PORT}/receive_alert?notification_id={notification_id}&primary_admin={primary_admin}"
    subject = "Alert"
    body = f"Alert for {url}. Click {link} to acknowledge."
    send_email(to, subject, body)


async def delete_job(job_id: job_id_t) -> bool:
    async with deleted_jobs_lock:
        deleted_jobs_cache.add(job_id)
    return False


async def pinging_job(job_data: JobData):

    async def single_request():
        try:
            async with ClientSession() as session:
                async with session.get(job_data.url) as response:
                    return response
        except:
            return None

    futures: PriorityQueue[Tuple[int, asyncio.Task]] = PriorityQueue()
    while True:
        async with deleted_jobs_lock:
            if job_data.job_id in deleted_jobs_cache:
                deleted_jobs_cache.remove(job_data.job_id)
                return

        task = asyncio.create_task(single_request())
        futures.put((time.time_ns(), task))

        latest = -1
        for (t, ftr) in futures.queue:
            if ftr.done():
                resp = ftr.result()
                if resp is not None and 200 <= resp.status < 300:
                    latest = max(latest, t)

        tmp: Optional[Tuple[int, asyncio.Task]] = None

        while True:
            if futures.empty():
                tmp = None
                break
            tmp = futures.get()
            if tmp[0] <= latest:
                continue
            futures.put(tmp)
            break

        if tmp is not None:
            if (time.time_ns() - tmp[0]) / 1_000_000 >= job_data.window:
                conn = db_access.setup_connection(DB_HOST, DB_PORT)

                try:
                    notification_id = db_access.save_notification(NotificationData(-1, datetime.now(), False, 1), conn)

                    send_alert(job_data.mail1, job_data.url, notification_id, True)
                    db_access.delete_job(job_data.job_id, conn)

                finally:
                    conn.close()
                try:

                    await asyncio.sleep(job_data.response_time / 1000)
                    conn = db_access.setup_connection(DB_HOST, DB_PORT)

                    if not (xd:=db_access.get_notification_by_id(notification_id, conn)).admin_responded:
                        print(xd)
                        second_notification_id = db_access.save_notification(NotificationData(-1, datetime.now(), False, 2), conn)
                        send_alert(job_data.mail2, job_data.url, second_notification_id, False)

                        await asyncio.sleep(job_data.response_time / 1000)

                        # Check if the secondary admin has responded and log the result
                finally:
                    conn.close()
                return

        await asyncio.sleep(job_data.period / 1000)


async def new_job(job_data: JobData):
    await pinging_job(job_data)
