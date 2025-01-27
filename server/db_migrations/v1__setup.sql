DROP TABLE IF EXISTS jobs;
DROP TABLE IF EXISTS notifications;

CREATE TABLE jobs (
    job_id SERIAL PRIMARY KEY not null,
    mail1 varchar(255) not null,
    mail2 varchar(255) not null,
    url varchar(511) not null,
    period INT not null,
    alerting_window INT not null,
    response_time INT not null,
    stateful_set_index INT not null
);

CREATE TABLE notifications (
    notification_id SERIAL PRIMARY KEY not null,
    time_sent timestamp not null,
    admin_responded BOOLEAN not null,
    notification_no INT not null
);