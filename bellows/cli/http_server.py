#!/usr/bin/env -S python
'''
script server - services HTTP POSTs that contain on/off commands
'''
import asyncio
from http import server as httpServer
import logging
import threading
import time

LOGGER = logging.getLogger(__name__)

class ScriptHandler(httpServer.BaseHTTPRequestHandler):
    '''
    ScriptHandler that handles POST requests
    '''
    def do_GET(self):
        print("got a get with:", self.path)
        command = self.path.split('/')[1]
        print(command)
        if command in self.server.commandList:
            self.send_response(200)
            self.end_headers()
            rthread = threading.Thread(target=asyncio.run, args=(self.server.commandList[command](),))
            rthread.start()
            print("processing done")
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
        
        
def main():
    '''
    Test main program for server
    '''
    address = ('', 8124)
    server = httpServer.HTTPServer(address, ScriptHandler)
    server.commandList = {}
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
