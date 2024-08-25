import asyncio
import copy
import json
import logging
import signal

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

def buildTimeServer(commandList):
    filledInTemplate = open("timeserver.txt", "w", encoding="utf-8")
    with open("timeservertemplate.txt", "r", encoding="utf-8") as templateFile:
        for line in templateFile.readlines():
            if "***begin insert***" in line:
                devices = []
                filledInTemplate.write("    devices = [\n")
                for entry in commandList:
                    if "on" in entry:
                        device = getDevice(entry)
                        devices.append(device)
                        filledInTemplate.write(f'               "{device}",\n')
                filledInTemplate.write("              ]\n")
                filledInTemplate.write("    timeOn = {\n")
                for device in devices:
                    filledInTemplate.write(f'              "{device}": [],\n')
                filledInTemplate.write("             }\n")
                filledInTemplate.write("    timeOff = {\n")
                for device in devices:
                    filledInTemplate.write(f'               "{device}": [],\n')
                filledInTemplate.write("              }\n")
                filledInTemplate.write("    sunriseOnOffset = {\n")
                for device in devices:
                    filledInTemplate.write(f'                      "{device}": [],\n')
                filledInTemplate.write("                      }\n")
                filledInTemplate.write("    sunriseOffOffset = {\n")
                for device in devices:
                    filledInTemplate.write(f'                       "{device}": [],\n')
                filledInTemplate.write("                       }\n")
                filledInTemplate.write("    sunsetOnOffset = {\n")
                for device in devices:
                    filledInTemplate.write(f'                      "{device}": [],\n')
                filledInTemplate.write("                     }\n")
                filledInTemplate.write("    sunsetOffOffset = {\n")
                for device in devices:
                    filledInTemplate.write(f'                       "{device}": [],\n')
                filledInTemplate.write("                      }\n")
                filledInTemplate.write("    deviceTL = {\n")
                for device in devices:
                    filledInTemplate.write(f'                "{device}": ')
                    filledInTemplate.write('{"timeOn": timeOn, "timeOff": timeOff,\n')
                    filledInTemplate.write('                                            "sunriseOn": sunriseOnOffset,\n')
                    filledInTemplate.write('                                            "sunriseOff": sunriseOffOffset,\n')
                    filledInTemplate.write('                                            "sunsetOn": sunsetOnOffset,\n')
                    filledInTemplate.write('                                            "sunsetOff": sunsetOffOffset},\n')
                filledInTemplate.write("               }\n")
                filledInTemplate.write("    deviceTLIndex = {\n")
                for device in devices:
                    filledInTemplate.write(f'                     "{device}": ')
                    filledInTemplate.write('{"timeOn": 0, "timeOff": 0,\n')
                    filledInTemplate.write('                                                 "sunriseOn": 0,\n')
                    filledInTemplate.write('                                                 "sunriseOff": 0,\n')
                    filledInTemplate.write('                                                 "sunsetOn": 0,\n')
                    filledInTemplate.write('                                                 "sunsetOff": 0},\n')
                filledInTemplate.write("                    }\n")
                filledInTemplate.write("    deviceUpdateTimes = {\n")
                for device in devices:
                    filledInTemplate.write(f'                          "{device}": ')
                    filledInTemplate.write('{"timeOn": 0, "timeOff": 0,\n')
                    filledInTemplate.write('                                                      "sunriseOn": 0,\n')
                    filledInTemplate.write('                                                      "sunriseOff": 0,\n')
                    filledInTemplate.write('                                                      "sunsetOn": 0,\n')
                    filledInTemplate.write('                                                      "sunsetOff": 0},\n')
                filledInTemplate.write("                        }\n")
            else:
                filledInTemplate.write(line)
    filledInTemplate.close()
    
def buildHTTPServer(commandList):
    filledInTemplate = open("httpserver.txt", "w", encoding="utf-8")
    with open("httpservertemplate.txt", "r", encoding="utf-8") as templateFile:
        for line in templateFile.readlines():
            if "***begin insert***" in line:
                filledInTemplate.write("    server.commandList = {\n")
                for entry in commandList:
                    filledInTemplate.write(f"                          '{entry}': True,\n")
                filledInTemplate.write("                         }\n")
                filledInTemplate.write("    server.lightStatus = {\n")
                for entry in commandList:
                    if "on" in entry:
                        device = getDevice(entry)
                        filledInTemplate.write(f"                          '{device}': 'unknown',\n")
                filledInTemplate.write("                         }\n")
                filledInTemplate.write("    server.lightStatusTime = {\n")
                for entry in commandList:
                    if "on" in entry:
                        device = getDevice(entry)
                        filledInTemplate.write(f"                              '{device}': 0,\n")
                filledInTemplate.write("                             }\n")
            else:
                filledInTemplate.write(line)
    filledInTemplate.close()
    filledInTemplate = open("index.txt", "w", encoding="utf-8")
    count = 0
    with open("indextemplate.txt", "r", encoding="utf-8") as templateFile:
        for line in templateFile.readlines():
            if "***begin insert1***" in line:
                for entry in commandList:
                    if "on" in entry or "off" in entry:
                        name = "name" + str(count)
                        count += 1
                        filledInTemplate.write(f'<li><button id="{entry}" style="visibility: hidden" onclick="wssend(\'{entry}\')" >{name}</button></li>\n')
            elif "***begin insert2***" in line:
                count = 0
                for entry in commandList:
                    if "on" in entry or "off" in entry:
                        name = "name" + str(count)
                        count += 1
                        filledInTemplate.write(f'<li><button id="{entry}" style="visibility: visible" type="submit" formaction="/{entry}" formmethod="get">{name}</button></li>\n')
            else:
                filledInTemplate.write(line)
    filledInTemplate.close()
                

async def entry(commandList):
    debug = logging.DEBUG == LOGGER.getEffectiveLevel()
    LOGGER.info("building bellows plus tools")
    for entry in commandList:
        LOGGER.info(f"entry: {entry}")
    buildHTTPServer(commandList)
    buildTimeServer(commandList)
