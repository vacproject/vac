#
#  Andrew McNab, University of Manchester.
#  Copyright (c) 2013-4. All rights reserved.
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

include VERSION

INSTALL_FILES=vacd vac VAC.py vacd.init \
          check-vacd VERSION vacd.logrotate cernvm3iso.spec \
          vacd.8 vac.conf.5 check-vacd.8 vac.1 CHANGES \
          example.vac.conf example.README example.user_data \
          example.prolog.sh example.epilog.sh admin-guide.html \
          testkvm.xml init.pp
          
TGZ_FILES=$(INSTALL_FILES) Makefile vac.spec

GNUTAR ?= tar
vac.tgz: $(TGZ_FILES)
	mkdir -p TEMPDIR/vac
	cp $(TGZ_FILES) TEMPDIR/vac
	cd TEMPDIR ; $(GNUTAR) zcvf ../vac.tgz --owner=root --group=root vac
	rm -R TEMPDIR

install: $(INSTALL_FILES)
	mkdir -p $(RPM_BUILD_ROOT)/var/lib/vac/bin \
	         $(RPM_BUILD_ROOT)/var/lib/vac/etc \
	         $(RPM_BUILD_ROOT)/var/lib/vac/doc \
	         $(RPM_BUILD_ROOT)/var/lib/vac/tmp \
	         $(RPM_BUILD_ROOT)/var/lib/vac/images \
	         $(RPM_BUILD_ROOT)/var/lib/vac/imagecache \
	         $(RPM_BUILD_ROOT)/var/lib/vac/vmtypes/example/shared \
	         $(RPM_BUILD_ROOT)/var/lib/vac/machineoutputs \
	         $(RPM_BUILD_ROOT)/var/lib/vac/machines \
	         $(RPM_BUILD_ROOT)/etc/rc.d/init.d \
	         $(RPM_BUILD_ROOT)/etc/logrotate.d
	cp vacd vac VAC.py check-vacd \
	   $(RPM_BUILD_ROOT)/var/lib/vac/bin
	cp VERSION vac.conf.5 vacd.8 CHANGES init.pp \
	   check-vacd.8 vac.1 example.vac.conf \
	   testkvm.xml cernvm3iso.spec \
	   $(RPM_BUILD_ROOT)/var/lib/vac/doc
	sed "s/<\!-- version -->/ $(VERSION)/" admin-guide.html \
	 > $(RPM_BUILD_ROOT)/var/lib/vac/doc/admin-guide.html
	cp example.README \
           $(RPM_BUILD_ROOT)/var/lib/vac/vmtypes/example/README
	cp example.user_data \
           $(RPM_BUILD_ROOT)/var/lib/vac/vmtypes/example/user_data
	cp example.prolog.sh \
           $(RPM_BUILD_ROOT)/var/lib/vac/vmtypes/example/prolog.sh
	cp example.epilog.sh \
           $(RPM_BUILD_ROOT)/var/lib/vac/vmtypes/example/epilog.sh
	cp vacd.init \
	   $(RPM_BUILD_ROOT)/etc/rc.d/init.d/vacd
	cp vacd.logrotate \
	   $(RPM_BUILD_ROOT)/etc/logrotate.d/vacd
	
rpm: vac.tgz
	rm -Rf RPMTMP
	mkdir -p RPMTMP/SOURCES RPMTMP/SPECS RPMTMP/BUILD \
         RPMTMP/SRPMS RPMTMP/RPMS/noarch RPMTMP/BUILDROOT
	cp -f vac.tgz RPMTMP/SOURCES        
	export VAC_VERSION=$(VERSION) ; rpmbuild -ba \
	  --define "_topdir $(shell pwd)/RPMTMP" \
	  --buildroot $(shell pwd)/RPMTMP/BUILDROOT vac.spec
