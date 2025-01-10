import asyncio
import time
from queue import PriorityQueue
from aiohttp import ClientSession
from typing import Tuple, Optional

from common import JobData, job_id_t


deleted_jobs_cache = set()
deleted_jobs_lock = asyncio.Lock()


async def delete_job(job_id: job_id_t) -> bool:
    async with deleted_jobs_lock:
        deleted_jobs_cache.add(job_id)
    return False


async def pinging_job(job_data: JobData):

    async def single_request():
        try:
            async with ClientSession() as session:
                async with session.get(job_data.url) as response:
                    return response
        except:
            return None

    futures: PriorityQueue[Tuple[int, asyncio.Task]] = PriorityQueue()
    failed_packets = set()
    while True:
        async with deleted_jobs_lock:
            if job_data.job_id in deleted_jobs_cache:
                deleted_jobs_cache.remove(job_data.job_id)
                return

        task = asyncio.create_task(single_request())
        futures.put((time.time_ns(), task))

        latest = -1
        for (t, ftr) in futures.queue:
            if ftr.done():
                resp = ftr.result()
                if resp is not None and 200 <= resp.status < 300:
                    latest = max(latest, t)
                else:
                    failed_packets.add(t)

        tmp: Optional[Tuple[int, asyncio.Task]] = None

        while True:
            if futures.empty():
                tmp = None
                break
            tmp = futures.get()
            if tmp[0] <= latest or tmp[0] in failed_packets:
                continue
            futures.put(tmp)
            break

        if tmp is not None:
            if (time.time_ns() - tmp[0]) / 1_000_000 >= job_data.window:
                # todo: email logic and exit
                print(f"no response!!!!!! {job_data.job_id=}")
                return

        await asyncio.sleep(job_data.period / 1000)


async def new_job(job_data: JobData):
    await pinging_job(job_data)
