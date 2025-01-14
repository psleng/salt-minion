"""
Test the ssh_known_hosts states
"""

import os
import shutil

import pytest
from tests.support.case import ModuleCase
from tests.support.mixins import SaltReturnAssertsMixin
from tests.support.runtests import RUNTIME_VARS

GITHUB_FINGERPRINT = "b8:d8:95:ce:d9:2c:0a:c0:e1:71:cd:2e:f5:ef:01:ba:34:17:55:4a:4a:64:80:d3:31:cc:c2:be:3d:ed:0f:6b"
GITHUB_IP = "140.82.121.4"


@pytest.mark.skip_if_binaries_missing("ssh", "ssh-keygen", check_all=True)
class SSHKnownHostsStateTest(ModuleCase, SaltReturnAssertsMixin):
    """
    Validate the ssh state
    """

    @classmethod
    def setUpClass(cls):
        cls.known_hosts = os.path.join(RUNTIME_VARS.TMP, "known_hosts")

    def tearDown(self):
        if os.path.isfile(self.known_hosts):
            os.remove(self.known_hosts)
        super().tearDown()

    @pytest.mark.slow_test
    def test_present(self):
        """
        ssh_known_hosts.present
        """
        kwargs = {
            "name": "github.com",
            "user": "root",
            "enc": "ssh-rsa",
            "fingerprint": GITHUB_FINGERPRINT,
            "config": self.known_hosts,
        }
        # test first
        ret = self.run_state("ssh_known_hosts.present", test=True, **kwargs)
        self.assertSaltNoneReturn(ret)

        # save once, new key appears
        ret = self.run_state("ssh_known_hosts.present", **kwargs)
        try:
            self.assertSaltTrueReturn(ret)
        except AssertionError:
            self.assertInSaltComment("Unable to receive remote host key", ret)
            self.skipTest("Unable to receive remote host key")

        self.assertSaltStateChangesEqual(
            ret, GITHUB_FINGERPRINT, keys=("new", 0, "fingerprint")
        )

        # save twice, no changes
        self.run_state("ssh_known_hosts.present", **kwargs)

        # test again, nothing is about to be changed
        ret = self.run_state("ssh_known_hosts.present", test=True, **kwargs)
        self.assertSaltTrueReturn(ret)

        # then add a record for IP address
        # pylint: disable=repeated-keyword
        ret = self.run_state("ssh_known_hosts.present", **dict(kwargs, name=GITHUB_IP))
        # pylint: enable=repeated-keyword
        try:
            self.assertSaltStateChangesEqual(
                ret, GITHUB_FINGERPRINT, keys=("new", 0, "fingerprint")
            )
        except AssertionError:
            self.assertInSaltComment("Unable to receive remote host key", ret)
            self.skipTest("Unable to receive remote host key")

        # record for every host must be available
        ret = self.run_function(
            "ssh.get_known_host_entries",
            ["root", "github.com"],
            config=self.known_hosts,
        )[0]
        try:
            self.assertNotIn(ret, ("", None))
        except AssertionError:
            raise AssertionError("Salt return '{}' is in ('', None).".format(ret))
        ret = self.run_function(
            "ssh.get_known_host_entries", ["root", GITHUB_IP], config=self.known_hosts
        )[0]
        try:
            self.assertNotIn(ret, ("", None, {}))
        except AssertionError:
            raise AssertionError(
                "Salt return '{}' is in ('', None,".format(ret) + " {})"
            )

    @pytest.mark.slow_test
    def test_present_fail(self):
        # save something wrong
        ret = self.run_state(
            "ssh_known_hosts.present",
            name="github.com",
            user="root",
            fingerprint="aa:bb:cc:dd",
            config=self.known_hosts,
        )
        self.assertSaltFalseReturn(ret)

    @pytest.mark.slow_test
    def test_absent(self):
        """
        ssh_known_hosts.absent
        """
        known_hosts = os.path.join(RUNTIME_VARS.FILES, "ssh", "known_hosts")
        shutil.copyfile(known_hosts, self.known_hosts)
        if not os.path.isfile(self.known_hosts):
            self.skipTest(
                "Unable to copy {} to {}".format(known_hosts, self.known_hosts)
            )

        kwargs = {"name": "github.com", "user": "root", "config": self.known_hosts}
        # test first
        ret = self.run_state("ssh_known_hosts.absent", test=True, **kwargs)
        self.assertSaltNoneReturn(ret)

        # remove once, the key is gone
        ret = self.run_state("ssh_known_hosts.absent", **kwargs)
        self.assertSaltStateChangesEqual(
            ret, GITHUB_FINGERPRINT, keys=("old", 0, "fingerprint")
        )

        # remove twice, nothing has changed
        ret = self.run_state("ssh_known_hosts.absent", **kwargs)
        self.assertSaltStateChangesEqual(ret, {})

        # test again
        ret = self.run_state("ssh_known_hosts.absent", test=True, **kwargs)
        self.assertSaltTrueReturn(ret)
