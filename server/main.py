import os

from aiohttp import web
from aiohttp.web_runner import GracefulExit
from aiohttp_swagger import setup_swagger
import asyncio
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from counters import *
import logging
import signal
import os, sys
import logging

from common import *
import db_access
from coroutines import new_job, continue_notifications
from logging_setup import setup_logging

STATEFUL_SET_INDEX = int(os.getenv('STATEFUL_SET_INDEX'))

db_conn = db_access.setup_connection(DB_HOST, DB_PORT)


async def metrics_handler(request):
    """Expose Prometheus metrics."""
    return web.Response(body=generate_latest(), content_type=CONTENT_TYPE_LATEST.rsplit(';', 1)[0])


async def health_handler(request):
    """Health check endpoint."""
    return web.Response(text="OK", status=200)


async def add_service(request: web.Request):
    """
    ---
    description: Adds a service to monitor.
    tags:
      - Service Monitoring
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            url:
              type: string
              description: URL of the service.
              example: "https://www.google.com/"
            primary_email:
              type: string
              description: Email of the primary administrator.
              example: "primary@example.com"
            secondary_email:
              type: string
              description: Email of the secondary administrator.
              example: "secondary@gmail.com"
            period:
              type: integer
              description: Service check period in ms.
              example: 10000
            alerting_window:
              type: integer
              description: Alerting window in ms.
              example: 10000
            response_time:
              type: integer
              description: Response time in ms.
              example: 10000
    responses:
      "200":
        description: Successful response
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: True
            job_id:
              type: integer
              example: 0
    """
    log_data = {"function_name" : "add_service"}
    logging.info("Add service request received", extra={"json_fields" : log_data})

    json = await request.json()
    try:
        url = json['url']
        mail1 = json['primary_email']
        mail2 = json['secondary_email']
        period = json['period']
        alerting_window = json['alerting_window']
        response_time = json['response_time']
    except KeyError as e:
        logging.error("Missing key in request: %s", e, extra={"json_fields" : log_data})
        return web.json_response({'error': str(e)}, status=400)
    if not isinstance(period, int) or not isinstance(alerting_window, int) or not isinstance(response_time, int):
        logging.error("Invalid data type for period, alerting_window or response_time",
                      extra={"json_fields" : log_data})
        return web.json_response({'error': ERR_MSG_CREATE_POSITIVE_INT}, status=400)
    if period <= 0 or alerting_window <= 0 or response_time <= 0:
        logging.error("Non-positive value for period, alerting_window or response_time",
                      extra={"json_fields" : log_data})
        return web.json_response({'error': ERR_MSG_CREATE_POSITIVE_INT}, status=400)

    job_data = JobData(-1, mail1, mail2, url ,period, alerting_window, response_time, True)
    try:
        job_id = db_access.save_job(job_data, db_conn, STATEFUL_SET_INDEX)
    except Exception as e:
        logging.error("Error saving job to database: %s", e,
                      extra={"json_fields" : {**log_data, "job_data" : job_data._asdict()}})
        return web.json_response({'error': str(e)}, status=501)
    job_data = JobData(job_id, mail1, mail2, url, period, alerting_window, response_time, True)
    asyncio.create_task(new_job(job_data, STATEFUL_SET_INDEX))

    logging.info("Service added",
                 extra={"json_fields" : {**log_data, "job_data" : job_data._asdict()}})
    return web.json_response({'success': True, 'job_id': job_id}, status=200)


async def receive_alert(request: web.Request):
    """
    ---
    description: Confirms that an alert was received.
    tags:
      - Service Monitoring
    produces:
      - application/json
    parameters:
      - in: query
        name: notification_id
        required: true
        type: integer
        description: ID of the received notification.
        example: 0
    responses:
      "200":
        description: Successful response
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: True
    """
    log_data = {"function_name" : "receive_alert"}
    logging.info("Receive alert request received", extra={"json_fields" : log_data})

    try:
        notification_id = int(request.query['notification_id'])
    except KeyError as e:
        logging.error("Missing key in request: %s", e, extra={"json_fields" : log_data})
        return web.json_response({'error': str(e)}, status=400)
    except ValueError as e:
        logging.error("Invalid value for notification_id: %s", e,
                      extra={"json_fields" : log_data})
        return web.json_response({'error': str(e)}, status=400)

    log_data.update({"notification_id": notification_id})
    try:
        if not db_access.update_notification_response_status(notification_id, db_conn):
            logging.info(f"Tried to update notification with {notification_id} ID, no changes to db were made", extra={"json_fields" : log_data})
            return web.json_response({'error': "Alert already acknowledged or does not exist"}, status=400)
    except Exception as e:
        logging.error("Error updating alert response status: %s", e,
                      extra={"json_fields" : log_data})
        return web.json_response({'error': str(e)}, status=500)

    logging.info("Alert received", extra={"json_fields" : log_data})
    return web.json_response({'success': True}, status=200)


async def get_alerting_jobs(request: web.Request):
    """
    ---
    description: Returns data of alerting jobs with a specified primary administrator's email.
    tags:
      - Service Monitoring
    produces:
      - application/json
    parameters:
      - in: query
        name: primary_email
        required: true
        type: string
        description: Email of the primary administrator.
        example: "primary@example.com"
    responses:
      "200":
        description: Successful response
        schema:
          type: object
          properties:
            jobs:
              type: array
              example: []
    """
    log_data = {"function_name" : "get_alerting_jobs"}
    logging.info("Get alerting jobs request received", extra={"json_fields" : log_data})

    try:
        mail1 = request.query['primary_email']
    except KeyError as e:
        logging.error("Missing key in request: %s", e, extra={"json_fields" : log_data})
        return web.json_response({'error': str(e)}, status=400)

    log_data["primary_email"] = mail1
    try:
        jobs = db_access.get_jobs(mail1, db_conn)
    except Exception as e:
        logging.error("Error getting jobs from database: %s", e,
                      extra={"json_fields" : log_data})
        return web.json_response({'error': str(e)}, status=500)
    resp = {"jobs": []}
    for job in jobs:
        resp["jobs"].append(job._asdict())
    logging.info("Alerting jobs retrieved", extra={"json_fields" : log_data})
    return web.json_response(resp, status=200)


async def del_job(request: web.Request):
    """
    ---
    description: Deletes a monitored service.
    tags:
      - Service Monitoring
    produces:
      - application/json
    parameters:
      - in: query
        name: job_id
        required: true
        type: integer
        description: ID of the alerting job to delete.
        example: 0
    responses:
      "200":
        description: Successful response
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: True
    """
    log_data = {"function_name" : "del_job"}
    logging.info("Delete job request received", extra={"json_fields" : log_data})

    try:
        job_id = request.query['job_id']
    except KeyError as e:
        logging.error("Missing key in request: %s", e, extra={"json_fields" : log_data})
        return web.json_response({'error': str(e)}, status=400)

    log_data["job_id"] = job_id
    try:
        db_access.set_job_inactive(int(job_id), db_conn)
    except Exception as e:
        logging.error("Error deleting job from database: %s", e, extra={"json_fields" : log_data})
        return web.json_response({'error': str(e)}, status=500)
    logging.info("Job deleted", extra={"json_fields" : log_data})
    return web.json_response({'success': True}, status=200)


async def hello(request: web.Request):
    """
    ---
    description: Returns a simple Hello, World! message.
    responses:
      200:
        description: Successful response
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: "Hello, World!"
    """
    return web.json_response({"message": "hello world"})


async def recover_jobs():
    log_data = {"function_name" : "recover_jobs"}
    logging.info("Recovering jobs", extra={"json_fields" : log_data})

    try:
      jobs = db_access.get_jobs_for_stateful_set(STATEFUL_SET_INDEX, db_conn)
    except Exception as e:
        logging.error("Error getting jobs from database: %s", e, extra={"json_fields" : log_data})
        return

    job_dict = {job.job_id: job for job in jobs}

    active_jobs_ids = [job.job_id for job in jobs if job.is_active]
    inactive_jobs_ids = [job.job_id for job in jobs if not job.is_active]

    try:
      notifications = db_access.get_notifications_for_jobs(inactive_jobs_ids, db_conn)
    except Exception as e:
        logging.error("Error getting notifications from database: %s", e, extra={"json_fields" : log_data})
        return

    pending_notifications_jobs_ids = [
      job_id for job_id in inactive_jobs_ids
      # if previously the pod crashed after sending an alert, but before setting the job
      # as inactive, there can be multiple notifications for the primary admin
      if notifications[job_id] and all(
        notification.notification_num == 1 and not notification.admin_responded
        for notification in notifications[job_id]
      )
    ]

    for job_id in active_jobs_ids:
        job = job_dict[job_id]
        asyncio.create_task(new_job(job, STATEFUL_SET_INDEX))
        logging.info("Resumed job", extra={"json_fields" : {**log_data, "job_data" : job._asdict()}})
    logging.info("Resumed all jobs", extra={"json_fields" : log_data})

    for job_id in pending_notifications_jobs_ids:
        job = job_dict[job_id]
        # get newest notification
        notification = max(notifications[job.job_id], key=lambda x: x.time_sent)
        asyncio.create_task(continue_notifications(job, notification))
        logging.info("Resumed job notifying", extra={"json_fields" : {**log_data, "job_data" : job._asdict()}})
    logging.info("Resumed all job notifications", extra={"json_fields" : log_data})

async def recover(app):
    asyncio.create_task(recover_jobs())


app = web.Application()
app.on_startup.append(recover)
app.router.add_post('/add_service', add_service)
app.router.add_get('/receive_alert', receive_alert)
app.router.add_get('/alerting_jobs', get_alerting_jobs)
app.router.add_get('/metrics_handler', metrics_handler)
app.router.add_get('/healthz', health_handler)
app.router.add_delete('/del_job', del_job)
app.router.add_get('/hello', hello)
setup_swagger(app, swagger_url="/api/doc", title="Alerting Platform API", description="API Documentation")


def handle_SIGINT(signum, frame):
    os.close(sys.stdout.fileno())
    raise GracefulExit()


signal.signal(signal.SIGTERM, handle_SIGINT)


if __name__ == '__main__':
    try:
        setup_logging()
    except Exception as e:
        logging.warning("Using default logging setup: %s", e)

    web.run_app(app, host='0.0.0.0', port=APP_PORT)
