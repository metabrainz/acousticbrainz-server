from flask_uwsgi_websocket import GeventWebSocket
import json

web_socket = None
ws_clients = {}


def init_websocket(app):
    global web_socket
    web_socket = GeventWebSocket(app)

    @web_socket.route('/websocket')
    def ws_connect(ws):
        ws_clients[ws.id] = ws

        while True:
            msg = ws.receive()
            if msg is not None:
                continue
            else:
                break

        del ws_clients[ws.id]


def ws_broadcast(message):
    """Sends specified message to all clients connected via WebSocket."""
    message = json.dumps(message)
    for id in ws_clients:
        ws_clients[id].send(message)
