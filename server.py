import json
import os
import logging
import socket
import threading
import time
import random
import secrets

if not os.path.exists('config.json'):
    logging.fatal('can not find config.json')
    exit(1)

try:
    with open('config.json', 'r') as f:
        config = json.loads(f.read())
except Exception as e:
    logging.fatal('can not load the configuration.')
    logging.exception(e)

assert 'server' in config
assert type(config['server']) == dict

Servers = {}
Ports = {}

# Create a port-map relation
for name in config['server']:
    server = config['server'][name]
    assert 'local' in server
    assert 'local_port' in server
    assert 'destination' in server
    assert 'destination_port' in server
    assert 'match' in server
    assert 'failover' in server
    assert 'failover_port' in server
    assert name not in Servers
    Servers[name] = server
    connection_name = server['local']+':' + str(server['local_port'])
    if connection_name not in Ports:
        Ports[connection_name] = {}
    Ports[connection_name][server['match']] = name


# Configurations has been loaded.
# Ports:
#   PORT: {
#       'MATCH': 'SERVER_NAME'
#   }


class ForwardServer():
    def __init__(self, instance, address, f2048b=b''):
        super().__init__()
        try:
            conn = socket.socket()
            conn.connect(address)
            if f2048b:
                conn.send(f2048b)
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

        self.worker_send.setDaemon(True)
        self.worker_send.start()
        self.worker_recv.setDaemon(True)
        self.worker_recv.start()

        print('Forward:', instance, address, f2048b)

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


class Router():
    def __init__(self, routerID, instance, config):
        super().__init__()
        self.routerID = routerID
        self.instance = instance
        self.config = config
        self.thread = threading.Thread(target=self.match)
        self.thread.setDaemon(True)
        self.thread.name = 'Router ID = '+self.routerID
        self.thread.start()

    def match(self):
        # Read first 2048 bit
        f2048b = self.instance.recv(2048)
        # Attempt to decode
        try:
            f2048decode = f2048b.decode()
        except:
            # Fails to decode
            self.final = ForwardServer(self.instance, (Servers[list(self.config.values())[
                0]]['failover'], Servers[list(self.config.values())[0]]['failover_port']), f2048b)
            #    Use the failover settings of the first in the dict.
            return

        # Attempt to match
        for name in self.config:
            if name in f2048decode:
                # Response a HTTP request back to the client
                self.instance.send(b'HTTP/1.1 200 OK\nServer: '+name.encode()+b'\r\n\r\n')
                self.final = ForwardServer(
                    self.instance, (Servers[self.config[name]]['destination'], Servers[self.config[name]]['destination_port']))
                print('Matched to:', self.config[name])
                return

        # No match: Failover
        self.final = ForwardServer(self.instance, (Servers[list(self.config.values())[
            0]]['failover'], Servers[list(self.config.values())[0]]['failover_port']), f2048b)


class Handle:
    def __init__(self, config, bind):
        self.config = config
        self.socket = socket.socket()
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
            routerID = secrets.token_hex(4)
            self.workers[routerID] = Router(routerID, instance, self.config)


Handlers = {}

for address in Ports:
    # Handle match
    Handlers[address] = Handle(
        Ports[address], (address.split(':')[0], int(address.split(':')[1])))

while True:
    pass
