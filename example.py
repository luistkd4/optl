from typing import Optional
from flask import Flask
import flask
from opentelemetry import context
from opentelemetry import propagate
from opentelemetry.trace.propagation import SPAN_KEY
import requests
from azure.servicebus import ServiceBusClient, ServiceBusMessage
from time import sleep

from opentelemetry import trace
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

#propagation
from opentelemetry.trace import propagation

#b3
from opentelemetry.propagate import set_global_textmap, extract, inject
from opentelemetry.propagators.b3 import B3Format
from werkzeug.datastructures import Headers
#PROPAGATOR = propagate.set_global_textmap(B3Format())
PROPAGATOR = propagate.get_global_textmap()


#Service_BUS
CONNECTION_STR = "Endpoint=sb://xxx"
QUEUE_NAME = "event"

def send_single_message(sender):
    # create a Service Bus message
    message = ServiceBusMessage("Single Message")
    # send the message to the queue
    sender.send_messages(message)
    print("Sent a single message")

servicebus_client = ServiceBusClient.from_connection_string(conn_str=CONNECTION_STR, logging_enable=True)

trace.set_tracer_provider(
TracerProvider(
        resource=Resource.create({SERVICE_NAME: "my-helloworld-service"})
    )
)

jaeger_exporter = JaegerExporter(
    # configure agent
    agent_host_name='localhost',
    agent_port=6831,
    # optional: configure also collector
    # collector_endpoint='http://localhost:14268/api/traces?format=jaeger.thrift',
    # username=xxxx, # optional
    # password=xxxx, # optional
    # max_tag_value_length=None # optional
)

trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(jaeger_exporter)
)

PORT = 8000
app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()

tracer = trace.get_tracer(__name__)

def get_header_from_flask_request():
    return flask.request.headers.get_all

def set_header_into_requests_request(request: requests.Request,ey: str, value: str):
    request.headers['key'] = value


@app.route("/hello")
def hello():
   #print(flask.request.headers.get_all)
   #print(flask.request)  
   #extract
   CONTEXT = PROPAGATOR.extract(
      flask.request.headers.get_all,
      flask.request
   )
   #inject
   #request_to_downstream = requests.Request(
   #     "GET", "http://httpbin.org/get"
   #  )  

   with tracer.start_as_current_span('Request'):
      requests.get("https://www.globalgetnet.com")
   with tracer.start_as_current_span('Service-BUS'):
      span = trace.get_current_span()
      span.set_attribute("bus.name", "tracing.servicebus.windows.net")
      span.add_event("event message",{"event_attributes": 1, "TESTE":2})
      servicebus_client = ServiceBusClient.from_connection_string(conn_str=CONNECTION_STR, logging_enable=True)
      with servicebus_client:
          sender = servicebus_client.get_queue_sender(queue_name=QUEUE_NAME)
          with sender:
              send_single_message(sender)   

   sleep(30 / 1000)


   return "hello world\n"

if __name__ == "__main__":
   app.run(host="0.0.0.0", port=PORT)
