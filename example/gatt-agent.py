#!/usr/bin/env python3

# Original source: from bluez-5.7/test/simple-agent

# EcoDroidLink/ykasidit@gmail.com modifications:
# - automate the agent for running on a headless Pi - to answer pair and connection requests without a blocking query
# - handle running on older bluez versions - agent registration (tested with Ubuntu 12.04's BlueZ 4.98)
#
# following file taken from https://github.com/ykasidit/ecodroidlink/blob/master/edl_agent
#

from __future__ import absolute_import, print_function, unicode_literals

import time
import logging
import logging.handlers
from optparse import OptionParser  # pylint: disable=W0402

import dbus
import dbus.service
import dbus.mainloop.glib

# import bluezutils

from gi.repository import GObject


logger = logging.getLogger("edl_agent")
logger.setLevel(logging.DEBUG)
handler = logging.handlers.SysLogHandler(address="/dev/log")
logger.addHandler(handler)


def printlog(s):
    logger.info(s)
    print(s)


BUS_NAME = "org.bluez"
AGENT_INTERFACE = "org.bluez.Agent1"
AGENT_PATH = "/test/agent"

bus = None
device_obj = None
dev_path = None


def set_trusted(item_path):
    props = dbus.Interface(bus.get_object("org.bluez", item_path), "org.freedesktop.DBus.Properties")
    props.Set("org.bluez.Device1", "Trusted", True)


def dev_connect(item_path):
    dev = dbus.Interface(bus.get_object("org.bluez", item_path), "org.bluez.Device1")
    dev.Connect()


class Rejected(dbus.DBusException):
    _dbus_error_name = "org.bluez.Error.Rejected"


class Agent(dbus.service.Object):
    exit_on_release = True

    def set_exit_on_release(self, exit_on_release):
        self.exit_on_release = exit_on_release

    @dbus.service.method(AGENT_INTERFACE, in_signature="", out_signature="")
    def Release(self):
        printlog("Release")
        if self.exit_on_release:
            mainloop.quit()

    @dbus.service.method(AGENT_INTERFACE, in_signature="os", out_signature="")
    def AuthorizeService(self, device, uuid):
        printlog("AuthorizeService (%s, %s)" % (device, uuid))
        authorize = "yes"  # ask("Authorize connection (yes/no): ")
        if authorize == "yes":
            return
        raise Rejected("Connection rejected by user")

    @dbus.service.method(AGENT_INTERFACE, in_signature="o", out_signature="s")
    def RequestPinCode(self, device):
        printlog("RequestPinCode (%s)" % (device))
        set_trusted(device)
        return "0000"  # ask("Enter PIN Code: ")

    @dbus.service.method(AGENT_INTERFACE, in_signature="o", out_signature="u")
    def RequestPasskey(self, device):
        printlog("RequestPasskey (%s)" % (device))
        set_trusted(device)
        passkey = "0000"  # ask("Enter passkey: ")
        return dbus.UInt32(passkey)

    @dbus.service.method(AGENT_INTERFACE, in_signature="ouq", out_signature="")
    def DisplayPasskey(self, device, passkey, entered):
        printlog("DisplayPasskey (%s, %06u entered %u)" % (device, passkey, entered))

    @dbus.service.method(AGENT_INTERFACE, in_signature="os", out_signature="")
    def DisplayPinCode(self, device, pincode):
        printlog("DisplayPinCode (%s, %s)" % (device, pincode))

    @dbus.service.method(AGENT_INTERFACE, in_signature="ou", out_signature="")
    def RequestConfirmation(self, device, passkey):
        printlog("RequestConfirmation (%s, %06d)" % (device, passkey))
        confirm = "yes"  # ask("Confirm passkey (yes/no): ")
        if confirm == "yes":
            set_trusted(device)
            return
        raise Rejected("Passkey doesn't match")

    @dbus.service.method(AGENT_INTERFACE, in_signature="o", out_signature="")
    def RequestAuthorization(self, device):
        printlog("RequestAuthorization (%s)" % (device))
        auth = "yes"  # ask("Authorize? (yes/no): ")
        if auth == "yes":
            return
        raise Rejected("Pairing rejected")

    @dbus.service.method(AGENT_INTERFACE, in_signature="", out_signature="")
    def Cancel(self):
        printlog("Cancel")


class AgentOld(dbus.service.Object):
    exit_on_release = True

    def set_exit_on_release(self, exit_on_release):
        self.exit_on_release = exit_on_release

    @dbus.service.method("org.bluez.Agent", in_signature="", out_signature="")
    def Release(self):
        print("Release")
        if self.exit_on_release:
            mainloop.quit()

    @dbus.service.method("org.bluez.Agent", in_signature="os", out_signature="")
    def Authorize(self, device, uuid):
        print("Authorize (%s, %s)" % (device, uuid))
        authorize = "yes"
        if authorize == "yes":
            return
        raise Rejected("Connection rejected by user")

    @dbus.service.method("org.bluez.Agent", in_signature="o", out_signature="s")
    def RequestPinCode(self, device):
        print("RequestPinCode (%s)" % (device))
        return "0000"

    @dbus.service.method("org.bluez.Agent", in_signature="o", out_signature="u")
    def RequestPasskey(self, device):
        print("RequestPasskey (%s)" % (device))
        passkey = "0000"
        return dbus.UInt32(passkey)

    @dbus.service.method("org.bluez.Agent", in_signature="ou", out_signature="")
    def DisplayPasskey(self, device, passkey):
        print("DisplayPasskey (%s, %d)" % (device, passkey))

    @dbus.service.method("org.bluez.Agent", in_signature="ou", out_signature="")
    def RequestConfirmation(self, device, passkey):
        print("RequestConfirmation (%s, %d)" % (device, passkey))
        confirm = "yes"
        if confirm == "yes":
            return
        raise Rejected("Passkey doesn't match")

    @dbus.service.method("org.bluez.Agent", in_signature="s", out_signature="")
    def ConfirmModeChange(self, mode):
        print("ConfirmModeChange (%s)" % (mode))
        authorize = "yes"
        if authorize == "yes":
            return
        raise Rejected("Mode change by user")

    @dbus.service.method("org.bluez.Agent", in_signature="", out_signature="")
    def Cancel(self):
        print("Cancel")


def pair_reply():
    printlog("Device paired")
    set_trusted(dev_path)
    dev_connect(dev_path)
    mainloop.quit()


def pair_error(error):
    err_name = error.get_dbus_name()
    if err_name == "org.freedesktop.DBus.Error.NoReply" and device_obj:
        printlog("Timed out. Cancelling pairing")
        device_obj.CancelPairing()
    else:
        printlog("Creating device failed: %s" % (error))

    mainloop.quit()


if __name__ == "__main__":
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    printlog("edl: agent starting")
    bus = dbus.SystemBus()
    capability = "KeyboardDisplay"
    parser = OptionParser()
    parser.add_option("-i", "--adapter", action="store", type="string", dest="adapter_pattern", default=None)
    parser.add_option("-c", "--capability", action="store", type="string", dest="capability")
    parser.add_option("-t", "--timeout", action="store", type="int", dest="timeout", default=60000)
    (options, args) = parser.parse_args()

    if options.capability:
        capability = options.capability

    mainloop = GObject.MainLoop()

    try:  # try new bluez 5.7 code
        obj = bus.get_object(BUS_NAME, "/org/bluez")
        manager = dbus.Interface(obj, "org.bluez.AgentManager1")

        # loop to handle and omit dbus.exceptions.DBusException:
        #    org.bluez.Error.AlreadyExists: Already Exists - in case user uses a GUI
        #    bluetooth-applet (that comes in GNOME, etc.) to handle pairing and
        #    connection requests... ours is not needed then

        while 1:
            try:
                path = "/test/agent"
                manager.RegisterAgent(path, capability)
                printlog("edl: auto-pair/accept agent registered - new bluez 5.7 method")
                agent = Agent(bus, path)
                break
            except dbus.exceptions.DBusException as e:
                es = str(e)
                if "org.bluez.Error.AlreadyExists" in es:
                    printlog(
                        "edl: [Optional] User might be on a Graphical Desktop with bluetooth-applet"
                        " to handle pairing and connection attempts by graphical diaglogs"
                        " - so our automated agent can't register in its place (and not required)"
                        " - agent registration failed with cause: "
                        + es
                        + " - so user can run 'killall bluetooth-applet' (or any other bluetooth pairing"
                        " program like 'blueman-manager' - try do a 'ps | grep blue' to check) anytime"
                        " to use our automated agent instead... waiting 15 secs to try again"
                    )
                    time.sleep(15)
                else:
                    # this is pobably an older bluez to throw to run the older compat code in outer "except:" below
                    raise e

        # Fix-up old style invocation (BlueZ 4)
        if len(args) > 0 and args[0].startswith("hci"):
            options.adapter_pattern = args[0]
            del args[:1]

        # if len(args) > 0:
        #     device = bluezutils.find_device(args[0],
        #                                     options.adapter_pattern)
        #     dev_path = device.object_path
        #     agent.set_exit_on_release(False)
        #     device.Pair(reply_handler=pair_reply, error_handler=pair_error,
        #                 timeout=60000)
        #     device_obj = device
        # else:
        #     manager.RequestDefaultAgent(path)
        manager.RequestDefaultAgent(path)
    except Exception:  # noqa    # pylint: disable=W0703
        printlog("edl: this is probably an older bluez version - trying old compat code...")
        # try older bluez 4.98 compat code
        manager = dbus.Interface(bus.get_object("org.bluez", "/"), "org.bluez.Manager")
        adapter_path = manager.DefaultAdapter()
        adapter = dbus.Interface(bus.get_object("org.bluez", adapter_path), "org.bluez.Adapter")
        capability = "DisplayYesNo"

        while 1:
            try:
                path = "/test/agent"
                adapter.RegisterAgent(path, capability)
                printlog("edl: auto-pair/accept agent registered with older bluez method")
                # older bluez uses "Agent" not "Agent1" as in 5.7
                agent = AgentOld(bus, path)  # make a new instance since we changed the AGENT_INTERFACE str above
                break
            except dbus.exceptions.DBusException as e:
                es = str(e)
                if "org.bluez.Error.AlreadyExists" in es:
                    printlog(
                        "edl: [Optional] User might be on a Graphical Desktop with bluetooth-applet to handle"
                        " pairing and connection attempts by graphical diaglogs - so our automated agent"
                        " can't register in its place (and not required) - agent registration failed with cause: "
                        + es
                        + " - so user can run 'killall bluetooth-applet' (or any other bluetooth pairing program"
                        " like 'blueman-manager' - try do a 'ps | grep blue' to check) anytime to use our automated"
                        " agent instead... waiting 15 secs to try again"
                    )
                else:
                    printlog("edl: unexpected exception in old method agent registration: " + es)
                time.sleep(15)

    mainloop.run()

    printlog("edl: agent exit!")
    # adapter.UnregisterAgent(path)
    # printlog("Agent unregistered")
