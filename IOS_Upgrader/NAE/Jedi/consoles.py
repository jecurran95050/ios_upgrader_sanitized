from IOS_Upgrader.NAE.Factory.Inventory import IOS_NetDev
from IOS_Upgrader.NAE.Maestro.SSH_Health_Check import SSH_healthy
import time

__author__ = 'jacurran'

##################################################

def lifeline_succeeded(hostname, auth_keychain, debug=False):
    enable_pw_keychain = auth_keychain["enable_pws"]

    HALT = False
    success = False

    if debug:
        quiet_setting = False
    else:
        quiet_setting = True

    if not HALT:
        network_device = IOS_NetDev(hostname, auth_keychain=auth_keychain)
        network_device.get_console_names()
        if debug:
            print network_device.console_list

        if not network_device.console_list:
            if debug:
                print "There are no **** lines which return a ping setup for {}".format(network_device.name)

        for line in network_device.console_list:
            if SSH_healthy(line,auth_keychain=auth_keychain):
                console_line = IOS_NetDev(line,auth_keychain=auth_keychain)
                time.sleep(5)
                console_line.login(quiet=quiet_setting)
                console_line.get_prompt()

                if console_line.prompt == network_device.raw_hostname + ">":
                    #This if condition confirms this is the correct console
                    for enable_pw in enable_pw_keychain:
                        console_line.sendcmd("enable",sleep=2)
                        console_line.sendcmd(enable_pw,sleep=2)
                        console_line.get_prompt()
                        if console_line.prompt == network_device.raw_hostname + "#":
                            break

                if console_line.prompt == network_device.raw_hostname + "#":
                    if debug:
                        print "Successfully entered enable mode on {} using {}" \
                        .format(network_device.raw_hostname, console_line.raw_hostname)
                    console_line.sendcmd("config t")
                    console_line.sendcmd("crypto key generate rsa general-keys mod 1024", sleep=5)
                    console_line.sendcmd("end")
                    console_line.sendcmd("copy running-config startup-config")
                    while not console_line.prompt_back():
                        time.sleep(5)
                    console_line.sendcmd("disable")
                    console_line.logout(quiet=quiet_setting)
                    success = True
                    break

                console_line.logout(quiet=quiet_setting)

    if success:
        return True
    else:
        return False