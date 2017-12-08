import subprocess, shlex, yaml, os
import time

from jbotui.helper.translator import translate

class JWorker(object):
    def __init__(self, target, user, passwd, workfile_name):
        self.target = target
        self.user = user
        self.passwd = passwd
        #self.workfile_name = workfile_name
        self.workfile_name = "demo_telefonica"
        #self.workfile_name = "teste_interno"
        print "Loading file: " + workfile_name + '.cfg'
        #self.generate_yaml_procedure(workfile_name)

    def generate_yaml_procedure(self, workfile_name):
        with open('workfiles/' + workfile_name + '.cfg', 'r') as workinfo:
            yaml_procedure = translate(workinfo, workfile_name)
            with open('jbotui/jbot/procedures/' + workfile_name + '2.yaml', 'w+') as yaml_file:
                yaml_file.write(yaml_procedure)

    def run_jbot(self):
        original_path = os.getcwd()
        try:
            results_file = open("processes/" + self.workfile_name + '.txt', 'w')
            results_file.write("Executing....")
            results_file.close()
        except IOError:
            print "Could not initiate log file."
        os.chdir(os.path.expanduser('jbotui/jbot'))
        try:
            results = subprocess.check_call(shlex.split('python jbot.py --procedure procedures/' + \
            self.workfile_name + '.yaml --user ' + \
            self.user + ' --passwd ' + self.passwd + ' --targetA ' + self.target + ' -c'))
        except Exception as err:
            print err
            print "Could not execute workflow"
        finally:
            os.chdir(original_path)
        write_attempts = 5
        while write_attempts > 0:
            try:
                print "Printing results"
                results_file = open("processes/" + self.workfile_name + '.txt', "w")
                results_file.write(results)
                results_file.close()
                break
            except IOError:
                time.sleep(37)
                write_attempts -= 1
        if write_attempts == 0:
            print "Could not write to log file."
