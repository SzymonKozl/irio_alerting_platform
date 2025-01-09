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
    failed_packets = set()
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
                resp = ftr.result()
                if 200 <= resp.status_code < 300:
                    latest = max(latest, t)
                else:
                    failed_packets.add(t)

        tmp: Optional[Tuple[int, Future]] = None

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
            print(tmp[0])
            if (time.time_ns() - tmp[0]) / 1_000_000 >= job_data.window:
                # todo: email logic and exit
                print(f"no response!!!!!! {job_data.job_id=}")
                return

        await asyncio.sleep(job_data.period / 1000)


async def new_job(job_data: JobData):
    await pinging_job(job_data)
