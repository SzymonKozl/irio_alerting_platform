import asyncio
import time
from concurrent.futures import ThreadPoolExecutor, Future
from queue import PriorityQueue
import requests
from typing import Tuple, Optional

from common import JobData, job_id_t


deleted_jobs_cache = set()
deleted_jobs_lock = asyncio.Lock()


async def delete_job(job_id: job_id_t) -> bool:
    async with deleted_jobs_lock:
        if job_id in deleted_jobs_cache:
            deleted_jobs_cache.remove(job_id)
            return True
    return False


async def pinging_job(job_data: JobData):

    def single_request():
        resp = requests.get(job_data.url)
        return resp

    executor = ThreadPoolExecutor(max_workers=1)
    futures: PriorityQueue[Tuple[int, Future]] = PriorityQueue()
    while True:
        async with deleted_jobs_lock:
            if job_data.job_id in deleted_jobs_cache:
                deleted_jobs_cache.remove(job_data.job_id)
                return

        future = executor.submit(single_request)
        futures.put((time.time_ns(), future))

        latest = -1
        for (t, ftr) in futures.queue:
            if ftr.done():
                latest = max(latest, t)

        tmp: Optional[Tuple[int, Future]] = None
        while not futures.empty() and (tmp := futures.get())[0] <= latest:
            pass

        if tmp is not None:
            if time.time_ns() - tmp[0] >= job_data.window:
                # todo: email logic and exit
                print(f"no response!!!!!! {job_data.job_id=}")
                return
            futures.put(tmp)

        await asyncio.sleep(job_data.period / 1000)


async def new_job(job_data: JobData):
    asyncio.run(pinging_job(job_data))
