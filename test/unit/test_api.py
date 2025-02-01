import sys
from pathlib import Path

server_dir = Path(__file__).parent.parent.parent / "server"
sys.path.append(str(server_dir))

import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from aiohttp import web
import main
from common import JobData


example_payload = {
    "url": "http://example.com",
    "primary_email": "primary@example.com",
    "secondary_email": "secondary@example.com",
    "period": 10,
    "alerting_window": 5,
    "response_time": 2
}


def setup_app():
    app = web.Application()
    app.router.add_post("/add_service", main.add_service)
    app.router.add_get("/receive_alert", main.receive_alert)
    app.router.add_get("/get_alerting_jobs", main.get_alerting_jobs)
    app.router.add_delete('/del_job', main.del_job)
    return app


@pytest.mark.asyncio
async def test_add_service_success(aiohttp_client):
    with patch("main.db_access.save_job", return_value=123), \
         patch("main.new_job", new_callable=AsyncMock):

        test_client = await aiohttp_client(setup_app())

        payload = example_payload.copy()

        resp = await test_client.post("/add_service", json=payload)
        assert resp.status == 200
        data = await resp.json()
        assert data == {"success": True, "job_id": 123}


@pytest.mark.asyncio
async def test_add_service_missing_keys(aiohttp_client):
    test_client = await aiohttp_client(setup_app())

    payload = {"url": "http://example.com"}
    resp = await test_client.post("/add_service", json=payload)
    assert resp.status == 400


@pytest.mark.asyncio
async def test_add_service_invalid_types(aiohttp_client):
    test_client = await aiohttp_client(setup_app())

    payload = example_payload.copy()
    payload["period"] = "ten"

    resp = await test_client.post("/add_service", json=payload)
    assert resp.status == 400


@pytest.mark.asyncio
async def test_add_service_non_positive_values(aiohttp_client):
    test_client = await aiohttp_client(setup_app())

    payload = example_payload.copy()
    payload["response_time"] = -1

    resp = await test_client.post("/add_service", json=payload)
    assert resp.status == 400


@pytest.mark.asyncio
async def test_receive_alert_success(aiohttp_client):
    with patch("main.db_access.update_notification_response_status", return_value=True):
        test_client = await aiohttp_client(setup_app())

        params = {"notification_id": "42"}

        resp = await test_client.get("/receive_alert", params=params)
        assert resp.status == 200
        data = await resp.json()
        assert data == {"success": True}


@pytest.mark.asyncio
async def test_receive_alert_missing_keys(aiohttp_client):
    test_client = await aiohttp_client(setup_app())

    params = {}

    resp = await test_client.get("/receive_alert", params=params)
    assert resp.status == 400


@pytest.mark.asyncio
async def test_receive_alert_invalid_notification_id(aiohttp_client):
    test_client = await aiohttp_client(setup_app())

    params = {"notification_id": "not_a_number"}

    resp = await test_client.get("/receive_alert", params=params)
    assert resp.status == 400


@pytest.mark.asyncio
async def test_get_alerting_jobs_success(aiohttp_client):
    jobData = JobData("primary@example.com", "secondary@example.com", "https://example.com", 12, 54, 42, 1, False)
    with patch("main.db_access.get_jobs", return_value=[jobData,]):
        test_client = await aiohttp_client(setup_app())

        params = {'primary_email': 'primary@example.com'}

        resp = await test_client.get("/get_alerting_jobs", params=params)
        assert resp.status == 200
        data = await resp.json()
        assert data == {"jobs": [jobData._asdict(),]}


@pytest.mark.asyncio
async def test_get_alerting_jobs_missing_primary_email(aiohttp_client):
    test_client = await aiohttp_client(setup_app())

    resp = await test_client.get("/get_alerting_jobs")
    assert resp.status == 400


@pytest.mark.asyncio
async def test_get_alerting_jobs_db_error(aiohttp_client):
    with patch("main.db_access.get_jobs", side_effect=Exception("Database error")):
        test_client = await aiohttp_client(setup_app())

        params = {'primary_email': 'test@example.com'}
        resp = await test_client.get("/get_alerting_jobs", params=params)
        assert resp.status == 500


@pytest.mark.asyncio
async def test_del_job_success(aiohttp_client):
    with patch("main.db_access.set_job_inactive", return_value=None):
        test_client = await aiohttp_client(setup_app())

        params = {'job_id': '1'}
        resp = await test_client.delete("/del_job", params=params)
        assert resp.status == 200
        data = await resp.json()
        assert data == {'success': True}


@pytest.mark.asyncio
async def test_del_job_missing_job_id(aiohttp_client):
    test_client = await aiohttp_client(setup_app())

    resp = await test_client.delete("/del_job")
    assert resp.status == 400


@pytest.mark.asyncio
async def test_del_job_db_error(aiohttp_client):
    with patch("main.db_access.set_job_inactive", side_effect=Exception("Database error")):
        test_client = await aiohttp_client(setup_app())

        params = {'job_id': '1'}
        resp = await test_client.delete("/del_job", params=params)
        assert resp.status == 500
