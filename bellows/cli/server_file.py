import asyncio
import copy
import json
import logging
import signal
from websockets.server import serve as wsserve

LOGGER = logging.getLogger(__name__)
lastStatus = {}
doCommand = []
gCommandList = {}
continueLoop = True
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
    debug = logging.DEBUG == LOGGER.getEffectiveLevel()
    address = ('', 8125)
    loop = asyncio.get_running_loop()
    global lastStatus
    global gCommandList
    global continueLoop
    gCommandList = commandList
    for command in commandList:
        if 'status' in command:
            try:
                v = await commandList[command]([0], allow_cache=False)
                LOGGER.debug(f"status: {v}")
                if v[0][0] == True:
                    state = 'on'
                else:
                    state = 'off'
            except Exception as e:
                LOGGER.debug(f"Exception: {e}")
                state = 'unknown'
            lastStatus[getDevice(command)] = state

    LOGGER.debug("Creating zcl server")
    wsserver = await wsserve(websocketHandler, "", 8126)
    async with wsserver:
        signal.signal(signal.SIGINT, sigint_handler)
        LOGGER.debug("Starting zcl server")
        await wsserver.start_serving()
        while continueLoop:
            await asyncio.sleep(0.1)
            if doCommand:
                LOGGER.debug(f"zcl server doing command: {doCommand[0]}")
                if 'status' in doCommand[0]:
                    try:
                        v = await commandList[doCommand[0]]([0], allow_cache=False)
                        LOGGER.debug(f"zcl server status: {v}")
                        if v[0][0] == False:
                            lastStatus[getDevice(doCommand[0])] = 'off'
                        else:
                            lastStatus[getDevice(doCommand[0])] = 'on'
                    except Exception as e:
                        LOGGER.debug(f"zcl server Exception: {e}")
                        lastStatus[getDevice(doCommand[0])] = 'unknown'
                else:
                    try:
                        v = await commandList[doCommand[0]]()
                        LOGGER.debug(f"zcl server status: {v}")
                        if v.as_tuple()[0] == 0:
                            lastStatus[getDevice(doCommand[0])] = 'off'
                        else:
                            lastStatus[getDevice(doCommand[0])] = 'on'
                    except Exception as e:
                        LOGGER.debug(f"zcl server Exception: {e}")
                        lastStatus[getDevice(doCommand[0])] = 'unknown'
                del doCommand[0]

async def websocketHandler(websocket):
    LOGGER.debug("websocket server connection is starting")
    consumer_task = asyncio.create_task(consumer_handler(websocket))
    producer_task = asyncio.create_task(producer_handler(websocket))
    done, pending = await asyncio.wait([consumer_task, producer_task],
                                     return_when=asyncio.FIRST_COMPLETED, )
    LOGGER.debug("websocket server connection is terminating")
    for task in pending:
        task.cancel()

async def consumer_handler(websocket):
    global gCommandList
    global doCommand
    try:
        async for message in websocket:
            while True:
                try:
                    message = await websocket.recv()
                    LOGGER.debug(f"{message}")
                    if message in gCommandList:
                        doCommand.append(message)
                    else:
                        LOGGER.warning("bad command read from websocket, closing client connection")
                        await websocket.close()
                        break
                except:
                    LOGGER.warning("can not read websocket, closing client connection")
                    await websocket.close()
                    break
    except Exception as e:
        LOGGER.warning(f"{e} while waiting for a message from websocket, connection closed")

async def producer_handler(websocket):
    global lastStatus
    await websocket.send(json.dumps(lastStatus))  # this message is sent on connection
    lastSentStatus = copy.deepcopy(lastStatus)
    while True:
        await asyncio.sleep(0.3)
        if lastStatus != lastSentStatus:
            try:
                await websocket.send(json.dumps(lastStatus))
                lastSentStatus = copy.deepcopy(lastStatus)
            except:
                LOGGER.warning("can not write to websocket, closing client connection")
                await websocket.close()
                break
            

