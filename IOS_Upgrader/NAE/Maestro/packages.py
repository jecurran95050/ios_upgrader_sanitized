from IOS_Upgrader.NAE.Maestro.SSH_Health_Check import SSH_healthy

__author__ = 'jacurran'

##################################################

def install_mode_upgrade_prep(network_device,
                              file_source="XXXXXXXXX://XXXXX/ftp/images"):
    HALT = False
    error = False

    if not SSH_healthy(network_device.name, auth_keychain=network_device.auth_keychain):
        error = "SSH v2 is not functioning on {}.".format(network_device.name)
        HALT = True

    if not HALT:
        try:
            network_device.login()
        except:
            error = "SSH v2 is not functioning on {}.".format(network_device.name)
            HALT  = True
        else:
            network_device.get_prompt()
            if "#" not in network_device.prompt:
                error = "{} has ARBAC issues, logon was not granted enable mode.".format(network_device.name)
                HALT = True

    if not HALT:
        network_device.determine_media()

        if not network_device.new_file_there(the_file=network_device.new_IOS_file,
                                             location=network_device.primary_copy_location):
            network_device.install_mode_software_clean()

        IOS_copy_error = network_device.file_upload(new_file=network_device.new_IOS_file,
                                                    md5_hash_provided=network_device.IOS_md5_hash,
                                                    file_source=file_source)
        if IOS_copy_error:
            error = "There was an issue copying IOS {} on device {}".format(network_device.new_IOS_file,
                                                                            network_device.name)
            HALT = True

    if not HALT and network_device.new_FPD_file:

        FPD_copy_error = network_device.file_upload(new_file=network_device.new_FPD_file,
                                                    md5_hash_provided=network_device.FPD_md5_hash,
                                                    file_source=file_source)
        if FPD_copy_error:
            error = "There was an issue copying FPD {} on device {}".format(network_device.new_FPD_file,
                                                                            network_device.name)
            HALT = True

    if not HALT:
        network_device.install_mode_no_manual()
        network_device.backup_run_config()
    network_device.logout()

    if error:
        return error
    elif network_device.new_FPD_file:
        return "Device {}\n\nSuccessfully prepped for:\nIOS {} &\nFPD file {}"\
            .format(network_device.name,
                    network_device.new_IOS_file,
                    network_device.new_FPD_file)
    else:
        return "Device {}\n\nSuccessfully prepped for:\nIOS {}"\
            .format(network_device.name,
                    network_device.new_IOS_file)

##################################################
