from IOS_Upgrader.NAE.Factory import Sales_Order
from IOS_Upgrader.NAE.Factory.Get_HW_SW import Get_HW_SW, All_Known_HW_PIDs
from IOS_Upgrader.NAE.Factory.Inventory import IOS_NetDev
from IOS_Upgrader.NAE.Maestro.SSH_Health_Check import SSH_healthy
from IOS_Upgrader.NAE.Jedi.consoles import lifeline_succeeded
import time

__author__ = 'jacurran'

##################################################

def reload_IOS(hostname, auth_keychain, design_tuple, LD=False):

    HALT = False
    result = ""

    try:
        HW_PID, Sup_PID, current_IOS = Get_HW_SW(hostname, auth_keychain)
    except:
        HW_PID = "SNMP_ERROR"
        Sup_PID = "SNMP_ERROR"
        current_IOS = "SNMP_ERROR"

    if not auth_keychain:
        result = "No auth keychain provided, aborting reload job for {}".format(hostname)

    elif HW_PID == "SNMP_ERROR":
        result = "SNMPv3 is not functioning on {}, please correct.".format(hostname)

    elif not design_tuple:
        result = "Could not find a Maestro compatible design standard for device:\n{}.".format(hostname)

    else:
        recommended_IOS_file = design_tuple[0]
        LD_IOS_file = design_tuple[6]

        if LD:
            network_device = Sales_Order.specs(name=hostname,
                                               auth_keychain=auth_keychain,
                                               HW_PID=HW_PID,
                                               Sup_PID=Sup_PID,
                                               current_IOS_file=current_IOS,
                                               new_IOS_file=LD_IOS_file,
                                               new_FPD_file=design_tuple[8])

        else:
            network_device = Sales_Order.specs(name=hostname,
                                               auth_keychain=auth_keychain,
                                               HW_PID=HW_PID,
                                               Sup_PID=Sup_PID,
                                               current_IOS_file=current_IOS,
                                               new_IOS_file=recommended_IOS_file,
                                               new_FPD_file=design_tuple[2])

        if network_device.current_IOS_file == "packages.conf" and network_device.install_mode_correct_IOS():
            result = "\n{} is already running {}, aborting!".format(hostname, network_device.new_IOS_file)
            HALT = True

        elif network_device.current_IOS_file == network_device.new_IOS_file:
            result = "Device is already running {}, aborting!".format(network_device.new_IOS_file)
            HALT = True

        if not HALT:
            if not SSH_healthy(network_device.name,auth_keychain=auth_keychain):
                HALT = True

        if not HALT:
            try:
                network_device.login()
            except:
                result = "SSH v2 is not functioning on {}.".format(network_device.name)
                HALT = True
            else:
                network_device.get_prompt()
                if "#" not in network_device.prompt:
                    result = "{} has ARBAC issues, logon was not granted enable mode.".format(network_device.name)
                    HALT = True

        if not HALT:
            network_device.determine_media()

            IOS_prestaged = True
            for location in network_device.media_list:
                if not network_device.new_file_there(the_file=network_device.new_IOS_file,
                                                     location=location):
                    IOS_prestaged = False

            if not IOS_prestaged:
                result = "New IOS file {}\nis not fully pre-staged on device {}!\nAborting...".format(
                    network_device.new_IOS_file,network_device.name)
                HALT = True

        if not HALT and network_device.modular_cmd:
            network_device.get_show_mod(stage="pre")

        if not HALT:
            network_device.get_neighbors()
            time.sleep(5)
            network_device.save_config()
            time.sleep(5)

            if network_device.current_IOS_file == "packages.conf":
                print "Activating new IOS on {}.".format(network_device.name)
                network_device.install_mode_software_install()
                print "Reloading {} now.".format(network_device.name)
                network_device.logout(quiet=True)  # Install mode won't reload the device until Paramiko logs out

            else:
                print "Reloading {} now!".format(network_device.name)
                network_device.reload()

            time.sleep(180)

            if not network_device.is_alive():
                for neighbor_device in network_device.neighbors.keys():
                    HW_PID, Sup_PID, current_IOS = Get_HW_SW(neighbor_device, auth_keychain)

                    if HW_PID in All_Known_HW_PIDs:
                        neighbor = IOS_NetDev(name=neighbor_device,auth_keychain=auth_keychain)

                        try:
                            neighbor.login()
                        except:
                            break
                        else:
                            neighbor.get_prompt()
                            if "#" not in neighbor.prompt:
                                break

                        neighbor.get_errdisabled_ints()
                        neighbor_Xconnect_list = network_device.neighbors[neighbor.name]

                        restore_these_ints = []
                        for neighbor_Xconnect in neighbor_Xconnect_list:
                            if neighbor_Xconnect in neighbor.err_dis_ints_list:
                                restore_these_ints.append(neighbor_Xconnect)

                        if restore_these_ints:
                            neighbor.restore_errdisabled_ints(restore_list=restore_these_ints)

                        neighbor.logout()

            while not network_device.is_alive() and network_device.reload_completion_check_cycles > 0:
                time.sleep(15)
                network_device.reload_completion_check_cycles -= 1
                network_device.is_alive()

            if not network_device.is_alive():
                result = "{} did not come back online.".format(network_device.name)
                HALT = True

        if not HALT:
            time.sleep(60)
            if not SSH_healthy(network_device.name, auth_keychain=auth_keychain):
                if not lifeline_succeeded(network_device.name, auth_keychain=auth_keychain):
                    result = "Could not access the console.\n{} requires manual SSH Key regeneration."\
                        .format(network_device.name)
                    HALT = True
                else:
                    if not SSH_healthy(network_device.name, auth_keychain=auth_keychain):
                        result = "{} requires manual SSH Key regeneration.".format(network_device.name)
                        HALT = True

        if not HALT:
            network_device.login()
            network_device.get_prompt()
            if "#" not in network_device.prompt:
                result = "{} has ARBAC issues, logon was not granted enable mode.".format(network_device.name)
                network_device.logout()
                HALT = True

        if not HALT:
            if network_device.modular_cmd:
                time.sleep(network_device.reload_finish_time_in_seconds)
            network_device.get_errdisabled_ints()
            if network_device.err_dis_ints_list:
                network_device.restore_errdisabled_ints()
                time.sleep(30)

                network_device.get_errdisabled_ints()
                if network_device.err_dis_ints_list:
                    if result:
                        result += "\n{} has links that are err-disabled."\
                            .format(network_device.name)
                    else:
                        result = "{} has links that are err-disabled."\
                            .format(network_device.name)

        if not HALT and network_device.modular_cmd:
            network_device.get_show_mod(stage="post")
            network_device.find_bad_modules()

            if network_device.modular_issues:
                if result:
                    result += "\nModules on {} that diff from their pre-reload state of:" \
                        .format(network_device.name)
                    for line in network_device.modular_issues:
                        result += "\n{}".format(line)
                else:
                    result = "Modules on {} that diff from their pre-reload state of:" \
                        .format(network_device.name)
                    for line in network_device.modular_issues:
                        result += "\n{}".format(line)

        if not HALT:
            HW_PID, Sup_PID, current_IOS = Get_HW_SW(network_device.name, auth_keychain)
            if HW_PID == "SNMP_ERROR":
                network_device.SNMPv3_config()
                time.sleep(10)

            HW_PID, Sup_PID, current_IOS = Get_HW_SW(network_device.name, auth_keychain)
            if HW_PID == "SNMP_ERROR":
                if result:
                    result += "\nSNMPv3 is not functioning on {} after reload.".format(network_device.name)
                else:
                    result = "SNMPv3 is not functioning on {} after reload.".format(network_device.name)

            network_device.logout()

    return result
