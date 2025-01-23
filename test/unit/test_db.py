import sys
from pathlib import Path

server_dir = Path(__file__).parent.parent / "server"
sys.path.append(str(server_dir))

import pytest
import pytest_postgresql
from datetime import datetime
import db_access
from common import JobData, NotificationData


def setup_db(conn):
    setup_file = server_dir / "db_migrations/v1__setup.sql"
    with open(setup_file, 'r') as file:
        sql_script = file.read()
    
    cursor = conn.cursor()
    cursor.execute(sql_script)
    conn.commit()


def test_db_access_delete_job(postgresql):
    setup_db(postgresql)

    cursor = postgresql.cursor()
    cursor.execute("INSERT INTO jobs VALUES (DEFAULT, 'mail1@example.com', 'mail2@example.com', 'http://example.com', 10, 20, 30, 0);")
    cursor.execute("INSERT INTO jobs VALUES (DEFAULT, 'mail3@example.com', 'mail4@example.com', 'http://another.com', 11, 21, 31, 1);")
    postgresql.commit()

    cursor.execute("SELECT job_id FROM jobs;")
    jobs_before = cursor.fetchall()
    assert len(jobs_before) == 2

    id_to_delete = jobs_before[0][0]

    db_access.delete_job(id_to_delete, postgresql)

    cursor.execute("SELECT job_id FROM jobs;")
    jobs_after = cursor.fetchall()
    assert len(jobs_after) == 1
    assert jobs_after[0][0] != id_to_delete

    cursor.close()


def test_db_access_save_job(postgresql):
    setup_db(postgresql)

    job = JobData(
        job_id=-1,
        mail1="mail1@example.com",
        mail2="mail2@example.com",
        url="http://example.com",
        period=30,
        window=10,
        response_time=200
    )
    
    set_idx = 1

    job_id = db_access.save_job(job, postgresql, set_idx)
    
    cursor = postgresql.cursor()
    cursor.execute("SELECT job_id FROM jobs;")
    result = cursor.fetchone()
    
    assert result is not None
    assert result[0] == job_id


def test_db_access_get_jobs(postgresql):
    setup_db(postgresql)

    primary_email = "mail1@example.com"

    cursor = postgresql.cursor()
    cursor.execute(f"INSERT INTO jobs VALUES (DEFAULT, '{primary_email}', 'mail2@example.com', 'http://example.com', 10, 20, 30, 0);")
    cursor.execute(f"INSERT INTO jobs VALUES (DEFAULT, '{primary_email}', 'mail3@example.com', 'http://another.com', 11, 21, 31, 1);")
    cursor.execute("INSERT INTO jobs VALUES (DEFAULT, 'mail4@example.com', 'mail5@example.com', 'http://yetanother.com', 12, 22, 32, 2);")
    postgresql.commit()

    jobs = db_access.get_jobs(primary_email, postgresql)

    assert len(jobs) == 2

    job1, job2 = jobs
    assert job1.mail1 == primary_email
    assert job2.mail1 == primary_email
    assert job1.mail2 == 'mail2@example.com'
    assert job2.mail2 == 'mail3@example.com'
    assert job1.url == "http://example.com"
    assert job2.url == "http://another.com"
    assert job1.period == 10
    assert job2.period == 11
    assert job1.window == 20
    assert job2.window == 21
    assert job1.response_time == 30
    assert job2.response_time == 31


def test_db_access_delete_notification(postgresql):
    setup_db(postgresql)

    cursor = postgresql.cursor()
    cursor.execute("INSERT INTO notifications VALUES (DEFAULT, CURRENT_TIMESTAMP, FALSE, FALSE);")
    cursor.execute("INSERT INTO notifications VALUES (DEFAULT, CURRENT_TIMESTAMP, FALSE, FALSE);")
    postgresql.commit()

    cursor.execute("SELECT notification_id FROM notifications;")
    notifications_before = cursor.fetchall()
    assert len(notifications_before) == 2

    id_to_delete = notifications_before[0][0]

    db_access.delete_notification(id_to_delete, postgresql)

    cursor.execute("SELECT notification_id FROM notifications;")
    notifications_after = cursor.fetchall()
    assert len(notifications_after) == 1
    assert notifications_after[0][0] != id_to_delete

    cursor.close()


def test_db_access_save_notification(postgresql):
    setup_db(postgresql)

    notification = NotificationData(
        notification_id=-1,
        time_sent=datetime.now(),
        primary_admin_responded=False,
        secondary_admin_responded=False
    )

    notification_id = db_access.save_notification(notification, postgresql)
    
    cursor = postgresql.cursor()
    cursor.execute("SELECT notification_id FROM notifications;")
    result = cursor.fetchone()
    
    assert result is not None
    assert result[0] == notification_id


def test_db_access_get_notification_by_id(postgresql):
    setup_db(postgresql)

    cursor = postgresql.cursor()
    cursor.execute("INSERT INTO notifications VALUES (0, CURRENT_TIMESTAMP, FALSE, FALSE);")
    cursor.execute("INSERT INTO notifications VALUES (1, CURRENT_TIMESTAMP, TRUE, TRUE);")
    cursor.execute("INSERT INTO notifications VALUES (2, CURRENT_TIMESTAMP, TRUE, FALSE);")
    postgresql.commit()

    notification = db_access.get_notification_by_id(1, postgresql)

    assert notification.primary_admin_responded == True
    assert notification.secondary_admin_responded == True


def test_db_access_udate_notification_response_status1(postgresql):
    setup_db(postgresql)

    notification_id = 0

    cursor = postgresql.cursor()
    cursor.execute(f"INSERT INTO notifications VALUES ({notification_id}, CURRENT_TIMESTAMP, FALSE, FALSE);")
    cursor.execute("INSERT INTO notifications VALUES (1, CURRENT_TIMESTAMP, TRUE, TRUE);")
    cursor.execute("INSERT INTO notifications VALUES (2, CURRENT_TIMESTAMP, TRUE, FALSE);")
    postgresql.commit()

    db_access.update_notification_response_status(notification_id, True, postgresql)

    cursor.execute(f"SELECT primary_admin_responded FROM notifications WHERE notification_id = {notification_id};")
    result = cursor.fetchone()

    assert result is not None
    assert result[0] == True


def test_db_access_udate_notification_response_status2(postgresql):
    setup_db(postgresql)

    notification_id = 0

    cursor = postgresql.cursor()
    cursor.execute(f"INSERT INTO notifications VALUES ({notification_id}, CURRENT_TIMESTAMP, FALSE, FALSE);")
    cursor.execute("INSERT INTO notifications VALUES (1, CURRENT_TIMESTAMP, TRUE, TRUE);")
    cursor.execute("INSERT INTO notifications VALUES (2, CURRENT_TIMESTAMP, TRUE, FALSE);")
    postgresql.commit()

    db_access.update_notification_response_status(notification_id, False, postgresql)

    cursor.execute(f"SELECT secondary_admin_responded FROM notifications WHERE notification_id = {notification_id};")
    result = cursor.fetchone()

    assert result is not None
    assert result[0] == True
