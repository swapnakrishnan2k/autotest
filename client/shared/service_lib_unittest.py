#  Copyright(c) 2013 Intel Corporation.
#
#  This program is free software; you can redistribute it and/or modify it
#  under the terms and conditions of the GNU General Public License,
#  version 2, as published by the Free Software Foundation.
#
#  This program is distributed in the hope it will be useful, but WITHOUT
#  ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
#  FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
#  more details.
#
#  You should have received a copy of the GNU General Public License along with
#  this program; if not, write to the Free Software Foundation, Inc.,
#  51 Franklin St - Fifth Floor, Boston, MA 02110-1301 USA.
#
#  The full GNU General Public License is included in this distribution in
#  the file called "COPYING".

import unittest
from mock import MagicMock, patch

import common
from autotest.client.shared import service_lib


class TestSystemd(unittest.TestCase):

    def setUp(self):
        self.service_name = "fake_service"
        init_name = "systemd"
        command_generator = service_lib._command_generators[init_name]
        self.service_command_generator = service_lib.ServiceCommandGenerator(
            command_generator)

    def test_all_commands(self):
        for cmd in (c for c in self.service_command_generator.commands if c != "list"):
            ret = getattr(
                self.service_command_generator, cmd)(self.service_name)
            if cmd == "is_enabled":
                cmd = "is-enabled"
            assert ret == ["systemctl", cmd, "%s.service" % self.service_name]


class TestSysVInit(unittest.TestCase):

    def setUp(self):
        self.service_name = "fake_service"
        init_name = "init"
        command_generator = service_lib._command_generators[init_name]
        self.service_command_generator = service_lib.ServiceCommandGenerator(
            command_generator)

    def test_all_commands(self):
        command_name = "service"
        for cmd in (c for c in self.service_command_generator.commands if c != "list"):
            ret = getattr(
                self.service_command_generator, cmd)(self.service_name)
            if cmd == "is_enabled":
                command_name = "chkconfig"
                cmd = ""
            elif cmd == 'enable':
                command_name = "chkconfig"
                cmd = "on"
            elif cmd == 'disable':
                command_name = "chkconfig"
                cmd = "off"
            assert ret == [command_name, self.service_name, cmd]


class TestSpecificServiceManager(unittest.TestCase):

    def setUp(self):
        self.run_mock = MagicMock()
        self.init_name = "init"
        command_generator = service_lib._command_generators[self.init_name]
        command_list = [c for c in service_lib.COMMANDS if c != "list"]
        service_command_generator = service_lib.ServiceCommandGenerator(
            command_generator, command_list)
        self.service_manager = service_lib.SpecificServiceManager(
            "boot.lldpad", service_command_generator, self.run_mock)

    def test_start(self):
        service = "lldpad"
        self.service_manager.start()
        assert self.run_mock.call_args[0][
            0] == "service boot.%s start" % service

    def test_stop_with_args(self):
        service = "lldpad"
        self.service_manager.stop(ignore_status=True)
        assert self.run_mock.call_args[0][
            0] == "service boot.%s stop" % service
        assert self.run_mock.call_args[1] == {'ignore_status': True}

    def test_list_is_not_present_in_SpecifcServiceManager(self):
        assert not hasattr(self.service_manager, "list")


class TestSystemdServiceManager(unittest.TestCase):

    def setUp(self):
        self.run_mock = MagicMock()
        self.init_name = "systemd"
        command_generator = service_lib._command_generators[self.init_name]
        service_manager = service_lib._service_managers[self.init_name]
        service_command_generator = service_lib.ServiceCommandGenerator(
            command_generator)
        self.service_manager = service_manager(
            service_command_generator, self.run_mock)

    def test_start(self):
        service = "lldpad"
        self.service_manager.start(service)
        assert self.run_mock.call_args[0][
            0] == "systemctl start %s.service" % service

    def test_list(self):
        self.service_manager.list()
        assert self.run_mock.call_args[0][
            0] == "systemctl list-unit-files --type=service"

    def test_set_default_runlevel(self):
        runlevel = service_lib.convert_sysv_runlevel(3)
        mktemp_mock = MagicMock(return_value="temp_filename")
        symlink_mock = MagicMock()
        rename_mock = MagicMock()

        @patch.object(service_lib, "mktemp", mktemp_mock)
        @patch("os.symlink", symlink_mock)
        @patch("os.rename", rename_mock)
        def _():
            self.service_manager.change_default_runlevel(runlevel)
            assert mktemp_mock.called
            assert symlink_mock.call_args[0][
                0] == "/usr/lib/systemd/system/multi-user.target"
            assert rename_mock.call_args[0][
                1] == "/etc/systemd/system/default.target"
        _()

    def test_unknown_runlevel(self):
        self.assertRaises(ValueError,
                          service_lib.convert_systemd_target_to_runlevel, "unknown")

    def test_runlevels(self):
        assert service_lib.convert_sysv_runlevel(0) == "poweroff.target"
        assert service_lib.convert_sysv_runlevel(1) == "rescue.target"
        assert service_lib.convert_sysv_runlevel(2) == "multi-user.target"
        assert service_lib.convert_sysv_runlevel(5) == "graphical.target"
        assert service_lib.convert_sysv_runlevel(6) == "reboot.target"


class TestSysVInitServiceManager(unittest.TestCase):

    def setUp(self):
        self.run_mock = MagicMock()
        self.init_name = "init"
        command_generator = service_lib._command_generators[self.init_name]
        service_manager = service_lib._service_managers[self.init_name]
        service_command_generator = service_lib.ServiceCommandGenerator(
            command_generator)
        self.service_manager = service_manager(
            service_command_generator, self.run_mock)

    def test_enable(self):
        service = "lldpad"
        self.service_manager.enable(service)
        assert self.run_mock.call_args[0][0] == "chkconfig lldpad on"

    def test_unknown_runlevel(self):
        self.assertRaises(ValueError,
                          service_lib.convert_sysv_runlevel, "unknown")

    def test_runlevels(self):
        assert service_lib.convert_systemd_target_to_runlevel(
            "poweroff.target") == '0'
        assert service_lib.convert_systemd_target_to_runlevel(
            "rescue.target") == 's'
        assert service_lib.convert_systemd_target_to_runlevel(
            "multi-user.target") == '3'
        assert service_lib.convert_systemd_target_to_runlevel(
            "graphical.target") == '5'
        assert service_lib.convert_systemd_target_to_runlevel(
            "reboot.target") == '6'