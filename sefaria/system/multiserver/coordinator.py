import json
import uuid

from django.core.exceptions import MiddlewareNotUsed

from sefaria.local_settings import MULTISERVER_ENABLED, MULTISERVER_REDIS_EVENT_CHANNEL, MULTISERVER_REDIS_CONFIRM_CHANNEL

from abstract import MessagingNode

import logging
logger = logging.getLogger(__name__)


class ServerCoordinator(MessagingNode):
    subscription_channels = [MULTISERVER_REDIS_EVENT_CHANNEL]

    def publish_event(self, obj, method, args = None):
        """

        :param obj:
        :param method:
        :param args:
        :return:
        """
        # Check to see if there's any messages in the queue before pushing/popping a new one.
        ## Edge case - needs thought - does the order of operations make for trouble in this case?##
        self.sync()

        payload = {
            "obj": obj,
            "method": method,
            "args": args or [],
            "id": uuid.uuid4()
        }
        msg_data = json.dumps(payload)

        import socket
        import os
        logger.warning("publish_event from {}:{} - {}".format(socket.gethostname(), os.getpid(), msg_data))

        self.redis_client.publish(MULTISERVER_REDIS_EVENT_CHANNEL, msg_data)

        # Since we are subscribed to this channel as well, throw away the message we just sent.
        # It would be nice to assume that nothing new came through in the microseconds that it took to publish ##
        # But the below should insulate against even that case ##
        popped_msg = self.pubsub.get_message()
        while popped_msg:
            if popped_msg["data"] != msg_data:
                logger.warning("Multiserver Message collision!")
                self._process_message(popped_msg)
            popped_msg = self.pubsub.get_message()

    def sync(self):
        msg = self.pubsub.get_message()
        if not msg or msg["type"] == "subscribe":
            return

        if msg["type"] != "message":
            logger.error("Surprising redis message type: {}".format(msg["type"]))

        self._process_message(msg)
        self.sync()  # While there are still live messages, keep processing them.

    def _process_message(self, msg):
        """
        :param msg: JSON encoded message.
         Expecting a message that looks like this:
         {'channel': 'msync',
          'data': '!!!!!!!!!',
          'pattern': None,
          'type': 'message',
         }

        :return:
        """


        # A list of all of the objects that be referenced
        from sefaria.model import library
        import sefaria.system.cache as scache
        import sefaria.model.text as text
        import sefaria.model.topic as topic

        import socket
        import os
        host = socket.gethostname()
        pid = os.getpid()
        logger.info("_process_message in {}:{} - {}".format(host, pid, msg["data"]))

        data = json.loads(msg["data"])

        obj = locals()[data["obj"]]
        method = getattr(obj, data["method"])

        try:
            method(*data["args"])

            confirm_msg = {
                'event_id': data["id"],
                'host': host,
                'pid': pid,
                'status': 'success'
            }

        except Exception as e:
            confirm_msg = {
                'event_id': data["id"],
                'host': host,
                'pid': pid,
                'status': 'error',
                'error': e.message
            }

        # Send confirmation
        msg_data = json.dumps(confirm_msg)
        logger.info("sending confirm from {}:{} - {}".format(host, pid, msg["data"]))
        self.redis_client.publish(MULTISERVER_REDIS_CONFIRM_CHANNEL, msg_data)


class MultiServerEventListenerMiddleware(object):
    """
    """
    delay = 0  # Will check for library updates every X requests.  0 means every request.

    def __init__(self):
        if not MULTISERVER_ENABLED:
            raise MiddlewareNotUsed
        self.req_counter = 0

    def process_request(self, request):
        if self.req_counter == self.delay:
            server_coordinator.sync()
            self.req_counter = 0
        else:
            self.req_counter += 1

        return None

server_coordinator = ServerCoordinator() if MULTISERVER_ENABLED else None