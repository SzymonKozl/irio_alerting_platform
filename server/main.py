from aiohttp import web
import asyncio

from common import *
import db_access
from coroutines import delete_job, new_job, init_smtp

STATEFUL_SET_INDEX = 1 # todo: set to real value

db_conn = db_access.setup_connection(DB_HOST, DB_PORT)


async def add_service(request: web.Request):
    json = await request.json()
    try:
        url = json['url']
        mail1 = json['primary_email']
        mail2 = json['secondary_email']
        period = json['period']
        alerting_window = json['alerting_window']
        response_time = json['response_time']
    except KeyError as e:
        return web.json_response({'error': str(e)}, status=400)
    if not isinstance(period, int) or not isinstance(alerting_window, int) or not isinstance(response_time, int):
        return web.json_response({'error': ERR_MSG_CREATE_POSITIVE_INT}, status=400)
    if period <= 0 or alerting_window <= 0 or response_time <= 0:
        return web.json_response({'error': ERR_MSG_CREATE_POSITIVE_INT}, status=400)

    job_data = JobData(-1, mail1, mail2, url ,period, alerting_window, response_time)
    try:
        job_id = db_access.save_job(job_data, db_conn, STATEFUL_SET_INDEX)
    except Exception as e:
        return web.json_response({'error': str(e)}, status=501)
    job_data = JobData(job_id, mail1, mail2, url, period, alerting_window, response_time)
    asyncio.create_task(new_job(job_data))

    return web.json_response({'success': True, 'job_id': job_id}, status=200)


async def receive_alert(request: web.Request):
    try:
        # Not using json here, because we want to send a link through email
        notification_id = int(request.query['notification_id'])
        primary_admin = request.query['primary_admin'].lower() == 'true'
    except KeyError as e:
        return web.json_response({'error': str(e)}, status=400)
    except ValueError as e:
        return web.json_response({'error': str(e)}, status=400)

    try:
        db_access.update_notification_response_status(notification_id, primary_admin, db_conn)
    except Exception as e:
        return web.json_response({'error': str(e)}, status=500)

    return web.json_response({'success': True}, status=200)


async def get_alerting_jobs(request: web.Request):
    json = await request.json()
    try:
        mail1 = json['primary_email']
    except KeyError as e:
        return web.json_response({'error': str(e)}, status=400)

    try:
        jobs = db_access.get_jobs(mail1, db_conn)
    except Exception as e:
        return web.json_response({'error': str(e)}, status=500)
    resp = {"jobs": []}
    for job in jobs:
        resp["jobs"].append(job._asdict())
    return web.json_response(resp, status=200)


async def del_job(request: web.Request):
    json = await request.json()
    try:
        job_id = json['job_id']
    except KeyError as e:
        return web.json_response({'error': str(e)}, status=400)
    try:
        db_access.delete_job(job_id, db_conn)
    except Exception as e:
        return web.json_response({'error': str(e)}, status=500)
    asyncio.create_task(delete_job(job_id))
    return web.json_response({'success': True}, status=200)


app = web.Application()
app.router.add_post('/add_service', add_service)
app.router.add_get('/receive_alert', receive_alert)
app.router.add_get('/alerting_jobs', get_alerting_jobs)
app.router.add_delete('/del_job', del_job)

if __name__ == '__main__':
    try:
        init_smtp()
    except Exception as e:
          print(f"Error initializing smtp connection: {e}")

    web.run_app(app, host=APP_HOST, port=APP_PORT)
