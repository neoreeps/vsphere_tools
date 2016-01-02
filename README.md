# vSphere Tools

This repository contains tools used to manage and manipulate vmware vSphere and vCenter.

* vtools.py - tool used to list vms and servers and to perform migration of VMs

# Requirements
* pyVmomi - official vmware vsphere python APIs (replaces pysphere which is now deprecated)

# vTools
```
-> ./vtools.py -h
usage: vtools.py [-h] -H HOST [-P PORT] -U USER [--password PASSWORD]
                 [-v VMNAMES] [-m] [-s SOURCE] [-d DEST]
                 [-l {vms,hosts,clusters}] [-X DRS] [-D] [-N]

Process args for vCenter connection

optional arguments:
  -h, --help            show this help message and exit
  -H HOST, --host HOST  Hostname or IP of vCenter or vSphere servers
  -P PORT, --port PORT  Port to use for connection
  -U USER, --user USER  Username for connection to server
  --password PASSWORD   Password for user, pompt if not provided
  -v VMNAMES, --vmnames VMNAMES
                        Name of VM(s) to perform action
  -m, --migrate         Migrate a VM, must specify at least dest option.
  -s SOURCE, --source SOURCE
                        Source host for vmotion when moving all VMs
  -d DEST, --dest DEST  Destination host for vmotion
  -l {vms,hosts,clusters}, --list {vms,hosts,clusters}
                        List type of either "vms" or "hosts"
  -X DRS, --drs DRS     List of hosts to perform DRS, use -X per host
  -D, --debug           Add debug verbosity to command output
  -N, --noact           Flag to simulate action
```

## Examples

Migrate all virtual machines from one host to another.  Useful for entering maintenance mode on an ESX server.
* -m - migrate action
* -v all - all vms
* -d - destination host
* -s - source host required due to 'all' vms being provided
```
-> ./vtools.py -H 10.4.80.77 -U root --password mypass123! -m -v all -d ghisqlesx01.ghi.local -s ghisqlesx02.ghi.local
```

Migrate one VM from one host to another.
```
-> ./vtools.py -H 10.4.80.77 -U root --password mypass123! -m -v ghIsqlMGMT01 -d ghisqlesx01.ghi.local
```

List servers with verbose output:
```
-> ./vtools.py -H 10.4.80.77 -U root --password mypass123! -l hosts -D
```

Balance VMs across ESX hosts (aka DRS):
```
-> ./vtools.py -H 10.4.80.77 -U root --password mypass123! -X ghisqlesx01.ghi.local -X ghisqlesx02.ghi.local -D
```

## pydoc
standard python documentation is available via 'pydoc pytools'
```
elp on module vtools:

NAME
    vtools - vtools.py: Connects to vSphere or vCenter to list or migrate objects.

FILE
    /Users/kenny/source/vsphere_tools/vtools.py

FUNCTIONS
    connect(args)
        Create connection based on args and ssl context; register to disconnect
        session at termination of process.
        :param args: args object containing arguments
        :return: connection object

    get_args()
        Parse arguments and return parser obj
        :return: args object

    get_cluster_list(conn, list=None)
        Helper function to return list of clusters
        :param conn: connection object
        :param list: list of strings to parse against
        :return: list of host objects

    get_host_list(conn, list=None)
        Helper function to return list of hosts
        :param conn: connection object
        :param list: list of strings to parse against
        :return: list of host objects

    get_objs(content, vimType, list)
        Get vsphere objects and return all or a subset based on 'list'
        :param content: connection content from vcenter
        :param vimType: object type to retrieve
        :param list: list of strings to parse against
        :return: list of objects

    get_vm_list(conn, list=None)
        Helper function to return list of virtual machines
        :param conn: connection object
        :param list: list of strings to parse against
        :return: list of vm objects

    migrate_vm(vm, dest)
        Migrate a vm to the destination vserver.
        :param conn: connection object
        :param vm: virtual machine object to migrate
        :param dest: host object for destination vsphere server

    perform_drs(hostObjs, hostNames)
        Perform VM balance using simple algorithm of balancing memory configured
        across hosts based on host memory ratio.
        :param hosts: list of hosts

    print_cluster_stats(clusters)
        Dump the cluster information for objects retrieved
        :param clusters: list of cluster objects

    print_host_stats(hosts)
        Dump the host information for data retrieved from vcenter
        :param hosts: must be a list of host objects

    print_vm_stats(vms)
        Dump the VM information for data retrieved from vcenter
        :param vms: must be a list of virtual machine objects

    wait_for_task(task)
        Waits and provides updates on a vSphere task
        :param task: task object

DATA
    DEBUG = False
    __author__ = 'Kenny Speer'
    __copyright__ = 'Copyright 2015'
    __credits__ = ['Kenny Speer']
    __email__ = 'kenny.speer@gmail.com'
    __license__ = 'GPL'
    __maintainer__ = 'Kenny Speer'
    __status__ = 'Production'
    __version__ = '1.0.3'
    vim = <pyVmomi.VmomiSupport.LazyModule object>

VERSION
    1.0.3

AUTHOR
    Kenny Speer

CREDITS
    ['Kenny Speer']

~
~
(END)
```
