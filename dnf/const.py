# const.py
# dnf constants.
#
# Copyright (C) 2012-2015  Red Hat, Inc.
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# the GNU General Public License v.2, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY expressed or implied, including the implied warranties of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.  You should have received a copy of the
# GNU General Public License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.  Any Red Hat trademarks that are incorporated in the
# source code or documentation are not subject to the GNU General Public
# License and may only be used or replicated with the express permission of
# Red Hat, Inc.
#

from __future__ import unicode_literals
import distutils.sysconfig

CONF_FILENAME='/etc/dnf/dnf.conf' # :api
CONF_AUTOMATIC_FILENAME='/etc/dnf/automatic.conf'
DISTROVERPKG=('system-release(releasever)', 'system-release',
              'distribution-release(releasever)', 'distribution-release',
              'redhat-release', 'suse-release')
GROUP_PACKAGE_TYPES = ('mandatory', 'default', 'conditional') # :api
INSTALLONLYPKGS=['kernel', 'kernel-PAE',
                 'installonlypkg(kernel)',
                 'installonlypkg(kernel-module)',
                 'installonlypkg(vm)',
                 'multiversion(kernel)']
LOG='dnf.log'
LOG_HAWKEY='hawkey.log'
LOG_LIBREPO='dnf.librepo.log'
LOG_MARKER='--- logging initialized ---'
LOG_RPM='dnf.rpm.log'
NAME='DNF'
PERSISTDIR='/var/lib/dnf' # :api
PID_FILENAME = '/var/run/dnf.pid'
RUNDIR='/run'
USER_RUNDIR='/run/user'
SYSTEM_CACHEDIR='/var/cache/dnf'
TMPDIR='/var/tmp/'
# CLI verbose values greater or equal to this are considered "verbose":
VERBOSE_LEVEL=6

PREFIX=NAME.lower()
PROGRAM_NAME=NAME.lower()  # Deprecated - no longer used, Argparser prints program name based on sys.argv
PLUGINCONFPATH = '/etc/dnf/plugins'  # :api
PLUGINPATH = '%s/dnf-plugins' % distutils.sysconfig.get_python_lib()
VERSION='4.2.7'
USER_AGENT = "dnf/%s" % VERSION

BUGTRACKER_COMPONENT=NAME.lower()
BUGTRACKER='https://bugzilla.redhat.com/enter_bug.cgi?product=Fedora&component=%s' % BUGTRACKER_COMPONENT
