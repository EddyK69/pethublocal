"""
 Test Feeder Generate
"""
import pytest
import json
import sys

sys.path.append('..')
import pethublocal.message as p
import pethublocal.generate as g
import pethublocal as log
from pethublocal.functions import config_load, json_print
from pethublocal.consts import CFG

pethubconfig = config_load()

# Variables to log to console or mqtt
TESTING_MESSAGE = True
TESTING_MQTT = False
hub = 'pethub/hub/'

if TESTING_MQTT and 'MQTTHost' in pethubconfig['config']:
    host = pethubconfig['config']['MQTTHost'] if 'MQTTHost' in pethubconfig['config'] else '127.0.0.1'
    port = pethubconfig['config']['MQTTPort'] if 'MQTTPort' in pethubconfig['config'] else 1883
    log.info('PyTest: Hub Init MQ %s', host)
    import paho.mqtt.client as mq
    mc = mq.Client("Pet-Hub-Test", clean_session=False)
    mc.connect(host, port)


def run_test(name, pethubconfig, topic, mqtt_message):
    log.info('TEST: ' + name)
    mqtt_topic = str(hub + topic)
    log.info('Topic: %s Message: %s', mqtt_topic, mqtt_message)
    result = {}
    if TESTING_MQTT:
        log.info('PyTest: Hub MQTT Publish')
        mqtt_result = mc.publish(mqtt_topic, mqtt_message, 1, False)
        log.info('Pytest: Publish ' + str(mqtt_result))

    if TESTING_MESSAGE:
        result = p.parse_hub(pethubconfig, mqtt_topic, mqtt_message)
        log.info(json_print(result))
    return result


@pytest.fixture
def global_variables():
    pytest.hub = 'H010-0123456'
    pytest.mac = '4444444444444444'
    pytest.devtype = 4               # Device Type 4 = Feeder


def setup_module():
    log.info('setup')


def teardown_module():
    log.info('teardown')
    with open('pethubconfig-updated.json', 'w') as fp:
        json.dump(pethubconfig, fp, indent=4)


# Generate Messages
@pytest.mark.parametrize("test_generate, response", [
    ("Config",      "09 00 00"),  # Config message
    ("Unknown0b",   "0b 00 00"),  # Unknown 0b message
    ("Battery",     "0c 00 00"),  # Battery state change
    ("Boot10",      "10 00 00"),  # Boot message 10
    ("Tags",        "11 00 00"),  # Tag provisioning
    ("Curfew",      "12 00 00"),  # Curfew
    ("PetMovement", "13 00 00"),  # Pet movement in / out cat flap
    ("Boot17",      "17 00 00"),  # Boot message 17
    ("Feeder",      "18 00 00"),  # Feeder message
])
@pytest.mark.pethubgenerate
def test_feeder_generate_ack(global_variables, request, test_generate, response):
    log.info('TEST: ' + request.node.name)
    result = g.generatemessage(pethubconfig, pytest.hub, pytest.devtype, 'Ack', mac=pytest.mac, suboperation=test_generate)
    log.info(json_print(result))
    for topic, message in result.items():
        assert topic == hub + pytest.hub + '/messages/' + pytest.mac
        assert ' 1000 127 00 00 ' in message # Ack message is type '00'
        assert response in message


@pytest.mark.parametrize("test_generate,response", [
    ("Boot9", "09 00 ff"),    # Boot message 09
    ("Boot10", "10 00"),      # Boot message 10
    ("Tags", "11 00 ff"),     # Tag provisioning
    ("Boot17", "17 00 00"),   # Boot message 17
    ("Unknown0b", "0b 00"),   # Unknown 0b message
    ("Battery", "0c 00"),     # Battery state change
])
@pytest.mark.pethubgenerate
def test_catflap_generate_get(global_variables, request, test_generate, response):
    log.info('TEST: ' + request.node.name)
    result = g.generatemessage(pethubconfig, pytest.hub, pytest.devtype, 'Get', mac=pytest.mac, suboperation=test_generate)
    log.info(json_print(result))
    for topic, message in result.items():
        assert topic == hub + pytest.hub + '/messages/' + pytest.mac
        assert ' 1000 127 01 00 ' in message # Ack message is type '00'
        assert response in message


@pytest.mark.pethubgenerate
def test_feeder_generate_settime(global_variables, request):
    log.info('TEST: ' + request.node.name)
    result = g.generatemessage(pethubconfig, pytest.hub, pytest.devtype, 'SetTime', mac=pytest.mac)
    log.info(json_print(result))
    for topic, message in result.items():
        assert topic == hub + pytest.hub + '/messages/' + pytest.mac
        assert ' 1000 127 07 00 ' in message
        assert ' 00 00 00 00 07' in message


# Set Feeder Settings
@pytest.mark.parametrize("test_generate,subop,response", [
    ("SetLeftScale", "10", " 0a e8 03 00 00"),       # Set Left Target Weight
    ("SetRightScale", "25", " 0b c4 09 00 00"),      # Set Right Target Weight
    ("SetBowlCount", "One", " 0c 01 00 00 00"),      # Set Bowl Count
    ("SetBowlCount", "Two", " 0c 02 00 00 00"),      # Set Bowl Count
    ("SetCloseDelay", "Fast", " 0d 00 00 00 00"),    # 0 Seconds
    ("SetCloseDelay", "Normal", " 0d a0 0f 00 00"),  # 4 Seconds "0fa0" = 4000
    ("SetCloseDelay", "Slow", " 0d 20 4e 00 00"),    # 20 Seconds "4e20" = 20000
    ("Set12", "500", " 12 f4 01 00 00"),             # Set Message 12
    ("CustomMode", "Intruder", " 14 00 01 00 00"),   # Set Custom Mode - Intruder
    ("CustomMode", "GeniusCat", " 14 80 00 00 00"),  # Set Custom Mode - Genius Cat Mode
    ("CustomMode", 128,         " 14 80 00 00 00"),  # Set Custom Mode - Genius Cat Mode as int
    ("CustomMode", "128",       " 14 80 00 00 00"),  # Set Custom Mode - Genius Cat Mode as string int
])
@pytest.mark.pethubgenerate
def test_feeder_generate_set_values(global_variables, request, test_generate, subop, response):
    log.info('TEST: ' + request.node.name)
    result = g.generatemessage(pethubconfig, pytest.hub, pytest.devtype, test_generate, mac=pytest.mac, suboperation=subop)
    log.info(json_print(result))
    for topic, message in result.items():
        assert topic == hub + pytest.hub + '/messages/' + pytest.mac
        assert ' 1000 127 09 00 ' in message
        assert response in message


@pytest.mark.parametrize("test_zeroscale,zerovalue,zeroresponse", [
    ("ZeroScale", "Left", "01"),  # Zero Left Scale
    ("ZeroScale", "Right", "02"), # Zero Right Scale
    ("ZeroScale", "Both", "03"),  # Zero Both Scales
])
@pytest.mark.pethubgenerate
def test_feeder_generate_zeroscales(global_variables, request, test_zeroscale, zerovalue, zeroresponse):
    log.info('TEST: ' + request.node.name)
    result = g.generatemessage(pethubconfig, pytest.hub, pytest.devtype, test_zeroscale, mac=pytest.mac, suboperation=zerovalue)
    log.info(json_print(result))
    for topic, message in result.items():
        assert topic == hub + pytest.hub + '/messages/' + pytest.mac
        assert ' 1000 127 0d 00 ' in message
        assert "00 19 00 00 00 03 00 00 00 00 01 " + zeroresponse in message


@pytest.mark.parametrize("test_generate, offset, tag, lockstate, tagstate, response", [
    ("TagProvision", "0", "0123456789", "Normal", "Enabled",        " 01 23 45 67 89 00 03 02 00 00"),
    ("TagProvision", "1", "900.000123456790", "Normal", "Enabled",  " 16 cd 5b 07 00 e1 01 02 01 00"),
    ("TagProvision", "2", "900.000123456792", "Normal", "Disabled", " 18 cd 5b 07 00 e1 01 02 02 01"),
])
@pytest.mark.pethubgenerate
def test_catflap_generate_setvalues(global_variables, request, test_generate, offset, tag, lockstate, tagstate, response):
    log.info('TEST: ' + request.node.name)
    result = g.generatemessage(pethubconfig, pytest.hub, pytest.devtype, test_generate, mac=pytest.mac, offset=offset, tag=tag, lockstate=lockstate, tagstate=tagstate)
    log.info(json_print(result))
    for topic, message in result.items():
        assert topic == hub + pytest.hub + '/messages/' + pytest.mac
        assert ' 1000 127 11 00 ' in message
        assert response in message
