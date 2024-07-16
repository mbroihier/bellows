#!/usr/bin/env -S python
import asyncio
import calendar
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

def next_sunset(currentTime):
    currentTimeStructure = time.gmtime(currentTime)
    sunsetASCII = sunset[currentTimeStructure.tm_mday][currentTimeStructure.tm_mon - 1]
    baseStructure = time.gmtime(currentTime + FULL_DAY)
    sunsetStructure = (baseStructure.tm_year,
                       baseStructure.tm_mon,
                       baseStructure.tm_mday,
                       int(sunsetASCII[:2]),
                       int(sunsetASCII[2:]),
                       0,
                       baseStructure.tm_wday,
                       baseStructure.tm_yday,
                       baseStructure.tm_isdst)
    sunsetTime = calendar.timegm(sunsetStructure)
    LOGGER.info(f"current time: {currentTime}, next sunset: {sunsetTime}")
    difference = sunsetTime - currentTime
    if difference < 1000:
        LOGGER.info(f"difference lower than one day: sunset is {sunsetASCII}")
        waitTime = FULL_DAY + difference
    elif difference > FULL_DAY + 1000:
        LOGGER.info(f"difference higher than one day: sunset is {sunsetASCII}")
        waitTime = difference - FULL_DAY
    else:
        waitTime = difference
    LOGGER.info(f"waitTime: {waitTime}")
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
    debugTimeDelta = 11.0
    currentTime = getTime()
    currentTimeStructure = time.gmtime(currentTime)
    lastTmYday = currentTimeStructure.tm_yday
    timeToDelay = next_sunset(currentTime)
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
                LOGGER.info(f"time stamp for update: {time.gmtime(currentTime)}, next sunset: {nextUpdateTime}, delta: {timeToDelay},  day = {dayCount}")
                if currentTimeStructure.tm_yday != lastTmYday + 1:
                    if currentTimeStructure.tm_yday != 1:
                        LOGGER.info(f"tm_yday discontinuity, value is: {currentTimeStructure.tm_yday}")
                lastTmYday = currentTimeStructure.tm_yday
            except Exception as e:
                LOGGER.error(f"Exception detected: {e}, terminating")
                break
    
if __name__ == "__main__":
    asyncio.run(lights())

