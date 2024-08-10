#!/usr/bin/env -S python
import asyncio
import calendar
import logging

import click
import click_log

import time
import sys
import websockets

from bellows.cli import opts
from bellows.cli import util

LOGGER = logging.getLogger(__name__)

FULL_DAY = 24 * 3600
sunset = {}
sunrise = {}

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

def read_sunriseSunset_file():
    with open("sunset.txt", "r", encoding="utf-8") as sunriseset_file:
        for line in sunriseset_file.readlines():
            numbers = line.split()
            monthsD = []
            monthsU = []
            for month in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]:
                monthsD.append(numbers[month * 2])
                monthsU.append(numbers[month * 2 - 1])
            sunset[int(numbers[0])] = monthsD
            sunrise[int(numbers[0])] = monthsU
    for day in [ 1,  2,  3,  4,  5,  6,  7,  8,  9, 10, 11, 12,
                 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24,
                 25, 26, 27, 28, 29, 30, 31 ]:
        LOGGER.debug(f"{day:2}: {sunset[day]}")
    for day in [ 1,  2,  3,  4,  5,  6,  7,  8,  9, 10, 11, 12,
                 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24,
                 25, 26, 27, 28, 29, 30, 31 ]:
        LOGGER.debug(f"{day:2}: {sunrise[day]}")
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
    LOGGER.debug(f"current time: {currentTime}, next sunset: {sunsetTime}")
    difference = sunsetTime - currentTime
    if difference < 1000:
        LOGGER.debug(f"difference lower than one day: sunset is {sunsetASCII}")
        waitTime = FULL_DAY + difference
    elif difference > FULL_DAY + 1000:
        LOGGER.debug(f"difference higher than one day: sunset is {sunsetASCII}")
        waitTime = difference - FULL_DAY
    else:
        waitTime = difference
    LOGGER.debug(f"waitTime: {waitTime}")
    return waitTime

def next_sunrise(currentTime):
    currentTimeStructure = time.gmtime(currentTime)
    sunriseASCII = sunrise[currentTimeStructure.tm_mday][currentTimeStructure.tm_mon - 1]
    baseStructure = time.gmtime(currentTime + FULL_DAY)
    sunriseStructure = (baseStructure.tm_year,
                        baseStructure.tm_mon,
                        baseStructure.tm_mday,
                        int(sunriseASCII[:2]),
                        int(sunriseASCII[2:]),
                        0,
                        baseStructure.tm_wday,
                        baseStructure.tm_yday,
                        baseStructure.tm_isdst)
    sunriseTime = calendar.timegm(sunriseStructure)
    LOGGER.debug(f"current time: {currentTime}, next sunrise: {sunriseTime}")
    difference = sunriseTime - currentTime
    if difference < 1000:
        LOGGER.debug(f"difference lower than one day: sunrise is {sunriseASCII}")
        waitTime = FULL_DAY + difference
    elif difference > FULL_DAY + 1000:
        LOGGER.debug(f"difference higher than one day: sunrise is {sunriseASCII}")
        waitTime = difference - FULL_DAY
    else:
        waitTime = difference
    LOGGER.debug(f"waitTime: {waitTime}")
    return waitTime

def next_time(currentTime, eventTime):
    currentTimeStructure = time.gmtime(currentTime)
    baseStructure = time.gmtime(currentTime + FULL_DAY)
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
    if difference < 1000:
        LOGGER.debug(f"difference lower than one day")
        waitTime = FULL_DAY + difference
    elif difference > FULL_DAY + 1000:
        LOGGER.debug(f"difference higher than one day")
        waitTime = difference - FULL_DAY
    else:
        waitTime = difference
    LOGGER.debug(f"waitTime: {waitTime}")
    return waitTime

@click.command()
@click_log.simple_verbosity_option(logging.getLogger(), default="INFO")
@util.background
async def timeServer():
    ''' Time Server '''
    global debug
    global debugTimeDelta
    logging.basicConfig(format='%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)4d] %(message)s',
                        datefmt=' %Y-%m-%d:%H:%M:%S', level=LOGGER.getEffectiveLevel())
    read_sunriseSunset_file()
    # buildTools creates this initially - edit times to the desired values 
    devices = ["b0:c7:de:ff:fe:52:ca:58", "34:10:f4:ff:fe:2f:3f:b6"]
    timeOn = {"b0:c7:de:ff:fe:52:ca:58": [ 11 * 60 * 60 + 0 * 60,
                                           12 * 60 * 60 + 0 * 60 ],
              "34:10:f4:ff:fe:2f:3f:b6": [ 11 * 60 * 60 + 0 * 60 ]}
    timeOff = {"b0:c7:de:ff:fe:52:ca:58": [ 11 * 60 * 60 + 30 * 60,
                                            12 * 60 * 60 + 30 * 60 ],
               "34:10:f4:ff:fe:2f:3f:b6": [ 11 * 60 * 60 + 30 * 60 ]}
    sunriseOnOffset = {"b0:c7:de:ff:fe:52:ca:58": [ 0 * 60 * 60 + 0 * 60 ],
                       "34:10:f4:ff:fe:2f:3f:b6": [ 0 * 60 * 60 + 0 * 60 ]}
    sunriseOffOffset = {"b0:c7:de:ff:fe:52:ca:58": [ 0 * 60 * 60 + 0 * 60 ],
                        "34:10:f4:ff:fe:2f:3f:b6": [ 0 * 60 * 60 + 0 * 60 ]}
    sunsetOnOffset = {"b0:c7:de:ff:fe:52:ca:58": [ 0 * 60 * 60 + 0 * 60 ],
                      "34:10:f4:ff:fe:2f:3f:b6": [ 0 * 60 * 60 + 0 * 60 ]}
    sunsetOffOffset = {"b0:c7:de:ff:fe:52:ca:58": [ 0 * 60 * 60 + 0 * 60 ],
                       "34:10:f4:ff:fe:2f:3f:b6": [ 0 * 60 * 60 + 0 * 60 ]}
    
    timeOn = {"b0:c7:de:ff:fe:52:ca:58": [],
              "34:10:f4:ff:fe:2f:3f:b6": []}
    timeOff = {"b0:c7:de:ff:fe:52:ca:58": [],
               "34:10:f4:ff:fe:2f:3f:b6": []}
    sunriseOnOffset = {"b0:c7:de:ff:fe:52:ca:58": [],
                       "34:10:f4:ff:fe:2f:3f:b6": []}
    sunriseOffOffset = {"b0:c7:de:ff:fe:52:ca:58": [],
                        "34:10:f4:ff:fe:2f:3f:b6": []}
    sunsetOnOffset = {"b0:c7:de:ff:fe:52:ca:58": [ 0 * 60 * 60 + 0 * 60 ],
                      "34:10:f4:ff:fe:2f:3f:b6": [ 0 * 60 * 60 + 0 * 60 ]}
    sunsetOffOffset = {"b0:c7:de:ff:fe:52:ca:58": [ 0 * 60 * 60 + 45 * 60 ],
                       "34:10:f4:ff:fe:2f:3f:b6": [ ]}
   
    deviceTL = {"b0:c7:de:ff:fe:52:ca:58": {"timeOn": timeOn, "timeOff": timeOff, "sunriseOn": sunriseOnOffset,
                                            "sunriseOff": sunriseOffOffset, "sunsetOn": sunsetOnOffset,
                                            "sunsetOff": sunsetOffOffset},
                     "34:10:f4:ff:fe:2f:3f:b6": {"timeOn": timeOn, "timeOff": timeOff, "sunriseOn": sunriseOnOffset,
                                            "sunriseOff": sunriseOffOffset, "sunsetOn": sunsetOnOffset,
                                            "sunsetOff": sunsetOffOffset}}
    deviceTLIndex = {"b0:c7:de:ff:fe:52:ca:58": {"timeOn": 0, "timeOff": 0, "sunriseOn": 0, "sunriseOff": 0,
                                                 "sunsetOn": 0, "sunsetOff": 0},
                     "34:10:f4:ff:fe:2f:3f:b6": {"timeOn": 0, "timeOff": 0, "sunriseOn": 0, "sunriseOff": 0,
                                                 "sunsetOn": 0, "sunsetOff": 0}}
    deviceUpdateTimes = {"b0:c7:de:ff:fe:52:ca:58": {"timeOn": 0, "timeOff": 0, "sunriseOn": 0, "sunriseOff": 0,
                                                     "sunsetOn": 0, "sunsetOff": 0},
                         "34:10:f4:ff:fe:2f:3f:b6": {"timeOn": 0, "timeOff": 0, "sunriseOn": 0, "sunriseOff": 0,
                                                     "sunsetOn": 0, "sunsetOff": 0}}
    # end of the information inserted by buildTools
    debug = logging.DEBUG == LOGGER.getEffectiveLevel()
    debugTimeDelta = 10.0
    # based on current time, update deviceUpdateTimes, and time line index
    currentTime = getTime()
    currentTimeStructure = time.gmtime(currentTime)
    lastTmYdaySS = currentTimeStructure.tm_yday
    lastTmYdaySR = lastTmYdaySS
    timeOfDay = currentTimeStructure.tm_hour * 3600 + currentTimeStructure.tm_min * 60 + currentTimeStructure.tm_sec
    nextUpdateTimeSS = currentTime + next_sunset(currentTime)
    nextUpdateTimeSR = currentTime + next_sunrise(currentTime)
    index = 0
    for device in devices:
        for eventType in deviceTLIndex[device]:
            timeArray = deviceTL[device][eventType][device]
            found = False
            for t in timeArray:
                if t > timeOfDay:
                    found = True
                    deviceTLIndex[device][eventType] = index
                    break
                index += 1
            if not found:
                deviceTLIndex[device][eventType] = 0
            index = 0
    for device in deviceTLIndex:
        LOGGER.info(f"Time line device: {device}")
        for k, v in deviceTLIndex[device].items():
            LOGGER.info(f"Time line index - {k}: {v}")
    for device in deviceTLIndex:
        for k, v in deviceTLIndex[device].items():
            if (k == "timeOn") and (len(timeOn[device]) > 0):
                deviceUpdateTimes[device][k] = next_time(currentTime, timeOn[device][v]) + currentTime
                deviceTLIndex[device][k] = (v + 1) % len(timeOn[device])
            if (k == "timeOff") and (len(timeOff[device]) > 0):
                deviceUpdateTimes[device][k] = next_time(currentTime, timeOff[device][v]) + currentTime
                deviceTLIndex[device][k] = (v + 1) % len(timeOff[device])
            if (k == "sunriseOn") and (len(sunriseOnOffset[device]) > 0):
                deviceUpdateTimes[device][k] = next_sunrise(currentTime) + sunriseOnOffset[device][v] + currentTime
                deviceTLIndex[device][k] = (v + 1) % len(sunriseOnOffset[device])
            if (k == "sunriseOff") and (len(sunriseOffOffset[device]) > 0):
                deviceUpdateTimes[device][k] = next_sunrise(currentTime) + sunriseOffOffset[device][v] + currentTime
                deviceTLIndex[device][k] = (v + 1) % len(sunriseOffOffset[device])
            if (k == "sunsetOn") and (len(sunsetOnOffset[device]) > 0):
                deviceUpdateTimes[device][k] = next_sunset(currentTime) + sunsetOnOffset[device][v] + currentTime
                deviceTLIndex[device][k] = (v + 1) % len(sunsetOnOffset[device])
            if (k == "sunsetOff") and (len(sunsetOffOffset[device]) > 0):
                deviceUpdateTimes[device][k] = next_sunset(currentTime) + sunsetOffOffset[device][v] + currentTime
                deviceTLIndex[device][k] = (v + 1) % len(sunsetOffOffset[device])
    for device in deviceUpdateTimes:
        LOGGER.info(f"Time of first update - device: {device}")
        for k, v in deviceUpdateTimes[device].items():
            if v != 0:
                LOGGER.info(f"Time of first update - {k}: {time.strftime('%d %b %Y %H:%M:%S',time.gmtime(v))}")

    while True:
        if not debug:
            await asyncio.sleep(1.0)
        currentTime = getTime()
        for device in deviceUpdateTimes:
            for k, v in deviceUpdateTimes[device].items():
                if (currentTime >= v) and (v > 0):
                    if "On" in k:
                        command = "on"
                    else:
                        command = "off"
                    if not debug:
                        try:
                            async with websockets.connect("ws://localhost:8126") as socket:
                                await socket.send("time server connection request")
                                message = await socket.recv()
                                LOGGER.info(f"received initial/connection status of: {message}")
                                LOGGER.info(f"device: {device}, command: {command}")
                                await socket.send(device+command)
                                message = await socket.recv()
                                LOGGER.info(f"received final status of: {message}")
                        except Exception as e:
                            LOGGER.error(f"Exception detected {e}, terminating")
                            sys.exit(-1)
                    index = deviceTLIndex[device][k]
                    if k == "timeOn":
                        deviceUpdateTimes[device][k] = next_time(currentTime, timeOn[device][index]) + currentTime
                        deviceTLIndex[device][k] = (index + 1) % len(timeOn[device])
                    if k == "timeOff":
                        deviceUpdateTimes[device][k] = next_time(currentTime, timeOff[device][index]) + currentTime
                        deviceTLIndex[device][k] = (index + 1) % len(timeOff[device])
                    if k == "sunriseOn":
                        deviceUpdateTimes[device][k] = (next_sunrise(currentTime) + sunriseOnOffset[device][index]
                                                        + currentTime)
                        deviceTLIndex[device][k] = (index + 1) % len(sunriseOnOffset[device])
                    if k == "sunriseOff":
                        deviceUpdateTimes[device][k] = (next_sunrise(currentTime) + sunriseOffOffset[device][index]
                                                        + currentTime)
                        deviceTLIndex[device][k] = (index + 1) % len(sunriseOffOffset[device])
                    if k == "sunsetOn":
                        deviceUpdateTimes[device][k] = (next_sunset(currentTime)
                                                        + sunsetOnOffset[device][index] + currentTime)
                        deviceTLIndex[device][k] = (index + 1) % len(sunsetOnOffset[device])
                    if k == "sunsetOff":
                        deviceUpdateTimes[device][k] = (next_sunset(currentTime) + sunsetOffOffset[device][index]
                                                        + currentTime)
                        deviceTLIndex[device][k] = (index + 1) % len(sunsetOffOffset[device])
                    showerror = ""
                    if ((abs(deviceUpdateTimes[device][k] - v - FULL_DAY) > 120)
                        and (deviceTLIndex[device][k] == index)):
                        showerror = "Out of Tolerance"
                    LOGGER.debug(f"{k} - {device}"
                                 f" {time.strftime('%d %b %Y %H:%M:%S',time.gmtime(currentTime))}{showerror}")
    
if __name__ == "__main__":
    asyncio.run(timeServer())

