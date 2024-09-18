#!/usr/bin/env -S python
import asyncio
import calendar
import copy
import logging

import click
import click_log

import json
import time
import sys
import websockets

from bellows.cli import opts
from bellows.cli import util

LOGGER = logging.getLogger(__name__)
FULL_DAY = 24 * 3600

class generalTimeUtilities():
    def __init__(self, debug=False, debugDelta=0, clock=0):
        self.debug = debug
        self.debugDelta = debugDelta
        self.clock = clock

    def getTime(self):
        if self.debug:
            self.clock += self.debugDelta
            t = self.clock
        else:
            t = time.time()
        return t

class daily():
    def __init__(self, debug=False):
        self.debug = debug

    def wallTimeToUnixTime(self, hour, minute, currentTime):
        currentTimeStructure = time.gmtime(currentTime)
        wallTimeStructure = (currentTimeStructure.tm_year,
                             currentTimeStructure.tm_mon,
                             currentTimeStructure.tm_mday,
                             hour,
                             minute,
                             0,
                             currentTimeStructure.tm_wday,
                             currentTimeStructure.tm_yday,
                             currentTimeStructure.tm_isdst)
        return calendar.timegm(wallTimeStructure)
                         
    def nextTime(self, currentTime, eventTime):
        currentTimeStructure = time.gmtime(currentTime)
        if currentTimeStructure.tm_hour * 3600 + currentTimeStructure.tm_min * 60 + 30> eventTime:
            baseStructure = time.gmtime(currentTime + FULL_DAY)
        else:
            baseStructure = time.gmtime(currentTime)
        nextTimeStructure = (baseStructure.tm_year,
                             baseStructure.tm_mon,
                             baseStructure.tm_mday,
                             int(eventTime/3600),
                             int((eventTime - int(eventTime/3600)*3600)/60),
                             0,
                             baseStructure.tm_wday,
                             baseStructure.tm_yday,
                             baseStructure.tm_isdst)
        nextTime = calendar.timegm(nextTimeStructure)
        LOGGER.debug(f"current time: {currentTime}, next time: {nextTime}")
        difference = nextTime - currentTime
        if difference < 0:
            LOGGER.debug(f"difference is negative {difference}, implies time has already passed - go to next day")
            waitTime = FULL_DAY + difference
        elif difference > FULL_DAY:
            LOGGER.error(f"difference higher than one day {difference}, shouldn't happen")
            waitTime = difference - FULL_DAY
        else:
            waitTime = difference
        return waitTime

class sunriseSunset():
    def __init__(self, debug=False):
        self.debug = debug
        self.sunset = {}
        self.sunrise = {}
        self.readSunriseSunsetFiles()

    
    def readSunriseSunsetFiles(self):
        with open("sunset.txt", "r", encoding="utf-8-sig") as sunset_file:
            for line in sunset_file.readlines():
                numbers = line.split()
                if int(numbers[0]) in self.sunset:
                    if int(numbers[1]) in self.sunset[int(numbers[0])]:
                        self.sunset[int(numbers[0])][int(numbers[1])].append(int(numbers[2][:2]) * 3600 +
                                                                             int(numbers[2][2:]) * 60)
                    else:
                        self.sunset[int(numbers[0])][int(numbers[1])] = [int(numbers[2][:2]) * 3600 +
                                                                         int(numbers[2][2:]) * 60]
                else: 
                    self.sunset[int(numbers[0])] = {int(numbers[1]) :
                                                    [int(numbers[2][:2]) * 3600 + int(numbers[2][2:]) * 60]}
        with open("sunrise.txt", "r", encoding="utf-8-sig") as sunrise_file:
            for line in sunrise_file.readlines():
                numbers = line.split()
                if int(numbers[0]) in self.sunrise:
                    if int(numbers[1]) in self.sunrise[int(numbers[0])]:
                        self.sunrise[int(numbers[0])][int(numbers[1])].append(int(numbers[2][:2]) * 3600 +
                                                                              int(numbers[2][2:]) * 60)
                    else:
                        self.sunrise[int(numbers[0])][int(numbers[1])] = [int(numbers[2][:2]) * 3600 +
                                                                          int(numbers[2][2:]) * 60]
                else: 
                    self.sunrise[int(numbers[0])] = {int(numbers[1]) :
                                                     [int(numbers[2][:2]) * 3600 + int(numbers[2][2:]) * 60]}
        if self.debug:
            for month in self.sunset:
                for day in self.sunset[month]:
                    LOGGER.debug(f"{month:2} {day:2} {self.sunset[month][day]}")
            for month in self.sunrise:
                for day in self.sunrise[month]:
                    LOGGER.debug(f"{month:2} {day:2} {self.sunrise[month][day]}")
        return

    def wallTimeToUnixTime(self, mon, day, hour, minute, currentTime, yearOffset=0):
        currentTimeStructure = time.gmtime(currentTime)
        wallTimeStructure = (currentTimeStructure.tm_year+yearOffset,
                             mon,
                             day,
                             hour,
                             minute,
                             0,
                             currentTimeStructure.tm_wday,
                             currentTimeStructure.tm_yday,
                             currentTimeStructure.tm_isdst)
        return calendar.timegm(wallTimeStructure)

    def nextSunsetSunriseEvent(self, currentTime, offsetTime, table):
        currentTimeStructure = time.gmtime(currentTime)
        tableKeys = sorted(list(table.keys()))
        for month in tableKeys:
            if month < currentTimeStructure.tm_mon:
                next
            dayKeys = sorted(list(table[month]))
            for day in dayKeys:
                if day < currentTimeStructure.tm_mday:                
                    next
                if month == 2 and day == 29:
                    leapHandleStructure = (currentTimeStructure.tm_year,
                                           month,
                                           day,
                                           0,
                                           0,
                                           currentTimeStructure.tm_wday,
                                           currentTimeStructure.tm_yday,
                                           currentTimeStructure.tm_isdst)
                    leapHandleStructure = time.gmtime(calendar.timegm(leapHandleStructure))
                    if leapHandleStructure.tm_mon == 3:
                        next  # not a leap year, go to next table entry
                else:
                    timeList = table[month][day]
                for value in timeList:
                    h = int(value/3600)
                    m = int((value - h*3600)/60)
                    candidateTime = self.wallTimeToUnixTime(month, day, h, m, currentTime) + offsetTime
                    if currentTime < candidateTime:
                        LOGGER.debug(f"month: {month}, day: {day}, value: {value},"
                                     f" hour: {h}, minute: {m}")
                        return candidateTime
        LOGGER.debug("crossing a year boundary, look at next year")
        for month in tableKeys:
            if month < currentTimeStructure.tm_mon:
                next
            dayKeys = sorted(list(table[month]))
            for day in dayKeys:
                if day < currentTimeStructure.tm_mday:
                    next
                if month == 2 and day == 29:
                    leapHandleStructure = (currentTimeStructure.tm_year,
                                           month,
                                           day,
                                           0,
                                           0,
                                           currentTimeStructure.tm_wday,
                                           currentTimeStructure.tm_yday,
                                           currentTimeStructure.tm_isdst)
                    leapHandleStructure = time.gmtime(calendar.timegm(leapHandleStructure))
                    if leapHandleStructure.tm_mon == 3:
                        next
                else:
                    timeList = table[month][day]
                for value in timeList:
                    h = int(value/3600)
                    m = int((value - h*3600)/60)
                    candidateTime = self.wallTimeToUnixTime(month, day, h, m, currentTime, 1) + offsetTime
                    if currentTime < candidateTime:
                        LOGGER.debug(f"month: {month}, day: {day}, value: {value},"
                                     f" hour: {h}, minute: {m}")
                        return candidateTime
        LOGGER.error("could not find a time")
        return -1
    def nextSunsetEvent(self, currentTime, offsetTime):
        return self.nextSunsetSunriseEvent(currentTime, offsetTime, self.sunset)
    def nextSunriseEvent(self, currentTime, offsetTime):
        return self.nextSunsetSunriseEvent(currentTime, offsetTime, self.sunrise)

@click.command()
@click.argument("month")
@click.argument("day")
@click.argument("hour")
@click.argument("minute")
@click.argument("offsettime")
@click_log.simple_verbosity_option(logging.getLogger(), default="INFO")
@util.background
async def lengthofday(month, day, hour, minute, offsettime):
    ''' all sunsets for a year '''
    global debug
    debugTimeDelta = 10.0
    debug = logging.DEBUG == LOGGER.getEffectiveLevel()

    logging.basicConfig(format='%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)4d] %(message)s',
                        datefmt=' %Y-%m-%d:%H:%M:%S', level=LOGGER.getEffectiveLevel())
    srss = sunriseSunset(debug)
    currentTimeStructure = time.gmtime(time.time())
    wallTimeStructure = (currentTimeStructure.tm_year,
                         int(month),
                         int(day),
                         int(hour),
                         int(minute),
                         0)
    currentTime =  calendar.timegm(wallTimeStructure)
    offset = 86400
    lastSunsetASCII = '0000'
    lastTime = currentTime
    for i in range(366):
        sunriseTime = srss.nextSunriseEvent(currentTime, int(offsettime))
        sunsetTime = srss.nextSunsetEvent(currentTime, int(offsettime))
        LOGGER.info(f"Event {i:3} calculated at {time.strftime('%d %b %Y %H:%M:%S',time.gmtime(currentTime))} "
                    f"is {time.strftime('%d %b %Y %H:%M:%S',time.gmtime(sunriseTime))}, "
                    f"is {time.strftime('%d %b %Y %H:%M:%S',time.gmtime(sunsetTime))}, "
                    f" delta is {sunsetTime - sunriseTime}")
        currentTime = sunsetTime
    
if __name__ == "__main__":
    asyncio.run(lengthofday())

