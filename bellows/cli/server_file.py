'''
Gateway server file - implements the ZCL gateway
'''

import asyncio
import copy
import json
import logging
import signal

from websockets.server import serve as wsserve

from . import InterprocessObjects
from . import zcl_chains
# pylint: disable-msg=C0103
# pylint: disable-msg=W1203
LOGGER = logging.getLogger(__name__)

def get_address(command):
    '''
    Get the address from a command
    '''
    result = command.replace('on', '')
    result = result.replace('off', '')
    result = result.replace('status', '')
    result = result.replace('readCT', '')
    result = result.replace('readLevel', '')
    result = result.replace('setCT', '')
    result = result.replace('setLevel', '')
    result = result.split(' ')[0]
    return result

def sigint_handler(_, __):
    '''
    On any signal, terminate gateway
    '''
    ipo = InterprocessObjects.InterprocessObjects()
    print("\nshutting down server....")
    ipo.continue_loop = False


async def entry(command_info, app):
    '''
    Entry of gateway via asnycio environment
    '''
    ipo = InterprocessObjects.InterprocessObjects()
    # setup attributes of Interprocess Object
    commandList = command_info[0]
    ipo.commandList = command_info[0]
    ipo.command_tuples = command_info[1]
    ipo.status_labels = command_info[2]
    ipo.result_indices = command_info[3]
    ipo.network_devices = command_info[4]
    ipo.continue_loop = True
    ipo.connection_number = 0
    ipo.doCommand = []
    ipo.lastStatus = {}
    ipo.last_update_time = 0
    ipo.message_update_counter = 0

    LOGGER.debug(f"command list: {commandList}, continue_loop: {ipo.continue_loop},"
                 " lastStatus: {ipo.lastStatus}")
    async def init_status(chains, address=None):
        '''
        Initialize status object
        '''
        for command in commandList:
            if address is not None:
                if not address in command:
                    continue
            addr = get_address(command)
            if 'status' in command:
                LOGGER.debug(f"initializing status for {addr}")
                await chains.execute(command)
            if 'readCT' in command:
                await chains.execute(command)

    chains = zcl_chains.ZCL_Chains(commandList)
    await init_status(chains)
    LOGGER.debug("Creating gateway")
    wsserver = await wsserve(websocketHandler, "", 8126)
    async with wsserver:
        signal.signal(signal.SIGINT, sigint_handler)
        LOGGER.debug("Starting gateway")
        await wsserver.start_serving()
        while ipo.continue_loop and app._ezsp.is_ezsp_running:
            await asyncio.sleep(0.1)
            if ipo.doCommand:
                LOGGER.info(f"gateway doing command: {ipo.doCommand[0]}")
                fields = ipo.doCommand[0].split(' ')
                if len(fields) == 1:
                    command = fields[0]
                    if ipo.lastStatus[get_address(command)] == 'unknown':
                        await init_status(chains, get_address(command))
                    await chains.execute(command)
                elif len(fields) == 2:
                    command = fields[0]
                    try:
                        params = int(fields[1])
                        if ipo.lastStatus[get_address(command)] == 'unknown':
                            await init_status(chains, get_address(command))
                        await chains.execute(command, params)
                    except ValueError as e:
                        LOGGER.warning(f"invalid parameter produced exception: {e}")
                else:
                    LOGGER.warning(f"{ipo.doCommand[0]} is not supported")
                del ipo.doCommand[0]
        LOGGER.info(f"gateway terminating - continue_loop: {ipo.continue_loop},"
                    " controller status: {app._ezsp.is_ezsp_running}")

async def websocketHandler(websocket):
    '''
    Websocket connection handler - start communication with a client
    '''
    ipo = InterprocessObjects.InterprocessObjects()
    LOGGER.debug("websocket server connection is starting")
    consumer_task = asyncio.create_task(consumer_handler(websocket, ipo.connection_number))
    producer_task = asyncio.create_task(producer_handler(websocket, ipo.connection_number))
    ipo.connection_number += 1
    _, pending = await asyncio.wait([consumer_task, producer_task],
                                     return_when=asyncio.FIRST_COMPLETED, )
    LOGGER.debug("websocket server connection is terminating")
    for task in pending:
        task.cancel()

async def consumer_handler(websocket, connection_number):
    '''
    Capture incoming bellows ZCL commands and queue them for processing
    '''
    ipo = InterprocessObjects.InterprocessObjects()
    LOGGER.info(f"gateway sending ({connection_number}): {json.dumps(ipo.lastStatus)}")
    await websocket.send(json.dumps(ipo.lastStatus))  # this message is sent on connection
    try:
        async for message in websocket:
            LOGGER.info(f"gateway connection received ({connection_number}): {message}")
            while True:
                try:
                    message = await websocket.recv()
                    LOGGER.info(f"gateway received({connection_number}): {message}")
                    if message.split(' ')[0] in ipo.commandList:
                        ipo.last_update_time = 0
                        ipo.message_update_counter += 1
                        ipo.doCommand.append(message)
                    else:
                        LOGGER.warning("bad command read from websocket, closing client"
                                       f"  connection({connection_number})")
                        await websocket.close()
                        break
                except Exception as e:
                    LOGGER.warning(f"{e} - can not read websocket, closing client connection"
                                   f" ({connection_number})")
                    await websocket.close()
                    break
    except Exception as e:
        LOGGER.warning(f"{e} while waiting for a message from websocket, connection closed"
                       f"({connection_number})")

async def producer_handler(websocket, connection_number):
    '''
    Produce status messages for clients waiting for status changes
    '''
    ipo = InterprocessObjects.InterprocessObjects()
    lastSentStatus = copy.deepcopy(ipo.lastStatus)
    local_message_update_counter = ipo.message_update_counter
    while True:
        await asyncio.sleep(0.3)
        if (((ipo.lastStatus != lastSentStatus) or
             (ipo.message_update_counter != local_message_update_counter)) and
            ipo.last_update_time != 0):
            LOGGER.info(f"gateway sending({connection_number}): {json.dumps(ipo.lastStatus)}")
            try:
                await websocket.send(json.dumps(ipo.lastStatus))
                lastSentStatus = copy.deepcopy(ipo.lastStatus)
                local_message_update_counter = ipo.message_update_counter
            except Exception as e:
                LOGGER.warning(f"{e} - can not write to websocket, closing client connection"
                               f"({connection_number})")
                await websocket.close()
                break
