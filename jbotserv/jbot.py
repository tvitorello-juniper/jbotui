#!/usr/bin/env python
# coding: utf-8
# Author: efrain@juniper.net
# Version 1.0  20150122 
import argparse   # Used for argument parsing
import StringIO   # Used for file read/write
from lxml import etree  # Used for xml manipulation
import re # For regular expression usage
import subprocess  # In order to perform system calls
from datetime import datetime # In order to retreive time and timespan
from datetime import timedelta # In order to retreive time and timespan
import time
from pprint import pprint  # just for dictionary printing, only for debuggin purposes
import os  # For exec to work
import sys  # For exec to work
import string  # For split multiline script into multiple lines
import smtplib     # for sending mails
from email.mime.image import MIMEImage   # for sending mails
from email.mime.multipart import MIMEMultipart # for sending mails
from email.mime.text import MIMEText  # for sending mails
import socket 
import yaml
import logging
from JRouter import * 

####################################################################################
####################################################################################
# Defining the classes and procedures used later on the script 
####################################################################################
####################################################################################
class AutoVivification(dict):
    """Implementation of perl's autovivification feature."""
    def __getitem__(self, item):
        try:
            return dict.__getitem__(self, item)
        except KeyError:
            value = self[item] = type(self)()
            return value

def hostname_resolves(hostname):
    try:
        socket.gethostbyname(hostname)
        return 1
    except socket.error:
        return 0

def hostname_alive(hostname):
    command = "ping -c 1 " + hostname
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    output, error = process.communicate()
    return_code = process.wait()
    if return_code == 0:
        return 1
    else:
        return 0
 
def send_mail(file_to_attach):
    SMTP_SERVER = 'smtp.gmail.com'
    SMTP_PORT = 587
    sender = 'juniper.support.local.team@gmail.com'
    password = 'j4n1p3r0s!'
    #    recipient = ['jesusangel.rojoaranda@telefonica.com','psagrerag@gmail.com','efrain.gonzalez@gmail.com','vicrodsa@gmail.com','atoparis@gmail.com','davjimen1@gmail.com']
    recipient = ['vitorellotm@gmail.com']
    subject = "Jbot upgrade results for "+target
    # Include in message the last line for logs
    message = "Jbot UPGRADE LOG SUMMARY for "+ target+"\n\n" 
    with open(file_to_attach, "rb") as f:
        for line in f: 
            if (("WARNING: " in line) or ("_ERROR_" in line) or ("ERROR" in line)): 
                message = message + line + "\n"
        #message = message + "Final result :\n" +line   #<--- Need to review 

    filename = file_to_attach

    msg = MIMEMultipart()
    msg['To'] = ", ".join(recipient)
    msg['From'] = sender
    msg['Subject'] = subject

    f = file(filename)
    attachment = MIMEText(f.read())
    attachment.add_header('Content-Disposition', 'attachment', filename=filename)           
    msg.attach(attachment)

    part = MIMEText('text', "plain")
    part.set_payload(message)
    msg.attach(part)

    session = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    session.ehlo()
    session.starttls()
    session.ehlo
    session.login(sender, password) 
    session.sendmail(sender, recipient, msg.as_string())
    session.quit() 



class Jbot:
    def __init__(self, procedure):
        # Initializing some variables, just in case
        path, self.procedure_name = os.path.split(procedure)

        logger.info('PROCEDURE_START: Procedure "%s" has started.', self.procedure_name)
        self.actual_block_id = 0
        self.next_block_id = 0
        self.actual_block_type = "none"
        # Dynamic variables inside the class (future feature)
        #self.vars = {}                
        
        # Reading and importing the procedure in yaml format
        
        try:
            with open(procedure) as f: 
                self.__procedure_yaml = yaml.load(f)
            self.__procedure_blocks = self.__procedure_yaml.keys()
            self.__procedure_blocks.sort()
            self.actual_block_id = self.__procedure_blocks[0]  # Now ALL procedures starts in the FIRST step/block '1' (make sense)
            self.next_block_id = self.actual_block_id # This is a hack in order to manage the case of first block in the 'step method'
            self.actual_block_type = self.__procedure_yaml[self.actual_block_id].keys()[1]
            
            # Establishing connections
            self.targets = AutoVivification()  # I think this is not needed, a basic dict should be enough
            # NOTE: junos-eznc-1.1.0 and earlier versions have a bug connecting to junos devices with 'non-official' 
            # format like daylies. so gather_facts=False is workaroudn
        except IndexError as ierr:
            logger.error('Exception: %s, <<: *defaults must be properly defined/idented in each step of procedure',ierr)
            sys.exit(1)    
        for t in target_list:
            try:
                self.targets[t]['Device'] = Device(user=user, host=target_list[t], password=passwd, gather_facts=True,auto_probe=True)
                self.targets[t]['Device'].open()
                self.targets[t]['Device'].timeout = 120*120
                self.targets[t]['JRouter'] = JRouter(user, target_list[t], passwd)
            except ConnectError as c_error:
                logger.error('Exception,Connection timeout: %s ',c_error)
                sys.exit(1)
        
    def step(self):
        try:    
            self.actual_block_id = self.next_block_id
            actual_block_keys = self.__procedure_yaml[self.actual_block_id].keys()
            # Remove known _keys_ 
            known_block_keys = [ 'onError', 'then','target']
            for key in known_block_keys:
                try:
                    actual_block_keys.remove(key)
                except ValueError:
                    pass
            # The remaining key is the action to perform
            if (len(actual_block_keys) == 1):
                self.actual_block_type = actual_block_keys[0]
            else:
                logger.info('There are unknown statements on block: %d %d', self.actual_block_id, self.next_block_id)
            
            self.next_block_id = -1  # At the end of this method this should NOT be -1, if so, there is a workflow issue
            block_result = -1 # At the end of this method this should NOT be -1, if so, there is a  issue
            
            #  Call method that matches block type
            
            if (self.actual_block_type == 'end'):
                self.__block_end()
            elif (self.actual_block_type == 'end_failure'):
                self.__block_end_failure()
            elif (self.actual_block_type == 'sleep'):
                self.__sleep()
            else:
                logger.info('Procedure: %s: Block to be executed: %d', self.procedure_name, self.actual_block_id)
                logger.info('Block info: \n%s', yaml.dump(self.__procedure_yaml[self.actual_block_id]))
                attr = self.__procedure_yaml[self.actual_block_id][self.actual_block_type]
                if 'target' in  self.__procedure_yaml[self.actual_block_id]:
                    group_result = True
                    for t in self.__procedure_yaml[self.actual_block_id]['target'].split():  # Need to check if target exists
                        try:    
                            if attr != None:
                                if (self.actual_block_type == 'procedure'):
                                    result = self.__procedure(**attr)
                                else:
                                    result = getattr(self.targets[t]['JRouter'],self.actual_block_type)(self.targets[t]['Device'],**attr)
                            else:
                                if (self.actual_block_type == 'procedure'):
                                    logger.error('Sub procedure MUST have arguments:')
                                    sys.exit(1)
                                else:
                                    result = getattr(self.targets[t]['JRouter'],self.actual_block_type)(self.targets[t]['Device'])
                            if (isinstance(result, bool)):
                                group_result = group_result and result
                            else:  # Something happens in the method because it did NOT return a boolean, exiting
                                logger.error('Something happened, result is not boolean (True/False): %s', result)
                                self.__block_end_failure()
                        except TypeError as t_error:
                            logger.error('Exception,Type error: %s ',t_error)
                            logger.info (JRouter.__doc__)
                            sys.exit(1)
                        except AttributeError as a_error:
                            logger.error('Exception,Attribute error: %s ',a_error)
                            logger.info (JRouter.__doc__)
                            sys.exit(1)   
                    self.__get_next_block(group_result)
                else:
                    logger.error("ERROR: Missing 'target' definition in step %s", self.actual_block_id)
                    sys.exit(1)
        except RuntimeError as r_time:
            logger.error('Exception: %s, Yaml file must be properly defined/idented in each step of procedure',r_time)
            sys.exit(1)    

    def __block_end(self):
        logger.info('PROCEDURE_ENDED: Procedure "%s" finished successfully!!!',self.procedure_name)
        #send_mail(self.debug_file)
        # At this point we could send syslog/mail/report, etc or do nothing

    def __block_end_failure(self):
        logger.error('PROCEDURE_STOPPED: Problems "%s" found during execution.',self.procedure_name)
        #send_mail(self.debug_file)
    def __sleep(self):
        
        timer = self.__procedure_yaml[self.actual_block_id][self.actual_block_type]
        
        if isinstance(timer, int):
            result = True
            logger.info('Block info: \n%s', yaml.dump(self.__procedure_yaml[self.actual_block_id]))
            sleep(float(timer))
            self.__get_next_block (result)
        else:
            logger.error("Sorry,sleep must be an integer")
            result = False
            self.__get_next_block (result)         
        
    def __get_next_block(self, result):  # not sure... if next_tag contains id
        # If block have 'then' sentence then next_block is that value
        # if there is NOT 'then' sentece, check the next contiguos block in the procedure
        
        if result:
            if 'then' in self.__procedure_yaml[self.actual_block_id]:
                self.next_block_id = self.__procedure_yaml[self.actual_block_id]['then']
                
            else:  # By default the 'next' block in case of True is the contiguos step
                for block,next_block_id in zip(self.__procedure_blocks, self.__procedure_blocks[1:]+[self.__procedure_blocks[0]]):
                    if (block == self.actual_block_id):
                        self.next_block_id = next_block_id
            logger.info('Block result is TRUE, next block is: %s', self.next_block_id )
        else: 
            if 'onError' in self.__procedure_yaml[self.actual_block_id]:
                self.next_block_id = self.__procedure_yaml[self.actual_block_id]['onError']
                logger.info('Block result is FALSE, next block is: %s', self.next_block_id )
            else:  # There is no default value 'so far', so a error is triggered.
                #self.__logging("__get_next_block","4","No _onError statement found on blcok: "+str(self.actual_block_id))
                logger.error('No onError statement found on block: %s', self.actual_block_id )
                self.__block_end_failure()

    def __procedure(self,procedure_name):
        # What if the sub procedure has more arguments than main procedure....???  So far same BOTH procedure MUST have same arguments
        inner_jbot = Jbot(procedure_name)
        while (inner_jbot.actual_block_type not in ("end","end_failure")):
            inner_jbot.step()
        if (inner_jbot.actual_block_type == "end"):
            return True
        else:
            return False
            
    def run(self):
        pass   

################################################################################################ 
################################################################################################
################################################################################################

# SCRIPT STARTS HERE

################################################################################################
################################################################################################
################################################################################################


################################################################################################
# Create and Parse Arguments
################################################################################################

parser_tmp = argparse.ArgumentParser(add_help=False)
parser_tmp.add_argument("--procedure", help="Procedure to be execute by Jbot", default = 'default_variables.txt')
full_parser = argparse.ArgumentParser()
full_parser.add_argument("--procedure", help="Procedure to be execute by Jbot", default = 'default_variables.txt')
full_parser.add_argument("--user", help="Username to be used")
full_parser.add_argument("--passwd", help="Password to be used")
full_parser.add_argument("-c", "--console", action='store_true', help="Console logs enabled")
procedure_yaml = {}
with open(parser_tmp.parse_known_args()[0].procedure, 'r') as f:
    procedure_yaml = yaml.load(f)
    if 'variables' in procedure_yaml:
        for variable in procedure_yaml['variables']:
            if 'description' in procedure_yaml['variables'][variable].keys():
                full_parser.add_argument('--' + variable, help=procedure_yaml['variables'][variable]['description'])
            else:
                full_parser.add_argument('--' + variable)
dynamic_args = vars(full_parser.parse_args())

################################################################################################
# Validate Arguments
###############################################################################################

###  Known and fixed arguments
if dynamic_args['procedure']:
    procedure = dynamic_args['procedure']
else:
    sys.exit("ERROR: No 'procedure' has been specified")
if dynamic_args['user']:
    user = dynamic_args['user']
else:
    sys.exit("ERROR: Missing 'user' argument")
if dynamic_args['passwd']:
    passwd = dynamic_args['passwd']
else:
    sys.exit("ERROR: Missing 'passwd' argument")    
###  Dynamic arguments
target_list = AutoVivification()
if 'variables' in procedure_yaml:
    for variable in procedure_yaml['variables']:
        if dynamic_args[variable]:
            if (procedure_yaml['variables'][variable]['type'] == 'target'):
                target_list[variable]=dynamic_args[variable]
            else:
                sys.exit("ERROR: Unknown variable type on procedure: " + variable)
        else:
            sys.exit("ERROR: Missing "+ variable + " argument")

################################################################################################
# JBOT starts here start 
################################################################################################

# Setting up logging directories and files
timestamp = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime(time.time()))
path,main_procedure_name = os.path.split(procedure)
project = main_procedure_name + "_" + timestamp
log_dir = "./logs/" + project
logger = logging.getLogger("__JBot__")
if not os.path.exists(log_dir):
    os.makedirs(log_dir, 0755)
formatter = '%(asctime)s %(name)s %(levelname)s:  %(message)s'
logging.basicConfig(filename=log_dir + "/"+ project + '_jbot.log',level=logging.INFO,format=formatter, datefmt='%Y-%m-%d %H:%M:%S')

if dynamic_args['console']:
    print "Console logs enabled"
    console = logging.StreamHandler()
    console.setLevel (logging.INFO)
    logging.getLogger('').addHandler(console)

my_Jbot = Jbot(procedure)
while (my_Jbot.actual_block_type not in ("end","end_failure")):
    my_Jbot.step()

