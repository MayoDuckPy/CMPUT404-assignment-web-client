#!/usr/bin/env python3
# coding: utf-8
# Copyright 2016 Abram Hindle, https://github.com/tywtyw2002, and https://github.com/treedust
# 
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Do not use urllib's HTTP GET and POST mechanisms.
# Write your own HTTP GET and POST
# The point is to understand what you have to send and get experience with it

import sys
import socket
import re
# you may use urllib to encode data appropriately
import urllib.parse as parser

CR = '\r\n'

def help():
    print('httpclient.py [GET/POST] [URL]\n')

class HTTPResponse(object):
    __slots__ = ['body', 'code']
    def __init__(self, code=200, body=''):
        self.code = code
        self.body = body

class HTTPClient(object):
    DEFAULT_CODE = 500
    DEFAULT_BODY = ''

    def get_host_port_path(self, url):
        '''Parse a url and return the tuple: (host, port, path).'''
        result = parser.urlparse(url)
        port = result.port if result.port else 80
        path = result.path if result.path else '/'
        return (result.hostname, port, path)

    def connect(self, host, port):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((host, port))
        return self.socket

    def disconnect(self):
        self.socket.shutdown(socket.SHUT_RDWR)
        self.socket.close()

    def get_code(self, data):
        return int(data.split()[1])

    def get_headers(self, data):
        headers = {}
        try:
            http_head = data.split(CR * 2)[0]  # Split on '\r\n\r\n'
            expr = re.compile('([a-zA-Z-]*): (.*)')
            for header in http_head.split(CR)[1:]:
                match = re.match(expr, header)
                if not match:
                    continue;

                headers[match.group(1).lower()] = match.group(2)

        except IndexError:
            return None

        return headers

    def get_body(self, data):
        try:
            return data.split(f'{CR}{CR}')[1]
        except IndexError:  # No body
            return ''
    
    def sendall(self, data):
        self.socket.sendall(data.encode('utf-8'))
        
    # Read everything from the socket
    def get_response(self, sock):
        recv_len = 1024
        buffer = bytearray()

        # Get all headers
        header_delimiter = (CR*2).encode()
        while header_delimiter not in buffer:
            part = sock.recv(recv_len)
            if not part:
                return buffer.decode()

            buffer.extend(part)

        # Check if server sends us content length
        content_length = 0
        headers = self.get_headers(buffer.decode())
        if not headers or 'content-length' not in headers.keys():
            # No Content-Length; use old-fashioned recvall
            while True:
                part = sock.recv(recv_len)
                if not part:
                    break

                buffer.extend(part)

            return buffer.decode()

        content_length = int(headers['content-length'])
        content_length -= len(buffer.split(header_delimiter)[1])

        # Fetch remaining content
        while content_length > 0:
            part = sock.recv(recv_len)
            buffer.extend(part)
            content_length -= len(part)

        return buffer.decode()

    def GET(self, url, args=None):
        code = self.DEFAULT_CODE
        body = self.DEFAULT_BODY

        host, port, path = self.get_host_port_path(url)
        request = f'GET {path} HTTP/1.1{CR}Host: {host}{CR}Content-Type: text/html{CR}{CR}'

        self.connect(host, port)
        self.sendall(request)
        data = self.get_response(self.socket)
        self.disconnect()

        code = self.get_code(data)
        body = self.get_body(data)
        return HTTPResponse(code, body)

    def POST(self, url, args=None):
        code = self.DEFAULT_CODE
        body = self.DEFAULT_BODY

        # Post data in args
        fields = ''
        if args and type(args) is dict:
            for field, value in args.items():
                fields += f'{field}={value}&'

        fields = fields[:-1]
        host, port, path = self.get_host_port_path(url)
        request = f'POST {path} HTTP/1.1{CR}Host: {host}{CR}Content-Type: application/x-www-form-urlencoded{CR}Content-Length: {len(fields)}{CR}{CR}{fields}{CR}'

        self.connect(host, port)
        self.sendall(request)
        data = self.get_response(self.socket)
        self.disconnect()

        code = self.get_code(data)
        body = self.get_body(data)
        return HTTPResponse(code, body)

    def command(self, url, command='GET', args=None):
        if (command == 'POST'):
            return self.POST(url, args)

        return self.GET(url, args)
    
if __name__ == '__main__':
    client = HTTPClient()
    command = 'GET'
    if (len(sys.argv) <= 1):
        help()
        sys.exit(1)
    elif (len(sys.argv) == 3):
        print(client.command(sys.argv[2], sys.argv[1]))
    else:
        print(client.command(sys.argv[1]))
