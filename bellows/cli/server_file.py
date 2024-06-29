import asyncio
import copy
import json
import logging
from websockets.server import serve as wsserve

LOGGER = logging.getLogger(__name__)
lastStatus = {}
class ZCLServerProtocol(asyncio.Protocol):
    def __init__(self, commandList, doCommand, lastStatus):
        super().__init__()
        self.commandList = commandList
        self.doCommand = doCommand
        self.lastStatus = lastStatus

    def connection_made(self, transport):
        self.transport = transport

    def data_received(self, data):
        message = data.decode()
        message = message.rstrip()
        LOGGER.debug(f"message recieved: {message}")
        if message in self.commandList:
            self.doCommand.append(message)
            if 'status' in message:
                self.transport.write(("ack " + self.lastStatus[getDevice(message)]).encode())
            else:
                self.lastStatus[getDevice(message)] = 'unknown'  # set status to unknown - about to be in transition
                self.transport.write(b"ack")
        else:
            self.transport.write(b"nack")
        self.transport.close()

def getDevice(command):
    result = command.replace('on', '')
    result = result.replace('off', '')
    result = result.replace('status', '')
    return result

async def entry(ctx, commandList, click):
    debug = logging.DEBUG == LOGGER.getEffectiveLevel()
    address = ('', 8125)
    loop = asyncio.get_running_loop()
    doCommand = []
    global lastStatus
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
    server = await loop.create_server(lambda: ZCLServerProtocol(commandList, doCommand, lastStatus), '', 8125)
    wsserver = await wsserve(reportStatus, "", 8126)
    async with server:
        LOGGER.debug("Starting zcl server************************##########################")
        await server.start_serving()
        await wsserver.start_serving()
        while True:
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
count = 0
async def reportStatus(websocket):
    global lastStatus
    global count
    count += 1
    LOGGER.debug(f"new ws server connection: {count} sending {lastStatus}")
    await websocket.send(json.dumps(lastStatus))
    lastSentStatus = copy.deepcopy(lastStatus)
    while True:
        await asyncio.sleep(1.0)
        if lastStatus != lastSentStatus:  #send an update
            LOGGER.debug(f"sending updated status {lastStatus}")
            try:
                await websocket.send(json.dumps(lastStatus))
                lastSentStatus = copy.deepcopy(lastStatus)
            except Exception as e:
                LOGGER.warning(f"ws got an exception: {e}, exiting client connection")
                break  #leave this client
            

