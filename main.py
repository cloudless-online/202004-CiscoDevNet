#!/usr/bin/python3

from Device import device as dev
from hosts import hosts, host_defaults
from pprint import pprint
from settings import DEBUG, DELIMITER, BACKUP_DIR, MAX_THREADS
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed
import datetime

change_list = {
	'if':{'is_host_available':'172.x.x.x'},
        'then':[
            'clock timezone GMT 0',
            'ntp server 172.x.x.x'
        ]
}


def save_config(hostname, config):
    if DEBUG: print("main::save_config for:", hostname)
    prefix = datetime.datetime.today().strftime('%Y-%m-%d-')
    try:
        with open(BACKUP_DIR + prefix + hostname,'w') as backup_file:
            backup_file.write(config)
    except Exception as e:
        print('Catched exception in save_config: ' + str(e))

def prepare_summary(device):
    response  = device.get_hostname() + DELIMITER
    response += device.get_type() + DELIMITER
    response += device.get_ios_version() + DELIMITER
    response += 'NPE' if device.is_npe() else 'PE'
    response += DELIMITER
    response += "CDP is ON, " + str(device.get_cdp_peer_num()) + " peers" if device.is_cdp_enabled() else "CDP is OFF"
    response += DELIMITER
    response += "Clock in Sync" if device.is_ntp_synchronized() else "Clock not sync"

    return response

def apply_changes(device):
    if DEBUG: print("Main::apply_changes")

    if_key = change_list['if']
    if DEBUG: pprint(if_key) 

    #looking for corresponding device method
    if_method_name = next(iter(if_key))
    if_method_args = if_key[if_method_name]

    then_cmds = change_list['then']
    if DEBUG: pprint(then_cmds)

    #looking for Device method to execute
    method = getattr(device, if_method_name)
    if method(if_method_args):
        if DEBUG: print("Proceed changes")
        device.send_config(then_cmds)
    else:
        print("Warning, can`t apply changes, If method return False.")
        pprint(change_list)

def device_proceed(device):
    device.get_ios_version()
    device.get_hostname()

    config = device.get_config()
    if config:
        save_config(device.get_hostname(), config)

    device.get_ios_version()

    #check if payload encryption enabled
    device.is_npe()

    #check if CDP enabled
    cdp_enabled = device.is_cdp_enabled()

    #get number of CDP peers
    if cdp_enabled:
         num_of_cdp_peers = device.get_cdp_peer_num()

    #apply configuration changes from change_list
    apply_changes(device)

    #check if NTP servers in sync status
    ntp_synchronized = device.is_ntp_synchronized()
    if DEBUG: print("NTP synchronized:", ntp_synchronized)

    summary = prepare_summary(device)
    device.disconnect()
    return summary    

def main():
    if DEBUG: print("main")

    #create list with initialized Device objects 
    device_list = dev.device_factory(hosts, host_defaults)
 
    if not device_list:
        print("Warning, no devices found")
        return 

    with ThreadPoolExecutor(max_workers = MAX_THREADS) as executor:
        future_to_res = {executor.submit(device_proceed,device): device for device in device_list}
        for future in as_completed(future_to_res):
            try:
                data = future.result()
            except Exception as exc:
                print('%r generated an exception: %s' % (exc))
            else:
                print(data)


   # for device in device_list:
   #     device_proceed(device)

if __name__ == '__main__':
  try:
    main()
  except Exception as e:
    print('Catched exception: ' + str(e))

