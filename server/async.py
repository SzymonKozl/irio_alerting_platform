import asyncio
import time
from collections import namedtuple
from concurrent.futures import ThreadPoolExecutor, Future
from queue import PriorityQueue
import requests
from typing import Tuple, Optional


job_id_t = int
JobData = namedtuple("JobData", ["job_id", "mail1", "mail2", "url", "period", "window"])


deleted_jobs_cache = set()
deleted_jobs_lock = asyncio.Lock()


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
                pass
            futures.put(tmp)

        await asyncio.sleep(job_data.period / 1000)
