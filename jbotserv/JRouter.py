#!/usr/bin/env python
# coding: utf-8
# Authors: psagrera@juniper.net
# Version: 1.0 20150122 


# xml specific
from lxml import etree  
from lxml.builder import E 
import xml.etree.ElementTree as ET
import xml.dom.minidom  
import lxml

# stdlib
import StringIO 
import re 
import subprocess as sub
from subprocess import Popen, PIPE
import os  
import sys 
import pdb
import errno
import time
from datetime import datetime
from time import sleep 
from pprint import pprint 
import logging
import hashlib
from socket import error as SocketError
import errno
import signal
#third-party 
import xmltodict 
import yaml
import paramiko
import ncclient.operations
import ncclient.transport.errors as NcErrors
import ncclient.operations.errors as TError
# junos-ez 
from jnpr.junos.utils.scp import SCP
from jnpr.junos.utils.fs import FS
from jnpr.junos.exception import *
from jnpr.junos.utils.config import Config
from jnpr.junos.utils.sw import SW
from jnpr.junos.utils.start_shell import StartShell
from jnpr.junos import Device


# Global Variables
timestamp =  datetime.now().strftime("%Y-%m-%d")
timestamp2 =  datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
timestamp3 = datetime.now().strftime ("%H_%M_%S")
timestamp4 = datetime.now().strftime ("%Y-%m-%d %H:%M:%S")

# Reduce verbosity 
logging.getLogger("paramiko").setLevel(logging.WARNING)


class JUpgrade (object):

        """
            ------- Functions starts here -------
        
        """
    
        def _is_dual_RE (self,conn):

            """
                Auxiliar function that return True if the system is dual-RE and both RE are available
            """
            
            try:
                re_info = conn.rpc.get_route_engine_information ()
                re_list = re_info.xpath('.//route-engine')

                if len(re_list) > 1:
                    return True
                else:
                    return False
            
            except RpcError as err:
                rpc_error = err.__repr__()
                self.logger.error(xmltodict.parse(rpc_error)['rpc-error']['error-message'])
                return False
        
        def get_slot_backup (self,conn):
            
            """
                Function that returns the backup slot (0|1)
            """
            
            try:
                inv = conn.rpc.get_route_engine_information()
                slot = inv.xpath ('//route-engine[mastership-state!="master"]/slot')
                return slot[0].text
            except IndexError as index_error:
                self.logger.error (index_error)
                return False
            except RpcError as err:
                rpc_error = err.__repr__()
                self.logger.error(xmltodict.parse(rpc_error)['rpc-error']['error-message'])
                return False

        def get_slot_master (self,conn):
            
            """
                Function that returns the master slot (0|1)- Only applicable in Dual-RE environment

            """
            
            try:
                inv = conn.rpc.get_route_engine_information()
                if conn.facts['2RE']:
                    slot = inv.xpath ('//route-engine[mastership-state="master"]/slot')
                    return slot[0].text
                else:
                    self.logger.error ("Not slot number in Single RE system")
                    return False
            except IndexError as index_error:
                self.logger.error (index_error)
                return False
            except RpcError as err:
                rpc_error = err.__repr__()
                self.logger.error(xmltodict.parse(rpc_error)['rpc-error']['error-message'])
                return False
               
        def RE_snapshot (self,conn,role): 


            """
                Function that takes a snapshot on the Routing Engine

                role:master/backup
                
                - yaml file syntax example:
                    
                    2: 
                       RE_snapshot: 
                       role: backup               
            """
            
            if self._is_dual_RE (conn) and role == 'backup': 

                slot_b = self.get_slot_backup(conn)
                self.logger.info ("Executing request system snapshot in the Backup RE.....")

                try:
                    if slot_b == '1':
                        conn.rpc.request_snapshot (re1=True,dev_timeout=100)
                        self.logger.info ("Snapshot successfull.....")
                        return True
                    else:
                        conn.rpc.request_snapshot (re0=True,dev_timeout=100)
                        self.logger.info ("Snapshot successfull.....")
                        return True
            
                except RpcError as err:
                    rpc_error = err.__repr__()
                    print rpc_error
                    #self.logger.error(xmltodict.parse(rpc_error)['rpc-error']['error-message'])
                    return False
            else:
                try:
                   self.logger.info ("Executing request system snapshot .....")
                   conn.rpc.request_snapshot ()
                   self.logger.info ("Snapshot successfull.....")
                   return True
                except RpcError as err:
                    rpc_error = err.__repr__()    
                    self.logger.error(xmltodict.parse(rpc_error)['rpc-error']['error-message'])
                    return False

        def add_sw_package (self,conn,version,role,validate=True): 
            
            """
              Function that install a Junos package on the Routing Engine 
    
                  version = JUNOS package to install (i.e jinstall64-12.2X49-D40.1-domestic-signed.tgz)   
                  role = Either master or backup    
                  validate = Check compatibility with current configuration (True or False)    
                      warning: junos package must exist in /var/tmp directory
                      - yaml file syntax example:
                      
                      3:
                         add_sw_package:
                           version: jinstall-12.3R4.6-domestic-signed.tgz
                           validate: True
                           role: master         
            """
            
            my_SW = SW (conn)
            
            sw_version = "" + version
            
            args = dict(no_validate=validate,package_name=sw_version)
            #args.update (kvargs)
            
            if not isinstance(validate, bool):
                self.logger.error("Sorry. 'validate' must be a boolean (True/False).Argument passed: %s",validate)
                return False

            if role != "backup" and role!="master":
               self.logger.error("Sorry. 'role' must be a master or backup. Argument passed: %s",role) 
               return False
            
            # Dual RE and role backup
            
            if self._is_dual_RE (conn) and role == 'backup': 
                
                slot_b = self.get_slot_backup(conn)
                version_backup = conn.rpc.cli ('show version invoke-on other-routing-engine',format = 'xml')
                
                if version_backup.xpath ("//software-information/package-information[name='jinstall']"):
                                  
                  jinstall_rollback = """ 
                          <request-package-rollback>
                          <re""" + slot_b + """></re"""+slot_b+ """>
                          </request-package-rollback>
                  """
                  self.logger.info ("package installation detected...Executing request system rollback...")
                  jrollback = conn.execute (jinstall_rollback)        
                  
                  if len(jrollback) > 0:
                      pass
                  else:
                      return False                                                  
                
                try:
                      if slot_b == "1":
                          self.logger.info("Trying to install package in re" + slot_b + ",please be patient.....")
                          if validate:
                            pack_add_rpc = conn.rpc.request_package_add (package_name = sw_version,re1=True,dev_timeout=100)
                          else:
                            pack_add_rpc = conn.rpc.request_package_add (package_name = sw_version,no_validate=True,re1=True,dev_timeout=100)
                          got = pack_add_rpc.getparent ()
                          rc = int(got.findtext('package-result').strip())
                          if rc == 0:
                              self.logger.info ("package added successfully !!!")
                              return True
                          else:
                              pack_err = got.findtext('output').strip()
                              self.logger.error (pack_err)
                              return False
                      else:
                          self.logger.info("Trying to install package in re" + slot_b + ",please be patient.....")                    
                          if validate:
                            pack_add_rpc = conn.rpc.request_package_add (package_name = sw_version,re0=True,dev_timeout=100)
                          else:
                            pack_add_rpc = conn.rpc.request_package_add (package_name = sw_version,no_validate=True,re0=True,dev_timeout=100)
                          got = pack_add_rpc.getparent ()
                          rc = int(got.findtext('package-result').strip())
                          if rc == 0:
                              self.logger.info ("package added successfully !!!")
                              return True
                          else:
                              pack_err = got.findtext('output').strip()
                              self.logger.error (pack_err)
                              return False
                except RpcError as err:
                  rpc_error = err.__repr__()
                  self.logger.error(xmltodict.parse(rpc_error)['rpc-error']['error-message'])
                  return False
            
            # Single RE or Master RE in DUAL-RE system or DUAL-RE system capable with only one available RE
            else:
                version_master = conn.rpc.get_software_information()

                if version_master.xpath ("//software-information/package-information[name='jinstall' or name = 'jinstall-ppc']"):
                    try:
                        self.logger.info ("package installation detected...Executing request system rollback...")
                        pack_roll=conn.rpc.request_package_rollback ()
                        got = pack_roll.getparent()
                        pack_error = got.findtext('output').strip()
                        # to catch messages like : ERROR: Another package installation in progress
                        if "ERROR" in pack_error:
                           self.logger.error (pack_error)
                           return False
                        else: 
                            pass
                    except RpcError as err:
                        rpc_error = err.__repr__()
                        self.logger.error(xmltodict.parse(rpc_error)['rpc-error']['error-message'])
                        return False                    
                
                try:
                    self.logger.info ("Trying to install software, please be patient.....")
                    if validate:
                        pack_add_rpc = conn.rpc.request_package_add (**args)
                        #pack_add_rpc = conn.rpc.request_package_add (package_name = sw_version)
                    else:
                        pack_add_rpc = conn.rpc.request_package_add (**args)
                        #pack_add_rpc = conn.rpc.request_package_add (package_name = sw_version,no_validate=True)
                    got = pack_add_rpc.getparent ()
                    file_error = got.findtext('output').strip()
                    
                    # If the file doesn't exist in the master Routing Engine, we need to catch it
                    if "ERROR" in file_error:
                        self.logger.error (file_error)
                        return False
                    else:
                        rc = int(got.findtext('package-result').strip())
                        if rc == 0:
                            self.logger.info ("package added successfully !!!")
                            return True
                        else:
                            pack_err = got.findtext('output').strip()
                            self.logger.error (pack_err)
                            return False
                    
                except RpcError as err:
                    rpc_error = err.__repr__()
                    self.logger.error(xmltodict.parse(rpc_error)['rpc-error']['error-message']) 
                    return False

        def jsnap (self,conn,type,test,snap_type,argument,mode="loose"):

                """
                        Function that execute jsnap tool 
                                                            
                            type = "pre" "post" or "check" depending on the action you want to achieve                                
                            test = path to file that contains jsnap tests                              
                            snap_type = "snap" , "snapchek" or "check" 
                            mode = either loose or strict (only valid for check section)
                                   
                                   loose : if the word "ERROR" is found during CHECK section it will return True
                                   strict: if the word "ERROR" is found during CHECK section it will return False
                                   
                            
                            - yaml file syntax example:

                                1:
                                   jsnap:
                                     type: pre
                                     test: jsnap_test/cang_validator.jsnap
                                     snap_type: snap 
                                1:
                                   jsnap:
                                     type: check
                                     test: jsnap_test/cang_validator.jsnap
                                     snap_type: check
                                     mode: strict
                                1:
                                   jsnap:
                                     type: snapcheck
                                     test: jsnap_test/cang_validator.jsnap
                                     snap_type: snapcheck
                                                                                               
                    
                """                

                dirpath = self.log_dir + "/snapshot/"
                
                if not os.path.exists (dirpath):
                     os.makedirs (dirpath,mode=0777)                    
                
                timestamp =  datetime.now().strftime("%Y-%m-%d")
                
                if snap_type == "snap":
                    
                    cmd = 'jsnap --snap' + " " + argument + ' -l ' + self.user + ' -p ' + self.password + ' -t ' + self.target  + ' /jbotserv/' + test
                    self.logger.info('Collecting Snapshot %s\n', argument)
		    jsnap_command = sub.Popen (cmd,stdout=sub.PIPE,stderr=sub.PIPE, shell=True,cwd=dirpath)
                    #tu = jsnap_command.communicate()
                    #print "TU:\n"
                    output, errors = jsnap_command.communicate()
                    if ((("Exiting." in errors) and ("jsnap" in jsnap_command)) or("Unable to connect to device: " in errors) and ("jsnap in command") or ("jsnap: not found" in errors)):
                        return False
                    else:
                        return True 
                    return True
                
                elif snap_type == "snapcheck":
                    
                    cmd = 'jsnap --'+ snap_type + " " + timestamp + '_'+ type + ' -l ' + self.user + ' -p ' + self.password + ' -t ' + self.target + ' /jbotserv/' + test
                    self.logger.info('Executing: %s', cmd)
                    jsnap_command = sub.Popen (cmd,stdout=sub.PIPE,stderr=sub.PIPE, shell=True,cwd=dirpath)
                    output, errors = jsnap_command.communicate()
                    
                    self.logger.info(output)
                    self.logger.info(errors)
                    
                    if ((("Exiting." in errors) and ("jsnap" in jsnap_command)) or("Unable to connect to device: " in errors) and ("jsnap in command") or ("jsnap: not found" in errors)):
                        return False
                    else:
                        return True 
                    return True            

                elif snap_type == "check":
                    cmd_check = '/usr/jawa/jsnap/jsnap --check' + " " + argument  + ' -l ' + self.user + ' -p ' + self.password + ' -t ' + self.target + ' /jbotserv/' + test 
                    self.logger.info('Comparing Snapshots: %s', argument)
                    jsnap_command = sub.Popen (cmd_check,stdout=sub.PIPE,stderr=sub.PIPE, shell=True,cwd=dirpath)
                    output, errors = jsnap_command.communicate()                     
                    self.logger.info(output)
                    self.logger.info(errors)
                    
                    if ((("Exiting." in errors) and ("jsnap" in jsnap_command)) or ("Unable to connect to device: " in errors) and ("jsnap" in jsnap_command) or ("jsnap: not found" in errors) or ("There are no snapfiles" in output )):
                        
                        self.logger.info(output)
                        self.logger.info(errors)
                        return False
                    
                    else:
                        if mode == "strict":
                            print "This is the output: " + output
                            if "ERROR" in output or "ERROR" in errors or "TEST FAILED" in output or "TEST FAILED" in errors:
                                return False
                            else:
                                return True
                        else:

                            return True
                else:
                    self.logger.error("Invalid snap type")
                    return False

        def switchover (self,conn):
            """
                Function to perfom RE switchover 
                todo:: test in-band connections
                - yaml file syntax example:
                    
                    8:
                       switchover:                    

            """
            # We need to verify that backup RE is ready before proceed
            b_slot = self.get_slot_backup(conn)
            b_state = conn.rpc.get_route_engine_information(slot=b_slot)
            state = b_state.findtext ('route-engine/mastership-state')
            
            if (state != "backup"):
                self.logger.error ("Backup RE is not ready")            
                return False
                
            try:
                conn.open()
                self.logger.warning('Executing switchover to complete the SW upgrade !!!')
                switchover_cmd = conn.cli ("request chassis routing-engine master switch no-confirm",format='xml',warning=False)
                conn.close ()
            except ConnectError as c_error:
                self.logger.error('Exception,Connection timeout: %s ',c_error)
                return False  
            except TError.TimeoutExpiredError as Terr:
                self.logger.warning (Terr)
                pass
            except NcErrors.SessionCloseError as Serr:
                self.logger.warning (Serr)
                pass
            except SocketError as S_err:
                self.logger.warning (S_err)
                pass
            sleep (60)
            try:
                print "Re-opening connection......."
                conn.open(auto_probe=300)
                return True
            except ConnectError as c_error:
                logger.error('Exception,Connection timeout: %s ',c_error)
                return False
        
        def reboot_RE (self,conn,role):
            """
                Function for rebooting backup RE
                role: master/backup               
            """
            #Dual RE and role backup
            if self._is_dual_RE (conn) and role == 'backup': 

                try:
                    self.logger.info ("Rebooting Backup Routing Engine....")
                    cmd = conn.rpc.request_reboot (other_routing_engine = True)
                    # sleeping to avoid quick return
                    sleep (1500)
                    return True 
                except RpcError as err:    
                    rpc_error = err.__repr__()
                    self.logger.error(xmltodict.parse(rpc_error)['rpc-error']['error-message'])
                    return False       
            # Single RE or DUAL-RE system capabable with only 1 available RE
            else:                
                
                try:
                   self.logger.info ("Rebooting Master Routing Engine....")
                   cmd = conn.rpc.request_reboot ()
                   self.logger.info("Closing connection....")       
                   #conn.close ()
                   self.logger.info("Connection closed....")
                   
                   self.logger.info("Waiting for RE to reboot....")
                   sleep (1500)
                   try:
                       conn.open(auto_probe=600)
                       return True
                   except ConnectError as c_error:
                       print timestamp4 + "__JRouter__ ERROR: Routing Engine is not Online after 10 min" + str(c_error)
                       return False
                
                except RpcError as err:
                    rpc_error = err.__repr__()
                    self.logger.error(xmltodict.parse(rpc_error)['rpc-error']['error-message'])
                    return False        
        
        def check_version (self,conn,version,role):
            
            """
                Function that reboots the Routing Engine if the version in jinstall package is the correct one

                    version = JUNOS version to be installed (i.e 12.2X49-D40.1)
                    role = master/backup
                    
                    - yaml file syntax example:
                    
                    7:
                       check_version_to_reboot:
                         version: "12.3R4.6"
            """
            
            # Dual RE and role backup
            if self._is_dual_RE (conn) and role == 'backup': 
                b_slot = self.get_slot_backup (conn)
                check_version_reboot_cmd = conn.rpc.cli ("show version invoke-on other-routing-engine",format = 'xml')
                version_loaded = check_version_reboot_cmd.xpath ('//multi-routing-engine-item[re-name="re'+b_slot+'"]/software-information/package-information[name="jinstall" or name = "jinstall-vmx"]')
            
                # checking whether jinstall package is in the list to be installed
                if len(version_loaded) <= 0:
                    self.logger.error ("No jinstall package to be installed !!  ")
                    return False
                else: 
                    for ver in version_loaded:
                        comment = ver.xpath ('comment')[0].text   
                        if (version in comment):  
                            return True
                        else:
                            #self.logger.error ("Version loaded in jinstall doesn't match with the version to load: %s %s!!  ",comment,version )
                            #return False
			    return True
            #Single RE or Dual RE capable with only one RE available
            
            else:
                check_version_reboot_cmd = conn.rpc.get_software_information ()               
                version_loaded = check_version_reboot_cmd.xpath ("//software-information/package-information[name='jinstall' or name='jinstall-ppc' or name='jinstall-vmx']")
   
                if len(version_loaded) <= 0:
                    self.logger.error ("No jinstall package to be installed !!  ")
                    return False
                else:
                    for ver in version_loaded:
                        comment = ver.xpath ('comment')[0].text
                        if (version in comment):
                            return True
                        else:
                            self.logger.error ("Version loaded in jinstall doesn't match with the version to load: %s %s !!  ",comment,version )
                            return False                        
                
        def scp_package (self,conn,package):
            
            """
                Function that copy the install package safely to the remote device (/var/tmp)
                and perform MD5 checksum

                    
                todo:: iterative (trying a couple of times in case of transmission issues)
                
                - yaml file syntax example:

                1:
                   scp_file:
                     package: jinstall-ppc-13.3R4.6-domestic-signed.tgz
                   
            """
            
            my_scp = SW (conn)
            self.logger.info("Sending package....")
            
            return my_scp.safe_copy (package,progress=myprogress2,cleanfs=True)                
        
        def __myprogress(self, conn, report):
            
            print "{0}:{1}".format(conn.hostname, report)

def myprogress2(conn, message):
        print "{0}:{1}".format(conn.hostname, message)


class JChecker(object):
        
        """
           
           Class that contains functions for verifying Device/s state
            
            ------- Functions starts here -------

        """

        def check_krt_queue (self,conn,polling_time,iterations=5):
        
            """
                Function that checks if there is routes stuck in the Kernel routing table (krt)
                    
                    + polling_time :pause (in seconds) between iterations (must be an integer)
                    + iterations = number of iterations to execute (must be > than 0 and integer)
                    
                    - yaml file syntax example:
                        
                        3:
                            check_krt_queue:
                                iterations: 3
                                polling_time: 10
                                
            """
            
            krtq_queue_length = "0"
            krtq_type = ""
            message = "Maximun number of iterations have been reached, process will be stopped at this point!!"
            

            if iterations == 0:
                self.logger.warning("Sorry. 'iterations' must be > than 0....setting a deafult value of 5")
                iterations = 5
            
            if not isinstance(iterations, int):
                self.logger.error("Sorry. 'iterations' must be an integer.")
                return False
            
            if not isinstance(polling_time, int):
                self.logger.error("Sorry. 'polling_time' must be an integer.")
                return False
            
            if (iterations > 0) :

    
                try:
                    inv = conn.rpc.get_krt_queue_information()
                    krtq_queue = inv.xpath ('//krt-queue')
                           
                    for krt in krtq_queue:
                    
                        krtq_type = krt.xpath ('krtq-type')[0].text
                        krtq_queue_length = krt.xpath ('krtq-queue-length')[0].text
                    
                        if krtq_queue_length != "0":
                            self.logger.info('Checking krt queue, iteration:%d,krtq_queue_length:%s',iterations,krtq_queue_length)
                            sleep (polling_time)
                            self.check_krt_queue(conn,iterations - 1)
                    
                    self.logger.info('No routes in krt queue,iteration:%d,krtq_queue_length:%s,check successfull',iterations,krtq_queue_length)
                    return True                
                except RpcError as err:
                    rpc_error = err.__repr__()
                    self.logger.error(xmltodict.parse(rpc_error)['rpc-error']['error-message'])
                    return False               
            else:

              self.logger.error(message)  
              return False

        def check_krt_state (self,conn,polling_time,iterations=5):

            """ 
                Function that checks if there is operations queued in the Kernel routing table (krt)

                    + polling_time :pause (in seconds) between iterations (must be an integer)
                    + iterations = number of iterations to execute (must be > than 0 and integer)
                    
                    - yaml file syntax example:
                        
                        4:
                            check_krt_state:
                                iterations: 3
                                polling_time: 10
            """

            krtq_operations_queued = "0"
            message = "Maximun number of iterations have been reached, process will be stopped at this point!!"

            if iterations == 0:
                self.logger.warning("Sorry. 'iterations' must be > than 0....setting a default value of 5")
                iterations = 5
            
            if not isinstance(iterations, int):
                self.logger.error("Sorry. 'iterations' must be an integer.")
                return False
            
            if not isinstance(polling_time, int):
                self.logger.error("Sorry. 'polling_time' must be an integer.")
                return False            
            

            if (iterations > 0) :
                try:
                    inv = conn.rpc.get_krt_state()
                    krtq_operations_queued = inv.xpath ('//krt-queue-state/krtq-operations-queued')[0].text
                    if krtq_operations_queued != "0":
                        self.logger.info('Checking krt state, iteration:%d,krtq_operations_queued:%s',iterations,krtq_operations_queued)
                        sleep (polling_time)
                        self.check_krt_state (conn,iterations - 1)
                    else:    
                        self.logger.info('No operations queued,iteration:%d,krtq_operations_queued:%s, check successfull',iterations,krtq_operations_queued)
                        self.logger.info('Check passed !!!')
                        return True
                except RpcError as err:
                   rpc_error = err.__repr__()
                   self.logger.error(xmltodict.parse(rpc_error)['rpc-error']['error-message'])
                   return False  
            else:
              self.logger.error(message)  
              return False                  
        
        def wait_for_routes_holddown (self,conn,polling_time,table_list="",iterations=5):
          
                """
                 function for checking routes in holdown within the tables specified in table_list
                    
                    iterations = number of iterations to execute                  
                    polling_time = pause (in seconds) between iterations                     
                    table_list = list of tables to check (i.e inet.0,inet.6,....)

                    - yaml file syntax example:
                        
                        2:
                            wait_for_routes_holddown:
                                iterations: 3
                                polling_time: 10
                                table_list: "inet.0,inet.3"

                 """                             
                r_hold_bgpl3vpn0 = "0"
                r_hold_inet0 = "0"
                r_hold_inet6 = "0"
                message = "Maximun number of iterations have been reached, process will be stopped at this point!!"
                holddown = {}
            
                if table_list == "":
                    self.logger.error("Sorry. 'table_list' cannot be an empty variable.")
                    return False            

                if iterations == 0:
                    self.logger.warning("Sorry. 'iterations' must be > than 0....setting a deafult value of 5")
                    iterations = 5
                
                if not isinstance(iterations, int):
                    self.logger.error("Sorry. 'iterations' must be an integer.")
                    return False
                
                if not isinstance(polling_time, int):
                    self.logger.error("Sorry. 'polling_time' must be an integer.")
                    return False
                              

                if (iterations > 0):
                    sleep (polling_time)
                    try:
                        inv = conn.rpc.get_route_summary_information()
                        r_hold = inv.xpath ("//route-table")
                        
                        for table in r_hold:
                            if table.xpath('table-name')[0].text in table_list:
                                holddown[table.xpath('table-name')[0].text]= table.xpath('holddown-route-count')[0].text
                        values = holddown.values()
                        keys = holddown.keys()
                        if values.count('0') != len(values):
                            self.logger.info('Checking routes in holdown,iteration:%d',iterations)
                            for k,v in zip(keys,values):
                                self.logger.info('Routes in holddown %s %s',k,v)
                            self.check_holddown (conn,iterations - 1,polling_time,table_list)
                        else:
                            self.logger.info('No routes in holdown,iteration:%d, check successfull',iterations)
                            return True
                    except RpcError as err:
                        rpc_error = err.__repr__()
                        self.logger.error(xmltodict.parse(rpc_error)['rpc-error']['error-message'])
                        return False
                else:
                    self.logger.error(message)
                    return False     
               
        def wait_fpc_status (self,conn,polling_time,iterations):
            
            """
                Dummy function that call 'call_wait_fpc_status'  
                
                 iterations = number of iterations

                 - yaml file syntax example:
                    
                    9: 
                       wait_fpc_status:
                         iterations: 10 
                         polling_time: 60   
            """
            
            return self.__call_wait_fpc_status (conn,iterations,polling_time,self.__get_slot_fpcs_no_empty(conn))

        def __call_wait_fpc_status (self,conn,iterations,polling_time,fpc_list,cont_ready=0,cont_pending=0):
            
            """
                Function that checks that FPCs are fully ready (only takes care of not empty slots):

                      1  Online            32      7          0       2048       11         13 --> OK
                      2  Online             0      0          0          0        0          0 --> NOK 

                 iterations = number of iterations
                 
                 **fpc_list = number of FPCs to check, we call this function: get_slot_fpcs_no_empty, from the 
                    dummy function (wait_fpc_status)      
                 
                 cont_ready = counter for tracking FPCs ready
                 
                 cont_pending = counter for tracking FPCs pending
                
                **Need to handle the case where after RE reboot (mx80 for instance) chassis fpc command returns "Empty"
                    + need to test in single RE system and/or mx240/mx480/m320/m120
            """


            message = "Maximun number of iterations have been reached, process will be stopped at this point!!"
            
            state = {}
            fpc_list_aux = ()

            if not isinstance(iterations, int):
                self.logger.error("Sorry. 'iterations' must be an integer.")
                return False     
           
            if (iterations > 0): 

                if len(fpc_list) > 0:
                    
                    self.logger.info ("----------------------------------------------")
                    self.logger.info ("Number of FPCs to check: %d,iterations pending: %d",len(fpc_list),iterations)
                    self.logger.info ("----------------------------------------------")    
                    
                    try:
                        inv = conn.rpc.get_fpc_information (dev_timeout=100)
                        fpcounter = inv.xpath ('//fpc[state != "Empty"]')
                            
                        for fpc in fpcounter:
                            
                            if fpc.findtext('slot') in fpc_list:
                                fpc_slot = fpc.findtext('slot')
                                fpc_st = fpc.findtext('state')
                                fpc_memory = fpc.findtext('memory-dram-size') 
                                state[fpc_slot] = [fpc_st,fpc_memory]
                        
                        values = state.values()
                        keys = state.keys()                        

                        for k,v in zip(keys,values):
                            cont_pending = 0
                            if v[0] != "Online" or v[1] == "0":
                                self.logger.info("Slot: %s,State: %s, DRAM: %s",k,v[0],v[1])
                                fpc_list_aux += (k,)
                                cont_pending = len (fpc_list_aux)
                            else: 
                                self.logger.info ("Slot: %s,State: %s, DRAM: %s, ready !!!",k,v[0],v[1])
                                cont_ready +=1
                                cont_pending = len (fpc_list_aux)
               
                        self.logger.info ("FPCs pending: %d, FPCs ready: %d",cont_pending,cont_ready)
                        if cont_pending == 0:
                            self.logger.info ("Check passed !!!")
                            return True 
                        sleep (polling_time)
                        return self.__call_wait_fpc_status (conn,iterations - 1,polling_time,fpc_list_aux,cont_ready,cont_pending)       
                            
                    except RpcError as err:
                        rpc_error = err.__repr__()
                        self.logger.error(xmltodict.parse(rpc_error)['rpc-error']['error-message'])
                        return False
                else:
                    self.logger.info ("Check passed !!!")
                    return True      
            else:
               self.logger.error(message)
               return False

        def __get_slot_fpcs_no_empty (self,conn):
            
            """
                Auxiliar function for retrieving non empty slots
            
            """

            fpc_slot = []
            try:
                inv = conn.rpc.get_fpc_information ()
                fpc_no_empty = inv.xpath ('//fpc[state != "Empty"]')
                for fpc in fpc_no_empty:
                    fpc_slot += fpc.findtext('slot')
                return  fpc_slot   
            
            except RpcError as err:
                rpc_error = err.__repr__()
                self.logger.error(xmltodict.parse(rpc_error)['rpc-error']['error-message'])
                return False
        
        def wait_for_RE_backup_status (self,conn,iterations,polling_time): 
          
                """
                    Function for checking RE BACKUP status
                        iterations = number of iterations                   
                        polling_time = sleep between iterations

                        - yaml file syntax example:
                        
                        1:
                           wait_for_RE_backup_status:
                             iterations: 15
                             polling_time: 60 

                                                                          
                """
                
                if not isinstance(iterations, int):
                    self.logger.error("Sorry. 'iterations' must be an integer.")
                    return False            

                if not isinstance(polling_time, int):
                    self.logger.error("Sorry. 'polling_time' must be an integer.")
                    return False
                
                b_slot = self.get_slot_backup (conn)
                
                if (iterations > 0 ):
                    try:
                        RE_state = conn.rpc.get_route_engine_information(slot = b_slot)
                        state = RE_state.findtext ('route-engine/mastership-state')
                        if (state == "Present"):
                            self.logger.info('RE state in iteration %s is: %s',iterations,state)
                            sleep (polling_time)
                            self.wait_for_RE_backup_status (conn,iterations - 1,polling_time)
                        else:
                            self.logger.info('RE state in iteration %s is: %s',iterations,state)
                            self.logger.info('Test passed !!!')
                            
                        return True
                    except RpcError as err:    
                        rpc_error = err.__repr__()
                        self.logger.error(xmltodict.parse(rpc_error)['rpc-error']['error-message'])
                        return False                       
                else:
                    self.logger.error('Maximun number of retries has been reached, test failed!!!') 
                    return False
                    
        def check_Routing_Engine_cpu_status (self,conn,role,iterations,polling_time,limit,cpu_idle_thresold=80,memory_util_thresold=75):

            """
                Functions for checking CPU status 
    
                    role = master/backup
                    iterations = number of iterations
                    polling_time = sleep between iterations
                    limit = number of intermediate tests that must be successfull to be considered the test OK
                    cpu_idle_thresold = cpu idle value acceptable
                    memory_util_thresold = memory value acceptable 
                        
                        Routing Engine status:
                          Slot 0:
                             [.........]
                            Memory utilization          15 percent 
                            CPU utilization:
                              [.........]  
                              Idle                      99 percent
                        
                        - yaml file syntax example:

                        4:
                           check_Routing_Engine_status:
                             role: "backup"
                             iterations: 3
                             polling_time: 10
                             limit: 1
                             cpu_idle_thresold: 60
                             memory_util_thresold: 75

            """

            counter_master = 0           
            counter_backup = 0
            
            cpu_state = {} 
            
            try:
                
                CPU_state = conn.rpc.get_route_engine_information ()
            
            except RpcError as err:
                    rpc_error = err.__repr__()
                    self.logger.error(xmltodict.parse(rpc_error)['rpc-error']['error-message'])
                    return False 
            
            CPU = CPU_state.xpath ('//route-engine')
                
            for i in range (iterations):
                
                self.logger.info('Iteration: %s \n', i+1)
                
                for cpu_st in CPU:
                
                    memory_utilization = cpu_st.findtext('memory-buffer-utilization')
                    cpu_idle = cpu_st.findtext('cpu-idle')
                    if self._is_dual_RE (conn):
                        cpu_mastership_state = cpu_st.findtext('mastership-state')
                    else:
                        cpu_mastership_state = 'master'
                    cpu_state [cpu_mastership_state] = [cpu_idle,memory_utilization]
                    
                    #master_values = {key:value for (key,value) in cpu_state.iteritems() if key == 'master' }
                    #backup_values = {key:value for (key,value) in cpu_state.iteritems() if key == 'backup' }
                    # For backward compatibility (python 2.6)
                    master_values = dict((key, value) for (key, value) in cpu_state.iteritems() if key == 'master' )
                    backup_values = dict((key, value) for (key, value) in cpu_state.iteritems() if key == 'backup' )
                m_value = master_values.values()
                b_value = backup_values.values()

                if role == 'master' and bool (m_value):
                    for item_master in m_value:
                        
                        if int(item_master[0]) >= cpu_idle_thresold and int(item_master[1]) <= memory_util_thresold:
                            self.logger.info ('CPU idle is : %s and memory usage is : %s in master RE, intermediate test OK',item_master[0],item_master[1])               
                        else:
                            self.logger.error('CPU idle is : %s and  memory usage is : %s in master RE, intermediate test NOT OK',item_master[0],item_master[1])
                            counter_master += 1
                elif role == 'backup' and bool (b_value):
                   
                   for item_backup in b_value:
                        if int(item_backup[0]) >= cpu_idle_thresold and int(item_backup[1]) <= memory_util_thresold:
                            self.logger.info ('CPU idle is : %s and memory usage is : %s in backup RE, intermediate test OK',item_backup[0],item_backup[1])
                        else:
                            self.logger.error('CPU idle is : %s and  memory usage is : %s in backup RE, intermediate test NOT OK',item_backup[0],item_backup[1])           
                            counter_backup += 1
                else:
                   self.logger.info ('Nothing to do, skipping....')
                   return True 
                
                sleep (polling_time)            
            
            if ((counter_master >= limit) or (counter_backup >= limit)):
                self.logger.error ('Check failed')
                return False
            else:
                self.logger.info ('Check passed !!!')
                return True  
        
        def check_filesystem_after_reboot (self,conn,version,role): 

            """
                Function that check components and file system after reboot

                    version: Junos version to check (i.e 11.4R8-S1.1)
                    todo:: verify capacity of the FileSystem 
                    todo:: test in SRX/EX
                - yaml file syntax example:    
                    
                    6:
                       check_filesystem_after_reboot:
                         version: "12.3R4.6"
                         role: master/backup
            """ 
            
            
            # Need to change the logic to avoid "No slot numbre in single RE system"
            if self._is_dual_RE (conn) and role == 'backup':   
                b_slot = self.get_slot_backup (conn)
            else:
                m_slot = self.get_slot_master (conn)
            soft_check_cmd = conn.rpc.cli ("show version invoke-on all-routing-engines", format='xml')
            comment = soft_check_cmd.xpath ('//package-information[contains(./comment,"boot")]')
            
            #Dictionaries
            components = {}
            f_system = {}
            
            #list of devices
            devices_list = ['/dev/ad0s1a','/dev/ad0s1e','/dev/ad1s1f','/dev/ad2s1f','/dev/da1s1f','/dev/da0s1e','/dev/da0s1a']

            
            for comm in comment:
                name = comm.xpath('comment')[0].text
    
                if version in name: 
                    self.logger.info('Correct version: %s',name)
                    try:
                        #Check that CF and HDD are present
                        devices_cmd = conn.rpc.get_chassis_inventory (detail = True)
                        # Dual RE and role backup
                        if self._is_dual_RE (conn) and role == 'backup':
                            devices = devices_cmd.xpath ('//chassis-module[name = "Routing Engine '+b_slot+'"]/chassis-re-disk-module')
                        # Dual RE and role backup
                        elif self._is_dual_RE (conn) and role == 'master':
                            devices = devices_cmd.xpath ('//chassis-module[name = "Routing Engine '+m_slot+'"]/chassis-re-disk-module')
                        # Dual RE system capable but only 1 RE available
                        elif conn.facts['2RE'] and not self._is_dual_RE (conn):
                            devices = devices_cmd.xpath ('//chassis-module[name = "Routing Engine '+m_slot+'"]/chassis-re-disk-module')
                        # Single RE
                        else:
                            devices = devices_cmd.xpath ('//chassis-module[name = "Routing Engine"]/chassis-re-disk-module')    
                        for dev in devices:
                            name_dev = dev.findtext ('name')
                            desc = dev.findtext ('description')
                            components[desc] = name_dev
                        
                        values = components.values()
                        keys = components.keys()
                        
                        
                        if len (keys) == 2:
                            self.logger.info('Components detected: %s',components)
                            #checking whether file system is properly mounted 
                            try:
                                file_system_cmd = conn.rpc.get_system_storage()
                                file_system = file_system_cmd.xpath('//filesystem')

                                for files in file_system:
                                    file = files.findtext('filesystem-name')
                                    mount = files.findtext('mounted-on')
                                    f_system [file] = mount
                                
                                values =  f_system.values()
                                keys = f_system.keys()
                                
                                #cleaning dictionary from '\n' 
                                #clean_dict = {key.strip('\n'): item.strip('\n') for key, item in f_system.items()}
                                clean_dict = dict((key.strip('\n'),item.strip('\n')) for (key,item) in f_system.items())
                                values =  clean_dict.values()
                                keys = clean_dict.keys()
                                self.logger.info('Checking system storage.....')
                                
                                #valores = {key:value for (key,value) in clean_dict.items() if key in devices_list}
                                valores = dict((key, value) for (key, value) in clean_dict.items() if key in devices_list )
                                if len(valores) == 3:    
                                    self.logger.info ("Filesystem mounted properly %s",valores)
                                    return True
                                else:
                                   self.logger.error ("Filesystem not mounted properly %s", valores)
                                   return False 
                            
                            except RpcError as err:
                                rpc_error = err.__repr__()
                                self.logger.error(xmltodict.parse(rpc_error)['rpc-error']['error-message'])
                                return False
                                
                        else:
                            self.logger.error('CF or HDD are missing,components detected: %s',components)
                            return False   
                    
                    except RpcError as err:
                        rpc_error = err.__repr__()
                        self.logger.error(xmltodict.parse(rpc_error)['rpc-error']['error-message'])
                        return False
                else:
                    self.logger.info('Version mismatch: %s',name)
                    return False

        def check_pfe_traffic(self,conn,iterations,polling_time,high_mark,limit,minimun):
          
                """
                 Function for checking pfe input/output pps  
                    
                    iterations = number of iterations                                                          
                    sl = sleep between iterations                                                          
                    
                    high_mark = "%" diff between input/output pps from which the test will be considered valid                                     
                      i.e: if diff between input and output is > 40 percent, this iteration will be marked as NOK
                    
                    limit = Number of iterations that must be OK                               
                      i.e: if 3 in 5 is OK then OK                                       
                    
                    minimun = minimun number of packets (input/output) from which to start the test
                                                                                     
                """

                counter = 0 
                
                self.logger.info('Checking pfe statistics traffic \n')
                for i in range (iterations):
                    self.logger.info('Iteration: %s \n', i+1)
                    try: 
                        inv = conn.rpc.get_pfe_statistics()
                        input_pps = inv.findtext('pfe-traffic-statistics/input-pps')
                        output_pps = inv.findtext('pfe-traffic-statistics/output-pps')                   
    
                        if ((int(input_pps) < minimun) and (int(output_pps) < minimun)):
                           self.logger.info('Skipping test due to a low pps throughtput %s %s',input_pps,output_pps) 
                           return True  
                        
                        self.logger.info('input pps: %s', input_pps)     
                        self.logger.info('output pps: %s \n', output_pps)     
                        
                        if (input_pps >= output_pps):
                            mx = input_pps
                            dif = abs (int(input_pps) - int(output_pps))
                            val1 = (dif *100)
                            val2 = (int(val1) / int (mx))
                            if (val2 > high_mark):
                                counter = counter + 1    
                        else:
                            mx = output_pps
                            dif = abs (int(input_pps) - int(output_pps))
                            val1 = (dif *100)
                            val2 = (int(val1) / int (mx))
                            if (val2 > high_mark):
                                counter = counter +1
                        sleep (polling_time)
                    except RpcError as err:    
                        rpc_error = err.__repr__()
                        self.logger.error(xmltodict.parse(rpc_error)['rpc-error']['error-message'])
                        return False                                   
                
                if (counter >= limit):
                    self.logger.error('Check failed !!!')
                    return False
                else:
                    self.logger.info('Check passed !!!')
                    return True            


class JCollector(object):

        """
            ------- Functions starts here -------
                
                warning: Following functions will be redone
        """        
     
        def commands_executor_file (self,conn,path):
                    
                #dirpath for saving data
 
                dirpath = self.log_dir + "/" + tag + "/" + self.target + "/" + timestamp + "/"
                
                index = 0     
                # Create directory if does not exist
                if not os.path.exists (dirpath):
                    os.makedirs (dirpath,mode=0777)
                    
                with open (self.output_dir,'rw+') as command:
                    self.logger.info ("Collecting Data from: %s",self.target )
                    cmd = command.readline()
                    
                    while cmd:
                        # Reading commands file and splitting command and format
                        
                        # example: show route table inet.0 protocol static;xml
                        split_command = re.split(r"\s*[,;]\s*", cmd.strip())
                        cmds = split_command [0]
                        formato = split_command [1]
                        index += 1
                        print "[" + str(index) + "]-" + cmds 
                                                
                        
                        if formato == "xml": # i.e show route summary | display xml
                            
                            self.logger.info ("Executing: %s",cmds) 
                            cmd_to_execute = conn.cli(cmds,format='xml')
                            xml_result = etree.tostring( cmd_to_execute ,pretty_print = True)    
                            cmd_clean = cmds.replace(" ","_")
                            filename = timestamp2 + '_'+ self.target  + "_" + cmd_clean + "." + formato
                            path = os.path.join (dirpath,filename)
                            self.logger.info ("Saving file as: %s",path) 
                            
                            with open (path,'w') as file_to_save:
                                file_to_save.write (xml_result)
                        
                        elif formato == "conf": # i.e "show system processes extensive"
                             
                             self.logger.info ("Executing: %s",cmds) 
                             cmd_to_execute = conn.cli(cmds)
                             cmd_clean = cmds.replace(" ","_").replace('"',"_")
                             filename = timestamp2  + '_'+ self.target + '_' + cmd_clean + "." + formato
                             path = os.path.join (dirpath,filename)
                             self.logger.info ("Saving file as: %s",path) 
                             
                             with open (path,'w') as file_to_save:
                                file_to_save.write (cmd_to_execute)                               
    
                        elif formato == "dxml": # i.e show configuration protocols isis | display xml rpc
                              
                             self.logger.info ("Executing: %s",cmds)             
                             cmd_to_execute = conn.cli(cmds)
                             xml_result = etree.tostring( cmd_to_execute ,pretty_print = True)
                             cmd_clean = cmds.replace(" ","_").replace ("_|_display_xml","").replace ("_rpc","")
                             filename_xml = timestamp2  + '_'+ self.target + '.' + cmd_clean + "." + "xml"
                             path = os.path.join (dirpath,filename_xml)
                             self.logger.info ("Saving file as: %s",path) 
                             
                             with open (path,'w') as file_to_save:
                                file_to_save.write (xml_result)
                        
                        elif formato == "set": # i.e show configuration isis | display set 
                             self.logger.info ("Executing: %s",cmds)       
                             cmd_to_execute = conn.cli(cmds)
                             cmd_clean = cmds.replace(" ","_").replace ("_|_display_set","")
                             filename = timestamp2  + '_'+ self.target + '.' + cmd_clean + "." + formato
                             path = os.path.join (dirpath,filename)
                             self.logger.info ("Saving file as: %s",path) 
                             with open (path,'w') as file_to_save:
                                file_to_save.write (cmd_to_execute)
                        
                        cmd = command.readline()

        def commands_executor (self,conn,command,format,xpath=None,save=False):

            """
                Function that issues command
                    
                    command = The command to be executed
                    format = xml,text or set 
                    save = save output in a file (True or False)
                    xpath = experimental (optional) - Only valid for operational commands in xml format
                        
                        3:
                           commands_executor:
                             command: show route table inet.0 protocol static
                             format: set
                             save: True
                             xpath: route-table/destination-count  
            """

            dirpath = self.log_dir + "/collector/" + timestamp + "/"
            
            # Create directory if does not exist
            if not os.path.exists (dirpath):
                os.makedirs (dirpath,mode=0777)
            
            if format == "text": 
                
                self.logger.info ("Executing: %s",command) 
                
                try:
                    cmd_to_execute = conn.rpc.cli (command)
                    xml_result = etree.tostring( cmd_to_execute)

                except RpcError as err:    
                    rpc_error = err.__repr__()
                    self.logger.error(xmltodict.parse(rpc_error)['rpc-error']['error-message'])
                    return False
                
                if save == True:
                    cmd_clean = command.replace(" ","_").replace('_"','_').replace('"_','_')
                    filename = timestamp2 + '_'+ self.target  + "_" + cmd_clean + "." + format
                    path = os.path.join (dirpath,filename)
                    self.logger.info ("Saving file as: %s",path)
                    
                    try:
                        with open (path,'w') as file_to_save:
                            file_to_save.write (xml_result)
                        return True
                    except IOError as err:
                       self.logger.error (err.errno, err.strerror)
                       return False 
                else:
                  self.logger.info (xml_result)
                  return True  

            elif format == "xml" and not "configuration" in command:
                
                self.logger.info ("Executing: %s",command) 
                
                try:
                    cmd_to_execute = conn.rpc.cli (command,format='xml')
                    xml_result = etree.tostring( cmd_to_execute)
                
                except RpcError as err:    
                    rpc_error = err.__repr__()
                    self.logger.error(xmltodict.parse(rpc_error)['rpc-error']['error-message'])
                    return False
                
                if save == True:
                    if xpath is not None:
                        xpath_result = cmd_to_execute.findtext (xpath)
                        if xpath_result == None:
                            self.logger.error("XPATH malformed !!!")
                            return False
                        else:
                            cmd_clean = command.replace(" ","_")
                            filename = timestamp2 + '_'+ self.target  + "_" + cmd_clean + "." + format
                            path = os.path.join (dirpath,filename)
                            self.logger.info ("Saving file as: %s",path)
                                   
                            try:
                                with open (path,'w') as file_to_save:
                                    file_to_save.write (xpath_result)
                                    return True
                            except IOError as err:
                                self.logger.error (err.errno, err.strerror)
                                return False
                    else:
                        cmd_clean = command.replace(" ","_")
                        filename = timestamp2 + '_'+ self.target  + "_" + cmd_clean + "." + format
                        path = os.path.join (dirpath,filename)
                        self.logger.info ("Saving file as: %s",path)
                               
                        try:
                            with open (path,'w') as file_to_save:
                                file_to_save.write (xml_result)
                                return True
                        except IOError as err:
                            self.logger.error (err.errno, err.strerror)
                            return False                  
                else:
                    if xpath is None:
                        self.logger.info (xml_result)
                        return True
                    else:
                        xpath_result = cmd_to_execute.findtext (xpath)
                        if xpath_result == None:
                             self.logger.error("XPATH malformed !!!")
                             return False
                        else:
                            self.logger.info (xpath_result)
                            return True
            
            elif format == "xml" and "configuration" in command:
                command = command + ' | display xml'
                self.logger.info ("Executing: %s",command)             
                cmd_to_execute = conn.cli(command,warning=False)
                xml_result = etree.tostring( cmd_to_execute)
                
                if save == True:
                    cmd_clean = command.replace(" ","_")
                    filename = timestamp2 + '_'+ self.target  + "_" + cmd_clean + "." + format
                    path = os.path.join (dirpath,filename)
                    self.logger.info ("Saving file as: %s",path)
                
                    try:
                        with open (path,'w') as file_to_save:
                            file_to_save.write (xml_result)
                            return True    
                    except IOError as err:
                       self.logger.error (err.errno, err.strerror)
                       return False 
                else:
                  self.logger.info (xml_result)
                  return True
            
            elif format == "set":
                command = command + ' | display set'
                cmd_to_execute = conn.cli (command,warning=False)
                
                if save == True:
                    cmd_clean = command.replace(" ","_")
                    filename = timestamp2 + '_'+ self.target  + "_" + cmd_clean + "." + format
                    path = os.path.join (dirpath,filename)
                    self.logger.info ("Saving file as: %s",path)
                    
                    try:
                        with open (path,'w') as file_to_save:
                            file_to_save.write (xml_result)
                            return True
                    except IOError as err:
                       self.logger.error (err.errno, err.strerror)
                       return False                     
                else:
                    self.logger.info (cmd_to_execute)
                    return True            
            
            else:
                self.logger.error ("Format not valid")
                return False          

        #def collect_logs_for_jtac (self,conn,both_RE=True):
        #def upload_to_jtac_server (self,conn,case_number,**args):

class JConfigurator(object):
        
        """
            ------- Functions starts here -------
        
        """
        def load_configuration_file (self,conn,path,format):
            
            """
                Function that load configuration on router from a file
        
                path : where the configuration file is located
                        
                format:  possible values 'set' or 'xml' or 'bracket'  (so far only format 'set' is supported)

            """
            return self.load_configuration(conn,"",format,path=path)

        def load_configuration (self,conn,data,format,path=None):
            
            """
                Function that load configuration on router
        
                data : configuration to be applied
                        
                format:  possible values 'set' or 'xml' or 'bracket'  (so far only format 'set' is supported)

            """

            if ((format == "set") or (format == "xml") or (format == "conf") or (format == "text") or (format == "txt")):
                # Checking if this attribute was already attached to Device
                # This is required when we are going to change configuration several times
                if hasattr(conn, "candidate"):   
                    pass
                else:
                    conn.bind( candidate = Config )
                try:
                    conn.candidate.lock()
                except LockError as l_error:
                    self.logger.info ("Unable to load the configuration %s:",l_error.rpc_error['message'])
                    conn.candidate.rollback()
                    return False                
                
                try:
                    if ((data == "") and (path != None)):   
                        conn.candidate.load(path=path,format=format)  # Load configuration from file
                    else:
                        conn.candidate.load(data,format=format)  # Load configuration from 'data' variable
                except ConfigLoadError as error:
                    self.logger.info ("Problems loading configuration: %s",error.rpc_error['message'])
                    return False
                except lxml.etree.XMLSyntaxError as error:
                    self.logger.info ("Problems loading XML configuration: %s", error)
                    return False

                self.logger.info("Configuration that is going to be committed: \n%s",conn.candidate.diff())
                
                try:
                     conn.candidate.commit()
                     conn.candidate.unlock()
                     return True
                except (CommitError,LockError) as err:
                    self.logger.info ("Unable to commit the configuration %s:",err.rpc_error['message'])
                    self.logger.info ("Rolling back configuration and exiting.......")
                    conn.candidate.rollback()
                    return False
            else:
                self.logger.error("Unknown junos configuration format: %s",format)
                return False        

        def rollback (self,conn,rollback_num=0):
            
            """
                Function that rollback configuration
                 rollback_num = number

                1:
                   rollback:
                     rollback_num: 1
            """
            
            if not isinstance(rollback_num, int):
                self.logger.error("Sorry. 'rollback_num' must be an integer.")
                return False

            conn.bind (cfg=Config)
            try:
                self.logger.info ("Rolling back configuration")
                conn.cfg.rollback(rollback_num)
                return True
            except RpcError as err:
                    rpc_error = err.__repr__()
                    self.logger.error(xmltodict.parse(rpc_error)['rpc-error']['error-message'])
                    return False

        def _pr939704_deployment (self,conn,file):

            """
                Customized function for using in GGCC upgrade procedure

                    warning:: Do not use for other purposes!!!
            """

            self.load_configuration (conn,"set system login user remote shell sh","set")
            #scp files (.sh and sshd (overwrite))
            # scp avoid_remote_command.sh in /var/home/remote
            # scp /var/etc/sshd_conf (overwrite with ForceCommand sh ./avoid_remote_command.sh)
            #ssh = paramiko.SSHClient() 
            #ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            #ssh.load_host_keys(os.path.expanduser(os.path.join("~", ".ssh", "known_hosts")))
            #ssh.connect (self.target,username='lab',password='lab123')
            #sftp = ssh.open_sftp()
            #sftp.put(file,"/var/tmp")
            #sftp.close ()
            #ssh.close()
            return True


class JRouter(JUpgrade,JCollector,JConfigurator,JChecker):  
       

        """
            
                Functions/arguments availables:
                   
                   - load_configuration_file (self,conn,path,format)
                   - load_configuration (self,conn,data,format,path=None)
                   - check_pfe_traffic(self,conn,iterations,sl,high_mark,limit,minimun)
                   - check_filesystem_after_reboot (self,conn,version)
                   - check_Routing_Engine_cpu_status (self,conn,role,iterations,polling_time,limit,cpu_idle_thresold=80,memory_util_thresold=75)
                   - wait_for_RE_backup_status (self,conn,iterations,polling_time)
                   - wait_fpc_status (self,conn,polling_time,iterations)
                   - wait_for_routes_holddown (self,conn,polling_time,table_list="",iterations=5)
                   - check_krt_state (self,conn,polling_time,iterations=5)
                   - check_krt_queue (self,conn,polling_time,iterations=5)
                   - check_version_and_reboot (self,conn,version)
                   - reboot_RE (self,conn)
                   - switchover (self,conn)
                   - jsnap (self,conn,type,test,snap_type)
                   - add_sw_package (self,conn,version,role,validate=True)
                   - RE_snapshot (self,conn,role)



        """
    # -----------------------------------------------------------------------
    # CONSTRUCTOR
    # -----------------------------------------------------------------------
        def __init__(self,user,target,password,logger=None):
    
                
                self.logger = logger or logging.getLogger("__JRouter__" + target)
                self.user = user
                self.target = target
                self.password = password
                self.output_dir = "output"
                self.log_dir = "./logs/" + target # temporal solution for jsnap logs
        
        #def connection (self,action):

    # -----------------------------------------------------------------------
    # OVERLOADS
    # -----------------------------------------------------------------------        

        def __repr__ (self):

                return "JRouter: user=%s,target=%s,output_dir=%s" (self.user,self.target,self.output_dir)


        
                    
        

                    
