#!/bin/python2
import cli
import re
import argparse
import boto3
import json

from csr_aws_guestshell import cag
cloudwatch=boto3.client('cloudwatch',region_name='us-east-1')
from boto.utils import get_instance_metadata


 ### To get instance id of host ##
        
def get_data():
        metadata = get_instance_metadata(timeout=2, num_retries=2)['instance-id']
        return metadata

### To get hostname of device ##
def get_host():
        cmd_output = cli.execute("sh run | i hostname ")
        for line in cmd_output.splitlines():
                if 'hostname' in line:
                    host=re.search(r'hostname (..............)', line).group(1)
                    return host

def create_alarm(metric,name):
    instance = get_data()
    host=get_host()
    print(instance)
    ##iprint(host)
    cloudwatch.put_metric_alarm(
    AlarmName=str(host+'_'+name),
    #print(AlarmName)
    ComparisonOperator='LessThanThreshold',
    EvaluationPeriods=1,
    MetricName=metric,
    Namespace='csr1000v',
    Period=300,
    Statistic='Average',
    Threshold=1.0,
    ActionsEnabled=True,
    OKActions=[
        'arn:aws:sns:us-east-1:325612769595:ServiceNow_Alerts',
    ],
    AlarmActions=[
        'arn:aws:sns:us-east-1:325612769595:ServiceNow_Alerts',
    ],
    AlarmDescription='BGP check alarm ',
    Dimensions=[
        {
          'Name': 'InstanceId',
          'Value': instance
        },
    ],
    )


csr = cag()

def print_cmd_output(command, output, print_output):
    if print_output:
        col_space = (80 - (len(command))) / 2
        print "\n%s %s %s" % ('=' * col_space, command, '=' * col_space)
        print "%s \n%s" % (output, '=' * 80)


def get_bgp_state(print_output):
    cmd_output = execute_command("show ip bgp neighbors", print_output)
    tunnel_states = cmd_output.split('BGP neighbor is ')
    for tunnel_state in tunnel_states:
        for line in tunnel_state.splitlines():
            if 'remote AS' in line:
                bgp_neig = re.search(r'(\d+.\d+.\d+.\d+),  remote AS', line).group(1)
                #print(bgp_neig)
            if 'BGP state =' in line:
                if 'UP' in line.upper():
                    #print "bgp is up"
                    metricname="bgp_neighbor_"+bgp_neig
                    alarmname="bgp_"+bgp_neig
                    #print(metricname)
                    #csr.send_metric("bgp_asn_"+as_number, 1, "BGP State")
                    csr.send_metric("bgp_neighbor_"+bgp_neig, 1, "BGP State")
                    create_alarm(metricname,alarmname)
                else:
                    print "bgp is down"
                    csr.send_metric("bgp_neighbor_"+bgp_neig, 0, "BGP State")


                    
                    
                    
def get_cpu(print_output):
    cmd_output = execute_command("show processes cpu ", print_output)
    for line in cmd_output.splitlines():
        if 'CPU utilization' in line:
            print (line)
            cpu= re.search(r'five minutes: ([0-9]?[0-9])', line).group(1)
            print(cpu)
            csr.send_metric("cpu_utilization",cpu,"cpu_state")
    



def execute_command(command, print_output):
    cmd_output = cli.execute(command)
    while len(cmd_output) == 0:
        print "CMD FAILED, retrying"
        cmd_output = cli.execute(command)

    print_cmd_output(command, cmd_output, print_output)
    return cmd_output


def get_stat_drop(print_output):
    cmd_output = execute_command(
        "show platform hardware qfp active statistics drop clear", print_output)

    if "all zero" in cmd_output:
        csr.send_metric("TailDrop", int(0), "Statistics drops")
        return

    if "TailDrop" not in cmd_output:
        csr.send_metric("TailDrop", int(0), "Statistics drops")

    for line in cmd_output.splitlines():
        if ("-" in line) or ("Global Drop Stats" in line):
            continue

        entries = line.split()
        if print_output:
            print "%s --> %s/%s" % (entries[0], entries[1], entries[2])
        #csr.send_metric(entries[0], int(entries[1]), "Statistics drops")


def get_datapath_util(print_output):
    cmd_output = execute_command(
        "show platform hardware qfp active datapath utilization", print_output)

    row_names = [
        "input_priority_pps",
        "input_priority_bps",
        "input_non_priority_pps",
        "input_non_priority_bps",
        "input_total_pps",
        "input_total_bps",
        "output_priority_pps",
        "output_priority_bps",
        "output_non_priority_pps",
        "output_non_priority_bps",
        "output_total_pps",
        "output_total_bps",
        "processing_load_pct"]

    i = 0
    for line in cmd_output.splitlines():
        m = re.search(
            r'.*\s+(?P<fivesecs>\d+)\s+(?P<onemin>\d+)\s+(?P<fivemin>\d+)\s+(?P<onehour>\d+)', line)
        if m:
            # print "%s --> %s %s %s %s" % (row_names[i],
            # m.group('fivesecs'),m.group('onemin'),m.group('fivemin'),m.group('onehour'))
            csr.send_metric(row_names[i] + '_fivesecs', m.group(
                'fivesecs'), "datapath utilization")
            csr.send_metric(row_names[i] + '_onemin', m.group(
                'onemin'), "datapath utilization")
            csr.send_metric(row_names[i] + '_fivemin', m.group(
                'fivemin'), "datapath utilization")
            csr.send_metric(row_names[i] + '_onehour', m.group(
                'onehour'), "datapath utilization")
            i = i + 1

def show_gig_interface_summary(print_output):
    cmd_output = execute_command("show interfaces summary", print_output)
    total_txbps = 0
    total_rxbps = 0
    for line in cmd_output.splitlines():
        if "Giga" in line:
            total_txbps += int(line.split()[-3])
            total_rxbps += int(line.split()[-5])

    csr.send_metric("output_gig_interface_summary_bps", total_txbps, "aggregate gig interfaces bps")
    csr.send_metric("input_gig_interface_summary_bps", total_rxbps, "aggregate gig interfaces bps")

def show_interface(print_output):
    cmd_output = execute_command("show interface summary", print_output)
    table_start = 0
    for line in cmd_output.splitlines():
        if 'Interface' in line:
            continue
        if "-" in line:
            table_start = 1
            continue
        if table_start == 0:
            continue
        entries = line.lstrip('*').split()
        cmd = "show interface %s" % (entries[0])
        interface_output = execute_command(cmd, print_output)
        m = re.search(
            r'.*\s+(?P<packets_input>\d+) packets input.*\s+(?P<bytes_input>\d+) bytes.*', interface_output)
        if m:
            # print "match! %s %s" %
            # (m.group('packets_input'),m.group('bytes_input'))
            csr.send_metric("packets_input_" +
                            entries[0], m.group('packets_input'), cmd)
            csr.send_metric("bytes_input_" +
                            entries[0], m.group('bytes_input'), cmd)

        m = re.search(
            r'.*\s+(?P<packets_output>\d+) packets output.*\s+(?P<bytes_output>\d+) bytes.*', interface_output)
        if m:
            # print "match! %s %s" %
            # (m.group('packets_output'),m.group('bytes_output'))
            csr.send_metric("packets_output_" +
                            entries[0], m.group('packets_output'), cmd)
            csr.send_metric("bytes_output_" +
                            entries[0], m.group('bytes_output'), cmd)
        m = re.search(
            r'.*\s+(?P<unknown_drops>\d+) unknown protocol drops.*', interface_output)
        if m:
            # print "match! %s" % (m.group('unknown_drops'))
            csr.send_metric("unknown_drops_" +
                            entries[0], m.group('unknown_drops'), cmd)
        m = re.search(
            r'.*Total output drops:\s+(?P<output_drops>\d+)\s+.*', interface_output)
        if m:
            # print "match! %s" % (m.group('output_drops'))
            csr.send_metric("output_drops_" +
                            entries[0], m.group('output_drops'), cmd)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload Stats to custom metrics")
    parser.add_argument('--display', help='Show Output', action='store_true')
    parser.add_argument('--category', help='Send ', default="all")

    args = parser.parse_args()

    if args.category in ["all", "drops"]:
        get_stat_drop(args.display)
    if args.category in ["all", "util"]:
        get_datapath_util(args.display)
    if args.category in ["all", "interface"]:
        show_interface(args.display)
    if args.category in ["all", "interface_summary"]:
        show_gig_interface_summary(args.display)
    if args.category in ["all", "cpu"]:
        get_cpu(args.display)
    if args.category in ["all", "bgp_status"]:
        get_bgp_state(args.display)
        print "bgp run"
