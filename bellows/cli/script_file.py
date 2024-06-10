import asyncio
import time
import bellows.cli.lights as lights
import logging

LOGGER = logging.getLogger(__name__)

async def entry(ctx, commandList, click):
    debug = logging.DEBUG == LOGGER.getEffectiveLevel()
    scale = 1.0
    if debug:
        scale = 0.001
    lights.read_sunset_file()
    currentTime = lights.getTime()
    print(f"first time read: {currentTime}")
    waitTime = lights.next_sunset(currentTime, True)
    print(f"first sunset delay in seconds: {waitTime}")
    lights.debugTimeDelta = waitTime
    while True:
        await asyncio.sleep(waitTime * scale)
        print("turning on")
        v = await commandList['b0:c7:de:ff:fe:52:ca:58on']()  # turn on light
        currentTime = lights.getTime()
        print(f"currentTime {currentTime}")
        waitTime = lights.next_sunset(currentTime)
        print(f"wait time until sunset {waitTime}")
        lights.debugTimeDelta = waitTime
        await asyncio.sleep(45 * 60.0 * scale)
        waitTime -= 45 * 60.0 * scale
        print(f"turning off - new waitTime {waitTime}")
        v = await commandList['b0:c7:de:ff:fe:52:ca:58off']()  # turn off light
