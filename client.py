import json
import os
import logging
import socket
import threading
import time
import random
import secrets
import time

if not os.path.exists('config.json'):
    logging.fatal('can not find config.json')
    exit(1)

try:
    with open('config.json', 'r') as f:
        config = json.loads(f.read())
except Exception as e:
    logging.fatal('can not load the configuration.')
    logging.exception(e)


class ForwardServer():
    def __init__(self, instance, address, keyword):
        super().__init__()
        try:
            conn = socket.socket()
            conn.connect(address)
            conn.send(b'''GET / HTTP/1.1\nConnect: '''+keyword.encode()+b'''\r\n\r\n''')
            if keyword in conn.recv(2048):
                print('Connection established.')
        except:
            try:
                instance.shutdown(socket.SHUT_RDWR)
            except:
                pass
            finally:
                instance.close()
            return
        self.worker_send = threading.Thread(
            target=self.worker, args=(instance, conn))
        self.worker_recv = threading.Thread(
            target=self.worker, args=(conn, instance))

        print('Started!')
        self.worker_send.setDaemon(True)
        self.worker_send.start()
        self.worker_recv.setDaemon(True)
        self.worker_recv.start()

        # print('Forward:', instance, address, f2048b)

    def worker(self, a, b):
        'From a --> b'
        while True:
            try:
                data = a.recv(2048)
                b.send(data)
                if data == b'':
                    raise Exception('Disconnected.')
            except:
                try:
                    a.shutdown(socket.SHUT_RDWR)
                    b.shutdown(socket.SHUT_RDWR)
                except:
                    pass
                finally:
                    a.close()
                    b.close()
                break


class Handle:
    def __init__(self, bind, server, keyword):
        self.socket = socket.socket()
        self.server = server
        self.keyword = keyword
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(bind)
        self.socket.listen(10)
        self.thread = threading.Thread(target=self.listen)
        self.thread.setDaemon(True)
        self.thread.name = bind[0] + ':'+str(bind[1])
        self.thread.start()
        self.workers = {}

    def listen(self):
        while True:
            instance, address = self.socket.accept()
            workerID = secrets.token_hex(4)
            self.workers[workerID] = ForwardServer(
                instance, self.server, self.keyword)


Handle(('0.0.0.0',8080),('localhost',65535),'en-UN')

while True:
    pass
