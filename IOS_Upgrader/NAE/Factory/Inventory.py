import paramiko
import time
import commands
from Get_HW_SW import sup_OID_list,Valid_Sup_PIDs
from subprocess import call, PIPE, STDOUT

__author__ = 'jacurran'

##################################################

Stack_OID_list = ["mib-2.47.1.1.1.1.2.1001",
                  "mib-2.47.1.1.1.1.2.2001",
                  "mib-2.47.1.1.1.1.2.3001",
                  "mib-2.47.1.1.1.1.2.4001",
                  "mib-2.47.1.1.1.1.2.5001",
                  "1.3.6.1.2.1.47.1.1.1.1.13.2",
                  "1.3.6.1.2.1.47.1.1.1.1.13.3",
                  "1.3.6.1.2.1.47.1.1.1.1.13.4",
                  "1.3.6.1.2.1.47.1.1.1.1.13.5",
                  "1.3.6.1.2.1.47.1.1.1.1.13.6"]

##################################################

class IOS_NetDev:
    """ Generic Network Device """

    # This allows for the submission of all possible attribute values.
    # Most device types represented by the child classes won't need them all.
    # Child classes will only forward the relevant ones here.
    # Non-relevant attributes will receive their default values.
    def __init__(self, name,
                 auth_keychain,
                 HW_PID="",
                 Sup_PID="",
                 current_IOS_file="",
                 new_IOS_file="",
                 IOS_md5_hash="",
                 new_FPD_file="",
                 FPD_md5_hash="",
                 ROMMON_file="",
                 ROMMON_md5_hash=""):

        self.simulation = False

        self.name = name
        self.loggedin = False
        self.auth_keychain = auth_keychain

        self.media_list = ["flash:"]
        self.removable_flash_list = []

        self.prime_boot_loc = "flash:"
        self.sec_boot_loc = None
        self.boot_statement_prefix = "boot system "
        self.single_boot_statement = False

        self.new_IOS_file = new_IOS_file
        self.IOS_md5_hash = IOS_md5_hash
        self.new_FPD_file = new_FPD_file
        self.FPD_md5_hash = FPD_md5_hash
        self.ROMMON_file = ROMMON_file
        self.ROMMON_md5_hash = ROMMON_md5_hash

        self.current_IOS_file = current_IOS_file
        self.primary_copy_location = None
        self.available_media = []
        self.prompt = ""
        self.stack_size = 0
        self.Sup_num = 0
        self.sup_OID_list = sup_OID_list
        self.HW_PID = HW_PID
        self.Sup_PID = Sup_PID
        self.enable_mode = True

        self.distance = -1
        self.reload_cmd_list = ["reload"]
        self.SSH_HUNG = False
        self.slice_points=(0,0)
        self.ROMMON_search_value = "THIS_WILL_BE_REPLACED_AT_CHILD_CLASS_LEVEL"

        self.Non_Sup_ROMMON_OID = "1.3.6.1.2.1.47.1.1.1.1.9.1000"
        self.file_ver = ""
        self.rommon_ver_list = []

        self.raw_hostname = ""

        self.reload_finish_time_in_seconds = 1
        self.reload_completion_check_cycles = 100
        self.console_list = []
        self.remove_cisco_com()

        self.modular_safe_words = []
        self.modular_cmd = ""
        self.modular_pre = []
        self.modular_post = []
        self.modular_issues = []

        self.modular_sw_ver_OID = ""
        self.modular_sw_ver_OID_alt = ""

        self.err_dis_ints_list = []
        self.all_cdp_ints = []
        self.neighbors = {}

    def SNMP_OS_Call(self, oid):
        OS_Call = commands.getoutput(
            '/usr/bin/snmpbulkwalk -v3 -l authNopriv -u {} -a SHA -A {} {} {}'
                .format(self.auth_keychain["SNMPv3_username"],self.auth_keychain["SNMPv3_password"],self.name,oid))
        return OS_Call

    def SNMPv3_config(self):
        if self.loggedin:
            self.sendcmd("config term")
            self.sendcmd("no snmp-server")
            self.sendcmd("snmp-server group XXXXXXXXXXXXX v3 auth"
                         " read XXXXXX write XXXXXXXX access XX")
            self.sendcmd("snmp-server user {} XXXXXXXXXX v3 auth"
                         " sha {} priv aes 128 {}"
                         .format(self.auth_keychain["SNMPv3_username"],
                                 self.auth_keychain["SNMPv3_password"],
                                 self.auth_keychain["SNMPv3_AES_password"]))
            self.sendcmd("end")
            self.sendcmd("copy run start")


    def get_stack_num(self):
        stack_num = 0
        if "3750" in self.HW_PID:
            for OID in Stack_OID_list:
                result = self.SNMP_OS_Call(OID).split()[-1][1:-1]
                if "3750" in result:
                    stack_num += 1
            self.stack_size = stack_num
        elif "C3850" in self.HW_PID:
            for OID in Stack_OID_list:
                result = self.SNMP_OS_Call(OID)
                if "C3850" in result:
                     stack_num += 1
            self.stack_size = stack_num

    def get_sup_num(self):
        self.Sup_num = 0
        for OID in sup_OID_list:
            result = self.SNMP_OS_Call(OID)
            if self.Sup_PID in result:
                self.Sup_num += 1

    def login(self, quiet=False):
        if not self.loggedin:
            username = self.auth_keychain["username_***"]
            password = self.auth_keychain["password_***"]

            # Create instance of SSHClient object
            self.ssh = paramiko.SSHClient()

            # Automatically add untrusted hosts (make sure okay for security policy in your environment)
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # initiate SSH connection
            self.ssh.connect(self.name, username=username, password=password, look_for_keys=False, allow_agent=False)

            # Use invoke_shell to establish an 'interactive session'
            self.remote_conn = self.ssh.invoke_shell()
            self.loggedin = True
            time.sleep(2)

            self.remote_conn.send("\r\r")
            ####  <<<----  This "\r\r" is why we couldn't use NetMiko for our console servers.

            if self.remote_conn.recv_ready():
                self.remote_conn.recv(100000)

            self.CS_menu_check()

            self.sendcmd("terminal length 0\n", buff=100000)

            if not quiet:
                print "Login to %s successful." % self.name

        else:
            if not quiet:
                print "You are already logged into %s." % self.name

    def logout(self, quiet=False):
        if self.loggedin:
            self.ssh.close()
            self.loggedin = False
            if not quiet:
                print "Successfully logged out of %s." % self.name


    def sendcmd(self, command, sleep=1, buff=100000):
        # Now let's try to send the router a command
        if self.loggedin:
            self.SSH_HUNG = False
            if not self.SSH_HUNG:
                self.remote_conn.send(command + "\n")
                # Wait for the command to complete
                time.sleep(sleep)

                if not self.remote_conn.recv_ready():
                    time.sleep(5)
                    if not self.remote_conn.recv_ready():
                        self.SSH_HUNG = True

            if not self.SSH_HUNG:
                self.output = self.remote_conn.recv(buff).split("\r\n")

                while True:
                    try:
                        index = self.output.index('')
                        del self.output[index]
                    except:
                        break

            elif self.SSH_HUNG:
                self.output = ["PARAMIKO INCOMPATIBILITY ERROR"]

            return self.output

    def get_prompt(self):
        if self.loggedin:
            self.prompt = self.sendcmd("")[0].strip()
            self.prompt = self.sendcmd("")[0].strip()
            self.prompt = self.sendcmd("")[0].strip()

    def CS_menu_check(self):
        prompt = self.sendcmd("")[0].strip()
        del prompt
        prompt = self.sendcmd("")[0].strip()
        if prompt in ["Selection:"]:
            self.sendcmd("x")

    def determine_media(self):
        if self.loggedin and self.media_list:
            available_media = self.media_list[:]
            for location in self.removable_flash_list:
                result = self.sendcmd("dir {}".format(location),sleep=1)
                for line in result:
                    if "bytes" in line:
                        available_media.append(location)
            primary_copy_location = available_media.pop(0)
            self.available_media = available_media
            self.primary_copy_location = primary_copy_location

    def new_file_there(self, location, the_file):
        if self.loggedin:
            file_there = False
            result = self.sendcmd("dir {}".format(location))
            for line in result:
                if the_file in line:
                    file_there = True
            if file_there:
                return True
            else:
                return False

    def valid_md5(self,location,the_file,md5_hash):
        if self.loggedin:
            md5_calc_done = False
            valid_md5 = False
            result = self.sendcmd("verify /md5 {}/{}".format(location, the_file), sleep=10)
            while not md5_calc_done:
                result2 = self.sendcmd("")
                result.extend(result2)
                for line in result:
                    if "Done!" in line:
                        md5_calc_done = True
                    if md5_hash in line:
                        valid_md5 = True
                        md5_calc_done = True
            if valid_md5:
                return True
            else:
                return False
        else:
            return False

    def del_new_file(self, location, the_file=""):
        if not the_file:
            the_file = self.new_IOS_file
        if self.loggedin:
            result = self.sendcmd("del {}{}".format(location, the_file))
            del result
            result = self.sendcmd("")
            del result
            result = self.sendcmd("")
            del result
            result = self.sendcmd("")
            del result

    def IOS_reclaim_space(self,location):
        if self.loggedin:
            result = self.sendcmd("dir {}".format(location))
            file_list = [line.split()[-1] for line in result]
            file_list = file_list[:-2]

            for file in file_list:
                if file != self.new_IOS_file \
                        and file != self.current_IOS_file \
                        and ".bin" in file:
                    if self.simulation:
                        print "{}{} will be deleted".format(location, file)
                    elif not self.simulation:
                        self.sendcmd("del {}{}".format(location,file))
                        self.sendcmd("")
                        self.sendcmd("")

    def fpd_reclaim_space(self,location):
        if self.loggedin:
            result = self.sendcmd("dir {}".format(location))
            file_list = [line.split()[-1] for line in result]
            file_list = file_list[:-2]

            for file in file_list:
                if file != self.new_FPD_file \
                        and "fpd" in file:
                    if self.simulation:
                        print "{}{} will be deleted".format(location, file)
                    elif not self.simulation:
                        self.sendcmd("del {}{}".format(location,file))
                        self.sendcmd("")
                        self.sendcmd("")

    def ROMMON_reclaim_space(self, location):
        self.reclaim_space(location=location,search_term=self.ROMMON_search_value)

    def reclaim_space(self, location, search_term):
        if self.loggedin:
            result = self.sendcmd("dir {}".format(location))
            file_list = [line.split()[-1] for line in result]
            file_list = file_list[:-2]

            for file in file_list:
                if search_term in file:
                    if self.simulation:
                        print "{}{} will be deleted".format(location, file)
                    elif not self.simulation:
                        self.sendcmd("del {}{}".format(location,file))
                        self.sendcmd("")
                        self.sendcmd("")

    def prompt_back(self):
        if self.loggedin and self.prompt:
            result = self.sendcmd("")
            if not self.prompt:
                self.get_prompt()
            if result:
                if result[0].strip() == self.prompt:
                    return True
                else:
                    return False
            else:
                return False

    def scp_copy_file(self, source, destination, the_file):
        # Needed to build copy command for SCP syntax.

        username = self.auth_keychain["username_***"]
        password = self.auth_keychain["password_***"]

        copy_command = "copy scp://{}:{}@{}/{} {}".format(username, password, source, the_file, destination)
        # Use the copy_file method and return True/False to signify if there was an error.
        copy_error = self.copy_file(destination, the_file, copy_command)
        return copy_error

    def ftp_copy_file(self, source, destination, the_file):
        # Converts ENS server file structure from SCP syntax to FTP syntax.
        source_server = source.split(":")[0]
        source_dir = source.split(":")
        if source_dir[-1] == "":
            source_dir = source_dir[:-1]
        source_dir = source_dir[-1].split("/")[-1]
        source = "{}/{}".format(source_server,source_dir)

        copy_command = "copy ftp://{}/{} {}".format(source, the_file, destination)
        # Use the copy_file method and return True/False to signify if there was an error.
        copy_error = self.copy_file(destination, the_file, copy_command)
        return copy_error

    def local_copy_file(self, source, destination, the_file):
        copy_command = "copy {}{} {}".format(source, the_file, destination)
        # Use the copy_file method and return True/False to signify if there was an error.
        copy_error = self.copy_file(destination, the_file, copy_command)
        return copy_error

    def copy_file(self, destination, the_file, copy_command):
        prompt_back_yet = False
        access_issue = False

        if self.loggedin:
            if not self.prompt:
                self.get_prompt()

            self.sendcmd(copy_command)
            self.sendcmd("")
            self.sendcmd("")
            time.sleep(5)

            if self.prompt_back():
                if not self.new_file_there(location=destination,the_file=the_file):
                    access_issue = True

            while not access_issue and not prompt_back_yet:
                time.sleep(5)
                prompt_back_yet = self.prompt_back()

            if access_issue:
                return True
            elif not self.new_file_there(location=destination,the_file=the_file):
                return True
            else:
                return False

    def backup_run_config(self, location=None):
        if not location:
            location = self.prime_boot_loc
        if self.loggedin:
            result = self.sendcmd("copy running-config {}".format(location))
            del result
            result = self.sendcmd("running-config")
            del result
            result = self.sendcmd("",sleep=3)
            del result
            result = self.sendcmd("")
            del result

    def get_boot_var_deletes(self):
        if self.loggedin:
            while not self.prompt_back():
                time.sleep(5)
            boot_vars = self.sendcmd("show run | i boot system",sleep=15)[1:-1]
            deletions = ["no "+boot_var for boot_var in boot_vars]
            return deletions

    def get_new_boot_vars(self):
        boot_statement_list = []

        if not self.single_boot_statement:
            boot_statement_list.append(self.boot_statement_prefix + self.prime_boot_loc + self.new_IOS_file)
            if self.sec_boot_loc:
                boot_statement_list.append(self.boot_statement_prefix + self.sec_boot_loc + self.new_IOS_file)

            boot_statement_list.append(self.boot_statement_prefix + self.prime_boot_loc + self.current_IOS_file)
            if self.sec_boot_loc:
                boot_statement_list.append(self.boot_statement_prefix + self.sec_boot_loc + self.current_IOS_file)

        elif self.single_boot_statement:
            boot_statement_list.append(self.boot_statement_prefix + self.prime_boot_loc + self.new_IOS_file)

        return boot_statement_list

    def change_boot_vars(self):
        if self.loggedin:
            commands = ["config terminal"]
            commands.extend(self.get_boot_var_deletes())
            commands.extend(self.get_new_boot_vars())
            commands.append("config-register *******")
            commands.append("end")
            commands.append("copy run start")
            for line in commands:
                if not self.simulation:
                    self.sendcmd(line,sleep=2)
                elif self.simulation:
                    print line

    def sys_prepare_ROMMON(self):
        if self.loggedin:
            commands = ["config terminal"]
            commands.extend(self.get_boot_var_deletes())
            commands.append(self.boot_statement_prefix + self.prime_boot_loc + self.ROMMON_file)
            if self.sec_boot_loc:
                commands.append(self.boot_statement_prefix + self.sec_boot_loc + self.ROMMON_file)
            commands.append(self.boot_statement_prefix + self.prime_boot_loc + self.current_IOS_file)
            if self.sec_boot_loc:
                commands.append(self.boot_statement_prefix + self.sec_boot_loc + self.current_IOS_file)
            commands.append("config-register ******")
            commands.append("end")
            commands.append("copy run start")
            for line in commands:
                if not self.simulation:
                    self.sendcmd(line,sleep=2)
                elif self.simulation:
                    print line
            self.sleep = 5

    def get_distance(self):
        """
        This function determines how many hops away from the Linux server a device sits.
        This is important to get a network depth model so the furthest network layer can be reloaded first.
        """

        distance = len(commands.getoutput("traceroute {}".format(self.name)).split("\n")[1:])
        if distance >= 30:
            self.distance = 0
        else:
            self.distance = distance

    def reload(self):
        if self.loggedin:
            try:
                for cmd in self.reload_cmd_list:
                    self.sendcmd(cmd,sleep=2)
                    self.sendcmd("")
                    self.sendcmd("")
            except:
                self.loggedin = False
                return "\n{} is reloading now.".format(self.name)
            else:
                self.loggedin = False
                return "\n{} is reloading now.".format(self.name)




    def is_alive(self, destination=None):
        if not destination:
            destination = self.name
        args = ("ping -c 1 " + destination).split()
        if call(args, stdout=PIPE, stderr=STDOUT) == 0:
            return True
        elif call(args, stdout=PIPE, stderr=STDOUT) == 0:
            return True
        else:
            return False

    def file_upload(self,new_file,
                    md5_hash_provided,
                    file_source="*****************"):

        if self.new_file_there(the_file=new_file,
                                 location=self.primary_copy_location):
            if md5_hash_provided:
                if not self.valid_md5(the_file=new_file,
                                        md5_hash=md5_hash_provided,
                                        location=self.primary_copy_location):
                    self.del_new_file(the_file=new_file,
                                        location=self.primary_copy_location)

        if not self.new_file_there(the_file=new_file,
                                     location=self.primary_copy_location):

            self.ftp_copy_file(source=file_source,
                                 destination=self.primary_copy_location,
                                 the_file=new_file)

            if self.new_file_there(the_file=new_file,
                                     location=self.primary_copy_location):
                if md5_hash_provided:
                    if not self.valid_md5(the_file=new_file,
                                            md5_hash=md5_hash_provided,
                                            location=self.primary_copy_location):
                        self.del_new_file(the_file=new_file,
                                            location=self.primary_copy_location)

        copy_attempt = 0
        while not self.new_file_there(the_file=new_file,
                                        location=self.primary_copy_location
                                        ) and copy_attempt < 3:

            self.scp_copy_file(source=file_source,
                                 destination=self.primary_copy_location,
                                 the_file=new_file)

            if self.new_file_there(the_file=new_file,
                                     location=self.primary_copy_location):
                if md5_hash_provided:
                    if not self.valid_md5(the_file=new_file,
                                            md5_hash=md5_hash_provided,
                                            location=self.primary_copy_location):
                        self.del_new_file(the_file=new_file,
                                            location=self.primary_copy_location)
            copy_attempt += 1

        if not self.new_file_there(the_file=new_file,
                                     location=self.primary_copy_location):
            return True  # Yes there was a problem copying the file from the server to the device.
        else:
            for location in self.available_media:
                if not self.new_file_there(location=location,
                                             the_file=new_file):
                    self.local_copy_file(source=self.primary_copy_location,
                                           destination=location,
                                           the_file=new_file)

            intra_device_copy_issue = False
            for location in self.available_media:
                if not self.new_file_there(location=location,
                                             the_file=new_file):
                    intra_device_copy_issue = True

            if intra_device_copy_issue:
                return True #There was an intra device copy issue
            else:
                return False  # No error copying the file to all locations.

    def strip_special_chars(self,string):
        strip_string = ""
        for char in string:
            if char.isdigit() or char.isalpha():
                strip_string += char
        return strip_string

    def ver_extractor(self, raw_syntax, slice_points=(0, 0)):

        slice_start = slice_points[0]
        slice_end = slice_points[1]
        if slice_end == 0:
            rough_ver = raw_syntax[slice_start:]
        else:
            rough_ver = raw_syntax[slice_start:slice_end]

        num_hold = ""
        alpha_hold = ""
        hold_list = []

        for char in rough_ver:
            if char.isdigit():
                num_hold += char
                if alpha_hold:
                    hold_list.append(alpha_hold)
                    alpha_hold = ""
            elif char.isalpha():
                alpha_hold += char
                if num_hold:
                    hold_list.append(num_hold)
                    num_hold = ""

        if num_hold:
            hold_list.append(num_hold)
        if alpha_hold:
            hold_list.append(alpha_hold)
        stripped_version = "-".join(hold_list)

        return stripped_version

    def Get_ROMMON_SNMP(self):
        # Tries to get a known valid supervisor PID using a list of possible SNMP OID values.
        #
        self.rommon_ver_list = []
        if self.Sup_PID:
            for Sup_OID in sup_OID_list:
                # Get the supervisor PID via SNMP
                Sup_PID = self.SNMP_OS_Call(oid=Sup_OID).split()[-1][1:-1]
                #
                # Checks against a valid results list, stops search once one is found.
                if Sup_PID in Valid_Sup_PIDs:
                    # Determine corresponding ROMMON OID from identified Sup OID
                    disassembled_OID = Sup_OID.split(".")
                    disassembled_OID[-2] = "9"
                    ROMMON_OID = ".".join(disassembled_OID)
                    #
                    ROMMON_ver = self.ver_extractor(raw_syntax=self.SNMP_OS_Call(oid=ROMMON_OID).split()[-1][1:-1])
                    self.rommon_ver_list.append(ROMMON_ver)
        else:
            ROMMON_ver = self.ver_extractor(raw_syntax=self.SNMP_OS_Call(oid=self.Non_Sup_ROMMON_OID).split()[-1][1:-1])
            self.rommon_ver_list.append(ROMMON_ver)

    def ROMMON_Compare(self):
        ROMMON_valid = True

        self.Get_ROMMON_SNMP()
        self.file_ver = self.ver_extractor(raw_syntax=self.ROMMON_file, slice_points=self.slice_points)

        for rommon_ver in self.rommon_ver_list:
            file_ver_temp_list = self.file_ver.split("-")[:]
            rommon_ver_temp_list = rommon_ver.split("-")[:]

            if len(rommon_ver_temp_list) >= len(file_ver_temp_list) and ROMMON_valid:
                for index in range(len(file_ver_temp_list)):
                    if rommon_ver_temp_list[index].isdigit() and file_ver_temp_list[index].isdigit():
                        rommon_ver_temp_list[index] = int(rommon_ver_temp_list[index])
                        file_ver_temp_list[index] = int(file_ver_temp_list[index])
                    if rommon_ver_temp_list[index] < file_ver_temp_list[index]:
                        ROMMON_valid = False
                        break
                    elif rommon_ver_temp_list[index] > file_ver_temp_list[index]:
                        break

            elif ROMMON_valid:
                for index in range(len(rommon_ver_temp_list)):
                    if rommon_ver_temp_list[index].isdigit() and file_ver_temp_list[index].isdigit():
                        rommon_ver_temp_list[index] = int(rommon_ver_temp_list[index])
                        file_ver_temp_list[index] = int(file_ver_temp_list[index])
                    if rommon_ver_temp_list[index] < file_ver_temp_list[index]:
                        ROMMON_valid = False
                        break
                    elif rommon_ver_temp_list[index] > file_ver_temp_list[index]:
                        break

        return ROMMON_valid

    def remove_cisco_com(self):
        if ".cisco.com" in self.name:
            index = self.name.index("*********")
            self.raw_hostname = self.name[:index]
        else:
            self.raw_hostname = self.name

    def get_console_names(self):
        self.console_list = []
        console_list = []
        live_console_list = []

        self.remove_cisco_com()

        """
        Sanitized
        """

        for console_name in console_list:
            if self.is_alive(console_name):
                live_console_list.append(console_name)
            else:
                if self.is_alive(console_name):
                    live_console_list.append(console_name)
                else:
                    if self.is_alive(console_name):
                        live_console_list.append(console_name)

        self.console_list = live_console_list

    def modular_get_sw_code(self):
        SNMP_sw_ver_code = self.SNMP_OS_Call(oid=self.modular_sw_ver_OID).split()[-1][1:-1]
        if SNMP_sw_ver_code == '' or SNMP_sw_ver_code == 'I':
            SNMP_sw_ver_code = self.SNMP_OS_Call(oid=self.modular_sw_ver_OID_alt).split()[-1][1:-1]

        if SNMP_sw_ver_code:
            self.modular_safe_words.append(SNMP_sw_ver_code)
            #self.modular_safe_words = list(set(self.modular_safe_words))

    def get_show_mod(self, stage):
        if self.loggedin and self.modular_cmd:
            self.modular_get_sw_code()
            if stage == "pre":
                self.modular_pre = self.sendcmd(self.modular_cmd,sleep=2)[1:-1]
            elif stage == "post":
                self.modular_post = self.sendcmd(self.modular_cmd,sleep=2)[1:-1]

    def find_bad_modules(self):
        self.modular_issues = []
        match = False
        print "{}: Safe Words List = {}".format(self.name,self.modular_safe_words)

        for pre_line in self.modular_pre:
            split_line_pre = [item for item in pre_line.split() if item not in self.modular_safe_words]
            for post_line in self.modular_post:
                split_line_post = [item for item in post_line.split() if item not in self.modular_safe_words]
                if split_line_pre == split_line_post:
                    match = True
                    break
            if not match:
                self.modular_issues.append(pre_line)
            else:
                match = False

    def get_errdisabled_ints(self):
        if self.loggedin:
            self.err_dis_ints_list = []
            output_list = self.sendcmd("show int status err-disabled")[2:-1]
            self.err_dis_ints_list = [line.split()[0] for line in output_list]

    def restore_errdisabled_ints(self, restore_list=None):
        if self.loggedin:
            if not restore_list:
                restore_list = self.err_dis_ints_list

            if restore_list:
                restore_config = ["conf t"]
                for int in restore_list:
                    restore_config.extend(["interface {}".format(int), "shut", "no shut"])
                restore_config.append("end")

                for line in restore_config:
                    self.sendcmd(line)

    def get_all_cdp_ints(self):
        if self.loggedin:
            all_cdp_int_lines = self.sendcmd("show cdp nei | i /")[1:-1]
            all_cdp_int_lines = [line for line in all_cdp_int_lines if len(line.split()) > 1]

            interface = ""
            self.all_cdp_ints = []
            for line in all_cdp_int_lines:
                if "/" in line.split()[1]:
                    interface = line.split()[0] + line.split()[1]
                elif "/" in line.split()[2]:
                    interface = line.split()[1] + line.split()[2]
                self.all_cdp_ints.append(interface)
                self.all_cdp_ints = list(set(self.all_cdp_ints))

    def get_neighbors(self):
        self.neighbors = {}
        tup_list = []
        hostname = ""

        if self.loggedin:
            self.get_all_cdp_ints()
            for int in self.all_cdp_ints:
                output = self.sendcmd("show cdp nei {}".format(int))[1:]
                for line in output:
                    for item in line.split():
                        if ".cisco.com" in line and "-cap" not in item or "wlc" in item:
                            hostname = item
                    if "/" in line.split()[-1] and len(line.split()) > 1:
                        neighbor_int = line.split()[-2] + line.split()[-1]
                        tuple = (hostname, neighbor_int)
                        tup_list.append(tuple)
                        break

            for hostname, neighbor_int in tup_list:
                if hostname not in self.neighbors.keys():
                    self.neighbors[hostname] = []

            for hostname, neighbor_int in tup_list:
                self.neighbors[hostname].append(neighbor_int)

    def get_time(self):
        try:
            return self.SNMP_OS_Call(oid="mib-2.197.1.2.9.0").split('"')[-2]
        except:
            return ""

    def install_mode_correct_IOS(self):
        sw_ver_code = self.SNMP_OS_Call(oid=self.modular_sw_ver_OID).split()[-1][1:-1]
        if not sw_ver_code or sw_ver_code == "I":
            sw_ver_code = self.SNMP_OS_Call(oid=self.modular_sw_ver_OID_alt).split()[-1][1:-1]
        return self.strip_special_chars(sw_ver_code) in self.strip_special_chars(self.new_IOS_file)

    def install_mode_no_manual(self):
        if self.loggedin:
            self.sendcmd("config terminal",sleep=2)
            self.sendcmd("no boot manual",sleep=2)
            self.sendcmd("end",sleep=2)

    def install_mode_software_clean(self):
        if self.loggedin:
            self.get_prompt()
            self.sendcmd("software clean")

            yes_no_prompt = False
            while not yes_no_prompt:
                time.sleep(15)
                answer = self.sendcmd("")[-1]
                if "[yes/no]:" in answer:
                    self.sendcmd("yes")
                    yes_no_prompt = True
                elif self.prompt_back():
                    break

    def install_mode_software_install(self):
        if self.loggedin:
            self.get_prompt()
            self.sendcmd("software install file {}{}".format(self.prime_boot_loc,self.new_IOS_file))

            yes_no_prompt = False
            while not yes_no_prompt:
                time.sleep(15)
                answer = self.sendcmd("")[-1]
                if "[yes/no]:" in answer:
                    self.sendcmd("yes",sleep=2)
                    yes_no_prompt = True
                elif self.prompt_back():
                    break

    def save_config(self):
        if self.loggedin:
            if not self.prompt:
                self.get_prompt()

            self.sendcmd("copy running-config startup-config",sleep=2)
            self.sendcmd("",sleep=2)
            self.sendcmd("")

            if not self.prompt_back():
                prompt_back_yet = False
                while not prompt_back_yet:
                    time.sleep(5)
                    prompt_back_yet = self.prompt_back()

##################################################

class Group1(IOS_NetDev):
    """ Class base Template for:
    Cisco 4500X
    Cisco Cat4948-10GE family
    Cisco Cat4900M"""

    # Child classes will only receive relevant attributes from Sales_Order.py.
    # Only these relevant values will be forwarded to the parent class constructor.
    # Non-relevant attributes will get their default value of "" and won't be referenced further.
    def __init__(self, name, auth_keychain, HW_PID, current_IOS_file, new_IOS_file, IOS_md5_hash,
                 ROMMON_file, ROMMON_md5_hash):
        IOS_NetDev.__init__(self, name,
                            auth_keychain=auth_keychain,
                            HW_PID=HW_PID,
                            current_IOS_file=current_IOS_file,
                            new_IOS_file=new_IOS_file,
                            IOS_md5_hash=IOS_md5_hash,
                            ROMMON_file=ROMMON_file,
                            ROMMON_md5_hash=ROMMON_md5_hash)

        self.media_list = ["bootflash:"]
        self.removable_flash_list = ["slot0:"]
        self.prime_boot_loc = "bootflash:"
        self.sec_boot_loc = "slot0:"
        self.boot_statement_prefix = "boot system flash "
        self.slice_points = (26, 0)

        self.ROMMON_search_value = "promupgrade"

##################################################

class C6500S2T(IOS_NetDev):
    """ Class tailored for Cat6500/Cat7600/6807 family with Sup 2T """

    # Child classes will only receive relevant attributes from Sales_Order.py.
    # Only these relevant values will be forwarded to the parent class constructor.
    # Non-relevant attributes will get their default value of "" and won't be referenced further.
    def __init__(self, name, auth_keychain, HW_PID, Sup_PID, current_IOS_file, new_IOS_file, IOS_md5_hash,
                 new_FPD_file, FPD_md5_hash):
        IOS_NetDev.__init__(self, name,
                            auth_keychain=auth_keychain,
                            HW_PID=HW_PID,
                            Sup_PID=Sup_PID,
                            current_IOS_file=current_IOS_file,
                            new_IOS_file=new_IOS_file,
                            IOS_md5_hash=IOS_md5_hash,
                            new_FPD_file=new_FPD_file,
                            FPD_md5_hash=FPD_md5_hash)

        self.prime_boot_loc = "bootdisk:"
        self.sec_boot_loc = "disk0:"
        self.boot_statement_prefix = "boot system flash "

        self.modular_sw_ver_OID = "mib-2.47.1.1.1.1.10.3000"
        self.modular_sw_ver_OID_alt = "mib-2.47.1.1.1.1.10.5000"

        self.get_sup_num()
        if self.Sup_num == 2:
            self.media_list = ["bootdisk:","slavebootdisk:"]
            self.removable_flash_list = ["disk0:","slavedisk0:"]

            self.modular_safe_words = ["Active", "(Acti", "Standby", "(Hot)"]
            self.modular_cmd = "show module switch all"
            self.reload_finish_time_in_seconds = 540

        elif self.Sup_num == 1:
            self.media_list = ["bootdisk:"]
            self.removable_flash_list = ["disk0:"]

            self.modular_cmd = "show module"
            self.reload_finish_time_in_seconds = 240

##################################################

class C6500(IOS_NetDev):
    """ Class tailored for Cat6500/Cat7600/6807 family with Sup 720 and Sup32 """

    # Child classes will only receive relevant attributes from Sales_Order.py.
    # Only these relevant values will be forwarded to the parent class constructor.
    # Non-relevant attributes will get their default value of "" and won't be referenced further.
    def __init__(self, name, auth_keychain, HW_PID, Sup_PID, current_IOS_file, new_IOS_file, IOS_md5_hash,
                 new_FPD_file, FPD_md5_hash):
        IOS_NetDev.__init__(self, name,
                            auth_keychain=auth_keychain,
                            HW_PID=HW_PID,
                            Sup_PID=Sup_PID,
                            current_IOS_file=current_IOS_file,
                            new_IOS_file=new_IOS_file,
                            IOS_md5_hash=IOS_md5_hash,
                            new_FPD_file=new_FPD_file,
                            FPD_md5_hash=FPD_md5_hash)

        self.prime_boot_loc = "sup-bootdisk:"
        self.sec_boot_loc = "disk0:"
        self.boot_statement_prefix = "boot system flash "

        self.modular_sw_ver_OID = "mib-2.47.1.1.1.1.10.3000"
        self.modular_sw_ver_OID_alt = "mib-2.47.1.1.1.1.10.5000"

        self.get_sup_num()
        if self.Sup_num == 2:

            self.media_list = ["sup-bootdisk:","slavesup-bootdisk:"]
            self.removable_flash_list = ["disk0:","slavedisk0:"]

            self.modular_safe_words = ["Active", "(Acti", "Standby", "(Hot)"]
            self.modular_cmd = "show module switch all"
            self.reload_finish_time_in_seconds = 540

        elif self.Sup_num == 1:

            self.media_list = ["sup-bootdisk:"]
            self.removable_flash_list = ["disk0:"]

            self.modular_cmd = "show module"
            self.reload_finish_time_in_seconds = 240

##################################################

class C4500(IOS_NetDev):
    """ Class tailored for Cat4500 family """

    # Child classes will only receive relevant attributes from Sales_Order.py.
    # Only these relevant values will be forwarded to the parent class constructor.
    # Non-relevant attributes will get their default value of "" and won't be referenced further.
    def __init__(self, name, auth_keychain, HW_PID, Sup_PID, current_IOS_file, new_IOS_file, IOS_md5_hash, ROMMON_file, ROMMON_md5_hash):
        IOS_NetDev.__init__(self, name,
                            auth_keychain=auth_keychain,
                            HW_PID=HW_PID,
                            Sup_PID=Sup_PID,
                            current_IOS_file=current_IOS_file,
                            new_IOS_file=new_IOS_file,
                            IOS_md5_hash=IOS_md5_hash,
                            ROMMON_file=ROMMON_file,
                            ROMMON_md5_hash=ROMMON_md5_hash)

        self.prime_boot_loc = "bootflash:"
        self.sec_boot_loc = "slot0:"
        self.boot_statement_prefix = "boot system flash "
        self.reload_cmd_list = ["redundancy reload shelf"]
        self.slice_points = (26,0)
        self.ROMMON_search_value = "promupgrade"

        self.modular_cmd = "show module"
        self.modular_sw_ver_OID = "mib-2.47.1.1.1.1.10.3000"
        self.modular_sw_ver_OID_alt = "mib-2.47.1.1.1.1.10.5000"

        self.reload_finish_time_in_seconds = 120

        self.get_sup_num()
        if self.Sup_num == 2:
            self.media_list = ["bootflash:","slavebootflash:"]
            self.removable_flash_list = ["slot0:","slaveslot0:"]

            self.modular_safe_words = ["Active", "hot", "Standby"]

        elif self.Sup_num == 1:
            self.media_list = ["bootflash:"]
            self.removable_flash_list = ["slot0:"]

##################################################

class C3750(IOS_NetDev):
    """ Class tailored for Cat3750 family """

    # Child classes will only receive relevant attributes from Sales_Order.py.
    # Only these relevant values will be forwarded to the parent class constructor.
    # Non-relevant attributes will get their default value of "" and won't be referenced further.
    def __init__(self, name, auth_keychain, HW_PID, current_IOS_file, new_IOS_file, IOS_md5_hash):
        IOS_NetDev.__init__(self, name,
                            auth_keychain=auth_keychain,
                            HW_PID=HW_PID,
                            current_IOS_file=current_IOS_file,
                            new_IOS_file=new_IOS_file,
                            IOS_md5_hash=IOS_md5_hash)

        self.media_list = []
        self.boot_statement_prefix = "boot system switch all "
        self.single_boot_statement = True
        self.reload_completion_check_cycles = 180

        self.modular_sw_ver_OID = "mib-2.47.1.1.1.1.10.1000"
        self.modular_sw_ver_OID_alt = "mib-2.47.1.1.1.1.10.2000"

        self.get_stack_num()
        for device in range(self.stack_size):
            media = "flash{}:".format(device+1)
            self.media_list.append(media)

        if self.stack_size > 1:
            self.reload_finish_time_in_seconds = 180
            self.modular_cmd = "show switch"
            self.modular_safe_words = ["Active", "Master", "Standby", "Member"]

##################################################

class C3850(IOS_NetDev):
    """ Class tailored for Cat3850 family """

    # Child classes will only receive relevant attributes from Sales_Order.py.
    # Only these relevant values will be forwarded to the parent class constructor.
    # Non-relevant attributes will get their default value of "" and won't be referenced further.
    def __init__(self, name, auth_keychain, HW_PID, current_IOS_file, new_IOS_file, IOS_md5_hash):
        IOS_NetDev.__init__(self, name,
                            auth_keychain=auth_keychain,
                            HW_PID=HW_PID,
                            current_IOS_file=current_IOS_file,
                            new_IOS_file=new_IOS_file,
                            IOS_md5_hash=IOS_md5_hash)

        self.boot_statement_prefix = "boot system switch all "
        self.reload_completion_check_cycles = 120

        self.modular_sw_ver_OID = "mib-2.47.1.1.1.1.10.1000"
        self.modular_sw_ver_OID_alt = "mib-2.47.1.1.1.1.10.2000"

        self.get_stack_num()
        if self.stack_size > 1:
            self.reload_finish_time_in_seconds = 180
            self.modular_cmd = "show switch"
            self.modular_safe_words = ["Active", "Master", "Standby", "Member"]

            self.media_list = []
            for device in range(self.stack_size):
                media = "flash-{}:".format(device+1)
                self.media_list.append(media)

##################################################

class ASR1000(IOS_NetDev):
    """ Class tailored for Cisco ASR1000 family"""

    # Child classes will only receive relevant attributes from Sales_Order.py.
    # Only these relevant values will be forwarded to the parent class constructor.
    # Non-relevant attributes will get their default value of "" and won't be referenced further.
    def __init__(self, name, auth_keychain, HW_PID, current_IOS_file, new_IOS_file, IOS_md5_hash, ROMMON_file, ROMMON_md5_hash):
        IOS_NetDev.__init__(self, name,
                            auth_keychain=auth_keychain,
                            HW_PID=HW_PID,
                            current_IOS_file=current_IOS_file,
                            new_IOS_file=new_IOS_file,
                            IOS_md5_hash=IOS_md5_hash,
                            ROMMON_file=ROMMON_file,
                            ROMMON_md5_hash=ROMMON_md5_hash)

        self.media_list = ["bootflash:"]
        self.prime_boot_loc = "bootflash:"
        self.boot_statement_prefix = "boot system flash "
        self.slice_points = (15,-4)

        self.ROMMON_search_value = "rommon"

    def sys_prepare_ROMMON(self):
        if self.loggedin:
            self.get_prompt()
            commands = ["upgrade rom-monitor filename {}{} all".format(self.prime_boot_loc,self.ROMMON_file)]
            for line in commands:
                if not self.simulation:
                    self.sendcmd(line,sleep=2)
                elif self.simulation:
                    print line

            if not self.simulation:
                time.sleep(10)
                prompt_back_yet = False
                while not prompt_back_yet:
                    time.sleep(5)
                    prompt_back_yet = self.prompt_back()

##################################################

class ISR4450(IOS_NetDev):
    """ Class tailored for Cisco ISR4450 family"""

    # Child classes will only receive relevant attributes from Sales_Order.py.
    # Only these relevant values will be forwarded to the parent class constructor.
    # Non-relevant attributes will get their default value of "" and won't be referenced further.
    def __init__(self, name, auth_keychain, HW_PID, current_IOS_file, new_IOS_file, IOS_md5_hash):
        IOS_NetDev.__init__(self, name,
                            auth_keychain=auth_keychain,
                            HW_PID=HW_PID,
                            current_IOS_file=current_IOS_file,
                            new_IOS_file=new_IOS_file,
                            IOS_md5_hash=IOS_md5_hash)

        self.media_list = ["bootflash:"]
        self.prime_boot_loc = "bootflash:"
        self.boot_statement_prefix = "boot system flash "

##################################################

class C4948(IOS_NetDev):
    """ Class tailored for Cisco Cat4948 family (Non 10GE)"""

    # Child classes will only receive relevant attributes from Sales_Order.py.
    # Only these relevant values will be forwarded to the parent class constructor.
    # Non-relevant attributes will get their default value of "" and won't be referenced further.
    def __init__(self, name, auth_keychain, HW_PID, current_IOS_file, new_IOS_file, IOS_md5_hash, ROMMON_file, ROMMON_md5_hash):
        IOS_NetDev.__init__(self, name,
                            auth_keychain=auth_keychain,
                            HW_PID=HW_PID,
                            current_IOS_file=current_IOS_file,
                            new_IOS_file=new_IOS_file,
                            IOS_md5_hash=IOS_md5_hash,
                            ROMMON_file=ROMMON_file,
                            ROMMON_md5_hash=ROMMON_md5_hash)

        self.media_list = ["bootflash:"]
        self.prime_boot_loc = "bootflash:"
        self.boot_statement_prefix = "boot system flash "
        self.slice_points = (26,0)

        self.ROMMON_search_value = "promupgrade"

##################################################

class C4948_10GE(Group1):
    """ Class tailored for Cisco Cat4948-10GE family"""

    # Child classes will only receive relevant attributes from Sales_Order.py.
    # Only these relevant values will be forwarded to the parent class constructor.
    # Non-relevant attributes will get their default value of "" and won't be referenced further.
    def __init__(self, name, auth_keychain, HW_PID, current_IOS_file, new_IOS_file, IOS_md5_hash, ROMMON_file, ROMMON_md5_hash):
        Group1.__init__(self, name,
                        auth_keychain=auth_keychain,
                        HW_PID=HW_PID,
                        current_IOS_file=current_IOS_file,
                        new_IOS_file=new_IOS_file,
                        IOS_md5_hash=IOS_md5_hash,
                        ROMMON_file=ROMMON_file,
                        ROMMON_md5_hash=ROMMON_md5_hash)

        self.slice_points = (24, 0)

    def IOS_reclaim_space(self,location):
        IOS_NetDev.IOS_reclaim_space(self,location=location)
        if self.loggedin:
            self.get_prompt()
            if not self.simulation:
                if not self.prompt:
                    self.get_prompt()
                self.sendcmd("squeeze /quiet {}".format(location))
                self.sendcmd("")
                self.sendcmd("")

                prompt_back_yet = False
                while not prompt_back_yet:
                    time.sleep(5)
                    prompt_back_yet = self.prompt_back()

##################################################

class C2600(IOS_NetDev):
    """ Class tailored for Cisco 2600 family """

    # Child classes will only receive relevant attributes from Sales_Order.py.
    # Only these relevant values will be forwarded to the parent class constructor.
    # Non-relevant attributes will get their default value of "" and won't be referenced further.
    def __init__(self, name, auth_keychain, HW_PID, current_IOS_file, new_IOS_file, IOS_md5_hash):
        IOS_NetDev.__init__(self, name,
                            auth_keychain=auth_keychain,
                            HW_PID=HW_PID,
                            current_IOS_file=current_IOS_file,
                            new_IOS_file=new_IOS_file,
                            IOS_md5_hash=IOS_md5_hash)

    def IOS_reclaim_space(self,location):
        IOS_NetDev.IOS_reclaim_space(self,location=location)
        if self.loggedin:
            self.get_prompt()
            if not self.simulation:
                if not self.prompt:
                    self.get_prompt()
                self.sendcmd("squeeze /quiet {}".format(location))
                self.sendcmd("")
                self.sendcmd("")

                prompt_back_yet = False
                while not prompt_back_yet:
                    time.sleep(5)
                    prompt_back_yet = self.prompt_back()

##################################################

class C4500X(Group1):
    """ Class tailored for Cisco 4500X Family"""

    # Child classes will only receive relevant attributes from Sales_Order.py.
    # Only these relevant values will be forwarded to the parent class constructor.
    # Non-relevant attributes will get their default value of "" and won't be referenced further.
    def __init__(self, name, auth_keychain, HW_PID, current_IOS_file, new_IOS_file, IOS_md5_hash, ROMMON_file, ROMMON_md5_hash):
        Group1.__init__(self, name,
                        auth_keychain=auth_keychain,
                        HW_PID=HW_PID,
                        current_IOS_file=current_IOS_file,
                        new_IOS_file=new_IOS_file,
                        IOS_md5_hash=IOS_md5_hash,
                        ROMMON_file=ROMMON_file,
                        ROMMON_md5_hash=ROMMON_md5_hash)

##################################################

class C4900M(Group1):
    """ Class tailored for Cisco Cat4900M"""

    # Child classes will only receive relevant attributes from Sales_Order.py.
    # Only these relevant values will be forwarded to the parent class constructor.
    # Non-relevant attributes will get their default value of "" and won't be referenced further.
    def __init__(self, name, auth_keychain, HW_PID, current_IOS_file, new_IOS_file, IOS_md5_hash, ROMMON_file, ROMMON_md5_hash):
        Group1.__init__(self, name,
                        auth_keychain=auth_keychain,
                        HW_PID=HW_PID,
                        current_IOS_file=current_IOS_file,
                        new_IOS_file=new_IOS_file,
                        IOS_md5_hash=IOS_md5_hash,
                        ROMMON_file=ROMMON_file,
                        ROMMON_md5_hash=ROMMON_md5_hash)

##################################################

class C7200(IOS_NetDev):
    """ Class tailored for Cisco 7200 family """

    # Child classes will only receive relevant attributes from Sales_Order.py.
    # Only these relevant values will be forwarded to the parent class constructor.
    # Non-relevant attributes will get their default value of "" and won't be referenced further.
    def __init__(self, name, auth_keychain, HW_PID, current_IOS_file, new_IOS_file, IOS_md5_hash,
                 new_FPD_file, FPD_md5_hash):
        IOS_NetDev.__init__(self, name,
                            auth_keychain=auth_keychain,
                            HW_PID=HW_PID,
                            current_IOS_file=current_IOS_file,
                            new_IOS_file=new_IOS_file,
                            IOS_md5_hash=IOS_md5_hash,
                            new_FPD_file=new_FPD_file,
                            FPD_md5_hash=FPD_md5_hash)

        self.media_list = ["disk2:"]
        self.prime_boot_loc = "disk2:"
        self.boot_statement_prefix = "boot system flash "

##################################################

class C6880(IOS_NetDev):
    """ Class tailored for Cisco 6880 family """

    # Child classes will only receive relevant attributes from Sales_Order.py.
    # Only these relevant values will be forwarded to the parent class constructor.
    # Non-relevant attributes will get their default value of "" and won't be referenced further.
    def __init__(self, name, auth_keychain, HW_PID, current_IOS_file, new_IOS_file, IOS_md5_hash):
        IOS_NetDev.__init__(self, name,
                            auth_keychain=auth_keychain,
                            HW_PID=HW_PID,
                            current_IOS_file=current_IOS_file,
                            new_IOS_file=new_IOS_file,
                            IOS_md5_hash=IOS_md5_hash)

        self.media_list = ["bootdisk:"]
        self.prime_boot_loc = "bootdisk:"

##################################################

class C3725(IOS_NetDev):
    """ Class tailored for Cisco 3725 family """

    # Child classes will only receive relevant attributes from Sales_Order.py.
    # Only these relevant values will be forwarded to the parent class constructor.
    # Non-relevant attributes will get their default value of "" and won't be referenced further.
    def __init__(self, name, auth_keychain, HW_PID, current_IOS_file, new_IOS_file, IOS_md5_hash):
        IOS_NetDev.__init__(self, name,
                            auth_keychain=auth_keychain,
                            HW_PID=HW_PID,
                            current_IOS_file=current_IOS_file,
                            new_IOS_file=new_IOS_file,
                            IOS_md5_hash=IOS_md5_hash)

        self.removable_flash_list = ["slot0:"]

##################################################

class C3560(IOS_NetDev):
    """ Class tailored for Cisco 3560 family """

    # Child classes will only receive relevant attributes from Sales_Order.py.
    # Only these relevant values will be forwarded to the parent class constructor.
    # Non-relevant attributes will get their default value of "" and won't be referenced further.
    def __init__(self, name, auth_keychain, HW_PID, current_IOS_file, new_IOS_file, IOS_md5_hash):
        IOS_NetDev.__init__(self, name,
                            auth_keychain=auth_keychain,
                            HW_PID=HW_PID,
                            current_IOS_file=current_IOS_file,
                            new_IOS_file=new_IOS_file,
                            IOS_md5_hash=IOS_md5_hash)

        self.single_boot_statement = True

##################################################

class C890(IOS_NetDev):
    """ Class tailored for Cisco 3560 family """

    # Child classes will only receive relevant attributes from Sales_Order.py.
    # Only these relevant values will be forwarded to the parent class constructor.
    # Non-relevant attributes will get their default value of "" and won't be referenced further.
    def __init__(self, name, auth_keychain, HW_PID, current_IOS_file, new_IOS_file, IOS_md5_hash):
        IOS_NetDev.__init__(self, name,
                            auth_keychain=auth_keychain,
                            HW_PID=HW_PID,
                            current_IOS_file=current_IOS_file,
                            new_IOS_file=new_IOS_file,
                            IOS_md5_hash=IOS_md5_hash)

        self.boot_statement_prefix = "boot system flash "

##################################################

