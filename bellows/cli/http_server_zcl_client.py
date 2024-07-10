#!/usr/bin/env -S python
'''
HTTP server and ZigBee client - services HTTP GETs and issues commands to the ZigBee Server
'''
import asyncio
from http import server as httpServer
import logging
import socket
import threading
import time

LOGGER = logging.getLogger(__name__)

class HTTPHandler(httpServer.BaseHTTPRequestHandler):
    '''
    HTTPHandler that handles GET requests of HTTP protocol - POSTs are ignored
    '''
    def do_GET(self):
        print("got a get with:", self.path)
        if self.path == '/':
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
        elif self.path == '/index.html':
            with open('./index.html', 'r') as fileObject:
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
    address = ('::', 8124)
    class HTTPServerV6(httpServer.HTTPServer):
        address_family = socket.AF_INET6
    server = HTTPServerV6(address, HTTPHandler)
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
