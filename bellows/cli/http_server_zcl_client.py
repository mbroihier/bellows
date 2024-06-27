#!/usr/bin/env -S python
'''
HTTP server and ZigBee client - services HTTP GETs and issues commands to the ZigBee Server
'''
import asyncio
from http import server as httpServer
import logging
import threading
import time

LOGGER = logging.getLogger(__name__)

class HTTPHandler(httpServer.BaseHTTPRequestHandler):
    '''
    HTTPHandler that handles GET requests of HTTP protocol - POSTs are ignored
    '''
    def run_async_command(self, command):
        v = asyncio.run(mainClient(command))
        if 'status' in command:
            device = command.replace('status', '')
            self.server.lightStatus[device] = v.split(' ')[1]
            self.server.lightStatusTime[device] = time.time()
            print(f"lightStatus for {device} is {self.server.lightStatus[device]}")
        else:
            device = command.replace('on', '')
            device = device.replace('off', '')
            self.server.lightStatus[device] = 'unknown'
            
        print(f"async command status: {v}")

    def do_GET(self):
        print("got a get with:", self.path)
        if self.path == '/':
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
        elif self.path == '/index.html':
            for device in self.server.lightStatus:
                # refresh status if it is unknown
                if self.server.lightStatus[device] == 'unknown' or (time.time() - self.server.lightStatusTime[device] >15.0):
                    count = 2
                    self.server.lightStatus[device] = 'unknown'
                    while self.server.lightStatus[device] == 'unknown' and count > 0:
                        print(f"reading status for {device}, count = {count}")
                        command = device + 'status'
                        sthread = threading.Thread(target=self.run_async_command, args=(command,))
                        sthread.start()
                        sthread.join()
                        count -= 1

            with open('./index.html', 'r') as fileObject:
                content = ""
                for line in fileObject:
                    for device in self.server.lightStatus:
                        if device in line:
                            if device+self.server.lightStatus[device] in line:
                                line = line.replace('visible', 'hidden')
                    content += line
                content = content.encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'text')
                self.send_header('Content-Length', len(content))
                self.end_headers()
                self.wfile.write(content)
        else:
            command = self.path.split('/')[1]
            command = command.rstrip("?")
            print(f"processing command: {command}")
            if command in self.server.commandList:
                try:
                    print(f"command issued but thread may not be done for a while")
                    cthread = threading.Thread(target=self.run_async_command, args=(command,))
                    cthread.start()
                    cthread.join()
                    time.sleep(0.3)
                    command = command.replace('on', 'status')
                    command = command.replace('off', 'status')
                    device = command.replace('status', '')
                    count = 2
                    while self.server.lightStatus[device] == 'unknown' and count > 0:
                        print(f"reading status, count = {count}")
                        sthread = threading.Thread(target=self.run_async_command, args=(command,))
                        sthread.start()
                        sthread.join()
                        count -= 1
                except Exception as e:
                    print(f"light command failed with exception: {e}")
                print("sending a reply to go back to index file")
                self.send_response(302)
                self.send_header('Location', '/index.html')
                self.end_headers()
            else:
                self.send_error(404)
                self.end_headers()

    def do_POST(self):
        length = int(self.headers['Content-Length'])
        line = self.rfile.read(length)
        print("got a post with:", line)

class HTTPServerBackground():
    def __init__(self, server):
        self.terminate = False
        self.server = server
    
    def background(self):
        while not self.terminate:
            self.server.handle_request()

    def shutdown(self):
        self.terminate = True
        
class ZigBeeClient(asyncio.Protocol):
    def __init__(self, message, on_lost):
        self.message = message
        self.on_lost = on_lost

    def connection_made(self, transport):
        transport.write(self.message.encode())

    def data_received(self, data):
        self.data = data

    def connection_lost(self, exc):
        self.on_lost.set_result(True)

async def mainClient(message):
    loop = asyncio.get_running_loop()
    on_lost = loop.create_future()
    transport, client = await loop.create_connection(
        lambda: ZigBeeClient(message, on_lost), "localhost", 8125)
    try:
        await on_lost
        print(client.data)
        return client.data.decode()
    finally:
        transport.close()

def main():
    '''
    Test main program for server
    '''
    address = ('', 8124)
    server = httpServer.HTTPServer(address, HTTPHandler)
    server.commandList = {'b0:c7:de:ff:fe:52:ca:58on': True,
                          'b0:c7:de:ff:fe:52:ca:58off': True,
                          'b0:c7:de:ff:fe:52:ca:58status': True,
                          '34:10:f4:ff:fe:2f:3f:b6on': True,
                          '34:10:f4:ff:fe:2f:3f:b6off': True,
                          '34:10:f4:ff:fe:2f:3f:b6status': True}
    server.lightStatus = {'b0:c7:de:ff:fe:52:ca:58': 'unknown',
                          '34:10:f4:ff:fe:2f:3f:b6': 'unknown'}
    server.lightStatusTime = {'b0:c7:de:ff:fe:52:ca:58': 0,
                              '34:10:f4:ff:fe:2f:3f:b6': 0}
    backgroundObject = HTTPServerBackground(server)
    backgroundThread = threading.Thread(target=backgroundObject.background)
    try:
        backgroundThread.start()
    except Exception as e:
        print(f"Received a {e} exception")
        backgroundObject.shutdown()
        backgroundThread.join()
    while True:
        try:
            time.sleep(1.0)
        except KeyboardInterrupt:
            backgroundObject.shutdown()
            backgroundThread.join()
            break

if __name__ == "__main__":
    main()
