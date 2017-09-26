#!/usr/bin/env python
# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------- #
# Monitors the Windows host using tasklist. Runs under cygwin.
# Filename: tasklist.py
# Author: Paul Holtz
# Date: 2017-09-19
# --------------------------------------------------------------------------- #
import csv
import time
import threading
import subprocess
import operator
import locale


class Tasklist(threading.Thread):
    """Monitors the active Windows processes through the tasklist command."""

    def __init__(self, queue, args):
        threading.Thread.__init__(self)
        self._is_running = True
        self.queue = queue
        self.args = args
        self.tasklist = []
        self.pstart = time.time()

    def exit(self):
        self._is_running = False

    def run(self):
        """Override default run() method when thread.start() is run."""
        while self._is_running:
            elapsed = time.time() - self.pstart
            if elapsed > 5:
                self.pstart = time.time()
                self.generate_tasklist()
            time.sleep(0.1)

    def generate_tasklist(self):
        self.invoke_tasklist()
        self.convert_cpu_time_to_percentage()
        if self.args.memory:
            self.sort_tasklist_by_mem_usage()
        self.queue.put(("tasklist", self.tasklist))

    def invoke_tasklist(self):
        """Invokes the windows tasklist command and returns a CSV-formatted
        list of currently running tasks. Then, parses the formatted tasklist
        into a list of dictionaries.
        """
        tasklist_process = subprocess.run(["tasklist", "/fo", "CSV", "/v"],
                                          encoding="UTF-8",
                                          stdout=subprocess.PIPE)
        tasklist_process.check_returncode()
        tasklist = tasklist_process.stdout.split("\n")
        self.tasklist = [
            {k: v for k, v in row.items()}
            for row in csv.DictReader(tasklist, skipinitialspace=True)
        ]

    def sort_tasklist_by_mem_usage(self):
        """Unpacks the mem usage statistics, sorts from greatest to least, then
        repacks the column.
        """
        for task in self.tasklist:
            task["Mem Usage"] = int(task["Mem Usage"]
                                    .replace(" K", "")
                                    .replace(",", ""))
        self.tasklist = sorted(self.tasklist,
                               key=operator.itemgetter("Mem Usage"),
                               reverse=True)
        for task in self.tasklist:
            task["Mem Usage"] = str(locale.format("%d",
                                                  task["Mem Usage"],
                                                  grouping=True)) + " K"

    def convert_cpu_time_to_percentage(self):
        """Replaces the CPU Time with a CPU % calculated based on the total time
        of the tasklist. Returns a new copy of the list of dictionaries.
        """
        cpu_total = 0
        for task in self.tasklist:
            hours, minutes, seconds = task["CPU Time"].split(":")
            task_time = int(hours) * 3600 + int(minutes) * 60 + int(seconds)
            task["CPU Time"] = task_time
            cpu_total += task_time
        # Need to use time since the last update, not total time
        # If you think about it, we can really only calculate CPU usage _over
        # time_, given these metrics
        for task in self.tasklist:
            task["CPU Time"] = round(task["CPU Time"] / cpu_total, 2)
