from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException

def connect_to_switch(ip, username, password):
    device = {
        "device_type": "cisco_ios",
        "host": ip,
        "username": username,
        "password": password,
        "fast_cli": False,
    }

    connection = ConnectHandler(**device)
    return connection

def fetch_switch_state(ip, username, password):
    connection = connect_to_switch(ip, username, password)

    hostname_output = connection.send_command("show running-config | include ^hostname")
    vlan_output = connection.send_command("show vlan brief")

    connection.disconnect()
    return hostname_output, vlan_output

