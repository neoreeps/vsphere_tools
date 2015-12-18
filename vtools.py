#!/usr/bin/env python
"""
vtools.py: Connects to vSphere or vCenter to list or migrate objects.
"""
__author__ = "Kenny Speer"
__copyright__ = "Copyright 2015"
__credits__ = ["Kenny Speer"]
__license__ = "GPL"
__version__ = "1.0.2"
__maintainer__ = "Kenny Speer"
__email__ = "kenny.speer@gmail.com"
__status__ = "Production"

from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
from pprint import pprint

import atexit
import argparse
import getpass
import ssl
import sys
import time


# global options
DEBUG = False
NOACTION = False


def get_args():
    """
    Parse arguments and return parser obj
    :return: args object
    """
    parser = argparse.ArgumentParser(
        description='Process args for vCenter connection')
    parser.add_argument('-H', '--host', required=True, action='store',
                        help='Hostname or IP of vCenter or vSphere servers')
    parser.add_argument('-P', '--port', type=int, default=443, action='store',
                        help='Port to use for connection')
    parser.add_argument('-U', '--user', required=True, action='store',
                        help='Username for connection to server')
    parser.add_argument('--password', action='store',
                        help='Password for user, pompt if not provided')
    parser.add_argument('-v', '--vmnames', action='append',
                        help='Name of VM(s) to perform action')
    parser.add_argument('-m', '--migrate', action='store_true',
                        help='Migrate a VM, must specify at least dest option.')
    parser.add_argument('-s', '--source', action='store',
                        help='Source host for vmotion when moving all VMs')
    parser.add_argument('-d', '--dest', action='store',
                        help='Destination host for vmotion')
    parser.add_argument('-l', '--list', action='store',
                        choices=['vms', 'hosts', 'clusters'],
                        help='List type of either "vms" or "hosts"')
    parser.add_argument('-X', '--drs', action='append',
                        help='List of hosts to perform DRS, use -X per host')
    parser.add_argument('-D', '--debug', action='store_true',
                        help='Add debug verbosity to command output')
    parser.add_argument('-N', '--noact', action='store_true',
                        help='Flag to simulate action')

    return parser.parse_args()


def connect(args):
    """
    Create connection based on args and ssl context; register to disconnect
    session at termination of process.
    :param args: args object containing arguments
    :return: connection object
    """
    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
    context.verify_mode = ssl.CERT_NONE

    try:
        conn = SmartConnect(host=args.host,
                            user=args.user,
                            pwd=args.password,
                            port=int(args.port),
                            sslContext=context)
    except Exception, e:
        print("\nException: %s" % e.msg)
        sys.exit(1)

    atexit.register(Disconnect, conn)
    return conn


def get_objs(content, vimType, list):
    """
    Get vsphere objects and return all or a subset based on 'list'
    :param content: connection content from vcenter
    :param vimType: object type to retrieve
    :param list: list of strings to parse against
    :return: list of objects
    """
    retList = []
    objView = content.viewManager.CreateContainerView(content.rootFolder,
                                                      vimType,
                                                      True)
    objList = objView.view
    objView.Destroy()
    if list is None:
        return objList

    for obj in objList:
        if obj.summary.config.name in list:
            retList.append(obj)

    return retList


def get_vm_list(conn, list=None):
    """
    Helper function to return list of virtual machines
    :param conn: connection object
    :param list: list of strings to parse against
    :return: list of vm objects
    """
    return get_objs(conn.content, [vim.VirtualMachine], list)


def get_host_list(conn, list=None):
    """
    Helper function to return list of hosts
    :param conn: connection object
    :param list: list of strings to parse against
    :return: list of host objects
    """
    return get_objs(conn.content, [vim.HostSystem], list)


def get_cluster_list(conn, list=None):
    """
    Helper function to return list of clusters
    :param conn: connection object
    :param list: list of strings to parse against
    :return: list of host objects
    """
    return get_objs(conn.content, [vim.ClusterComputeResource], list)


def print_host_stats(hosts):
    """
    Dump the host information for data retrieved from vcenter
    :param hosts: must be a list of host objects
    """
    assert isinstance(hosts, (list, tuple))

    for host in hosts:
        print('NAME: %s' % host.summary.config.name)
        print('MEMORY: %d GB' %
              (int(host.summary.hardware.memorySize)/1024**3 + 1))

        if DEBUG:
            pprint(vars(host.summary))
            pprint(vars(host.summary.quickStats))

    print('TOTAL HOSTS: %s' % len(hosts))


def print_cluster_stats(clusters):
    """
    Dump the cluster information for objects retrieved
    :param clusters: list of cluster objects
    """
    assert isinstance(clusters, (list, tuple))

    for cluster in clusters:
        print('NAME: %s' % cluster.name)

        if DEBUG:
            pprint(vars(cluster.summary))
            pprint(vars(cluster))


def print_vm_stats(vms):
    """
    Dump the VM information for data retrieved from vcenter
    :param vms: must be a list of virtual machine objects
    """
    assert isinstance(vms, (list, tuple))

    for vm in vms:
        print('NAME: %s' % vm.summary.config.name)
        print('HOST: %s' % vm.runtime.host.name)
        print('MEM:  %s' % vm.summary.config.memorySizeMB)
        print('STATE: %s' % vm.runtime.powerState)

        if DEBUG:
            pprint(vars(vm.summary.config))
            pprint(vars(vm.runtime))

    print('TOTAL VMS: %s' % len(vms))


def migrate_vm(vm, dest):
    """
    Migrate a vm to the destination vserver.
    :param conn: connection object
    :param vm: virtual machine object to migrate
    :param dest: host object for destination vsphere server
    """
    print('Migrating %s to destination host %s' %
          (vm.summary.config.name, dest.summary.config.name))

    if vm.summary.config.template is True:
        print('Not possible to migrate templates, moving on.')
        return

    if vm.runtime.host.name == dest.summary.config.name:
        print('Migrate complete! VM already running on dest host.')
        return

    if NOACTION is True:
        print('NOACT: Migration complete!')
        return

    task = vm.Migrate(pool=vm.resourcePool,
                      host=dest,
                      priority=vim.VirtualMachine.MovePriority.defaultPriority)

    wait_for_task(task)


def wait_for_task(task):
    """
    Waits and provides updates on a vSphere task
    :param task: task object
    """

    while task.info.state == vim.TaskInfo.State.running:
        time.sleep(2)

    if task.info.state == vim.TaskInfo.State.success:
        if task.info.result is not None:
            print('Task completed successfully w/ result: %s' %
                  task.info.result)
        else:
            print('Task completed successfully.')
    else:
        # raise task.info.error
        print('Task did not complete successfully: %s' % task.info.error)
        pprint(vars(task.info.error))

    return task.info.result


def perform_drs(hostObjs, hostNames):
    """
    Perform VM balance using simple algorithm of balancing memory configured
    across hosts based on host memory ratio.
    :param hosts: list of hosts
    """
    # TODO: Add memory used, not just configured
    # TODO: Add CPU usage
    # TODO: Minimize movement by first calculating current configuration,
    #       we are just blindly creating queues and moving without regard to
    #       current running configuration which results in unnecessary moves
    print('\n%d hosts found: %s\n' % (len(hostObjs), hostNames))

    # obtain a list of VMs residing on the hosts requested
    vms = []
    vmList = get_vm_list(conn)
    for vm in vmList:
        if vm.runtime.host.name in hostNames:
            if vm.summary.config.template is False:
                vms.append(vm)

    # sort the VMs based on memory configured
    vms.sort(key=lambda x: x.summary.config.memorySizeMB, reverse=True)
    if DEBUG:
        print('\n%d vms found: %s\n' %
              (len(vms), [x.summary.config.memorySizeMB for x in vms]))

    class Queue(object):
        """
        Simple class object to represent a host queue for vm migrations
        """

        weight = 0

        def __init__(self, hostObj):
            self.host = hostObj
            self.name = hostObj.summary.config.name
            self.weight = hostObj.summary.hardware.memorySize
            self.vm_list = []

        def add_vm(self, vm):
            self.vm_list.append(vm)

        @property
        def number_vms(self):
            return len(self.vm_list)

    # create queues based on installed memory
    queues = [Queue(x) for x in hostObjs]
    for vm in vms:
        vm_weight = int(vm.summary.config.memorySizeMB) * (1024**2)
        queues.sort(key=lambda x: x.weight, reverse=True)
        queues[0].weight = queues[0].weight - vm_weight
        queues[0].add_vm(vm)
        if DEBUG:
            print('\nadded %d to queue %s w/ weight %d' %
                  (vm_weight, queues[0].name, queues[0].weight))

    if DEBUG:
        for queue in queues:
            print('QUEUE: %s' % queue.name)
            print('NUM: %s' % queue.number_vms)
            print('WEIGHT: %s' % queue.weight)

    # now migrate the vms to the appropriate hosts
    for queue in queues:
        for vm in queue.vm_list:
            migrate_vm(vm, queue.host)


if __name__ == "__main__":

    # parse the args and prepare for execution
    args = get_args()

    # set password or ask for it
    if not args.password:
        args.password = getpass.getpass(
            prompt='Enter password for host %s and user %s: ' %
            (args.host, args.user))

    # enable verbose data output if debug is enabled
    DEBUG = args.debug
    # disable action, only simulate
    NOACTION = args.noact

    # create connection based on args
    conn = connect(args)

    # if listing, then obtain and print the objects
    if args.list == 'vms':
        vmList = get_vm_list(conn, args.vmnames)
        print_vm_stats(vmList)
    elif args.list == 'hosts':
        hostList = get_host_list(conn)
        print_host_stats(hostList)
    elif args.list == 'clusters':
        clusterList = get_cluster_list(conn)
        print_cluster_stats(clusterList)

    # if migrating, verify we have a valid vm and host name
    if args.migrate is True:
        # must have either a name or 'all' to specify the VMs
        # if all, then we need a source host
        if not args.vmnames:
            print('\nMust specify VM name (or all) with -v for migration.\n')
            sys.exit(2)
        elif args.vmnames == ['all']:
            vmnames = None
            if not args.source:
                print('\nMust specify a source host to move all VMs.\n')
                sys.exit(2)
        else:
            vmnames = args.vmnames

        # get and validate destination host
        hosts = get_host_list(conn, args.dest)
        if 0 == len(hosts):
            print('\nvSphere Host %s cannot be found.\n' % args.dest)
            sys.exit(3)
        else:
            dest_host = hosts[0]

        # get a list of all VMs, we'll parse later
        vms = get_vm_list(conn, vmnames)
        if 0 == len(vms):
            print('\nVirtual Machine %s cannot be found.\n' % vmnames)
            sys.exit(3)

        # haven't exited yet, so start the migration
        # TODO: currently this is serial, add parallelism
        for vm in vms:
            if args.source:
                if vm.runtime.host.name != args.source:
                    continue

            migrate_vm(vm, dest_host)

    if args.drs:
        if 2 > len(args.drs):
            print('\nNumber of hosts for DRS must be at least 2.  '
                  '%s provided\n' % len(args.drs))
            sys.exit(2)

        # validate the hosts requested actually exit
        hostList = get_host_list(conn, args.drs)
        if len(hostList) != len(args.drs):
            print('\n%d hosts requested were not found.\n' %
                  int(len(args.drs) - len(hostList)))
            sys.exit(2)

        # hosts exist, now perform DRS
        perform_drs(hostList, args.drs)
