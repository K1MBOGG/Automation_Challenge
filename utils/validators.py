import re
def validate_inputs(ip, username, password, hostname, vlan_entries_data):
        ip = ip.strip()
        username = username.strip()
        password = password.strip()
        hostname = hostname.strip()

        if not ip:
            return False, "Switch IP is required"
        if not username:
            return False, "Username is required"
        if not password:
            return False, "Password is required"

        vlan_list = []
        vlan_pattern = re.compile(r"^[A-Za-z0-9_-]+$")

        for i, (vlan_id, vlan_name) in enumerate(vlan_entries_data, start=1):
            vlan_id = vlan_id.strip()
            vlan_name = vlan_name.strip()

            # fila vacía: ignorar
            if not vlan_id and not vlan_name:
                continue

            # fila incompleta: error
            if not vlan_id or not vlan_name:
                return False, f"Row {i}: VLAN ID and Name must both be filled"

            if not vlan_id.isdigit():
                return False, f"Row {i}: VLAN ID must be a number"

            vlan_id_int = int(vlan_id)
            if vlan_id_int < 1 or vlan_id_int > 4094:
                return False, f"Row {i}: VLAN ID must be between 1 and 4094"

            if not vlan_pattern.match(vlan_name):
                return False, f"Row {i}: VLAN Name has invalid characters"

            vlan_list.append((vlan_id_int, vlan_name))

        # hostname opcional, pero si viene, validarlo
        if hostname:
            hostname_pattern = re.compile(r"^[A-Za-z0-9_-]+$")
            if not hostname_pattern.match(hostname):
                return False, "Hostname has invalid characters"

        # al menos un cambio debe existir
        if not hostname and not vlan_list:
            return False, "Provide at least a hostname or one VLAN"

        return True, {   "hostname": hostname,
            "vlans": vlan_list
        }