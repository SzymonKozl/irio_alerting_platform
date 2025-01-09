import asyncio
from json import dumps

from flask import Flask, request, Response
from flasgger import Swagger

from common import *
import db_access
from coroutines import delete_job, new_job


app = Flask(__name__)
swagger = Swagger(app)

DB_HOST = 'localhost'
DB_PORT = 5432

db_conn = db_access.setup_connection(DB_HOST, DB_PORT)


@app.route('/add_service', methods=['POST'])
def add_service():
    json = request.get_json()
    try:
        url = json['url']
        mail1 = json['primary_email']
        mail2 = json['secondary_email']
        period = json['period']
        alerting_window = json['alerting_window']
        response_time = json['response_time']
    except KeyError as e:
        return Response(dumps({'error': str(e)}), status=400, mimetype='application/json')
    if not isinstance(period, int) or not isinstance(alerting_window, int) or not isinstance(response_time, int):
        return Response(dumps({'error': ERR_MSG_CREATE_POSITIVE_INT}), status=400, mimetype='application/json')
    if period <= 0 or alerting_window <= 0 or response_time <= 0:
        return Response(dumps({'error': ERR_MSG_CREATE_POSITIVE_INT}), status=400, mimetype='application/json')

    job_data = JobData(-1, mail1, mail2, url ,period, alerting_window, response_time)
    try:
        job_id = db_access.save_job(job_data, db_conn)
    except Exception as e:
        return Response(dumps({'error': str(e)}), status=500, mimetype='application/json')
    job_data = JobData(job_id, mail1, mail2, url, period, alerting_window, response_time)
    asyncio.create_task(new_job(job_data))

    return Response(dumps({'success': True}), status=200, mimetype='application/json')


@app.route('/alerting_jobs', methods=['GET'])
def get_alerting_jobs():
    json = request.get_json()
    try:
        mail1 = json['primary_email']
    except KeyError as e:
        return Response(dumps({'error': str(e)}), status=400, mimetype='application/json')

    try:
        jobs = db_access.get_jobs(mail1, db_conn)
    except Exception as e:
        return Response(dumps({'error': str(e)}), status=500, mimetype='application/json')
    resp = {"jobs": []}
    for job in jobs:
        resp["jobs"].append(job._asdict())
    return Response(dumps(resp), status=200, mimetype='application/json')


@app.route('/del_job', methods=['DELETE'])
def del_job():
    json = request.get_json()
    try:
        job_id = json['job_id']
    except KeyError as e:
        return Response(dumps({'error': str(e)}), status=400, mimetype='application/json')
    try:
        db_access.delete_job(job_id, db_conn)
    except Exception as e:
        return Response(dumps({'error': str(e)}), status=500, mimetype='application/json')
    asyncio.create_task(delete_job(job_id))
    return Response(dumps({'success': True}), status=200, mimetype='application/json')


if __name__ == '__main__':
    app.run(debug=True)
