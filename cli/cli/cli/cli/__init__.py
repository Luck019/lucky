"""
Copyright (c) 2020 by Cisco Systems, Inc.
All rights reserved.

Run Cisco IOS CLI commands and receive the output.

This module contains utility functions that run Cisco IOS CLI commands and provide
the output.

"""

__version__="2.0.0"

import re
import shutil
import os
import copy
import glob
import sys
import subprocess
import random
from datetime import datetime

LOGFILE = "/data/iosp.log"
BKUP_LOGFILE = "/data/iosp.log.1"

MAX_WAIT_TIME = None

class CLICommandError(Exception):
    """A base class for exception that are raised when a single command cannot be run in IOS."""
    def __init__(self, command, message, *args):
        self.command = command
        self.message = '{}: There was a problem running the command: "{}"'.format(message, command)
        super(CLICommandError, self).__init__(self.message, *args)

class IOSPCLIConfError(Exception):
    """Raised when some commands in a bulk configuration fail.

    Contains a list of the commands, along with a list of the failures."""
    def __init__(self, results, *args):
        self.results = results
        self.failed = [c.start() for c in re.finditer('FAILURE', results)]
        self.message = 'ConfigError: There was a problem with {} commands while configuring the device.\n'.format(len(self.failed)) + results

    def __str__(self):
        return str(self.message)

class IOSPCLIError(Exception):
    '''Exception raised when iosp_server returns a failure due to cli syntax or cli execution failure'''
    def __init__(self):
        self.message = "CLI syntax error or execution Failure"

    def __str__(self):
        return str(self.message)

class IOSPSystemError(Exception):
    '''Exception raised when iosp_server returns a system failure'''
    def __init__(self):
        self.message = "System Error"

    def __str__(self):
        return str(self.message)

class IOSPUnexpectedError(Exception):
    '''Exception raised when iosp_server returns a system failure'''
    def __init__(self):
        self.message = "Unexpected Error"

    def __str__(self):
        return str(self.message)

def _log_to_file(message):
    """Log to a file if LOGFILE is defined"""
    if LOGFILE is None: 
        return

    logfile = open(LOGFILE, 'a')
    logfile.write(datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f') + "  " + message + "\n")
    logfile.close()
    # Rotate file is size more than 2 MB
    if os.stat(LOGFILE).st_size > 2000000:
        shutil.move(LOGFILE, BKUP_LOGFILE)

def _log_output_file(file):
    ofile = open(file, 'r')
    _log_to_file("%s"%ofile.read())
    ofile.close()

# validate a command
def valid(command):
    CONF_REGEX = '^(conf|confi|config|configu|configur|configure)$'
    commands = command.split(';')

    for cmd in commands:
        if re.match(CONF_REGEX, cmd.strip()): return False

    return True

parser_dict = {"PARSER_COMMAND":"", "PARSER_ERROR":"", "PARSER_ERROR_POS":"", "PARSER_OUTPUT":"", "PARSER_RETURN_CODE":"", "PARSER_RETURN_STATUS":"", "PARSER_PROMPT":""}
def ConfigResult(ResultFile):
    ofile = open(ResultFile, 'r')
    outputlist = []
    for line in ofile:
        if re.match("\[CALL.*PARSER_COMMAND]:", line):
            newelem = []
            newelem = parser_dict
            newelem["PARSER_COMMAND"] = re.sub(r"\[CALL.*PARSER_COMMAND]:", "", line)
            #re.sub(r'\(.*\)', '', 'foobar (###)')
        if re.match("\[CALL.*PARSER_ERROR]:", line):
            newelem["PARSER_ERROR"] = re.sub(r"\[CALL.*PARSER_ERROR]:", "", line)
        if re.match("\[CALL.*PARSER_ERROR_POS]:", line):
            newelem["PARSER_ERROR_POS"] = re.sub(r"\[CALL.*PARSER_ERROR_POS]:","", line)
        if re.match("\[CALL.*PARSER_OUTPUT]:", line):
            newelem["PARSER_OUTPUT"] = re.sub(r"\[CALL.*PARSER_OUTPUT]:","", line)
        if re.match("\[CALL.*PARSER_RETURN_CODE]:", line):
            newelem["PARSER_RETURN_CODE"] = re.sub(r"\[CALL.*PARSER_RETURN_CODE]:","", line)
            if "SUCCESS" in line:
                newelem["PARSER_RETURN_STATUS"] = "SUCCESS"
            else:
                newelem["PARSER_RETURN_STATUS"] = "FAILURE"
        if re.match("\[CALL.*PARSER_PROMPT]:", line):
            newelem["PARSER_PROMPT"] = re.sub(r"\[CALL.*PARSER_PROMPT]:","", line)
            addelem = copy.copy(newelem)
            outputlist.append(addelem)
    ofile.close()
    linenum = 1
    outputstr = ""
    for cmdresult in outputlist:
        if "SUCCESS" in cmdresult.get("PARSER_RETURN_STATUS"):
            cmd_res_str = "Line " + str(linenum) + " SUCCESS: " + cmdresult.get("PARSER_COMMAND")
        else:
            cmd_res_str = "Line " + str(linenum) + " FAILURE: " + cmdresult.get("PARSER_COMMAND") + "**CLI Line " + str(linenum) + ": " + cmdresult.get("PARSER_ERROR")
        linenum = linenum + 1
        outputstr = outputstr + cmd_res_str
    return outputstr

def configure(configuration):
    """Apply a configuration (set of Cisco IOS CLI config-mode commands) to the device
    and return a list of results.

    configuration = '''interface gigabitEthernet 0/0
                         no shutdown'''

    # push it through the Cisco IOS CLI.
    try:
        results = cli.configure(configuration)
        print "Success!"
    except CLIConfigurationError as e:
        print "Failed configurations:"
        for failure in e.failed:
            print failure

    Args:
        configuration (str or iterable): Configuration commands, separated by newlines.

    Returns:
        list(ConfigResult): A list of results, one for each line.

    Raises:
        CLISyntaxError: If there is a syntax error in the configuration.

    """

    _log_to_file("CLI configuration invoked for '" + str(configuration) + "'")

    if len(configuration) == 0:
        return ''

    date_str = datetime.now().strftime('%Y_%m_%d_%H_%M_%S_%f') + "_" + str(random.getrandbits(32))
    cmd_file = "/tmp/.iosp_" + date_str + ".cmd"
    output_file = "/tmp/.iosp_" + date_str + ".output"
    cmdfile = open(cmd_file, 'w')
    if not isinstance(configuration, str):
        configuration = "\n".join(configuration)
    for cmd in configuration.split("\n"):
        cmdfile.write('%s\n' % cmd.lstrip())
    cmdfile.close()

    #_log_to_file("Commands added to file '" + cmd_file + "'")
    try:
        subprocess.check_output("iosp_client -c -om 3 -o " + output_file + " -i " + cmd_file,
                                                    stderr=subprocess.STDOUT, shell=True)

        result = ConfigResult(output_file)
    except subprocess.CalledProcessError as iosp_client_error:
        _log_to_file("%s"%iosp_client_error)
        error_output = iosp_client_error.output
        _log_to_file("IOSP Client call failed with error code %d %s"%(iosp_client_error.returncode, error_output.decode()))
        _log_to_file("Received Output: ")
        _log_output_file(output_file)
        result = ConfigResult(output_file)
        os.remove(cmd_file)
        os.remove(output_file)
        if iosp_client_error.returncode == 1:
            raise IOSPCLIConfError(result)
        elif iosp_client_error.returncode == 2:
            raise IOSPSystemError
        else:
            raise IOSPUnexpectedError
    
    os.remove(cmd_file)
    os.remove(output_file)
    return result

def configurep(configuration):
    """Apply a configuration (set of Cisco IOS CLI config-mode commands) to the device
    and prints the result.

    configuration = '''interface gigabitEthernet 0/0
                         no shutdown'''

    # push it through the Cisco IOS CLI.
    configurep(configuration)

    Args:
        configuration (str or iterable): Configuration commands, separated by newlines.

    """

    try:
        results = configure(configuration)
        if len(results) > 0:
            print(results)
    except IOSPCLIConfError as ce:
        print(ce)
    except IOSPSystemError as se:
        print(se)
    except IOSPUnexpectedError as ue:
        print(ue)
    except CLICommandError as cce:
        print(cce)
    except Exception as e:
        print(e)


_SUPERFLUOUS_CONFIG_LINE = "Enter configuration commands, one per line.  End with CNTL/Z."


def cli(command):
    """Execute Cisco IOS CLI command(s) and return the result.

    A single command or a delimited batch of commands may be run. The
    delimiter is a space and a semicolon, " ;". Configuration commands must be
    in fully qualified form.

    output = cli("show version")
    output = cli("show version ; show ip interface brief")
    output = cli("configure terminal ; interface gigabitEthernet 0/0 ; no shutdown")

    Args:
        command (str): The exec or config CLI command(s) to be run.

    Returns:
        string: CLI output for show commands and an empty string for
            configuration commands.

    Raises:
        IOSPCLIError: CLI syntax or execution Error
        IOSPSystemError: System error
        IOSPUnexpectedError: Unexpected Error

    """

    _log_to_file("CLI execution invoked for '" + command + "'")
    command = command.strip()

    if command == '':
        return ''

    if not valid(command):
        raise CLICommandError(command, "You have to specify the configuration mode")

    date_str = datetime.now().strftime('%Y_%m_%d_%H_%M_%S_%f') + "_" + str(random.getrandbits(32))
    cmd_file = "/tmp/.iosp_" + date_str + ".cmd"
    output_file = "/tmp/.iosp_" + date_str + ".output"
    cmdfile = open(cmd_file, 'w')
    for cmd in command.split(";"):
        cmdfile.write('%s\n' % cmd.lstrip())
    cmdfile.close()

    #_log_to_file("Commands added to file '" + cmd_file + "'")
    try:
        subprocess.check_output("iosp_client -om 3 -o " + output_file + " -i " + cmd_file,
                                stderr=subprocess.STDOUT, shell=True)

    except subprocess.CalledProcessError as iosp_client_error:
        _log_to_file("%s"%iosp_client_error)
        error_output = iosp_client_error.output
        _log_to_file("IOSP Client call failed with error code %d %s"%(iosp_client_error.returncode, error_output.decode()))
        _log_output_file(output_file)
        os.remove(cmd_file)
        os.remove(output_file)
        if iosp_client_error.returncode == 1:
            raise IOSPCLIError
        elif iosp_client_error.returncode == 2:
            raise IOSPSystemError
        else:
            raise IOSPUnexpectedError
    
    text = ""
    ofile = open(output_file, 'U')
    for line in ofile:
        if not re.match("\[CALL_.*", line) and not line.isspace():
            text = text + line
    ofile.close()
    os.remove(cmd_file)
    os.remove(output_file)
    text = text.replace(_SUPERFLUOUS_CONFIG_LINE,"")
    return text


def execute(command):
    """Execute Cisco IOS CLI exec-mode command and return the result.

    command_output = execute("show version")

    Args:
        command (str): The exec-mode command to run.

    Returns:
        str: The output of the command.

    Raises:
        CLICommandError: If there are multiple commands sopecified in command line.

    """
    command = command.strip('\n')

    if command == '':
        return ''

    if ";" in command or "\n" in command:
        _log_to_file("Multiple commands invocation not allowed in execute call, '" + command +"'")
        raise CLICommandError(command, "You may not run multiple commands using execute().")

    return (cli(command))


def executep(command):
    """Execute Cisco IOS CLI exec-mode command and print the result.

    executep("show version")

    Args:
        command (str): The exec-mode command to run.

    """

    try:
        text = execute(command)
        if len(text) > 0:
            print(text)
    except IOSPCLIError as ce:
        print(ce)
    except IOSPSystemError as se:
        print(se)
    except IOSPUnexpectedError as ue:
        print(ue)
    except CLICommandError as cce:
        print(cce)
    except Exception as e:
        print(e)


def clip(command):
    """Execute Cisco IOS CLI command(s) and print the result.

    A single command or a delimited batch of commands may be run. The
    delimiter is a space and a semicolon, " ;". Configuration commands must be
    in fully qualified form.

    clip("show version")
    clip("show version ; show ip interface brief")
    clip("configure terminal ; interface gigabitEthernet 0/0 ; no shutdown")

    Args:
        command (str): The exec or config CLI command(s) to be run.

    """

    try:
        text = cli(command)
        if len(text) > 0:
            print(text)
    except IOSPCLIError as ce:
        print(ce)
    except IOSPSystemError as se:
        print(se)
    except IOSPUnexpectedError as ue:
        print(ue)
    except CLICommandError as cce:
        print(cce)
    except Exception as e:
        print(e)

