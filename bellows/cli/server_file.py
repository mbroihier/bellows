'''
Gateway server file - implements the ZCL gateway
'''

import asyncio
import copy
import json
import logging
import signal
import time
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
    ipo.status_labels = command_info[1]
    ipo.result_indices = command_info[2]
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
                '''
                try:
                    v = await commandList[command]([3,4,7,16395,16396])
                    LOGGER.debug(f"color temperature: {v}")
                    color_temperature = v[0][7]
                    x = v[0][3]
                    y = v[0][4]
                    min_mireds = v[0][16395]
                    max_mireds = v[0][16396]
                    v = await commandList[addr+'readLevel']([0])
                    LOGGER.debug(f"light level: {v}")
                    light_level = v[0][0]
                except Exception as e:
                    LOGGER.debug(f"Exception: {e}")
                    color_temperature = 0
                    light_level = 0
                    x = 0
                    y = 0
                    min_mireds = 0
                    max_mireds = 0
                ipo.update_status.send((addr, 'X', x))
                ipo.update_status.send((addr, 'Y', y))
                ipo.update_status.send((addr, 'Level', light_level))
                ipo.update_status.send((addr, 'minMireds', min_mireds))
                ipo.update_status.send((addr, 'maxMireds', max_mireds))
                ipo.update_status.send((addr, 'CT', color_temperature))
                '''

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
                if 'status' in ipo.doCommand[0]:
                    await chains.execute(ipo.doCommand[0])
                elif 'readCT' in ipo.doCommand[0]:
                    await chains.execute(ipo.doCommand[0])
                elif 'setCT' in ipo.doCommand[0]:
                    try:
                        #step_color_temp = 0x4c  # as defined in spec
                        new_temperature = int(ipo.doCommand[0].split(' ')[-1])
                        address = get_address(ipo.doCommand[0])
                        if new_temperature > 0:
                            new_temperature_mireds = int((1000000 / new_temperature))
                        else:
                            new_temperature_mireds = 0
                        if ipo.lastStatus[address] == 'on':
                            if (ipo.lastStatus[address+'minMireds'] < new_temperature_mireds <
                                ipo.lastStatus[address+'maxMireds']):
                                LOGGER.debug(f"new temperature in mireds: {new_temperature_mireds}")
                                old_color_temp_mireds = ipo.lastStatus[address+'CT']
                                LOGGER.debug(f"old temperature in mireds: {old_color_temp_mireds}")
                                if old_color_temp_mireds > new_temperature_mireds:
                                    step = old_color_temp_mireds - new_temperature_mireds
                                    direction = 'Down'
                                else:
                                    step = new_temperature_mireds - old_color_temp_mireds
                                    direction = 'Up'
                                v = await commandList[ipo.doCommand[0].split(' ')[0]](new_temperature_mireds, 1)
                                LOGGER.warning(f"gateway status: {v}")
                                ipo.update_status.send((address, 'CT', new_temperature_mireds))
                            else:
                                LOGGER.warning("temperature out of range, not changed")
                        else:
                            LOGGER.warning("can't change color temperature when bulb is off")

                    except Exception as e:
                        LOGGER.warning(f"gateway Exception: {e} color temperature not changed")
                elif 'readLevel' in ipo.doCommand[0]:
                    await chains.execute(ipo.doCommand[0])
                elif 'setLevel' in ipo.doCommand[0]:
                    try:
                        step_level = 0x02  # as defined in spec
                        new_level = int(ipo.doCommand[0].split(' ')[-1])
                        old_level = ipo.lastStatus[get_address(ipo.doCommand[0])+'Level']
                        LOGGER.warning(f"new light level: {new_level}")
                        LOGGER.warning(f"old light level: {old_level}")
                        if ipo.lastStatus[get_address(ipo.doCommand[0])] == 'on':
                            if 0 < new_level < 255:
                                if old_level > new_level:
                                    step = old_level - new_level
                                    direction = 'Down'
                                else:
                                    step = new_level - old_level
                                    direction = 'Up'
                                v = await commandList[ipo.doCommand[0].split(' ')[0]](new_level, 1)
                                LOGGER.warning(f"gateway status: {v}")
                            else:
                                new_level = old_level
                                LOGGER.warning("light level out of range, not changed")
                        else:
                            new_level = old_level
                            LOGGER.warning("can't change light level when bulb is off")
                    except Exception as e:
                        LOGGER.warning(f"gateway Exception: {e} light level not changed")
                        new_level = old_level
                    ipo.update_status.send((get_address(ipo.doCommand[0]), 'Level', new_level))
                elif ('on' in ipo.doCommand[0] or 'off' in ipo.doCommand[0]):
                    if ipo.lastStatus[get_address(ipo.doCommand[0])] == 'unknown':
                        await init_status(chains, get_address(ipo.doCommand[0]))
                    else:
                        await chains.execute(ipo.doCommand[0])
                else:
                    LOGGER.warning(f"logic error {ipo.doCommand[0]} is only partially implemented")
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
