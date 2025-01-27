import sys
from pathlib import Path

server_dir = Path(__file__).parent.parent.parent / "server"
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


def insert_example_jobs(conn):
    cursor = conn.cursor()
    cursor.execute("INSERT INTO jobs VALUES (DEFAULT, 'mail1@example.com', 'mail2@example.com', 'http://example.com', 10, 11, 12, 0, true)")
    cursor.execute("INSERT INTO jobs VALUES (DEFAULT, 'mail3@example.com', 'mail2@example.com', 'http://ugabuga.com', 100, 100, 200, 1, true)")
    cursor.execute("INSERT INTO jobs VALUES (DEFAULT, 'mail4@example.com', 'mail5@example.com', 'http://service.com', 1000, 10, 100, 1, false)")
    conn.commit()


def test_db_access_set_job_inactive(postgresql):
    setup_db(postgresql)

    cursor = postgresql.cursor()
    cursor.execute("INSERT INTO jobs VALUES (DEFAULT, 'mail1@example.com', 'mail2@example.com', 'http://example.com', 10, 20, 30, 0, true);")
    cursor.execute("INSERT INTO jobs VALUES (DEFAULT, 'mail3@example.com', 'mail4@example.com', 'http://another.com', 11, 21, 31, 1, true);")
    postgresql.commit()

    cursor.execute("SELECT job_id FROM jobs WHERE is_active;")
    jobs_before = cursor.fetchall()
    assert len(jobs_before) == 2

    id_to_deactivate = jobs_before[0][0]

    db_access.set_job_inactive(id_to_deactivate, postgresql)

    cursor.execute("SELECT job_id FROM jobs WHERE is_active;")
    jobs_after = cursor.fetchall()
    assert len(jobs_after) == 1
    assert jobs_after[0][0] != id_to_deactivate

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
        response_time=200,
        is_active=True
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
    cursor.execute(f"INSERT INTO jobs VALUES (DEFAULT, '{primary_email}', 'mail2@example.com', 'http://example.com', 10, 20, 30, 0, true);")
    cursor.execute(f"INSERT INTO jobs VALUES (DEFAULT, '{primary_email}', 'mail3@example.com', 'http://another.com', 11, 21, 31, 1, false);")
    cursor.execute("INSERT INTO jobs VALUES (DEFAULT, 'mail4@example.com', 'mail5@example.com', 'http://yetanother.com', 12, 22, 32, 2, true);")
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
    assert job1.is_active == True
    assert job2.is_active == False


def test_db_access_save_notification(postgresql):
    setup_db(postgresql)
    insert_example_jobs(postgresql)

    notification = NotificationData(
        notification_id=-1,
        time_sent=datetime.now(),
        admin_responded=False,
        notification_num=1,
        job_id=1
    )

    notification_id = db_access.save_notification(notification, postgresql)
    
    cursor = postgresql.cursor()
    cursor.execute("SELECT notification_id FROM notifications;")
    result = cursor.fetchone()
    
    assert result is not None
    assert result[0] == notification_id


def test_db_access_get_notification_by_id(postgresql):
    setup_db(postgresql)
    insert_example_jobs(postgresql)

    cursor = postgresql.cursor()
    cursor.execute("INSERT INTO notifications VALUES (0, CURRENT_TIMESTAMP, FALSE, 1, 1);")
    cursor.execute("INSERT INTO notifications VALUES (1, CURRENT_TIMESTAMP, TRUE, 2, 3);")
    cursor.execute("INSERT INTO notifications VALUES (2, CURRENT_TIMESTAMP, TRUE, 1, 3);")
    postgresql.commit()

    notification = db_access.get_notification_by_id(1, postgresql)

    assert notification.admin_responded == True
    assert notification.notification_num == 2


def test_db_access_udate_notification_response_status1(postgresql):
    setup_db(postgresql)
    insert_example_jobs(postgresql)

    notification_id = 0

    cursor = postgresql.cursor()
    cursor.execute(f"INSERT INTO notifications VALUES ({notification_id}, CURRENT_TIMESTAMP, FALSE, 1, 3);")
    cursor.execute("INSERT INTO notifications VALUES (1, CURRENT_TIMESTAMP, TRUE, 1, 2);")
    cursor.execute("INSERT INTO notifications VALUES (2, CURRENT_TIMESTAMP, TRUE, 2, 1);")
    postgresql.commit()

    db_access.update_notification_response_status(notification_id, postgresql)

    cursor.execute(f"SELECT admin_responded FROM notifications WHERE notification_id = {notification_id};")
    result = cursor.fetchone()

    assert result is not None
    assert result[0] == True
