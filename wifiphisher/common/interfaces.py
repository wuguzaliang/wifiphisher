"""
This module was made to handle all the interface related operations of
the program
"""

import random
import collections
import logging
import pyric
import pyric.pyw as pyw
import wifiphisher.common.constants as constants

LOGGER = logging.getLogger("wifiphisher.interfaces")


def set_interface_mac(interface_name, mac_address=None, generate_random=True):
    """
    Set the specified MAC address for the interface if generate_random is
    False otherwise set a random MAC address to the interface

    :param interface_name: Name of an interface
    :param mac_address: A MAC address
    :param generate_random: Whether a random MAC address should be
        generated or not
    :type interface_name: str
    :type mac_address: str
    :type random: bool
    :return: result(status, old_mac_address, new_mac_address)
    :rtype: namedtuple(bool, str, str)
    .. note: This method will set the interface to managed mode
    """
    result_tuple = collections.namedtuple(
        "result", "status, old_mac_address, new_mac_address")
    status = False
    old_mac_address = None
    new_mac_address = mac_address

    if generate_random:
        new_mac_address = "00:00:00:{:02x}:{:02x}:{:02x}".format(
            random.randint(0, 255), random.randint(0, 255),
            random.randint(0, 255))

    card_result = get_interface_card(interface_name)

    if new_mac_address and card_result.status and set_interface_mode(
            interface_name, "managed", card_result.card):
        try:
            old_mac_address = pyw.macget(card_result.card)
            pyw.macset(card_result.card, new_mac_address)
            status = True
        except pyric.error:
            LOGGER.exception("Failed to change MAC address!")

    return result_tuple(status, old_mac_address, new_mac_address)


def set_interface_mode(interface_name, mode, card=None):
    """
    Set the specified mode for the interface

    :param interface_name: Name of an interface
    :param mode: Mode of an interface
    :param card: The card for the interface
    :type interface_name: str
    :type mode: str
    :type card: pyric.devinfo
    :return: True if successful and False otherwise
    :rtype: bool
    .. note: Available modes are unspecified, ibss, managed, AP
        AP VLAN, wds, monitor, mesh, p2p.
    """
    interface_card = card
    succeeded = False

    if not card:
        interface_card = get_interface_card(interface_name).card

    if interface_card and pyw.validcard(interface_card) and turn_interface(
            interface_name, on=False, card=interface_card):
        try:
            pyw.modeset(interface_card, mode)
        except pyric.error:
            LOGGER.exception("Failed to set %s to %s", interface_name, mode)
        else:
            succeeded = turn_interface(
                interface_name, on=True, card=interface_card)

    return succeeded


def turn_interface(interface_name, on=True, card=None):
    """
    Turn the interface up or down based on the on parameter

    :param interface_name: Name of an interface
    :param on: Turn on or off
    :param card: The card for the interface
    :type interface_name: str
    :type on: bool
    :type card: pyric.devinfo
    :return: True if operation was successful and False otherwise
    :rtype: bool
    """
    interface_card = card
    succeeded = False

    if not card:
        interface_card = get_interface_card(interface_name).card

    if interface_card and pyw.validcard(interface_card):
        try:
            if on:
                pyw.up(interface_card)
            else:
                pyw.down(interface_card)
        except pyric.error:
            state = "ON" if on else "OFF"
            LOGGER.exception("Failed to turn %s %s!", interface_name, state)
        else:
            succeeded = True

    return succeeded


def set_interface_channel(interface_name, channel, card=None):
    """
    Set the channel for the interface

    :param interface_name: Name of an interface
    :param channel: A channel number
    :param card: The card for the interface
    :type interface_name: str
    :type channel: int
    :type card: pyric.devinfo
    :return: True if operation was successful and False otherwise
    :rtype: bool
    """

    interface_card = card
    succeeded = False

    if not card:
        interface_card = get_interface_card(interface_name).card

    if interface_card and pyw.validcard(interface_card):
        try:
            pyw.chset(interface_card, channel)
        except pyric.error:
            LOGGER.exception("Failed to set %s to channel %s", interface_name,
                             channel)
        else:
            succeeded = True

    return succeeded


def find_interface(mode, exclude=[]):
    """
    Return an interface with the given mode. The function prioritizes
    physical interfaces over virtual ones.

    :param mode: An operation mode
    :param exclude: An interface to exclude
    :type mode: str
    :type exclude: [str,]
    :return: result(status, interface_name, is_virtual)
    :rtype: namedtuple(bool, str, bool)
    .. note: exclude does not exclude the interface from search. It
        only gives priority to other physical interfaces
    :Example:

        # assuming 2 interface
        # name      modes
        # wlan1 - AP, monitor
        # wlan2 - monitor
        >>> result = find_interface("monitor", exclude=["wlan1"])
        >>> result.status
        True
        >>> result.interface_name
        'wlan2'
        >>> result.is_virtual
        False
    """
    interface = None
    alternative_interface = None
    result_tuple = collections.namedtuple("result",
                                          "status, interface_name, is_virtual")

    for wireless_interface in pyw.winterfaces():
        if has_mode(wireless_interface, mode):
            if wireless_interface not in exclude:
                interface = wireless_interface
                break
            elif not alternative_interface:
                alternative_interface = wireless_interface

    if interface:
        result = result_tuple(True, interface, False)
    elif alternative_interface:
        result = result_tuple(True, alternative_interface, True)
    else:
        result = result_tuple(False, None, False)

    return result


def setup_interfaces(monitor_interface=None,
                     ap_interface=None,
                     internet_interface=None):
    """
    """
    result_tuple = collections.namedtuple("result", [
        "status", "monitor_interface", "monitor_virtual", "ap_interface",
        "ap_virtual", "internet_interface", "error_message"
    ])
    result = result_tuple(True, None, False, None, False, None, None)

    if monitor_interface and ap_interface:
        if monitor_interface == ap_interface:
            result.status = False
            result.error_message = "Monitor interface and AP interface can not be the same"
        elif not has_mode(monitor_interface, "monitor"):
            result.status = False
            result.error_message = "Monitor interface {} is invalid".format(
                monitor_interface)
        elif not has_mode(ap_interface, "AP"):
            result.status = False
            result.error_message = "AP interface {} is invalid".format(
                ap_interface)
        else:
            result.monitor_interface = monitor_interface
            result.ap_interface = ap_interface
    elif monitor_interface:
        if has_mode(monitor_interface, "monitor"):
            find_result = find_interface("AP", exclude=[monitor_interface])

            if find_result.status:
                result.status = True
                result.monitor_interface = monitor_interface
                result.ap_interface = find_result.interface_name
                result.ap_virtual = find_result.is_virtual
            else:
                result.status = False
                result.error_message = "Failed to find an interface with AP mode"
        else:
            result.status = False
            result.error_message = "Monitor interface {} is invalid".format(
                monitor_interface)
    elif ap_interface:
        if has_mode(ap_interface, "AP"):
            find_result = find_interface("monitor", exclude=[ap_interface])

            if find_result.status:
                result.status = True
                result.ap_interface = ap_interface
                result.monitor_interface = find_result.interface_name
                result.monitor_virtual = find_result.is_virtual
            else:
                result.status = False
                result.error_message = "Failed to find an interface with monitor mode"
        else:
            result.status = False
            result.error_message = "AP interface {} is invalid".format(
                monitor_interface)
    else:
        find_mon_result = find_interface("monitor")
        find_ap_result = find_interface(
            "AP",
            exclude=[find_mon_result.interface_name]
            if find_mon_result.status else [])
        if not find_mon_result.status:
            result.status = False
            result.error_message = "Failed to find an interface with monitor mode"
        elif not find_ap_result.status:
            result.status = False
            result.error_message = "Failed to find an interface with AP mode"
        else:
            result.monitor_interface = find_mon_result.interface_name
            result.monitor_virtual = find_mon_result.is_virtual
            result.ap_interface = find_ap_result.interface_name
            result.ap_virtual = find_ap_result.is_virtual

    if internet_interface and result.status and not pyw.isinterface(
            internet_interface):
        result.status = False
        result.error_message = "Internet interface {} is invalid".format(
            internet_interface)

    return result


def has_mode(interface_name, mode):
    """
    Return whether the provided interface has the provided mode

    :param interface_name: Name of the interface
    :param mode: Mode of operation
    :type interface_name: str
    :type mode: list
    :return: True if interface has the mode and False otherwise
    :rtype: bool
    :Example:

        >>> has_mode("DoesNotExist", "AP")
        False

        >>> has_mode("HasAP", "AP")
        True

        >>> has_mode("NoMonitor", "monitor")
        False
    """
    modes = []

    card_result = get_interface_card(interface_name)

    if card_result.status:
        try:
            modes = pyw.devmodes(card_result.card)
        except pyric.error:
            LOGGER.exception("Failed to check if %s has %s mode",
                             interface_name, mode)

    return mode in modes


def get_interface_card(interface_name):
    """
    return the card object for the given interface

    :param interface_name: Name of an interface
    :type interface_name: str
    :return: result(status, card)
    :rtype: namedtuple(bool, pyric.pyw.Card)
    :Example:

        >>> result = get_interface_card("valid_card")
        >>> result.status
        True
        >>> result.card
        Card(phy=0,dev=valid_card, ifindex=3)

        >>> result = get_interface_card("bad_card")
        >>> result.status
        False
    """
    result_tuple = collections.namedtuple("result", "status, card")
    status = False
    card = None

    try:
        card = pyw.getcard(interface_name)
    except pyric.error:
        LOGGER.exception("Failed to get the card object for %s",
                         interface_name)
    else:
        status = True

    return result_tuple(status, card)
