#
#  VAC.py - common functions, classes, and variables for Vac
#
#  Andrew McNab, University of Manchester.
#  Copyright (c) 2013. All rights reserved.
#
#  Redistribution and use in source and binary forms, with or
#  without modification, are permitted provided that the following
#  conditions are met:
#
#    o Redistributions of source code must retain the above
#      copyright notice, this list of conditions and the following
#      disclaimer. 
#    o Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution. 
#
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND
#  CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
#  INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
#  MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
#  DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS
#  BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
#  EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
#  TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#  DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
#  ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
#  OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
#  OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
#  POSSIBILITY OF SUCH DAMAGE.
#
#  Contacts: Andrew.McNab@cern.ch  http://www.gridpp.ac.uk/vac/
#

import os
import sys
import uuid
import time
import errno
import base64
import shutil
import libvirt
import tempfile

from stat import *

from ConfigParser import RawConfigParser

class VacState:
   unknown, shutdown, starting, running, paused, zombie = ('Unknown', 'Shut down', 'Starting', 'Running', 'Paused', 'Zombie')

class VacVM:
   def __init__(self, hname):
      self.name=hname
      self.state=VacState.unknown
      self.uuidStr=None
      self.vmtypeName=None

      conn = libvirt.open(None)
      if conn == None:
          print 'Failed to open connection to the hypervisor'
          raise

      try:
          dom = conn.lookupByName(self.name)          
          self.uuidStr = dom.UUIDString()

          for vmtypeName, vmtype in vmtypes.iteritems():
               if os.path.isdir('/var/lib/vac/machines/' + self.name + '/' + vmtypeName + '/' + self.uuidStr):
                   self.vmtypeName = vmtypeName
                   break
          
          if not self.vmtypeName:
            self.state = VacState.zombie
            self.uuidStr = None
          elif (dom.info()[0] != libvirt.VIR_DOMAIN_RUNNING and
                dom.info()[0] != libvirt.VIR_DOMAIN_BLOCKED):
            self.state = VacState.paused
          else:
            self.state = VacState.running
            self.cpuSeconds = dom.info()[4] / 1000000000.0

      except:
          self.state = VacState.shutdown
 
          # try to find state of last instance to be created   
          self.uuidFromLatestVM()

          if self.uuidStr and self.vmtypeName and \
             not os.path.exists('/var/lib/vac/machines/' + self.name + '/' + self.vmtypeName + '/' + self.uuidStr + '/started') :
            self.state = VacState.starting

      conn.close()
      
      if self.uuidStr and os.path.exists('/var/lib/vac/machines/' + self.name + '/' + self.vmtypeName + '/' + self.uuidStr 
                                         + '/shared/machinefeatures/shutdowntime') :
          f = open('/var/lib/vac/machines/' + self.name + '/' + self.vmtypeName + '/' + self.uuidStr 
                                         + '/shared/machinefeatures/shutdowntime')
          self.shutdownTime = int(f.read().strip())
          f.close()
      
   def uuidFromLatestVM(self):

      self.uuidStr     = None
      self.vmtypeName = None
      
      for vmtypeName, vmtype in vmtypes.iteritems():
        try:
             dirslist = os.listdir('/var/lib/vac/machines/' + self.name + '/' + vmtypeName)
        except:
             continue

        for onedir in dirslist:
          if os.path.isdir('/var/lib/vac/machines/' + self.name + '/' + vmtypeName + '/' + onedir):
             if self.vmtypeName and self.uuidStr:
                if os.stat('/var/lib/vac/machines/' + self.name + '/' + vmtypeName + '/' + onedir).st_ctime > os.stat('/var/lib/vac/machines/' + self.name + '/' + self.vmtypeName + '/' + self.uuidStr).st_ctime:
                  self.uuidStr = onedir          
                  self.vmtypeName = vmtypeName
             else:
               self.vmtypeName = vmtypeName
               self.uuidStr = onedir
          
   def makeISO(self):
      try:
        os.makedirs('/var/lib/vac/machines/' + self.name + '/' + self.vmtypeName + '/' + self.uuidStr + '/iso.d')
      except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir('/var/lib/vac/machines/' + self.name + '/' + self.vmtypeName + '/' + self.uuidStr + '/iso.d'):
            pass 
        else: raise

      f = open('/var/lib/vac/machines/' + self.name + '/' + self.vmtypeName + '/' + self.uuidStr + '/iso.d/context.sh', 'w')

      if 'rootpublickey' in vmtypes[self.vmtypeName]:

          if vmtypes[self.vmtypeName]['rootpublickey'][0] == '/':
              rootpublickey_file = vmtypes[self.vmtypeName]['rootpublickey']
          else:
              rootpublickey_file = '/var/lib/vac/vmtypes/' + self.vmtypeName + '/' + vmtypes[self.vmtypeName]['rootpublickey']

          shutil.copy2(rootpublickey_file, '/var/lib/vac/machines/' + self.name + '/' + self.vmtypeName + '/' + self.uuidStr + '/iso.d/root.pub')
          f.write('ROOT_PUBKEY=root.pub\n')
  
      if 'user_data' in vmtypes[self.vmtypeName]:

          if vmtypes[self.vmtypeName]['user_data'][0] == '/':
              user_data_file = vmtypes[self.vmtypeName]['user_data']
          else:
              user_data_file = '/var/lib/vac/vmtypes/' + self.vmtypeName + '/' + vmtypes[self.vmtypeName]['user_data']

          try:
            u = open(user_data_file, 'r')
          except:
            raise 'Failed to open' + user_data_file  
            
          user_data_contents = u.read()
          u.close()
          f.write('EC2_USER_DATA=' +  base64.b64encode(user_data_contents) + '\n')
  
      f.write('ONE_CONTEXT_PATH="/var/lib/amiconfig"\n')
      f.write('MACHINEFEATURES="/etc/machinefeatures"\n')
      f.write('JOBFEATURES="/etc/jobfeatures"\n')
      f.close()
                                     
      f = open('/var/lib/vac/machines/' + self.name + '/' + self.vmtypeName + '/' + self.uuidStr + '/iso.d/prolog.sh', 'w')
      f.write('mkdir -p /etc/vac /etc/machinefeatures /etc/jobfeatures /etc/machineoutputs\n')
      
#      f.write('cat <<EOF >/etc/rc.d/rc3.d/S11vacmounts\n#!/bin/sh\n')
      f.write('mount ' + os.uname()[1] + ':/var/lib/vac/machines/' + self.name + '/' + self.vmtypeName + '/' + self.uuidStr + '/shared/vac /etc/vac\n')
      f.write('mount ' + os.uname()[1] + ':/var/lib/vac/machines/' + self.name + '/' + self.vmtypeName + '/' + self.uuidStr + '/shared/jobfeatures /etc/jobfeatures\n')
      f.write('mount ' + os.uname()[1] + ':/var/lib/vac/machines/' + self.name + '/' + self.vmtypeName + '/' + self.uuidStr + '/shared/machinefeatures /etc/machinefeatures\n')
      f.write('mount -o rw ' + os.uname()[1] + ':/var/lib/vac/machines/' + self.name + '/' + self.vmtypeName + '/' + self.uuidStr + '/shared/machineoutputs /etc/machineoutputs\n')
#      f.write('EOF\n')
#      f.write('chmod +x /etc/rc.d/rc3.d/S11vacmounts\n')

      if 'shutdown_command' in vmtypes[self.vmtypeName] and \
         'shutdown_command_user' in vmtypes[self.vmtypeName]:
            f.write('''grep "^# Enable shutdown_command mechanism" /etc/sudoers 2>/dev/null >/dev/null
if [ $? != 0 ] ; then
echo "# Enable shutdown_command mechanism" >>/etc/sudoers
echo "Defaults:''' + vmtypes[self.vmtypeName]['shutdown_command_user'] + ''' !requiretty" >>/etc/sudoers
echo "Defaults:''' + vmtypes[self.vmtypeName]['shutdown_command_user'] + ''' visiblepw" >>/etc/sudoers
echo ''' + vmtypes[self.vmtypeName]['shutdown_command_user'] + ''' ALL = NOPASSWD: /etc/vac/vac-shutdown-vm >> /etc/sudoers
fi\n''')

      f.write('# end of vac prolog.sh\n\n')

      # if a prolog is given for this vmtype, we append that to vac's part of the script
      if 'prolog' in vmtypes[self.vmtypeName]:

          if vmtypes[self.vmtypeName]['prolog'][0] == '/':
              prolog_file = vmtypes[self.vmtypeName]['prolog']
          else:
              prolog_file = '/var/lib/vac/vmtypes/' + self.vmtypeName + '/' + vmtypes[self.vmtypeName]['prolog']

          try:
            g = open(prolog_file, "r")
            f.write(g.read())
            g.close()
          except:
            raise 'Failed to read prolog file', prolog_file
  
      f.close()
      
      if 'epilog' in vmtypes[self.vmtypeName]:

          if vmtypes[self.vmtypeName]['epilog'][0] == '/':
              epilog_file = vmtypes[self.vmtypeName]['epilog']
          else:
              epilog_file = '/var/lib/vac/vmtypes/' + self.vmtypeName + '/' + vmtypes[self.vmtypeName]['epilog']

          shutil.copy2(epilog_file, '/var/lib/vac/machines/' + self.name + '/' + self.vmtypeName + '/' + self.uuidStr + '/iso.d/epilog.sh')
  
      os.system('genisoimage -quiet -o /var/lib/vac/machines/' + self.name + '/' + self.vmtypeName + '/' + self.uuidStr 
                + '/context.iso /var/lib/vac/machines/' + self.name + '/' + self.vmtypeName + '/' + self.uuidStr + '/iso.d')
             
   def exportFileSystems(self):
      os.makedirs('/var/lib/vac/machines/' + self.name + '/' + self.vmtypeName + '/' + self.uuidStr + '/shared/vac')
      os.makedirs('/var/lib/vac/machines/' + self.name + '/' + self.vmtypeName + '/' + self.uuidStr + '/shared/jobfeatures')
      os.makedirs('/var/lib/vac/machines/' + self.name + '/' + self.vmtypeName + '/' + self.uuidStr + '/shared/machineoutputs')
      os.makedirs('/var/lib/vac/machines/' + self.name + '/' + self.vmtypeName + '/' + self.uuidStr + '/shared/machinefeatures')

      # We share this via NFS rather than in the CDROM image so only root can see the key!
      if 'hostkey' in vmtypes[self.vmtypeName]:
        if vmtypes[self.vmtypeName]['hostkey'][0] == '/':
            hostkey_file = vmtypes[self.vmtypeName]['hostkey']
        else:
            hostkey_file = '/var/lib/vac/vmtypes' + self.vmtypeName + '/' + vmtypes[self.vmtypeName]['hostkey']
                    
        # Enforce root-only read permission on the factory machine, used by NFS too
        os.chmod(hostkey_file, S_IRUSR)
        shutil.copy2(hostkey_file, '/var/lib/vac/machines/' + self.name + '/' + self.vmtypeName + '/' + self.uuidStr + '/shared/vac/hostkey.pem')
             
      if 'hostcert' in vmtypes[self.vmtypeName]:
        if vmtypes[self.vmtypeName]['hostcert'][0] == '/':
            hostcert_file = vmtypes[self.vmtypeName]['hostcert']
        else:
            hostcert_file = '/var/lib/vac/vmtypes' + self.vmtypeName + '/' + vmtypes[self.vmtypeName]['hostcert']

        shutil.copy2(hostcert_file, '/var/lib/vac/machines/' + self.name + '/' + self.vmtypeName + '/' + self.uuidStr + '/shared/vac/hostcert.pem')
       
      if 'shutdown_command' in vmtypes[self.vmtypeName]:
        if vmtypes[self.vmtypeName]['shutdown_command'][0] == '/':
            shutdown_file = vmtypes[self.vmtypeName]['shutdown_command']
        else:
            shutdown_file = '/var/lib/vac/vmtypes' + self.vmtypeName + '/' + vmtypes[self.vmtypeName]['shutdown_command']

        shutil.copy2(shutdown_file, '/var/lib/vac/machines/' + self.name + '/' + self.vmtypeName + '/' + self.uuidStr + '/shared/vac/vac-shutdown-vm')
             
        os.chmod('/var/lib/vac/machines/' + self.name + '/' + self.vmtypeName + '/' + self.uuidStr + '/shared/vac/vac-shutdown-vm', 
                 S_IRUSR | S_IXUSR | S_IRGRP | S_IXGRP | S_IROTH | S_IXOTH )

        createFile('/var/lib/vac/machines/' + self.name + '/' + self.vmtypeName + '/' + self.uuidStr + '/shared/machinefeatures/shutdown_command', 
                   '/etc/vac/vac-shutdown-vm\n')

      createFile('/var/lib/vac/machines/' + self.name + '/' + self.vmtypeName + '/' + self.uuidStr + '/shared/machinefeatures/shutdowntime', 
                 str(int(time.time() + vmtypes[self.vmtypeName]['max_wallclock_seconds']))  + '\n')
                                                     
      os.system('exportfs ' + self.name + ':/var/lib/vac/machines/' + self.name + '/' + self.vmtypeName + '/' + self.uuidStr + '/shared')
      os.system('exportfs -o rw,no_root_squash ' + self.name + ':/var/lib/vac/machines/' + self.name + '/' + self.vmtypeName + '/' + self.uuidStr + '/shared/machineoutputs')

   def makeRootDisk(self):
      if domainType == 'kvm':
         # With kvm we can make a small QEMU qcow2 disk for each instance of 
         # this virtualhostname, backed by the full image given in conf
         if os.system('qemu-img create -b ' + vmtypes[self.vmtypeName]['root_image'] + 
             ' -f qcow2 /var/lib/vac/machines/' + self.name + '/' + self.vmtypeName + '/' + self.uuidStr + '/sparse-root.qcow2 >/dev/null') != 0:
          logLine('creation of COW disk image fails!')
          raise NameError('Creation of COW disk image fails!')
      elif domainType == 'xen':
         # Because Xen COW is broken, we unzip/copy the root.disk, overwriting 
         # any copy already in the top level directory of this virtualhostname
         if vmtypes[self.vmtypeName]['root_image'][-3:] == '.gz':
          print 'gunzip from',vmtypes[self.vmtypeName]['root_image'],'to /var/lib/vac/machines/' + self.name + '/root.disk'
          if os.system('gunzip -c ' + vmtypes[self.vmtypeName]['root_image'] +
                       ' >/var/lib/vac/machines/' + self.name + '/root.disk 2>/dev/null') != 0:
            logLine('gunzip of disk image fails!')
            raise NameError('gunzip of disk image fails!')
         else:
          logLine('copy from' + vmtypes[self.vmtypeName]['root_image'] + ' to /var/lib/vac/machines/' + self.name + '/root.disk')
          if shutil.copy(vmtypes[self.vmtypeName]['root_image'], 
                         '/var/lib/vac/machines/' + self.name + '/root.disk') != 0:
            logLine('copy of disk image fails!')
            raise NameError('copy of disk image fails!')

   def destroyVM(self):
      conn = libvirt.open(None)
      if conn == None:
          logLine('Failed to open connection to the hypervisor')
          raise NameError('failed to open connection to the hypervisor')

      dom = conn.lookupByName(self.name)
      
      if dom:
          dom.destroy()

      conn.close()

   def createVM(self, vmtypeName):
      self.uuidStr = str(uuid.uuid4())
      self.vmtypeName = vmtypeName

      os.makedirs('/var/lib/vac/machines/' + self.name + '/' + self.vmtypeName + '/' + self.uuidStr)

      self.makeISO()
      self.makeRootDisk()
      self.exportFileSystems()

      if not 'mac' in virtualmachines[self.name]:
          print 'No mac given in configuration for',self.name
          raise

      conn = libvirt.open(None)
      if conn == None:
          print 'Failed to open connection to the hypervisor'
          raise

      if domainType == 'kvm':
          xmldesc="""<domain type='kvm'>
  <name>""" + self.name + """</name>
  <uuid>""" + self.uuidStr + """</uuid>
  <memory unit='GiB'>2</memory>
  <currentMemory unit='GiB'>2</currentMemory>
  <vcpu>""" + str(conn.getInfo()[2]) + """</vcpu>
  <os>
    <type arch='x86_64' machine='rhel6.2.0'>hvm</type>
    <boot dev='network'/>
    <bios useserial='yes'/>
  </os>
  <pm>
    <suspend-to-disk enabled='no'/>
    <suspend-to-mem  enabled='no'/>
  </pm>
  <features>
    <acpi/>
    <apic/>
    <pae/>
  </features>
  <clock offset='utc'/>
  <on_poweroff>destroy</on_poweroff>
  <on_reboot>destroy</on_reboot>
  <on_crash>destroy</on_crash>
  <devices>
    <emulator>/usr/libexec/qemu-kvm</emulator>
    <disk type='file' device='disk'>
     <driver name="qemu" type="qcow2" cache="none" />
     <source file='/var/lib/vac/machines/""" + self.name + '/' + self.vmtypeName + '/' + self.uuidStr +  """/sparse-root.qcow2' />
     <target dev='hda' bus='ide'/>
    </disk>
    <disk type='file' device='cdrom'>
      <source file='/var/lib/vac/machines/""" + self.name + '/' + self.vmtypeName + '/' + self.uuidStr +  """/context.iso'/>
      <target dev='hdc'/>
      <readonly/>
      <driver name='qemu' type='raw'/>
    </disk>
    <controller type='usb' index='0'>
      <address type='pci' domain='0x0000' bus='0x00' slot='0x01' function='0x2'/>
    </controller>
    <interface type='bridge'>
      <mac address='""" + virtualmachines[self.name]['mac'] + """'/>
      <source bridge='p1p1'/>
      <model type='virtio'/>
      <address type='pci' domain='0x0000' bus='0x00' slot='0x03' function='0x0'/>
    </interface>
    <serial type='pty'>
      <target port='0'/>
    </serial>
    <graphics type='vnc' port='-1' autoport='yes' keymap='en-gb'/>
    <video>
      <model type='vga' vram='9216' heads='1'/>
      <address type='pci' domain='0x0000' bus='0x00' slot='0x02' function='0x0'/>
    </video>
    <memballoon model='virtio'>
      <address type='pci' domain='0x0000' bus='0x00' slot='0x05' function='0x0'/>
    </memballoon>
  </devices>
</domain>
"""        
      elif domainType == 'xen':
          xmldesc="""<domain type='xen'>
  <name>""" + self.name + """</name>
  <uuid>""" + self.uuidStr + """</uuid>
  <memory unit='MiB'>768</memory>
  <currentMemory unit='MiB'>768</currentMemory>
  <vcpu>""" + str(conn.getInfo()[2]) + """</vcpu>
  <bootloader>/usr/bin/pygrub</bootloader>
  <os>
    <type arch='x86_64' machine='xenpv'>linux</type>
  </os>
  <clock offset='utc' adjustment='reset'/>
  <on_poweroff>destroy</on_poweroff>
  <on_reboot>restart</on_reboot>
  <on_crash>restart</on_crash>
  <devices>
    <disk type='file' device='disk'>
      <driver name='file'/>
      <source file='/var/lib/vac/machines/""" + self.name +  """/root.disk' />
      <target dev='hda' bus='xen'/>
    </disk>
    <disk type='file' device='cdrom'>
      <source file='/var/lib/vac/machines/""" + self.name + '/' + self.vmtypeName + '/' + self.uuidStr +  """/context.iso'/>
      <target dev='hdc'/>
      <readonly/>
      <driver name='file'/>
    </disk>
    <console type='pty'>
      <target type='xen' port='0'/>
    </console>
    <graphics type='vnc' port='-1' autoport='yes' listen='0.0.0.0' keymap='en-us'>
      <listen type='address' address='0.0.0.0'/>
    </graphics>
    <interface type='bridge'>
      <mac address='""" + virtualmachines[self.name]['mac'] + """'/>
      <source bridge='br-eth0'/>
      <model type='virtio'/>
      <address type='pci' domain='0x0000' bus='0x00' slot='0x03' function='0x0'/>
    </interface>
  </devices>
</domain>
"""        

      else:
          raise 'domain_type not recognised!'
      
      createFile('/var/lib/vac/machines/' + self.name + '/' + self.vmtypeName + '/' + self.uuidStr + '/started', 
                  str(int(time.time())) + '\n')
      
      createFile('/var/lib/vac/machines/' + self.name + '/' + self.vmtypeName + '/' + self.uuidStr + '/heartbeat', 
                 '0.0\n')
      
      try:
           dom = conn.createXML(xmldesc, 0)
      except:
           logLine('Failed trying to create VM domain for ' + self.name)

      conn.close()
     
def createFile(targetname, contents):
   # Create a text file containing contents in the vac tmp directory
   # then move it into place. Rename is an atomic operation in POSIX,
   # including situations where targetname already exists.
   
   try:
     ftup = tempfile.mkstemp(prefix='/var/lib/vac/tmp',text=True)
     os.write(ftup[0], contents)
     os.close(ftup[0])
     os.rename(ftup[1], targetname)
     return True
   except:
     return False

def logLine(text):
   print time.strftime('%b %d %H:%M:%S [') + str(os.getpid()) + ']: ' + text
   sys.stdout.flush()
          
virtualmachines = {}
factories = []
vmtypes = {}
domainType = 'kvm'
vcpuPerMachine = None
mbPerMachine = None
deleteOldFiles = True

def readConf():
      global factories, vcpuPerMachine, mbPerMachine, domainType, deleteOldFiles
      
      parser = RawConfigParser()

      # Main configuration file, including global [settings] section
      parser.read('/etc/vac.conf')
      
      # Optional file for vitualmachine sections for this factory machine
      parser.read('/etc/vac-virtualmachines.conf')
      
      # Optional file with [factories] listing all factories in this vac space
      parser.read('/etc/vac-factories.conf')

      # Optional file with [targetshares] for all factories in this vac space
      parser.read('/etc/vac-targetshares.conf')


      # general settings from [Settings] section

      if not parser.has_section('settings'):
        print 'Must have a settings section!'
        raise NameError('Must have a settings section!')
      
      if parser.has_option('settings', 'domain_type'):
          # defaults to 'kvm' but can specify 'xen' instead
          domainType = parser.get('settings','domain_type').strip()
             
      if (parser.has_option('settings', 'delete_old_files') and
          parser.get('settings','delete_old_files').strip().lower() == 'false'):
           deleteOldFiles = False
      else:
           deleteOldFiles = True
             
      if parser.has_option('settings', 'vcpu_per_machine'):
          # if this isn't set, then we will share cores by number
          # of virtual machines defined
          vcpuPerMachine = int(parser.get('settings','vcpu_per_machine'))
             
      if parser.has_option('settings', 'mb_per_machine'):
          # if this isn't set, then we will share physical by number
          # of virtual machines defined
          mbPerMachine = int(parser.get('settings','mb_per_machine'))
             
      # all other sections are VM types or Virtual Machines or Factories
      for sectionName in parser.sections():

         if (sectionName.lower() == 'settings'):
           continue 
           
         sectionNameSplit = sectionName.lower().split(None,1)
         
         if sectionNameSplit[0] == 'vmtype':
             vmtype = {}
             vmtype['root_image'] = parser.get(sectionName, 'root_image')

             vmtype['share'] = 0.0
                                            
             if parser.has_option('targetshares', sectionNameSplit[1]):
                 vmtype['share'] = float(parser.get('targetshares', sectionNameSplit[1]))

             if parser.has_option(sectionName, 'hostcert'):
                 vmtype['hostcert'] = parser.get(sectionName, 'hostcert')
             
             if parser.has_option(sectionName, 'hostkey'):
                 vmtype['hostkey'] = parser.get(sectionName, 'hostkey')

             if parser.has_option(sectionName, 'rootpublickey'):
                 vmtype['rootpublickey'] = parser.get(sectionName, 'rootpublickey')

             if parser.has_option(sectionName, 'user_data'):
                 vmtype['user_data'] = parser.get(sectionName, 'user_data')

             if parser.has_option(sectionName, 'prolog'):
                 vmtype['prolog'] = parser.get(sectionName, 'prolog')

             if parser.has_option(sectionName, 'epilog'):
                 vmtype['epilog'] = parser.get(sectionName, 'epilog')

             if parser.has_option(sectionName, 'max_wallclock_seconds'):
                 vmtype['max_wallclock_seconds'] = int(parser.get(sectionName, 'max_wallclock_seconds'))
             else:
                 vmtype['max_wallclock_seconds'] = 86400
             
             if parser.has_option(sectionName, 'shutdown_command'):
                 vmtype['shutdown_command'] = parser.get(sectionName, 'shutdown_command')

             if parser.has_option(sectionName, 'shutdown_command_user'):
                 vmtype['shutdown_command_user'] = parser.get(sectionName, 'shutdown_command_user')

             if parser.has_option(sectionName, 'backoff_seconds'):
                 vmtype['backoff_seconds'] = int(parser.get(sectionName, 'backoff_seconds'))
             else:
                 vmtype['backoff_seconds'] = 10
             
             if parser.has_option(sectionName, 'fizzle_seconds'):
                 vmtype['fizzle_seconds'] = int(parser.get(sectionName, 'fizzle_seconds'))
             else:
                 vmtype['fizzle_seconds'] = 600
             
             vmtypes[sectionNameSplit[1]] = vmtype
             
         elif sectionName.lower() == 'factories':
             try:
                 factories = (parser.get('factories', 'names')).lower().split()
             except:
                 pass
             
         elif sectionNameSplit[0] == 'virtualmachine':
             virtualmachine = {}
             virtualmachine['mac'] = parser.get(sectionName, 'mac')
             
             virtualmachines[sectionNameSplit[1]] = virtualmachine
             try:
              os.makedirs('/var/lib/vac/machines/' + sectionNameSplit[1])
             except OSError as exc: # Python >2.5
              if exc.errno == errno.EEXIST and os.path.isdir('/var/lib/vac/machines/' + sectionNameSplit[1]):
                pass
              else: raise

