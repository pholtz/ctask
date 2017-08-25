#!/usr/bin/env python
# -*- coding: utf-8 -*-
#---------------------------------------------------------------------#
# Monitors the Windows host using tasklist. Runs under cygwin.
# Filename: ctask.py
# Author: Paul Holtz
# Date: 2017-08-24
#---------------------------------------------------------------------#
import io
import os
import sys
import csv
import time
import argparse
import logging
import subprocess
import operator
import curses

logging.basicConfig(filename="monitor.log", 
					filemode="w", 
					format="%(asctime)s %(levelname)s : %(message)s", 
					level=logging.INFO)

def main(screen):
	parser = argparse.ArgumentParser(description="Monitors host processes", epilog="Paul Holtz, 2017")
	args = parser.parse_args()

	# Clear the screen
	screen.clear()
	screen.nodelay(True)
	window = curses.newwin(int(curses.LINES - 2), int(curses.COLS - 2), 1, 1)
	window.box()

	while True:
		lines, cols = window.getmaxyx()
		if lines < 24 or cols < 80:
			sys.exit("Terminal window cannot be less than 24x80, you were {}x{}".format(lines, cols))

		input_code = screen.getch()
		if input_code == ord("q"):
			break
		# Image Name: The name of the executable
		# PID: Process identifier
		# Session Name: The name of the session
		# Session#: ???
		# Mem Usage: In Kilos
		# Status: The status of the process
		# User Name: Which user the process is running under
		# CPU Time: How many seconds the process has gotten on the cpu since starting
		# Window Title: If the process is running in a window, what's the window name
		tasks = get_tasklist()

		#Sort the tasks by memory usage
		tasks = sorted(tasks, key = operator.itemgetter("Mem Usage"), reverse = True)
		
		#Display the tasks using curses
		#window.addstr(0, 0, "Current Mode: Typing mode", curses.A_REVERSE)
		window.addstr(1, 3, ("PID".ljust(10) + "Image Name".ljust(10)).ljust(cols - 4), curses.A_REVERSE)

		for idx, task in enumerate(tasks):
			if idx >= lines - 3:
				break
			window.addstr(idx + 2, 3, (task["PID"].ljust(10) + task["Image Name"].ljust(10)).ljust(cols - 4))
		screen.refresh()
		window.refresh()
		time.sleep(1)

def get_tasklist():
	"""Invokes the windows tasklist command and returns a CSV-formatted list 
	of currently running tasks. Then, parses the CSV-formatted tasklist into 
	a list of dictionaries.
	"""
	tasklist_process = subprocess.run(["tasklist", "/fo", "CSV", "/v"], encoding = "UTF-8", stdout = subprocess.PIPE)
	tasklist_process.check_returncode()
	tasklist = tasklist_process.stdout.split("\n")
	tasks = [{k: v for k, v in row.items()} for row in csv.DictReader(tasklist, skipinitialspace=True)]
	for task in tasks:
		task["Mem Usage"] = int(task["Mem Usage"].replace(" K", "").replace(",", ""))
	return tasks

def calculate_cpu_percentages(tasks):
	"""Replaces the CPU Time with a CPU % calculated based on the total time of the tasklist."
	Returns a new copy of the list of dictionaries (tasklist).
	"""
		# min: 4.69s  
	# max: 2008.08 s  
	# avg : 207.63 s
	# Then you can find out usage in % from above using definition of %.

	# % utilization = (resource used time / total resource availability time)
	# ex: if cpu was available for 100 seconds and out of that 80 seconds it was used then

	# % utilization = 80/100 = 80% CPU utilization
	# From your given time, total available time is missing. Find that out and use above formula.

	# % utilization = avg. usage/total availability
	# no. of cores shouldn't matter as that is present in both cases.

	# % utilization = ( (no. of cores * avg util)/(no. of core * total availability))  
	# I am not sure about azure cloud monitoring but if it is providing same then you can use it.
	raise NotImplementedError


if __name__ == "__main__":
	curses.wrapper(main)