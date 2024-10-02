from IOS_Upgrader.NAE.Factory import Sales_Order
from IOS_Upgrader.NAE.Factory.Get_HW_SW import Get_HW_SW
from Prep_Work import IOS_upgrade_prep, ROMMON_upgrade_prep
from packages import install_mode_upgrade_prep

__author__ = 'jacurran'

##################################################

def IOS_Maestro(hostname,
                auth_keychain,
                design_tuple,
                LD=False,
                CR=True,
                file_source="************://*****/***/******"):
    result = ""
    sufficient_ROMMON = True

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

        if current_IOS == LD_IOS_file and LD:
            result = "Device {}:\nCurrently running Limited Deployment IOS:\n{}".format(hostname,LD_IOS_file)

        elif current_IOS == recommended_IOS_file and not LD:
            result = "Device {}:\nCurrently running recommended IOS:\n{}".format(hostname,recommended_IOS_file)

        else:
            if not LD and not CR:
                result = "IOS Upgrade Required, will use:\n{}\nOnce your CR is approved.".format(recommended_IOS_file)

            elif LD and not CR:
                if LD_IOS_file:
                    result = "IOS Upgrade Required, will use LD image:\n{}\nOnce your CR is approved.".format(LD_IOS_file)
                else:
                    result = "This device is flagged as LD but there is currently no approved LD image."+\
                             "\nPlease consult with the design team."

            elif LD and CR and LD_IOS_file:
                intro = "This device is flagged as limited deployment."+\
                        "\nIOS Selected:\n{}".format(LD_IOS_file)

                network_device = Sales_Order.specs(name=hostname,
                                                   auth_keychain=auth_keychain,
                                                   HW_PID=HW_PID,
                                                   Sup_PID=Sup_PID,
                                                   current_IOS_file=current_IOS,
                                                   new_IOS_file=LD_IOS_file,
                                                   IOS_md5_hash=design_tuple[7],
                                                   new_FPD_file=design_tuple[8],
                                                   FPD_md5_hash=design_tuple[9],
                                                   ROMMON_file=design_tuple[4],
                                                   ROMMON_md5_hash=design_tuple[5])

                if network_device.ROMMON_file:
                    sufficient_ROMMON = network_device.ROMMON_Compare()


                if not sufficient_ROMMON:
                    result = ROMMON_upgrade_prep(network_device=network_device,
                                                 file_source=file_source)

                elif current_IOS == "packages.conf" and network_device.install_mode_correct_IOS():
                    result = "Device {}:\nIs using install mode." \
                             "\nCurrently running Limited Deployment IOS:\n{}".format(hostname,LD_IOS_file)

                elif current_IOS == "packages.conf" and not network_device.install_mode_correct_IOS():
                    result = install_mode_upgrade_prep(network_device=network_device,
                                                       file_source=file_source)
                    result = intro + "\n\n" + result

                else:
                    result = IOS_upgrade_prep(network_device=network_device,
                                              file_source=file_source)
                    result = intro+"\n\n"+result


            elif CR:
                intro = "IOS Selected:\n{}.".format(recommended_IOS_file)

                network_device = Sales_Order.specs(name=hostname,
                                                   auth_keychain=auth_keychain,
                                                   HW_PID=HW_PID,
                                                   Sup_PID=Sup_PID,
                                                   current_IOS_file=current_IOS,
                                                   new_IOS_file=recommended_IOS_file,
                                                   IOS_md5_hash=design_tuple[1],
                                                   new_FPD_file=design_tuple[2],
                                                   FPD_md5_hash=design_tuple[3],
                                                   ROMMON_file=design_tuple[4],
                                                   ROMMON_md5_hash=design_tuple[5])

                if network_device.ROMMON_file:
                    sufficient_ROMMON = network_device.ROMMON_Compare()

                if not sufficient_ROMMON:
                    result = ROMMON_upgrade_prep(network_device=network_device,
                                                 file_source=file_source)

                elif current_IOS == "packages.conf" and network_device.install_mode_correct_IOS():
                    result = "Device {}:\nIs using install mode." \
                             "\nCurrently running recommended IOS:\n{}".format(hostname,recommended_IOS_file)

                elif current_IOS == "packages.conf" and not network_device.install_mode_correct_IOS():
                    result = install_mode_upgrade_prep(network_device=network_device,
                                                       file_source=file_source)
                    result = intro + "\n\n" + result

                else:
                    result = IOS_upgrade_prep(network_device=network_device,
                                              file_source=file_source)
                    result = intro+"\n\n"+result

    return result

##################################################

