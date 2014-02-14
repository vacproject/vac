Name: vac
Version: %(echo ${VAC_VERSION:-0.0})
Release: 1
BuildArch: noarch
Summary: Vac daemon and tools
License: BSD
Group: System Environment/Daemons
Source: vac.tgz
URL: http://www.gridpp.ac.uk/vac/
Vendor: GridPP
Packager: Andrew McNab <Andrew.McNab@cern.ch>
Requires: libvirt-python,genisoimage,nfs-utils,lvm2

%description
Vac implements the Vacuum model for running virtual machines.

%prep

%setup -n vac

%build

%install
make install
mkdir -p $RPM_BUILD_ROOT/usr/sbin

# we are rpm so we can put files in /usr/sbin etc too
cp -f $RPM_BUILD_ROOT/var/lib/vac/bin/vac $RPM_BUILD_ROOT/usr/sbin

mkdir -p $RPM_BUILD_ROOT/usr/share/man/man1 $RPM_BUILD_ROOT/usr/share/man/man5 $RPM_BUILD_ROOT/usr/share/man/man8
cp -f $RPM_BUILD_ROOT/var/lib/vac/doc/vac.1 $RPM_BUILD_ROOT/usr/share/man/man1
cp -f $RPM_BUILD_ROOT/var/lib/vac/doc/vac.conf.5 $RPM_BUILD_ROOT/usr/share/man/man5
cp -f $RPM_BUILD_ROOT/var/lib/vac/doc/vacd.8 \
      $RPM_BUILD_ROOT/var/lib/vac/doc/vacd.8 \
           $RPM_BUILD_ROOT/usr/share/man/man8

%files
/usr/sbin/vac
/usr/share/man/man1
/usr/share/man/man5
/usr/share/man/man8
/var/lib/vac/bin
/var/lib/vac/etc
/var/lib/vac/doc
/var/lib/vac/tmp
/var/lib/vac/images
/var/lib/vac/vmtypes
/var/lib/vac/machines
/etc/rc.d/init.d/vacd
 