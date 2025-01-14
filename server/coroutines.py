import asyncio
import time
import smtplib
import os
from queue import PriorityQueue
from aiohttp import ClientSession
from typing import Tuple, Optional
from email.mime.text import MIMEText
from dotenv import load_dotenv
from datetime import datetime


import db_access
from common import *


# Maybe an explicit init function would be better
deleted_jobs_cache = set()
deleted_jobs_lock = asyncio.Lock()

smtp_server = 'smtp.gmail.com'
smtp_port = 587
smtp_username = os.environ.get('SMTP_USERNAME')
smtp_password = os.environ.get('SMTP_PASSWORD')
smtp = smtplib.SMTP(smtp_server, smtp_port)
smtp.starttls()
smtp.login(smtp_username, smtp_password)
smtp_lock = asyncio.Lock()


def send_email(to: str, subject: str, body: str):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = smtp_username
    msg['To'] = to
    try:
        with smtp_lock:
            smtp.sendmail(smtp_username, to, msg.as_string())
    except Exception as e:
        print(f"Error sending email: {e}")


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
                    notification_id = db_access.save_notification(NotificationData(-1, datetime.now(), False, False), conn)
                    db_access.delete_job(job_data.job_id, conn)

                    print("Alerting 1")
                    print(notification_id)

                    await asyncio.sleep(job_data.response_time / 1000)

                    if not db_access.notification_admin_response_status(notification_id, True, conn):
                        print("Alerting 2")

                        await asyncio.sleep(job_data.response_time / 1000)

                        # Check if the secondary admin has responded and log the result
                            
                    else:
                        print("ACK")

                    db_access.delete_notification(notification_id, conn)
                finally:
                    conn.close()

                return

        await asyncio.sleep(job_data.period / 1000)


async def new_job(job_data: JobData):
    await pinging_job(job_data)
