import threading
import time
import timeit
import random
from IOS_Upgrader.NAE.Maestro.Maestros import IOS_Maestro
from IOS_Upgrader.NAE.Factory.Locksmith import get_key
############  !!!!!!!!!!!!!
from dictionaries import get_login_keychain, get_standards_tuple  ########This was sanitized out
############  !!!!!!!!!!!!!
from IOS_Upgrader.NAE.Factory.Get_HW_SW import Get_HW_SW

__author__ = 'jacurran'

LD = False

##################################################

# This function reads a text file and returns a list.
def read_txt(filename):
    file = open(filename)
    FileList = file.readlines()
    FileList = [x.strip() for x in FileList]
    file.close()
    return FileList

##################################################

class Queue:
    def __init__(self):
        self.job = []
    def isEmpty(self):
        return self.job == []
    def enqueue(self, item):
        self.job.insert(0, item)
    def dequeue(self):
        return self.job.pop()
    def size(self):
        return len(self.job)

##################################################

class myThread (threading.Thread):
    def __init__(self, hostname,log_file_name,LD):
        threading.Thread.__init__(self)
        self.hostname = hostname
        self.log_file_name = "./job_logs/"+log_file_name
        self.LD = LD
        self.auth_keychain = get_login_keychain()

    def write_txt(self,data):
        myfile = open(self.log_file_name, "a+")
        myfile.write(data + "\n")
        myfile.close()

    def run(self):
        #insert function here such as Maestro job

        start_time = timeit.default_timer()

        if self.auth_keychain:
            HW_PID, Sup_PID, current_IOS = Get_HW_SW(self.hostname, auth_keychain=self.auth_keychain)
            Maestro_Key = get_key(hostname=self.hostname,
                                  hw_pid=HW_PID,
                                  sup_pid=Sup_PID)
            design_tuple = get_standards_tuple(Maestro_Key=Maestro_Key)

            result = IOS_Maestro(hostname=self.hostname, auth_keychain=self.auth_keychain,
                                 design_tuple=design_tuple, LD=self.LD)

        else:
            result = "No auth keychain provided, aborting IOS staging job for {}".format(self.hostname)

        end_time = timeit.default_timer()

        time.sleep(random.randint(1,5))

        self.write_txt(result)
        self.write_txt("\nJob finished in {} seconds.".format(end_time - start_time))
        self.write_txt("\n"+"-"*40+"\n")

##################################################

input_file = raw_input("Devices file: ").strip()
log_file_name = raw_input("Log File Name: ").strip()

LD_check = raw_input("Are these devices LD? (Y/N default = N): ").lower().strip()
if LD_check == "y":
    LD = True
print

##################################################

log_file = open("./job_logs/"+log_file_name,"w")
log_file.write("\n")
log_file.close()

##################################################

device_list = read_txt(input_file)

q = Queue()

for device in device_list:
    job = myThread(hostname=device,log_file_name=log_file_name,LD=LD)
    q.enqueue(job)

workbench_max_size = 15
workbench = []

while len(workbench) < workbench_max_size and not q.isEmpty():
    workbench.append(q.dequeue())

for job in workbench:
    job.start()

while not q.isEmpty():
    holding_list = []
    for job in workbench:
        if job.isAlive():
            holding_list.append(job)

    workbench = holding_list

    while len(workbench) < workbench_max_size and not q.isEmpty():
        next_device = q.dequeue()
        workbench.append(next_device)
        next_device.start()

    time.sleep(5)
