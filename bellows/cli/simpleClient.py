#!/usr/bin/env -S python
import asyncio
import calendar
import logging

import click
import click_log

import time
import sys
import websockets

from bellows.cli import util

LOGGER = logging.getLogger(__name__)

FULL_DAY = 24 * 3600
sunset = {}
sunrise = {}

@click.command()
@click.argument("zclcommand")
@click_log.simple_verbosity_option(logging.getLogger(), default="INFO")
@util.background
async def simpleClient(zclcommand):
    ''' simpleClient '''
    logging.basicConfig(format='%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)4d] %(message)s',
                        datefmt=' %Y-%m-%d:%H:%M:%S', level=LOGGER.getEffectiveLevel())
    try:
        async with websockets.connect("ws://localhost:8126") as socket:
            await socket.send("simpleClient connection request")
            message = await asyncio.wait_for(socket.recv(), timeout=1.0)
            LOGGER.info(f"received initial/connection status of: {message}")
            await socket.send(zclcommand)
            message = await asyncio.wait_for(socket.recv(), timeout=5.0)
            LOGGER.info(f"received final status of: {message}")
    except TimeoutError as e:
        LOGGER.error("TimeoutError while receiving status")
    except Exception as e:
        LOGGER.error(f"Exception detected {e}, terminating")
    
if __name__ == "__main__":
    asyncio.run(simpleClient())

