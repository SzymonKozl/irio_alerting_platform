import os
from typing import Optional, List

import psycopg2

from common import JobData, job_id_t, NotificationData, notification_id_t


def setup_connection(db_host: str, db_port: int) -> Optional[psycopg2.extensions.connection]:
    db_user = os.environ.get("DB_USER")
    db_pass = os.environ.get("DB_PASS")
    db_name = os.environ.get("DB_NAME")

    try:
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_pass,
            database=db_name
        )
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
        return None

    return conn


def delete_job(job_id: job_id_t, conn: psycopg2.extensions.connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        f"""
        DELETE FROM jobs WHERE job_id = %s;
        """,
        (job_id,)
    )
    conn.commit()


def save_job(job: JobData, conn: psycopg2.extensions.connection, set_idx: int) -> job_id_t:
    cursor = conn.cursor()
    cursor.execute(
        f"""
        INSERT INTO jobs VALUES (DEFAULT, %s, %s, %s, %s, %s, %s, %s)
        RETURNING job_id;
        """,
        (job.mail1, job.mail2, job.url, job.period, job.window, job.response_time, set_idx)
    )
    conn.commit()
    return job_id_t(cursor.fetchone()[0])


def get_jobs(primary_email: str, conn: psycopg2.extensions.connection) -> List[JobData]:
    cursor = conn.cursor()
    cursor.execute(
        f"""
        SELECT * FROM jobs WHERE mail1 = %s;
        """,
        (primary_email,)
    )
    rows = cursor.fetchall()

    jobs = []
    for row in rows:
        jobs.append(JobData(row[0], row[1], row[2], row[3], row[4], row[5], row[6]))
    return jobs


def delete_notification(notification_id: int, conn: psycopg2.extensions.connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        f"""
        DELETE FROM notifications WHERE notification_id = %s;
        """,
        (notification_id,)
    )
    conn.commit()


def save_notification(notification: NotificationData, conn: psycopg2.extensions.connection) -> notification_id_t:
    cursor = conn.cursor()
    cursor.execute(
        f"""
        INSERT INTO notifications VALUES (DEFAULT, %s, %s, %s)
        RETURNING notification_id;
        """,
        (notification.time_sent, notification.primary_admin_responded, notification.secondary_admin_responded)
    )
    conn.commit()
    return notification_id_t(cursor.fetchone()[0])


def get_notification_by_id(notification_id: int, conn: psycopg2.extensions.connection) -> NotificationData:
    cursor = conn.cursor()
    cursor.execute(
        f"""
        SELECT * FROM notifications WHERE notification_id = %s;
        """,
        (notification_id,)
    )

    return NotificationData(*cursor.fetchone())


def update_notification_response_status(notification_id: int, primary_admin: bool, conn: psycopg2.extensions.connection) -> None:
    cursor = conn.cursor()

    if primary_admin:
        cursor.execute(
            f"""
            UPDATE notifications SET primary_admin_responded = TRUE WHERE notification_id = %s;
            """,
            (notification_id,)
        )
    else:
        cursor.execute(
            f"""
            UPDATE notifications SET secondary_admin_responded = TRUE WHERE notification_id = %s;
            """,
            (notification_id,)
        )

    conn.commit()
