#!/usr/bin/env python2.7
from __future__ import print_function

import sys
import os
import time
from threading import Thread

from pymesos import MesosExecutorDriver, Executor, decode_data
from addict import Dict


class MyExecutor(Executor):
    def launchTask(self, driver, task):
        def run_task(task):
            sendback = Dict()
            sendback.state = 'TASK_RUNNING'
            sendback.task_id.value = task.task_id.value
            sendback.timestamp = time.time()
            driver.sendStatusUpdate(sendback)

            os.system(decode_data(task.data))

            sendback = Dict()
            sendback.state = 'TASK_FINISHED'
            sendback.task_id.value = task.task_id.value
            sendback.timestamp = time.time()
            driver.sendStatusUpdate(sendback)

        thread = Thread(target=run_task, args=(task,))
        thread.start()


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.DEBUG)
    driver = MesosExecutorDriver(MyExecutor(), use_addict=True)
    driver.run()
