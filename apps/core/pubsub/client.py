import json
import time
import threading
import logging
from queue import Queue
from time import sleep
from functools import wraps
from google.cloud import pubsub_v1
from google.api_core.exceptions import NotFound, AlreadyExists

class PubSubRPCClient:
    
    def __init__(self, project_id, topic_name, subscription_name):
        self.project_id = project_id
        self.topic_name = topic_name
        self.subscription_name = subscription_name

        self.publisher = pubsub_v1.PublisherClient()
        self.subscriber = pubsub_v1.SubscriberClient()

        topic_path = self.publisher.topic_path(self.project_id, self.topic_name)
        self.subscription_path = self.subscriber.subscription_path(self.project_id, self.subscription_name)

        self.callbacks = {}
        self.response_queue = Queue()

        self.internal_lock = threading.Lock()
        self.callback_exec_complete = threading.Event()
        self.stop_event = threading.Event()
        self.message_counter = 0

        # Create a subscription if it dosen't exist
        try:
            self.subscriber.create_subscription(name=self.subscription_path, topic=topic_path)
        except AlreadyExists:
            pass
        except Exception as ex:
            logging.error(f"Failed to create subscription : {ex}")

        self.thread = threading.Thread(target=self._process_messages)
        self.thread.setDaemon(True)
        self.thread.start()

    def _process_messages(self):
        def callback(message):
            with self.internal_lock:
                try:
                    if not message.data:
                        logging.error("Received an empty Pub/Sub Message")
                        message.ack()
                        return
                    
                    message_data = json.loads(message.data.decode('utf-8'))
                    print("Received Message:", message_data)
                    method_name = message_data.get('method')
                    args = message_data.get('args', [])
                    kwargs = message_data.get('kwargs', {})

                    if method_name in self.callbacks:
                        result = self.callbacks[method_name](*args, **kwargs)
                        response_message = {
                            'result': result,
                            'message_id': message_data.get('message_id')
                        }
                        self.response_queue.put(response_message)
                    else:
                        logging.error(f"Method '{method_name}' not registered.")

                    self.callback_exec_complete.set()
                except json.decoder.JSONDecodeError as e:
                    logging.error(f"Failed to decode JSON message: {e}")
                except UnicodeDecodeError as e:
                    logging.error(f"Failed to decode message data : {e}")

                message.ack()

        self.subscriber.subscribe(self.subscription_path, callback=callback)

        while not self.stop_event.is_set():
            self.stop_event.wait(timeout=0.1)

    def stop_listening(self):
        if self.thread and self.thread.is_alive():
            self.stop_event.set()
            self.thread.join()

    def publish_message(self, method_name, *args, **kwargs):
        with self.internal_lock:
            message_id = f'msg_{self.message_counter}'
            message_payload = {
                'method': method_name,
                'args': args,
                'kwargs': kwargs,
                'message_id': f'msg_{self.message_counter}'
            }
            message_data = json.dumps(message_payload).encode('utf-8')
            future = self.publisher.publish(
                self.publisher.topic_path(self.project_id, self.topic_name),
                data=message_data
            )
            result = future.result()
            self.message_counter += 1

        return message_id, result
    
    def remote_method(self, method_name):
        def decorator(func):
            self.callbacks[method_name] = func

            @wraps(func)
            def wrapper(*args, **kwargs):
                message_id, _ = self.publish_message(method_name, *args, **kwargs)
                self.callback_exec_complete.wait()
                response_message = self.wait_for_response(message_id)
                return response_message.get('result')
            return wrapper
        
        return decorator
    
    def wait_for_response(self, message_id, timeout=100):
        start_time = time.time()
        while time.time() - start_time < timeout:
            response_message = self.response_queue.get()
            if response_message and response_message.get('message_id') == message_id:
                return response_message
            
            sleep(0.1)

        logging.warning(f"Timeout waiting for response for message_id: {message_id}")
        return None
    
    