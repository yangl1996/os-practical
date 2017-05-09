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
TASK_MEM = 128
EXECUTOR_CPUS = 0.1
EXECUTOR_MEM = 128


class MyScheduler(Scheduler):

	def __init__(self):
		self.started = 0

	def resourceOffers(self, driver, offers):
		filters = {'refuse_seconds': 5}

		for offer in offers:
			offer_cpu = self.getResource(offer.resources, 'cpus')
			offer_mem = self.getResource(offer.resources, 'mem')

			if offer_cpu < TASK_CPU or offer_mem < TASK_MEM:
				continue
			
			ip = Dict()
			hostname = Dict()
			NetworkInfo = Dict()
			DockerInfo = Dict()
			ContainerInfo = Dict()
			CommandInfo = Dict()
			
			# first container
			if self.started == 0:
				# ip
				ip.key = 'ip'
				ip.value = '192.168.0.100'
				# hostname
				hostname.key = 'hostname'
				hostname.value = 'calico-demo-jupyter'
				# NetworkInfo
				NetworkInfo.name = 'calico'
				# DockerInfo
				DockerInfo.image = 'jupyter/minimal-notebook'
				DockerInfo.network = 'USER'
				DockerInfo.parameters = [ip, hostname]
				# ContainerInfo
				ContainerInfo.type = 'DOCKER'
				ContainerInfo.docker = DockerInfo
				ContainerInfo.network_infos = [NetworkInfo]
				# CommandInfo
				CommandInfo.shell = False
			# second container
			elif self.started == 1:
				# ip
				ip.key = 'ip'
				ip.value = '192.168.0.101'
				# hostname
				hostname.key = 'hostname'
				hostname.value = 'calico-demo-box1'
				# NetworkInfo
				NetworkInfo.name = 'calico'
				# DockerInfo
				DockerInfo.image = 'sickp/alpine-sshd'
				DockerInfo.network = 'USER'
				DockerInfo.parameters = [ip, hostname]
				# ContainerInfo
				ContainerInfo.type = 'DOCKER'
				ContainerInfo.docker = DockerInfo
				ContainerInfo.network_infos = [NetworkInfo]
				# CommandInfo
				CommandInfo.shell = False
			# third container
			elif self.started == 2:
				# ip
				ip.key = 'ip'
				ip.value = '192.168.0.102'
				# hostname
				hostname.key = 'hostname'
				hostname.value = 'calico-demo-box2'
				# NetworkInfo
				NetworkInfo.name = 'calico'
				# DockerInfo
				DockerInfo.image = 'sickp/alpine-sshd'
				DockerInfo.network = 'USER'
				DockerInfo.parameters = [ip, hostname]
				# ContainerInfo
				ContainerInfo.type = 'DOCKER'
				ContainerInfo.docker = DockerInfo
				ContainerInfo.network_infos = [NetworkInfo]
				# CommandInfo
				CommandInfo.shell = False
			else:
				return

			task = Dict()
			task_id = str(uuid.uuid4())
			task.task_id.value = task_id
			task.agent_id.value = offer.agent_id.value
			task.name = 'calico-demo'
			task.container = ContainerInfo
			task.command = CommandInfo
			task.resources = [
				dict(name='cpus', type='SCALAR', scalar={'value': TASK_CPU}),
				dict(name='mem', type='SCALAR', scalar={'value': TASK_MEM}),
			]
			self.started += 1
			print("Created docker container number ", self.started)
			driver.launchTasks(offer.id, [task], filters)

	def getResource(self, res, name):
		for res_item in res:
			if res_item.name == name:
				return res_item.scalar.value
		return 0.0

	def statusUpdate(self, driver, update):
		logging.debug('Task {}: {}'.format(update.task_id.value, update.state))


def main(master):
	framework = Dict()
	framework.name = "MyFramework"
	framework.user = getpass.getuser()
	framework.hostname = socket.gethostname()

	driver = MesosSchedulerDriver(
		MyScheduler(),
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