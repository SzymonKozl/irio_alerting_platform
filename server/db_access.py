import os
from typing import Optional, List, Set

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


def set_job_inactive(job_id: job_id_t, conn: psycopg2.extensions.connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        f"""
        UPDATE jobs SET is_active=false WHERE jobs.job_id = %s;
        """,
        (job_id,)
    )
    conn.commit()


def save_job(job: JobData, conn: psycopg2.extensions.connection, set_idx: int) -> job_id_t:
    cursor = conn.cursor()
    cursor.execute(
        f"""
        INSERT INTO jobs VALUES (DEFAULT, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING job_id;
        """,
        (job.mail1, job.mail2, job.url, job.period, job.window, job.response_time, set_idx, job.is_active)
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
        jobs.append(JobData(row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[8]))
    return jobs


def save_notification(notification: NotificationData, conn: psycopg2.extensions.connection) -> notification_id_t:
    cursor = conn.cursor()
    cursor.execute(
        f"""
        INSERT INTO notifications VALUES (DEFAULT, %s, %s, %s, %s)
        RETURNING notification_id;
        """,
        (notification.time_sent, notification.admin_responded, notification.notification_num, notification.job_id)
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


def update_notification_response_status(notification_id: int, conn: psycopg2.extensions.connection) -> None:
    cursor = conn.cursor()

    cursor.execute(
        f"""
        UPDATE notifications SET admin_responded = TRUE WHERE notification_id = %s;
        """,
        (notification_id,)
    )

    conn.commit()


def get_active_job_ids(conn: psycopg2.extensions.connection, pod_index: int) -> Set[job_id_t]:
    """
    :param conn: postgres connection
    :param pod_index: index of pod
    :return: list of all active jobs assigned to this pod
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT job_id FROM jobs WHERE is_active = TRUE and stateful_set_index = %s;
        """,
        (pod_index,)
    )
    conn.commit()

    return {job_id_t(x[0]) for x in cursor.fetchall()}


def get_jobs_for_stateful_set(stateful_set_index: int, conn: psycopg2.extensions.connection) -> List[JobData]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM jobs WHERE stateful_set_index = %s;
        """,
        (stateful_set_index,)
    )
    rows = cursor.fetchall()
    
    jobs = []
    for row in rows:
        jobs.append(JobData(row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[8]))
    return jobs
