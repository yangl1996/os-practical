import requests
import json

APIROOT = 'http://192.168.1.83:5050/api/v1/scheduler'
STREAM = None
CPU_REQ = 0.1
MEM_REQ = 32

def subscribe():
    payload = {'type': 'SUBSCRIBE',
               'subscribe': {
                   'framework_info': {
                       'user': 'testuser',
                       'name': 'testframework'
                       }
                   }
               }
    r = requests.post(APIROOT, json=payload, stream=True)
    return r

def get_event(res):
    res_len = int(res.raw.readline().decode())
    res_body = res.raw.read(res_len).decode()
    return json.loads(res_body)

def accept_offer(offer):
    print("Accept the offer")
    # tell the master that we accept the offer here
    # we omit the remaining part here

def on_offers(evt):
    for offer in evt['offers']['offers']:
        resource = {}
        for re in offer['resources']:
            # we only care about cpu and mem
            if re['name'] == 'cpus':
                resource['cpus'] = re['scalar']['value']
            elif re['name'] == 'mem':
                resource['mem'] = re['scalar']['value']
        print("Offered: ", resource)
        if resource['cpus'] < CPU_REQ or resource['mem'] < MEM_REQ:
            # ignore the offer if not enough resource
            continue
        accept_offer(offer)


def handle_event(evt):
    etype = evt['type']
    if etype == 'SUBSCRIBED':
        print("Subscribed to event stream.")
    elif etype == 'OFFERS':
        on_offers(evt)
    elif etype == 'HEARTBEAT':
        print("Received heartbeat from master")


def start_conn():
    global STREAM
    req = subscribe()
    STREAM = req.headers['Mesos-Stream-Id']
    while True:
        event = get_event(req)
        handle_event(event)


start_conn()
