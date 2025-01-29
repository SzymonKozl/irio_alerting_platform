import asyncio
import time
import smtplib
from queue import PriorityQueue
from aiohttp import ClientSession
from typing import Tuple, Optional
from email.mime.text import MIMEText
from datetime import datetime
import logging


import db_access
from common import *
from counters import *


active_jobs_cache = set()
active_jobs_sync_loc = threading.Lock()
cleanup_job_initialized = False

smtp_server = os.environ.get("SMTP_SERVER")
smtp_server = 'smtp.gmail.com' if not smtp_server else smtp_server
smtp_port = os.environ.get("SMTP_PORT")
smtp_port = 587 if not smtp_port else int(smtp_port)
smtp_username = os.environ.get('SMTP_USERNAME')
smtp_password = os.environ.get('SMTP_PASSWORD')


def send_email(to: str, subject: str, body: str):
    log_data = {"function_name": "send_email", "to": to, "subject": subject}
    logging.info("Send email called", extra={"json_fields": log_data})

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = smtp_username
    msg['To'] = to
    try:
        logging.info("Email sent", extra={"json_fields": log_data})
        smtp = smtplib.SMTP(smtp_server, smtp_port)
        smtp.starttls()
        smtp.login(smtp_username, smtp_password)
        smtp.sendmail(smtp_username, to, msg.as_string())
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


async def pinging_task(job_data: JobData, pod_index: int):
    global cleanup_job_initialized, active_jobs_sync_loc
    with active_jobs_sync_loc:
        active_jobs_cache.add(job_data.job_id)
        if not cleanup_job_initialized:
            logging.info("Starting active job updater job")
            cleanup_job_initialized = True
            asyncio.create_task(active_job_updater_task(pod_index))

    async def single_request():
        is_connected = False
        try:
            async with ClientSession() as session:
                PINGS_SENT_CTR.inc()
                is_connected = True
                HTTP_CONNS_ACTIVE_CTR.inc()
                async with session.get(job_data.url) as response:
                    if 200 <= response.status < 300:
                        SUCCESSFUL_PINGS_CTR.inc()
                    HTTP_CONNS_ACTIVE_CTR.dec()
                    return response
        except:
            if is_connected:
                HTTP_CONNS_ACTIVE_CTR.dec()
            return None

    futures: PriorityQueue[Tuple[int, asyncio.Task]] = PriorityQueue()
    while True:

        delay_start = time.time_ns()
        with active_jobs_sync_loc:
            if job_data.job_id not in active_jobs_cache:
                logging.info(f"Found that job with {job_data.job_id} is not active. finishing task.", extra={"json_fields": job_data})
                JOBS_ACTIVE_CTR.dec()
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
                    JOBS_ACTIVE_CTR.dec()

                    send_alert(job_data.mail1, job_data.url, notification_id, True)
                    db_access.set_job_inactive(job_data.job_id, conn)

                finally:
                    conn.close()
                try:

                    await asyncio.sleep(job_data.response_time / 1000)
                    conn = db_access.setup_connection(DB_HOST, DB_PORT)

                    if not db_access.get_notification_by_id(notification_id, conn).admin_responded:
                        second_notification_id = db_access.save_notification(NotificationData(-1, datetime.now(), False, 2, job_data.job_id), conn)
                        send_alert(job_data.mail2, job_data.url, second_notification_id, False)

                        await asyncio.sleep(job_data.response_time / 1000)

                        # Check if the secondary admin has responded and log the result
                finally:
                    conn.close()
                return

        delay = time.time_ns() - delay_start
        if delay / 1_000_000 > job_data.period:
            logging.warning("handling the event loop consumed more time than the pinging period! keeping pinging period cannot be guaranteed!", extra={"json_fields": job_data})
        await asyncio.sleep(max(0, job_data.period / 1000 - delay / 1_000_000))


async def new_job(job_data: JobData, pod_index: int):
    JOBS_ACTIVE_CTR.inc()
    await pinging_task(job_data, pod_index)


async def continue_notifications(job_data: JobData, notification_data: NotificationData):
    log_data = {"function_name": "continue_notifications", "job_data": job_data._asdict()}
    logging.info("Continue notifications called", extra={"json_fields": log_data})

    if job_data.is_active:
        try:
            conn = db_access.setup_connection(DB_HOST, DB_PORT)
            db_access.set_job_inactive(job_data.job_id, conn)
        finally:
            conn.close()

    remaining_response_time = notification_data.time_sent.timestamp() * 1000 + job_data.response_time - time.time_ns() / 1_000_000

    try:
        await asyncio.sleep(max(0, remaining_response_time / 1000))
        conn = db_access.setup_connection(DB_HOST, DB_PORT)

        notifications = db_access.get_notifications_for_jobs([job_data.job_id], conn)[job_data.job_id]
        if not any(notification.admin_responded for notification in notifications):
            second_notification_id = db_access.save_notification(NotificationData(-1, datetime.now(), False, 2, job_data.job_id), conn)
            send_alert(job_data.mail2, job_data.url, second_notification_id, False)
            await asyncio.sleep(job_data.response_time / 1000)
        logging.info("Notifying complete", extra={"json_fields": log_data})
    except Exception as e:
        logging.error("Error while sending a second notification: %s", e, extra={"json_fields": log_data})
    finally:
        conn.close()


async def active_job_updater_task(pod_index: int):
    global active_jobs_cache, active_jobs_sync_loc
    """
    Responsible for stopping deleted jobs.
    :param pod_index: pod index
    :return: None
    """
    while True:
        await asyncio.sleep(1)
        conn = db_access.setup_connection(DB_HOST, DB_PORT)
        try:
            active_jobs_cache_new = db_access.get_active_job_ids(conn, pod_index)
        except:
            active_jobs_cache_new = None
        finally:
            conn.close()
        if active_jobs_cache_new is not None:
            with active_jobs_sync_loc:
                active_jobs_cache = active_jobs_cache_new
