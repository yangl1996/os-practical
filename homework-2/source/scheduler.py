#!/usr/bin/env python2.7
from __future__ import print_function

import sys
import uuid
import time
import socket
import signal
import getpass
from threading import Thread
from os.path import abspath, join, dirname

from pymesos import MesosSchedulerDriver, Scheduler, encode_data
from addict import Dict

TASK_CPU = 0.1
TASK_MEM = 32
EXECUTOR_CPUS = 0.1
EXECUTOR_MEM = 32
CMD = 'touch /root/done && echo hi >> /root/done'


class MyScheduler(Scheduler):

    def __init__(self, executor):
        self.executor = executor

    def resourceOffers(self, driver, offers):
        filters = {'refuse_seconds': 5}

        for offer in offers:
            offer_cpu = self.getResource(offer.resources, 'cpus')
            offer_mem = self.getResource(offer.resources, 'mem')
            
            if offer_cpu < TASK_CPU or offer_mem < TASK_MEM:
                continue

            task_submit = Dict()
            task_id = str(uuid.uuid4())
            task_submit.task_id.value = task_id
            task_submit.agent_id.value = offer.agent_id.value
            task_submit.name = 'exec {}'.format(task_id)
            task_submit.executor = self.executor
            task_submit.data = encode_data(CMD)
            task_submit.resources = [
                dict(name='cpus', type='SCALAR', scalar={'value': TASK_CPU}),
                dict(name='mem', type='SCALAR', scalar={'value': TASK_MEM}),
            ]

            driver.launchTasks(offer.id, [task_submit], filters)

    def getResource(self, res, name):
        for res_item in res:
            if res_item.name == name:
                return res_item.scalar.value
        return 0.0

    def statusUpdate(self, driver, update):
        logging.debug('Task {}: {}'.format(update.task_id.value, update.state))


def main(master):
    executor = Dict()
    executor.executor_id.value = 'MyExecutor'
    executor.name = executor.executor_id.value
    executor.command.value = '/usr/bin/python /root/mesos/executor.py'
    executor.resources = [
        dict(name='mem', type='SCALAR', scalar={'value': EXECUTOR_MEM}),
        dict(name='cpus', type='SCALAR', scalar={'value': EXECUTOR_CPUS}),
    ]

    framework = Dict()
    framework.name = "MyFramework"
    framework.user = getpass.getuser()
    framework.hostname = socket.gethostname()

    driver = MesosSchedulerDriver(
        MyScheduler(executor),
        framework,
        master,
        use_addict=True,
    )

    def signal_handler(signal, frame):
        driver.stop()

    def launch_the_driver():
        driver.run()

    driver_thread = Thread(target=launch_the_driver, args=())
    driver_thread.start()

    print('Started')
    signal.signal(signal.SIGINT, signal_handler)

    while driver_thread.is_alive():
        time.sleep(1)


if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.DEBUG)
    if len(sys.argv) != 2:
        print("Usage: python scheduler.py <mesos_master>")
        sys.exit(1)
    else:
        main(sys.argv[1])
