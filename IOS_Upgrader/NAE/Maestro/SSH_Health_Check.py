from IOS_Upgrader.NAE.Factory.Inventory import IOS_NetDev
import threading
import time

__author__ = 'jacurran'

###############################################################################

class myThread(threading.Thread):
    def __init__(self, hostname, auth_keychain):
        threading.Thread.__init__(self)
        self.hostname = hostname
        self.auth_keychain = auth_keychain

    def run(self):
        #insert function here such as Maestro job
        answer = health_test(self.hostname,auth_keychain=self.auth_keychain)
        time.sleep(5)

        if answer == "good":
            self.health = "good"
        else:
            self.health = "bad"

###############################################################################

def health_test(hostname,auth_keychain):
    network_device = IOS_NetDev(name=hostname,auth_keychain=auth_keychain)

    if not network_device:
        return "bad"
    else:
        try:
            network_device.login(quiet=True)
        except:
            return "bad"
        else:
            network_device.get_prompt()
            network_device.logout(quiet=True)
            if network_device.prompt != 'PARAMIKO INCOMPATIBILITY ERROR':
                return "good"
            else:
                return "bad"

###############################################################################

def SSH_healthy(hostname,auth_keychain,debug=False):
    ssh_test = myThread(hostname=hostname,auth_keychain=auth_keychain)
    ssh_test.setDaemon(True)
    ssh_test.start()

    cycles = 18

    while cycles > 0:
        if not ssh_test.isAlive():
            break
        else:
            time.sleep(5)
            cycles -= 1

    if cycles <= 0 and ssh_test.isAlive():
        if debug:
            print "Hung SSH session detected on {}, stopping daemon thread!".format(hostname)
        ssh_test._Thread__stop()
        del ssh_test
        return False

    if ssh_test.health == "good":
        return True
    else:
        return False
