#!/usr/bin/env python
# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------- #
# Monitors the Windows host using tasklist. Runs under cygwin.
# Filename: ctask.py
# Author: Paul Holtz
# Date: 2017-08-24
# --------------------------------------------------------------------------- #
import time
import argparse
import logging
import curses
import locale
import queue
from tasklist import Tasklist
from loadpercentage import LoadPercentage
from physicalmemory import PhysicalMemory

locale.setlocale(locale.LC_ALL, "en_US")
logging.basicConfig(filename="sip.log",
                    filemode="w",
                    format="%(asctime)s %(levelname)s : %(message)s",
                    level=logging.INFO)


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

    q = queue.Queue()
    threads = []
    threads.append(Tasklist(q, args))
    threads.append(LoadPercentage(q))
    threads.append(PhysicalMemory(q))
    for thread in threads:
        thread.start()
    curses.wrapper(loop, args=args, threads=threads, q=q)
    for thread in threads:
        thread.exit()


def loop(screen, args=None, threads=None, q=None):
    # Clear the screen
    screen.clear()
    screen.nodelay(True)
    window = curses.newwin(int(curses.LINES - 2), int(curses.COLS - 2), 1, 1)
    lines, cols = window.getmaxyx()
    curses.curs_set(0)
    window.addstr(0, 0, "System Information & Processes".center(cols))

    while True:
        lines, cols = window.getmaxyx()
        if lines < 24 or cols < 80:
            print(
                "Terminal window cannot be less than 24x80, you were "
                "{}x{}".format(lines, cols))
            break

        input_code = screen.getch()
        if input_code == ord("q"):
            break

        if q.empty():
            time.sleep(0.1)
            continue

        header, payload = q.get(False)
        if header == "tasklist":
            render_tasklist(window, payload)
        elif header == "loadpercentage":
            render_loadpercentage(window, payload)
        elif header == "maxcapacity":
            render_maxcapacity(window, payload)

        screen.refresh()
        window.refresh()


def render_tasklist(window, tasks):
    """Given the tasklist dictionary, pack and return a list of fixed-width
    strings that can be flushed to the curses interface.
    """
    lines, cols = window.getmaxyx()
    table_buffer = []
    table_buffer.append(
        ("PID".ljust(10) +
         "Image Name".ljust(20) +
         "Mem Usage".ljust(15) +
         "CPU Time".ljust(10) +
         "User Name".ljust(25))
        .ljust(cols))
    for idx, task in enumerate(tasks):
        table_buffer.append(
            (task["PID"][0:9].ljust(10) +
             task["Image Name"][0:19].ljust(20) +
             str(task["Mem Usage"])[0:14].ljust(15) +
             str(task["CPU Time"])[0:9].ljust(10) +
             task["User Name"][0:24].ljust(25))
            .ljust(cols - 4))

    for idx, table_entry in enumerate(table_buffer):
        if idx >= lines - 6:
            break
        elif idx == 0:
            window.addstr(
                idx + 5, 0, table_entry, curses.A_REVERSE)
        else:
            window.addstr(idx + 5, 0, table_entry)


def render_loadpercentage(window, loadpercentage):
    load = "[]"
    padding = 2
    lines, cols = window.getmaxyx()
    half_cols = int(cols / 2)
    half_cols_pad = int(half_cols - padding - len(load))
    bar_fill = int(half_cols_pad / 100.0 * float(loadpercentage))
    bar = ("|" * bar_fill).ljust(half_cols_pad)
    load = load.replace("[]", "[{}]".format(bar))
    window.addstr(1, 0, "Processor".center(half_cols_pad))
    window.addstr(2, 0, load)
    window.addstr(3, 0, "{}%".format(
        loadpercentage).center(half_cols_pad))


def render_maxcapacity(window, maxcapacity):
    mem = "[]"
    padding = 2
    lines, cols = window.getmaxyx()
    half_cols = int(cols / 2)
    half_cols_pad = int(half_cols - padding - len(mem))
    bar_fill = int(half_cols_pad / 100.0 * float(50))
    bar = ("|" * bar_fill).ljust(half_cols_pad)
    mem = mem.replace("[]", "[{}]".format(bar))
    window.addstr(1, half_cols + padding, "Memory".center(half_cols_pad))
    window.addstr(2, half_cols + padding, mem)
    window.addstr(3, half_cols + padding,
                  "? / {} GB".format(maxcapacity).center(half_cols_pad))


if __name__ == "__main__":
    main()
