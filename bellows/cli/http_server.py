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
    def run_async_command(self, command):
        v = asyncio.run(command())
        print(f"async command status: {v}")

    def do_GET(self):
        print("got a get with:", self.path)
        if self.path == '/':
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
        elif self.path == '/index.html':
            with open('./index.template', 'r') as fileObject:
                content = ""
                for line in fileObject:
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
                    rthread = threading.Thread(target=self.run_async_command, args=(self.server.commandList[command],))
                    rthread.start()
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
