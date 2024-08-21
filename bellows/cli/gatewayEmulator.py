#!/bin/env python
import asyncio
import copy
import json
import logging
import signal

import click
import click_log
from websockets.server import serve as wsserve
from bellows.cli import opts
from bellows.cli import util

LOGGER = logging.getLogger(__name__)
lastStatus = {}
doCommand = []
gCommandList = {}
continueLoop = True
connectionNumber = 0
def getDevice(command):
    result = command.replace('on', '')
    result = result.replace('off', '')
    result = result.replace('status', '')
    return result

def sigint_handler(signal, frame):
    global continueLoop
    print("/nshutting down server....")
    continueLoop = False

async def entry(commandList):
    loop = asyncio.get_running_loop()
    global lastStatus
    global gCommandList
    global continueLoop
    gCommandList = commandList
    for command in commandList:
            lastStatus[getDevice(command)] = 'off'

    LOGGER.debug("Creating pseudo gateway")
    wsserver = await wsserve(websocketHandler, "", 8126)
    async with wsserver:
        signal.signal(signal.SIGINT, sigint_handler)
        LOGGER.debug("Starting pseudo gateway")
        await wsserver.start_serving()
        while continueLoop:
            await asyncio.sleep(0.1)
            if doCommand:
                LOGGER.info(f"gateway doing command: {doCommand[0]}")
                if 'on' in doCommand[0]:
                    lastStatus[getDevice(doCommand[0])] = 'on'
                elif 'off' in doCommand[0]:
                    lastStatus[getDevice(doCommand[0])] = 'off'
                elif 'status' in doCommand[0]:
                    pass
                LOGGER.debug(f"gateway status: {lastStatus}")
                del doCommand[0]

async def websocketHandler(websocket):
    global connectionNumber
    global LOGGER
    LOGGER.debug("websocket server connection is starting")
    consumer_task = asyncio.create_task(consumer_handler(websocket, connectionNumber))
    producer_task = asyncio.create_task(producer_handler(websocket, connectionNumber))
    connectionNumber += 1
    done, pending = await asyncio.wait([consumer_task, producer_task],
                                     return_when=asyncio.FIRST_COMPLETED, )
    LOGGER.debug("websocket server connection is terminating")
    for task in pending:
        task.cancel()

async def consumer_handler(websocket, connectionNumber):
    global gCommandList
    global doCommand
    global LOGGER
    LOGGER.info(f"gateway sending ({connectionNumber}): {json.dumps(lastStatus)}")
    await websocket.send(json.dumps(lastStatus))  # this message is sent on connection
    try:
        async for message in websocket:
            LOGGER.info(f"gateway connection received ({connectionNumber}): {message}")  # connection message
            print(f"gateway connection received ({connectionNumber}): {message}")  # connection message
            while True:
                try:
                    message = await websocket.recv()
                    LOGGER.info(f"gateway received({connectionNumber}): {message}")
                    if message in gCommandList:
                        doCommand.append(message)
                    else:
                        LOGGER.warning(f"bad command read from websocket, closing client connection({connectionNumber})")
                        await websocket.close()
                        break
                except:
                    LOGGER.warning(f"can not read websocket, closing client connection ({connectionNumber})")
                    await websocket.close()
                    break
    except Exception as e:
        LOGGER.warning(f"{e} while waiting for a message from websocket, connection closed({connectionNumber})")

async def producer_handler(websocket, connectionNumber):
    global lastStatus
    lastSentStatus = copy.deepcopy(lastStatus)
    while True:
        await asyncio.sleep(0.3)
        if lastStatus != lastSentStatus:
            LOGGER.info(f"gateway sending({connectionNumber}): {json.dumps(lastStatus)}")
            try:
                await websocket.send(json.dumps(lastStatus))
                lastSentStatus = copy.deepcopy(lastStatus)
            except:
                LOGGER.warning(f"can not write to websocket, closing client connection({connectionNumber})")
                await websocket.close()
                break


@click.command()
@click_log.simple_verbosity_option(logging.getLogger(), default="INFO")
@util.background
async def gateway():
    global LOGGER
    LOGGER = logging.getLogger(__name__)
    logging.basicConfig(format='%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)4d] %(message)s',
                        datefmt=' %Y-%m-%d:%H:%M:%S', level=LOGGER.getEffectiveLevel())
    commandList = { 'b0:c7:de:ff:fe:52:ca:58on': True,
                    'b0:c7:de:ff:fe:52:ca:58off': True,
                    'b0:c7:de:ff:fe:52:ca:58status': True,
                    '34:10:f4:ff:fe:2f:3f:b6on': True,
                    '34:10:f4:ff:fe:2f:3f:b6off': True,
                    '34:10:f4:ff:fe:2f:3f:b6status': True }
    LOGGER.debug('entering gateway D')
    await entry(commandList)

if __name__ == "__main__":
    asyncio.run(gateway())
