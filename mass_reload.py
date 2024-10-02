import threading
import time
import timeit
import random
import commands
from IOS_Upgrader.NAE.Factory.Locksmith import get_key
from IOS_Upgrader.NAE.Jedi.Jedi import reload_IOS
############  !!!!!!!!!!!!!
from dictionaries import get_login_keychain, get_standards_tuple   #This was sanitized out
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

def get_distance(hostname):
    """
    This function determines how many hops away from the Linux server a device sits.
    This is important to get a network depth model so the furthest network layer can be reloaded first.
    """
    distance = len(commands.getoutput("traceroute {}".format(hostname)).split("\n")[1:])
    if distance >= 30:
        return 0
    else:
        return distance

##################################################

class Queue:
    def __init__(self):
        self.jobs = []
    def isEmpty(self):
        return self.jobs == []
    def enqueue(self, item):
        self.jobs.insert(0, item)
    def dequeue(self):
        return self.jobs.pop()
    def size(self):
        return len(self.jobs)

##################################################

class myThread (threading.Thread):
    def __init__(self, hostname,error_log_file_name,success_log_file_name,LD,job_distance):
        threading.Thread.__init__(self)
        self.hostname = hostname
        self.error_log_file_name = "./job_logs/"+error_log_file_name
        self.success_log_file_name = "./job_logs/"+success_log_file_name
        self.LD = LD
        self.distance = job_distance
        self.auth_keychain = get_login_keychain()
    #
    def error_write_txt(self,data):
        myfile = open(self.error_log_file_name, "a+")
        myfile.write(data + "\n")
        myfile.close()
    #
    def success_write_txt(self,data):
        myfile = open(self.success_log_file_name, "a+")
        myfile.write(data + "\n")
        myfile.close()
    #
    def run(self):
        #insert function here such as Jedi job
        start_time = timeit.default_timer()

        if self.auth_keychain:
            HW_PID, Sup_PID, current_IOS = Get_HW_SW(self.hostname, auth_keychain=self.auth_keychain)
            Maestro_Key = get_key(hostname=self.hostname,
                                  hw_pid=HW_PID,
                                  sup_pid=Sup_PID)
            design_tuple = get_standards_tuple(Maestro_Key=Maestro_Key)

            result = reload_IOS(hostname=self.hostname,auth_keychain=self.auth_keychain,
                                design_tuple=design_tuple,LD=self.LD)
        else:
            result = "No auth keychain provided, aborting reload job for {}".format(self.hostname)


        end_time = timeit.default_timer()

        time.sleep(random.randint(1,5))
        #
        if result:
            self.error_write_txt(result)
            self.error_write_txt("\nJob finished in {} seconds.".format(end_time - start_time))
            self.error_write_txt("\n"+"-"*40+"\n")
        else:
            self.success_write_txt("{} reloaded with no critical errors.".format(self.hostname))
            self.success_write_txt("\nJob finished in {} seconds.".format(end_time - start_time))
            self.success_write_txt("\n" + "-" * 40 + "\n")

##################################################

input_file = raw_input("Devices file: ").strip()
error_log_file_name = raw_input("Error Log File Name: ").strip()
success_log_file_name = raw_input("Successful Reloads Log File Name: ").strip()

LD_check = raw_input("Are these devices LD? (Y/N default = N): ").lower().strip()
if LD_check == "y":
    LD = True
print

##################################################

error_log_file = open("./job_logs/"+error_log_file_name,"w")
error_log_file.write("\n")
error_log_file.close()

##################################################

success_log_file = open("./job_logs/"+success_log_file_name,"w")
success_log_file.write("\n")
success_log_file.close()

##################################################

device_list = read_txt(input_file)

unordered_q = Queue()
q = Queue()

for device in device_list:
    device_distance = get_distance(device)
    job = myThread(hostname=device,error_log_file_name=error_log_file_name,
                   success_log_file_name=success_log_file_name,LD=LD,job_distance=device_distance)
    unordered_q.enqueue(job)

job_distance = 31
while job_distance > -1:
    for job in unordered_q.jobs:
        if job.distance == job_distance:
            q.enqueue(job)
    job_distance -= 1


workbench_max_size = 50
workbench = []

job_distance = q.jobs[-1].distance
while len(workbench) < workbench_max_size and not q.isEmpty():
    workbench.append(q.dequeue())

for job in workbench:
    if job.distance == job_distance:
        #print job.distance
        job.start()
    else:
        time.sleep(120)
        job_distance = job.distance
        #print job.distance
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
        if next_device.distance == job_distance:
            #print next_device.distance
            next_device.start()
        else:
            time.sleep(120)
            job_distance = next_device.distance
            #print next_device.distance
            next_device.start()

    time.sleep(5)
