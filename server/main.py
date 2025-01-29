from aiohttp import web
from aiohttp.web_runner import GracefulExit
from aiohttp_swagger import setup_swagger
import asyncio
import signal
import os, sys
import logging

from common import *
import db_access
from coroutines import new_job, init_smtp, continue_notifications
from logging_setup import setup_logging

STATEFUL_SET_INDEX = 1 # todo: set to real value

db_conn = db_access.setup_connection(DB_HOST, DB_PORT)


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
      - in: query
        name: primary_admin
        required: true
        type: boolean
        description: Received by the primary admin.
        example: true
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
        primary_admin = request.query['primary_admin'].lower() == 'true'
    except KeyError as e:
        logging.error("Missing key in request: %s", e, extra={"json_fields" : log_data})
        return web.json_response({'error': str(e)}, status=400)
    except ValueError as e:
        logging.error("Invalid value for notification_id: %s", e,
                      extra={"json_fields" : log_data})
        return web.json_response({'error': str(e)}, status=400)

    log_data.update({"notification_id": notification_id, "primary_admin": primary_admin})
    try:
        db_access.update_notification_response_status(notification_id, db_conn)
    except Exception as e:
        logging.error("Error updating alert response status: %s", e, 
                      extra={"json_fields" : log_data})
        return web.json_response({'error': str(e)}, status=500)

    logging.info("Alert received", extra={"json_fields" : log_data})
    return web.json_response({'success': True}, status=200)


async def get_alerting_jobs(request: web.Request):
    """
    ---
    description: Returns IDs of alerting job with a specified primary administrator's email.
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


async def recover_jobs():
    log_data = {"function_name" : "recover_jobs"}
    logging.info("Recovering jobs", extra={"json_fields" : log_data})

    try:
      jobs = db_access.get_jobs_for_stateful_set(STATEFUL_SET_INDEX, db_conn)
    except Exception as e:
        logging.error("Error getting jobs from database: %s", e, extra={"json_fields" : log_data})
        return
    
    try:
      notifications = db_access.get_notifications_for_jobs([job.job_id for job in jobs], db_conn)
    except Exception as e:
        logging.error("Error getting notifications from database: %s", e, extra={"json_fields" : log_data})
        return

    pending_notifications_jobs = []
    active_jobs = []

    for job in jobs:
        if (len(notifications[job.job_id]) == 1 and
            notifications[job.job_id][0].notification_num == 1 and
            not notifications[job.job_id][0].admin_responded):
              pending_notifications_jobs.append(job)
        elif job.is_active:
            # Previous check is needed, because the pod might crash 
            # after saving the first notification and before setting the job as inactive
            active_jobs.append(job)

    for job in active_jobs:
        asyncio.create_task(new_job(job, STATEFUL_SET_INDEX))
        logging.info("Resumed job", extra={"json_fields" : {**log_data, "job_data" : job._asdict()}})
    
    for job in pending_notifications_jobs:
        asyncio.create_task(continue_notifications(job, notifications[job.job_id][0]))
        logging.info("Resumed notifying", extra={"json_fields" : {**log_data, "job_data" : job._asdict()}})
    

async def recover(app):
    asyncio.create_task(recover_jobs())


app = web.Application()
app.on_startup.append(recover)
app.router.add_post('/add_service', add_service)
app.router.add_get('/receive_alert', receive_alert)
app.router.add_get('/alerting_jobs', get_alerting_jobs)
app.router.add_delete('/del_job', del_job)
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

    try:
        init_smtp()
    except Exception as e:
        logging.error("Error initializing SMTP connection: %s", e,
                      extra={"json_fields" : {"function_name" : "main"}})

    web.run_app(app, host=APP_HOST, port=APP_PORT)
