#!/usr/bin/env python
# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------- #
# Monitors the Windows host using tasklist. Runs under cygwin.
# Filename: ctask.py
# Author: Paul Holtz
# Date: 2017-08-24
# --------------------------------------------------------------------------- #
import sys
import csv
import time
import argparse
import logging
import subprocess
import operator
import curses
import locale
import threading
import queue

locale.setlocale(locale.LC_ALL, "en_US")
logging.basicConfig(filename="wmicli.log",
                    filemode="w",
                    format="%(asctime)s %(levelname)s : %(message)s",
                    level=logging.INFO)


class Tasklist(threading.Thread):

    def __init__(self, queue):
        threading.Thread.__init__(self)
        self.queue = queue
        self.tasklist = []

    def run(self):
        """This method overrides the default run() method and is called when
        thread.start() is run.
        """
        self.generate_tasklist()
        # Comms with the main thread -- send back final information
        self.queue.put(("complete", self.tasklist))

    def generate_tasklist(self):
        if self.queue.empty():
            self.queue.put(("working"))


def main():
    parser = argparse.ArgumentParser(description="Monitors host processes",
                                     epilog="Paul Holtz, 2017")
    parser.add_argument(
        "-m",
        "--memory",
        action="store_true",
        help="Sort by memory usage")
    parser.add_argument(
        "-c",
        "--cpu",
        action="store_true",
        help="Sort by cpu time")
    args = parser.parse_args()
    curses.wrapper(loop, args=args)


def loop(screen, args=None):
    # Clear the screen
    screen.clear()
    screen.nodelay(True)
    window = curses.newwin(int(curses.LINES - 2), int(curses.COLS - 2), 1, 1)
    window.box()

    queue = queue.Queue()
    tasklist = Tasklist(queue)
    tasklist.start()

    while True:
        lines, cols = window.getmaxyx()
        if lines < 24 or cols < 80:
            sys.exit(
                "Terminal window cannot be less than 24x80, you were "
                "{}x{}".format(lines, cols))

        input_code = screen.getch()
        if input_code == ord("q"):
            break

        tasks = get_tasklist()
        tasks = convert_cpu_time_to_percentage(tasks)
        if args.memory:
            tasks = sort_tasklist_by_mem_usage(tasks)

        cpu_usage = get_wmic_cpu()
        window.addstr(1, 2, ("CPU Usage: " + cpu_usage + "%").ljust(80))

        mem_total = get_wmic_mem()
        window.addstr(2, 2, ("Mem Total: " + mem_total + " GB").ljust(80))

        # wmic_process = subprocess.run(
        #     [
        #         "wmic",
        #         "process",
        #         "get",
        #         "Name",
        #         "Priority",
        #         "ProcessId",
        #         "ThreadCount"
        #     ])

        # Display the tasks using curses
        table_buffer = pack_task_table_buffer(tasks, cols)
        for idx, table_entry in enumerate(table_buffer):
            if idx >= lines - 6:
                break
            elif idx == 0:
                window.addstr(idx + 5, 2, table_entry, curses.A_REVERSE)
            else:
                window.addstr(idx + 5, 2, table_entry)

        screen.refresh()
        window.refresh()
        time.sleep(1)


def get_tasklist():
    """Invokes the windows tasklist command and returns a CSV-formatted list
    of currently running tasks. Then, parses the CSV-formatted tasklist into
    a list of dictionaries.
    """
    tasklist_process = subprocess.run(["tasklist", "/fo", "CSV", "/v"],
                                      encoding="UTF-8",
                                      stdout=subprocess.PIPE)
    tasklist_process.check_returncode()
    tasklist = tasklist_process.stdout.split("\n")
    tasks = [
        {k: v for k, v in row.items()}
        for row in csv.DictReader(tasklist, skipinitialspace=True)
    ]
    return tasks


def sort_tasklist_by_mem_usage(tasks):
    """Unpacks the mem usage statistics, sorts from greatest to least, then
    repacks the column.
    """
    for task in tasks:
        task["Mem Usage"] = int(task["Mem Usage"]
                                .replace(" K", "")
                                .replace(",", ""))
    tasks = sorted(tasks,
                   key=operator.itemgetter("Mem Usage"),
                   reverse=True)
    for task in tasks:
        task["Mem Usage"] = str(locale.format("%d",
                                              task["Mem Usage"],
                                              grouping=True)) + " K"
    return tasks


def convert_cpu_time_to_percentage(tasks):
    """Replaces the CPU Time with a CPU % calculated based on the total time
    of the tasklist. Returns a new copy of the list of dictionaries (tasklist).
    """
    cpu_total = 0
    for task in tasks:
        hours, minutes, seconds = task["CPU Time"].split(":")
        task_time = int(hours) * 3600 + int(minutes) * 60 + int(seconds)
        task["CPU Time"] = task_time
        cpu_total += task_time
    # Need to use time since the last update, not total time
    # If you think about it, we can really only calculate CPU usage _over
    # time_, given these metrics
    for task in tasks:
        task["CPU Time"] = round(task["CPU Time"] / cpu_total, 2)
    return tasks


def pack_task_table_buffer(tasks, cols):
    """Given the tasklist dictionary, pack and return a list of fixed-width
    strings that can be flushed to the curses interface.
    # Image Name: The name of the executable
    # PID: Process identifier
    # Session Name: The name of the session
    # Session#: ???
    # Mem Usage: In Kilos
    # Status: The status of the process
    # User Name: Which user the process is running under
    # CPU Time: How many seconds the process has gotten on the cpu
    # Window Title: If the process is running in a window
    """
    table_buffer = []
    table_buffer.append(
        ("PID".ljust(10) +
         "Image Name".ljust(20) +
         "Mem Usage".ljust(15) +
         "CPU Time".ljust(10) +
         "User Name".ljust(25))
        .ljust(cols - 4))
    for idx, task in enumerate(tasks):
        table_buffer.append(
            (task["PID"][0:9].ljust(10) +
             task["Image Name"][0:19].ljust(20) +
             str(task["Mem Usage"])[0:14].ljust(15) +
             str(task["CPU Time"])[0:9].ljust(10) +
             task["User Name"][0:24].ljust(25))
            .ljust(cols - 4))
    return table_buffer


def get_wmic_cpu():
    """Display some statistics around overall cpu usage."""
    wmic_process = subprocess.run(
        ["wmic", "cpu", "list", "full", "/format:list"],
        encoding="UTF-8",
        stdout=subprocess.PIPE)
    wmic_process.check_returncode()
    cpu_records = wmic_process.stdout.split("\n")
    cpu_usage = ""
    for record in cpu_records:
        key, value = record.split("=") if "=" in record else ("", "")
        if "LoadPercentage" in key:
            cpu_usage = value
    return cpu_usage


def get_wmic_mem():
    """Display some statistics around overall memory usage."""
    wmic_process = subprocess.run(
        ["wmic", "memphysical", "list", "full", "/format:list"],
        encoding="UTF-8",
        stdout=subprocess.PIPE)
    wmic_process.check_returncode()
    mem_records = wmic_process.stdout.split("\n")
    mem_total = 0
    for record in mem_records:
        key, value = record.split("=") if "=" in record else ("", "")
        if "MaxCapacity" in key:
            mem_total = str(int(int(value) / 1024**2))
    return mem_total


if __name__ == "__main__":
    main()
