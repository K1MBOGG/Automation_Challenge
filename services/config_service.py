def get_vlan_conflicts(current_vlans, desired_vlans):
        conflicts = []

        for vlan_id, desired_name in desired_vlans:
            if vlan_id in current_vlans:
                current_name = current_vlans[vlan_id]
                if current_name != desired_name:
                    conflicts.append(
                        f"VLAN {vlan_id}: current='{current_name}', desired='{desired_name}'"
                    )

        return conflicts

def build_config_commands(current_hostname,current_vlans, desired_hostname, desired_vlans, force_conflicts=False):
        commands = []
        detected_conflicts = []

        if desired_hostname and current_hostname != desired_hostname:
            commands.append(f"hostname {desired_hostname}")

        for vlan_id, desired_name in desired_vlans:
            if vlan_id not in current_vlans:
                commands.append(f"vlan {vlan_id}")
                commands.append(f" name {desired_name}")
            else:
                current_name = current_vlans[vlan_id]

                if current_name == desired_name:
                    continue

                detected_conflicts.append(
                    f"VLAN {vlan_id} exists as '{current_name}', desired '{desired_name}'"
                )

                if force_conflicts:
                    commands.append(f"vlan {vlan_id}")
                    commands.append(f" name {desired_name}")

        return commands, detected_conflicts

def validate_post_change(current_hostname, current_vlans, desired_hostname, desired_vlans):
        results = []
        has_error = False
        has_warning = False

        #results.append("=== Validation Results ===\n")

        # -------- Hostname --------
        if desired_hostname:
            results.append("Hostname:")

            if current_hostname == desired_hostname:
                results.append(f"✔ OK - {desired_hostname}")
            else:
                results.append(
                    f"✖ ERROR - Hostname mismatch (current: '{current_hostname}', expected: '{desired_hostname}')"
                )
                has_error = True

            results.append("")

        # -------- VLANs --------
        if desired_vlans:
            results.append("VLANs:")

            for vlan_id, desired_name in desired_vlans:
                if vlan_id not in current_vlans:
                    results.append(f"✖ ERROR - VLAN {vlan_id} missing")
                    has_error = True
                else:
                    current_name = current_vlans[vlan_id]

                    if current_name == desired_name:
                        results.append(f"✔ OK - VLAN {vlan_id} ({desired_name})")
                    else:
                        results.append(
                            f"⚠ WARNING - VLAN {vlan_id} name mismatch (current: '{current_name}', expected: '{desired_name}')"
                        )
                        has_warning = True

            results.append("")

        # -------- Global Status --------
        if has_error:
            results.append("✖ Configuration validation FAILED. Device is NOT compliant.")
        elif has_warning:
            results.append("⚠ Configuration validation completed with warnings.")
        else:
            results.append("✔ Configuration successfully validated. Device is compliant.")

        return results

def extract_relevant_changes(diff_text):
    relevant_lines = []

    for line in diff_text.splitlines():
        #print("LINE RAW:", repr(line))   # 👈 clave

        stripped = line.lstrip()
        #print("LINE STRIPPED:", repr(stripped))

        if not (line.startswith("+") or line.startswith("-")):
            continue

        content = stripped[1:].strip()
        #print("CONTENT:", content)

        if (
            content.startswith("hostname")
            or content.startswith("vlan")
            or content.startswith("name")
        ):
            #print("MATCH FOUND:", stripped)
            relevant_lines.append(stripped)

    #print("FINAL RELEVANT:", relevant_lines)

    return relevant_lines

def parse_hostname(hostname_output):
        for line in hostname_output.splitlines():
            line = line.strip()
            if line.startswith("hostname "):
                return line.split("hostname ", 1)[1].strip()
        return None

def parse_vlan_brief(vlan_output):
    vlans = {}

    for line in vlan_output.splitlines():
        line = line.strip()

        if not line:
            continue

        # Saltar cabeceras
        if line.startswith("VLAN Name") or line.startswith("----"):
            continue

        parts = line.split()

        # Esperamos al menos:
        # VLAN_ID  VLAN_NAME  STATUS ...
        if len(parts) < 3:
            continue

        vlan_id = parts[0]

        if not vlan_id.isdigit():
            continue

        vlan_name = parts[1]
        vlans[int(vlan_id)] = vlan_name

    return vlans