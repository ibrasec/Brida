# -*- coding: utf-8 -*-
import frida
import codecs
import Pyro4
import sys

reload(sys)   
sys.setdefaultencoding('utf-8')

class Unbuffered(object):
   def __init__(self, stream):
       self.stream = stream
   def write(self, data):
       self.stream.write(data)
       self.stream.flush()
   def writelines(self, datas):
       self.stream.writelines(datas)
       self.stream.flush()
   def __getattr__(self, attr):
       return getattr(self.stream, attr)

@Pyro4.expose
class BridaServicePyro:
    def __init__(self, daemon):
        self.daemon = daemon
    def spawn_application(self,application_id,frida_script,remote):

        self.application_id = application_id
        self.frida_script = frida_script

        if remote == True:
            self.device = frida.get_remote_device()
        else:
            self.device = frida.get_usb_device()

        self.pid = self.device.spawn([self.application_id])

        self.session = self.device.attach(self.pid)

        with codecs.open(self.frida_script, 'r', 'utf-8') as f:
            source = f.read()

        self.script = self.session.create_script(source)
        self.script.load()

        return

    def resume_application(self):

        self.device.resume(self.pid)

        return

    def reload_script(self):

        with codecs.open(self.frida_script, 'r', 'utf-8') as f:
            source = f.read()

        self.script = self.session.create_script(source)
        self.script.load()

        return

    def disconnect_application(self):

        self.device.kill(self.pid)
        return

    def callexportfunction(self, methodName, args):
        method_to_call = getattr(self.script.exports, methodName)

        # Take the Java list passed as argument and create a new variable list of argument
        # (necessary for bridge Python - Java, I think)
        s = []
        for i in args:
            s.append(i)

        return_value = method_to_call(*s)
        return return_value

    @Pyro4.oneway
    def shutdown(self):
        print('shutting down...')
        self.daemon.shutdown()

# Disable python buffering (cause issues when communicating with Java...)
sys.stdout = Unbuffered(sys.stdout)

host = sys.argv[1]
port = int(sys.argv[2])
daemon = Pyro4.Daemon(host=host,port=port)

#daemon = Pyro4.Daemon(host='127.0.0.1',port=9999)
bs = BridaServicePyro(daemon)
uri = daemon.register(bs,objectId='BridaServicePyro')

print("Ready.")
daemon.requestLoop()
