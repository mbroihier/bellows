#!/usr/bin/env -S python
import asyncio

import logging

import click
import click_log

import time

from bellows.cli import opts
from bellows.cli import util

LOGGER = logging.getLogger(__name__)

FULL_DAY = 24 * 3600
DELTA_UPPER_LIMIT = 300
DELTA_LOWER_LIMIT = -300
sunset = {}

clock = time.time()
debug = logging.DEBUG == LOGGER.getEffectiveLevel()
debugTimeDelta = 0.0

def getTime():
    global debug
    global clock
    global debugTimeDelta
    if debug:
        LOGGER.info(f"using simulated time with delta of {debugTimeDelta}")
        clock += debugTimeDelta
        t = clock
    else:
        t = time.time()
    return t

def read_sunset_file():
    with open("sunset.txt", "r", encoding="utf-8") as sunriseset_file:
        for line in sunriseset_file.readlines():
            numbers = line.split()
            months = []
            for month in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]:
                months.append(numbers[month * 2])
            sunset[int(numbers[0])] = months
            LOGGER.debug(f"{numbers[0]}: {sunset[int(numbers[0])]}");
    return

def next_sunset(currentTime, firstTime=False):
    currentTimeStructure = time.gmtime(currentTime)
    currentTimeSecondOfTheDay = currentTimeStructure.tm_hour * 3600 + currentTimeStructure.tm_min * 60
    todaysSunset = sunset[currentTimeStructure.tm_mday][currentTimeStructure.tm_mon - 1]
    todaysSunsetSecondOfTheDay = int(todaysSunset[:2]) * 3600 + int(todaysSunset[2:]) * 60
    LOGGER.info(f"current second of the day: {currentTimeSecondOfTheDay}, today's sunset "
                f"second of the day: {todaysSunsetSecondOfTheDay}")
    difference = todaysSunsetSecondOfTheDay - currentTimeSecondOfTheDay
    if firstTime:
        if difference < 0:
            waitTime = FULL_DAY + difference
    else:
        if difference > DELTA_UPPER_LIMIT or difference < DELTA_LOWER_LIMIT:
            was = difference
            difference = difference + FULL_DAY
            LOGGER.info(f"needed to compensate, new difference: {difference}, was: {was}")
            if difference > DELTA_UPPER_LIMIT or difference < DELTA_LOWER_LIMIT:
                if difference > 0:
                    difference -= 2 * FULL_DAY
                    LOGGER.info(f"reworking, new difference: {difference}")
                else:
                    LOGGER.error(f"logic error in time delta compensation")
        waitTime = FULL_DAY + difference
    LOGGER.info(f"difference between the two: {difference}, wait time: {waitTime}")
    return waitTime

@click.command()
@click_log.simple_verbosity_option(logging.getLogger(), default="WARNING")
@opts.device
@opts.baudrate
@opts.flow_control
@click.pass_context
@util.background
async def lights(ctx, device, baudrate, flow_control):
    ''' Lights control task '''
    global debug
    global debugTimeDelta
    click_log.basic_config()
    read_sunset_file()
    debug = logging.DEBUG == LOGGER.getEffectiveLevel()
    debugTimeDelta = 10.0
    currentTime = getTime()
    currentTimeStructure = time.gmtime(currentTime)
    lastTmYday = currentTimeStructure.tm_yday
    timeToDelay = next_sunset(currentTime, True)
    nextUpdateTime = currentTime + timeToDelay
    await asyncio.sleep(1.0)
    dayCount = 0;
    while True:
        currentTime = getTime()
        if currentTime >= nextUpdateTime:
            try:
                currentTimeStructure = time.gmtime(currentTime)
                timeToDelay = next_sunset(currentTime)
                nextUpdateTime = currentTime + timeToDelay
                dayCount += 1
                LOGGER.info(f"time stamp for update: {time.gmtime(currentTime)}, day = {dayCount}")
                if currentTimeStructure.tm_yday != lastTmYday + 1:
                    if currentTimeStructure.tm_yday != 1:
                        LOGGER.info(f"tm_yday discontinuity, value is: {currentTimeStructure.tm_yday}")
                lastTmYday = currentTimeStructure.tm_yday
            except Exception as e:
                LOGGER.error(f"Exception detected: {e}, terminating")
                break
    
if __name__ == "__main__":
    asyncio.run(lights())

