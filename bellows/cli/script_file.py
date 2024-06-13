import asyncio
import time
import bellows.cli.lights as lights
import logging
import bellows.cli.http_server as http_server

from http import server as httpServer
import threading

LOGGER = logging.getLogger(__name__)

async def entry(ctx, commandList, click):
    debug = logging.DEBUG == LOGGER.getEffectiveLevel()
    address = ('', 8124)
    server = httpServer.HTTPServer(address, http_server.ScriptHandler)
    server.commandList = commandList
    backgroundObject = http_server.HTTPServerBackground(server)
    backgroundThread = threading.Thread(target=backgroundObject.background)
    backgroundThread.start()
    scale = 1.0
    if debug:
        scale = 0.001
    lights.read_sunset_file()
    async def check_status():
        try:
            await commandList['b0:c7:de:ff:fe:52:ca:58status']([0], allow_cache=False)
            light1Status = True
        except:
            light1Status = False
        try:
            await commandList['34:10:f4:ff:fe:2f:3f:b6status']([0], allow_cache=False)
            light2Status = True
        except:
            light2Status = False
        return light1Status, light2Status
    light1Status, light2Status = await check_status()
    print(f"light 1 status: {light1Status}")
    print(f"light 2 status: {light2Status}")
    currentTime = lights.getTime()
    print(f"first time read: {currentTime}")
    waitTime = lights.next_sunset(currentTime, True)
    print(f"first sunset delay in seconds: {waitTime}")
    lights.debugTimeDelta = waitTime
    while True:
        await asyncio.sleep(waitTime * scale)
        if not light1Status:
            light1Status, light2Status = await check_status()
        if light1Status:
            try:
                print("turning on")
                v = await commandList['b0:c7:de:ff:fe:52:ca:58on']()  # turn on light
                LOGGER.info(f"{v}")
            except:
                light1Status = False
                print("couldn't turn light on")
        else:
            print("can't turn light on")
        currentTime = lights.getTime()
        print(f"currentTime {currentTime}")
        waitTime = lights.next_sunset(currentTime)
        print(f"wait time until sunset {waitTime}")
        lights.debugTimeDelta = waitTime
        await asyncio.sleep(45 * 60.0 * scale)
        waitTime -= 45 * 60.0 * scale
        if light1Status:
            try:
                print(f"turning off - new waitTime {waitTime}")
                v = await commandList['b0:c7:de:ff:fe:52:ca:58off']()  # turn off light
                LOGGER.info(f"{v}")
            except:
                light1Status = False
                print(f"couldn't turn light off - waiting {waitTime}")
        else:
            print(f"can't turn light off - waiting {waitTime}")
