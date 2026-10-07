import ssl, paho.mqtt.client as mqtt

def on_connect(c, u, f, rc):
    print("rc =", rc)
    c.subscribe("device/03900D5B2403257/report")

def on_message(c, u, msg):
    print(msg.payload[:300])

c = mqtt.Client()
c.username_pw_set("bblp", "ac5a6ac3")
c.tls_set(cert_reqs=ssl.CERT_NONE)
c.tls_insecure_set(True)
c.on_connect = on_connect
c.on_message = on_message
c.connect("192.168.2.4", 8883, 60)
c.loop_forever()