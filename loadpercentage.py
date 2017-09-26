#!/usr/bin/env python
# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------- #
# Monitors the Windows host using tasklist. Runs under cygwin.
# Filename: tasklist.py
# Author: Paul Holtz
# Date: 2017-09-20
# --------------------------------------------------------------------------- #
import time
import threading
import subprocess


class LoadPercentage(threading.Thread):
    """Monitors the system load percentage through wmic."""

    def __init__(self, queue):
        threading.Thread.__init__(self)
        self._is_running = True
        self.queue = queue
        self.loadpercentage = 0
        self.pstart = time.time()

    def exit(self):
        self._is_running = False

    def run(self):
        """Override default run() method when thread.start() is run."""
        while self._is_running:
            elapsed = time.time() - self.pstart
            if elapsed > 1:
                self.pstart = time.time()
                self.get_loadpercentage()
                self.queue.put(("loadpercentage", self.loadpercentage))
            time.sleep(0.1)

    def get_loadpercentage(self):
        """Display some statistics around overall cpu usage."""
        wmic_process = subprocess.run(
            ["wmic", "cpu", "list", "full", "/format:list"],
            encoding="UTF-8",
            stdout=subprocess.PIPE)
        wmic_process.check_returncode()
        cpu_records = wmic_process.stdout.split("\n")
        for record in cpu_records:
            key, value = record.split("=") if "=" in record else ("", "")
            if "LoadPercentage" in key:
                self.loadpercentage = value
