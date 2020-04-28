from netmiko import ConnectHandler
from pprint import pprint
import re
from settings import DEBUG

class Device():
    _hostname = None
    _ios = None
    _type = None
    _is_npe = None
    _cdp_enabled = None
    _net_connect = None

    _conn_cred = list()
   
    #
    # Device constructor, argument - connection info
    # 
    def __init__(self, host_info):
        if DEBUG: print("Device::__init__")
        #TODO: add connection info check
        self._conn_cred = host_info

    #
    # Connect or reconnect to device or reuse connection if it`s still alive
    #
    def _connect(self):
	#don`t reconnect if connection already active 
        if self._net_connect is not None  and  self._net_connect.is_alive():
            if DEBUG: print("Connection to host " + self._conn_cred['host'] +" is alive")
            return self._net_connect.is_alive()

        try:
            if DEBUG: print("Device::connect to host " + self._conn_cred['host'])
            self._net_connect = ConnectHandler(**self._conn_cred)
            return self._net_connect.is_alive()
        except Exception as e:
            print('Catched exception in Device::_connect:' + str(e))

    def disconnect(self):
       if DEBUG: print("Device:disconnect")
       self._net_connect.disconnect()

    #
    # Send commands to device and return response
    # 
    def _send_cmd(self, cmd):
        if DEBUG: print("Device::_send_cmd:" + cmd)
        if self._connect():
            return self._net_connect.send_command(cmd)

    #
    # get as much information as possible from show version
    #
    def _parse_show_version(self):
        out = self._send_cmd("sh version | in System image file is | Software | bytes of memory")

        #looking for information about IOS version
        m = re.search('Software .* Version (.+),.*', out, re.MULTILINE)
        if m:
             self._ios = m.group(1)
             if DEBUG: print("IOS:", self._ios)

        #looking for device type
        m = re.search('cisco (.*) .* processor .* bytes of memory', out, re.MULTILINE)
        if m:
             self._type = m.group(1)
             if DEBUG: print("Type:", self._type)

        #looking for NPE mark in IOS version
        m = re.search('image file is .*_npe', out, re.MULTILINE)
        if m:
             self._is_npe = True
        else:
             self._is_npe = False

        if DEBUG: print("Is NPE:", self._is_npe)

    def send_config(self, commands):
        if DEBUG: print("Device::send_config:", commands)
        try:
            out = self._net_connect.send_config_set(commands)
            if DEBUG: print(out)
        except Exception as e:
            print('Catched exception in send_config: ',self.get_hostname(), str(e))

    def get_config(self):
        if DEBUG: print("Deivce::get_config")
        return self._send_cmd("show running-config")

    def get_ios_version(self):
        if DEBUG: print("Deivce::get_ios_version")
        if self._ios is None:
            self._parse_show_version()
        return self._ios

    def get_type(self):
        if DEBUG: print("Deivce::get_type")
        if self._type is None:
            self._parse_show_version()
        return self._type

    #
    # check host availability from device using ping
    #
    def is_host_available(self, host):
        if DEBUG: print("Device::is_host_available for ", host)
        out = self._send_cmd("ping " + host)
        if DEBUG: print(out)
        m = re.search('Success rate is 100 percent', out, re.MULTILINE)
        if m:
            if DEBUG: print("Host is available:", host)
            return True
        else:
            if DEBUG: print("Host is unavailable:", host)
            return False

    def is_npe(self):
        if DEBUG: print("Deivce::is_npe")
        if self._is_npe is  None:
            self._parse_show_version()
        return self._is_npe

    def is_cdp_enabled(self):
        if DEBUG: print("Deivce::is_cdp_enabled")
        if self._cdp_enabled is not None:
           return self._cdp_enabled
        out = self._send_cmd("show cdp | in enabled")

        m = re.search('is.*not.* enabled', out, re.MULTILINE)
        if m:
             self._cdp_enabled = False
        else:
             self._cdp_enabled = True

        return self._cdp_enabled

    def get_cdp_peer_num(self):
        if DEBUG: print("Deivce::get_cdp_peer_num")
        if self.is_cdp_enabled() is False:
            return None
        out = self._send_cmd("show cdp neighbor detail | in Device ID").splitlines()
        if DEBUG: print("Num of CDP neighbors:", len(out))
        return len(out)       

    #
    # Check NTP status, return true if synchronized, else return false
    #
    def is_ntp_synchronized(self):
        if DEBUG: print("Deivce::is_ntp_synchronized")
        out = self._send_cmd("sh ntp status | in Clock is")

        m = re.search('Clock is synchronized', out, re.MULTILINE)
        if m:
             return True
        else:
             return False


    def get_hostname(self):
        if DEBUG: print("Device::get_hostname")
        
        if self._hostname is not None:
             return self._hostname

        out = self._send_cmd("show running-config | in ^hostname .*$")
        #strip all before hostname
        m = re.search('^hostname (.+)$', out)
        if m:
             self._hostname = m.group(1)
        return self._hostname


#
# factory function, return initialized list of Device objects
#
def device_factory(hosts, defaults):
    if DEBUG: print("In factory")
    _dev_list = list()
    if DEBUG: pprint(hosts)
 
    for host in hosts:
        try:
            if DEBUG: pprint(host)
            host_info = dict()

            #fill information about host with default settings
            host_info['host'] = next(iter(host)) 
            host_info['device_type'] = defaults["type"]
            host_info['username'] = defaults["user"]
            host_info['password'] = defaults["password"]
            host_info['port'] = defaults['port']
            host_info['secret'] = defaults['secret']
           

	    #TODO replace with personal host settings 
            #if type(host) is dict:
            #    if 'device_type' in host.keys():
            #        host_info['device_type'] = host['device_type']
            #    else:
            #        host_info['device_type'] = defaults['type']


	    #instantiate Device object and place it to list           
            _dev_list.append(Device(host_info))

        except Exception as e:
            print('Catched exception in device_factory: ' + str(e))

    return _dev_list

