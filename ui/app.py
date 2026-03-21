import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from utils.validators import validate_inputs,validate_connection_inputs
from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException
from services.switch_service import fetch_switch_state

class AutomationApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Switch Automation Tool")
        self.root.geometry("700x600")

        self.build_ui()
        self.current_hostname = None
        self.current_vlans = {}

    def build_ui(self):
        # Device Connection Frame
        device_frame = ttk.LabelFrame(self.root, text="Device Connection")
        device_frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(device_frame, text="Switch IP:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.ip_entry = ttk.Entry(device_frame, width=30)
        self.ip_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(device_frame, text="Username:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.username_entry = ttk.Entry(device_frame, width=30)
        self.username_entry.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(device_frame, text="Password:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.password_entry = ttk.Entry(device_frame, width=30, show="*")
        self.password_entry.grid(row=2, column=1, padx=5, pady=5)

        # Desired Configuration Frame
        config_frame = ttk.LabelFrame(self.root, text="Desired Configuration")
        config_frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(config_frame, text="Hostname:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.hostname_entry = ttk.Entry(config_frame, width=30)
        self.hostname_entry.grid(row=0, column=1, padx=5, pady=5)

        # VLAN Frame
        vlan_frame = ttk.LabelFrame(self.root, text="VLANs")
        vlan_frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(vlan_frame, text="VLAN ID").grid(row=0, column=0, padx=5, pady=5)
        ttk.Label(vlan_frame, text="VLAN Name").grid(row=0, column=1, padx=5, pady=5)

        self.vlan_entries = []

        for i in range(3):
            vlan_id_entry = ttk.Entry(vlan_frame, width=10)
            vlan_id_entry.grid(row=i + 1, column=0, padx=5, pady=5)

            vlan_name_entry = ttk.Entry(vlan_frame, width=30)
            vlan_name_entry.grid(row=i + 1, column=1, padx=5, pady=5)

            self.vlan_entries.append((vlan_id_entry, vlan_name_entry))

        # Button Frame
        button_frame = ttk.Frame(self.root)
        button_frame.pack(fill="x", padx=10, pady=10)

        ttk.Button(button_frame, text="Preview", command=self.preview_config).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Apply", command=self.apply_config).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Clear", command=self.clear_fields).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Read Config", command=self.read_switch_state).pack(side="left", padx=5)

        # Output Frame
        output_frame = ttk.LabelFrame(self.root, text="Output")
        output_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.output_text = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD, height=15)
        self.output_text.pack(fill="both", expand=True, padx=5, pady=5)
    
    def apply_config(self):
        self.output_text.delete("1.0", tk.END)

        ip = self.ip_entry.get()
        username = self.username_entry.get()
        password = self.password_entry.get()
        hostname = self.hostname_entry.get()

        vlan_entries_data = []
        for vlan_id_entry, vlan_name_entry in self.vlan_entries:
                vlan_entries_data.append(
                    (vlan_id_entry.get(), vlan_name_entry.get())
                )

        valid, result = validate_inputs(
                                        ip,
                                        username,
                                        password,
                                        hostname,
                                        vlan_entries_data
                                    )

        if not valid:
            self.output_text.insert(tk.END, f"Error: {result}")
            return

        desired_hostname = self.hostname_entry.get().strip()
        desired_vlans = self.get_desired_vlans()
        force_conflicts = False

        try:
            self.output_text.insert(tk.END, "Connecting to switch...\n")
            self.root.update()

            connection = self.connect_to_switch()

            # Pre-change read
            self.output_text.insert(tk.END, "\nReading current config...\n")
            self.root.update()

            hostname_output = connection.send_command("show running-config | include ^hostname")
            vlan_output = connection.send_command("show vlan brief")
            running_config_output = connection.send_command("show running-config")

            self.current_hostname = self.parse_hostname(hostname_output)
            self.current_vlans = self.parse_vlan_brief(vlan_output)
            conflicts = self.get_vlan_conflicts(desired_vlans)

            if conflicts:
                conflict_message = "The following VLAN conflicts were detected:\n\n"
                conflict_message += "\n".join(conflicts)
                conflict_message += "\n\nDo you want to continue and apply these conflicting VLAN renames?"

                continue_apply = messagebox.askyesno("VLAN Conflicts Detected", conflict_message)

                if not continue_apply:
                    self.output_text.insert(tk.END, "\nApply operation cancelled by user due to VLAN conflicts.\n")
                    connection.disconnect()
                    return

                force_conflicts = True
            # Save pre-change backup
            pre_hostname_label = self.current_hostname if self.current_hostname else "unknown_switch"
            pre_run_file = self.save_backup("backups/prechange", pre_hostname_label, "running-config", running_config_output)
            pre_vlan_file = self.save_backup("backups/prechange", pre_hostname_label, "show-vlan", vlan_output)

            #self.output_text.insert(tk.END, f"Pre-change backup saved:\n- {pre_run_file}\n- {pre_vlan_file}\n")
            self.output_text.insert(tk.END, f"\nPre-change backup completed.\n")
            self.root.update()

            # Build commands
            commands, detected_conflicts = self.build_config_commands(
                                                                    desired_hostname,
                                                                    desired_vlans,
                                                                    force_conflicts=force_conflicts
                                                                )

            if not commands:
                    self.output_text.insert(tk.END, "\nNo configuration changes required.\n")

                    if detected_conflicts:
                        self.output_text.insert(tk.END, "\nConflicts detected:\n")
                        for item in detected_conflicts:
                            self.output_text.insert(tk.END, f"- {item}\n")

                    connection.disconnect()
                    return

            
            self.output_text.insert(tk.END, "\nPlanned configuration:\n\n")
            for cmd in commands:
                self.output_text.insert(tk.END, f"  {cmd}\n")
            self.root.update()
            self.output_text.insert(tk.END, "\nApplying configuration...\n")

            config_result = connection.send_config_set(commands)
            connection.set_base_prompt()
            #self.output_text.insert(tk.END, "\n=== Device response ===\n\n")
            #self.output_text.insert(tk.END, f"{config_result}\n")
            self.root.update()

            # Save config
            self.output_text.insert(tk.END, "\nSaving configuration...\n")
            self.root.update()
            save_result = connection.save_config()

            #self.output_text.insert(tk.END, f"{save_result}\n")
            self.root.update()

            # Post-change read
            self.output_text.insert(tk.END, "\nReading post-change config...\n\n")
            self.root.update()

            post_hostname_output = connection.send_command("show running-config | include ^hostname")
            post_vlan_output = connection.send_command("show vlan brief")
            post_running_config_output = connection.send_command("show running-config")

            connection.disconnect()

            self.current_hostname = self.parse_hostname(post_hostname_output)
            self.current_vlans = self.parse_vlan_brief(post_vlan_output)

            # Save post-change backup
            post_hostname_label = self.current_hostname if self.current_hostname else desired_hostname
            post_run_file = self.save_backup("backups/postchange", post_hostname_label, "running-config", post_running_config_output)
            post_vlan_file = self.save_backup("backups/postchange", post_hostname_label, "show-vlan", post_vlan_output)
            self.output_text.insert(tk.END, "Post-change backup completed.\n\n")
            self.output_text.insert(tk.END, "Execution completed.\n\n")
            ## diff
            running_diff = self.generate_diff(
                running_config_output,
                post_running_config_output,
                from_name="running-config-pre",
                to_name="running-config-post"
            )

            vlan_diff = self.generate_diff(
                vlan_output,
                post_vlan_output,
                from_name="show-vlan-pre",
                to_name="show-vlan-post"
            )
            
            

            relevant_changes = self.extract_relevant_changes(running_diff)
            diff_run_file = self.save_text_file(
                "backups/diff",
                post_hostname_label,
                "running-config-diff",
                running_diff if running_diff else "No differences found.",
                extension="diff"
            )

            diff_vlan_file = self.save_text_file(
                "backups/diff",
                post_hostname_label,
                "show-vlan-diff",
                vlan_diff if vlan_diff else "No differences found.",
                extension="diff"
            )

            # Validation
            validation_results = self.validate_post_change(desired_hostname, desired_vlans)
            summary_lines = []
            summary_lines.append("\n=== Execution Summary ===\n")

            if desired_hostname:
                summary_lines.append(f"- Requested hostname: {desired_hostname}")
            else:
                summary_lines.append("- Requested hostname: none")

            if desired_vlans:
                summary_lines.append("- Requested VLANs:")
                for vlan_id, vlan_name in desired_vlans:
                    summary_lines.append(f"  - VLAN {vlan_id}: {vlan_name}")
            else:
                summary_lines.append("- Requested VLANs: none")

            if commands:
                summary_lines.append("\nApplied commands:\n")
                for cmd in commands:
                    summary_lines.append(f"  {cmd}")
            else:
                summary_lines.append("\nApplied commands: none")

            if detected_conflicts:
                if force_conflicts:
                    summary_lines.append("\nConflicts:\n VLAN 30 renamed from '30' to 'treinta' (user approved")
                else:
                    summary_lines.append("\nConflicts detected:")
                for item in detected_conflicts:
                    summary_lines.append(f"  - {item}")
            else:
                summary_lines.append("\nConflicts detected: none")

            summary_lines.append("\n=== Validation Results ===\n")
            for item in validation_results:
                summary_lines.append(f"  {item}")

            #self.output_text.insert(tk.END, "\n=== Relevant Changes (Hostname & VLANs) ===\n")

            summary_lines.append("\n=== Relevant Changes (Hostname & VLANs) ===\n")

            if relevant_changes:
                for line in relevant_changes:
                    summary_lines.append(f"  {line}")
            else:
                summary_lines.append("  No relevant changes detected.")

            summary_lines.append("\n=== Generated files ===")
            summary_lines.append("\nBackups:\n")
            summary_lines.append(f"  - Pre running-config: {pre_run_file}")
            summary_lines.append(f"  - Pre VLAN output: {pre_vlan_file}")
            summary_lines.append(f"  - Post running-config: {post_run_file}")
            summary_lines.append(f"  - Post VLAN output: {post_vlan_file}")
            summary_lines.append("\nDiffs:\n")
            summary_lines.append(f"  - Running-config diff: {diff_run_file}")
            summary_lines.append(f"  - VLAN diff: {diff_vlan_file}")


            #self.output_text.insert(tk.END, "\nPost-change backup saved:\n")
            #self.output_text.insert(tk.END, f"- {post_run_file}\n- {post_vlan_file}\n")
            self.output_text.insert(tk.END, "\n".join(summary_lines))

        except NetmikoAuthenticationException:
            self.output_text.delete("1.0", tk.END)
            self.output_text.insert(tk.END, "Authentication failed. Please verify username/password.")
        except NetmikoTimeoutException:
            self.output_text.delete("1.0", tk.END)
            self.output_text.insert(tk.END, "Connection timed out. Device unreachable or SSH not available.")
        except Exception as e:
            self.output_text.delete("1.0", tk.END)
            self.output_text.insert(tk.END, f"Unexpected error: {str(e)}")
    def preview_config(self):
        self.output_text.delete("1.0", tk.END)

        ip = self.ip_entry.get()
        username = self.username_entry.get()
        password = self.password_entry.get()
        hostname = self.hostname_entry.get()

        vlan_entries_data = []
        for vlan_id_entry, vlan_name_entry in self.vlan_entries:
            vlan_entries_data.append(
                (vlan_id_entry.get(), vlan_name_entry.get())
            )

        valid, result = validate_inputs(
                                            ip,
                                            username,
                                            password,
                                            hostname,
                                            vlan_entries_data
                                        )

        if not valid:
            self.output_text.insert(tk.END, f"Error: {result}")
            return

        desired_hostname = result["hostname"]
        desired_vlans = result["vlans"]

        # Si todavía no se leyó el switch, hacerlo automáticamente
        if self.current_hostname is None and not self.current_vlans:
            self.output_text.insert(tk.END, "Reading current config...\n\n")
            self.root.update()

            try:
                hostname_output, vlan_output = fetch_switch_state(ip, username, password)

                self.current_hostname = self.parse_hostname(hostname_output)
                self.current_vlans = self.parse_vlan_brief(vlan_output)

                self.output_text.insert(tk.END, "Switch config loaded.\n\n")
                self.root.update()
            except NetmikoAuthenticationException:
                self.output_text.insert(tk.END, "Authentication failed.\n")
                return
            except NetmikoTimeoutException:
                self.output_text.insert(tk.END, "Connection timeout.\n")
                return
            except Exception as e:
                self.output_text.insert(tk.END, f"Error: {str(e)}\n")
                return

        force_conflicts = False
        conflicts = self.get_vlan_conflicts(desired_vlans)

        if conflicts:
            conflict_message = "The following VLAN conflicts were detected:\n\n"
            conflict_message += "\n".join(conflicts)
            conflict_message += "\n\nDo you want to continue and include these conflicting VLAN renames in the preview?"

            continue_preview = messagebox.askyesno("VLAN Conflicts Detected", conflict_message)

            if not continue_preview:
                self.output_text.insert(tk.END, "Preview cancelled by user due to VLAN conflicts.")
                return

            force_conflicts = True

        commands, detected_conflicts = self.build_config_commands(
            desired_hostname,
            desired_vlans,
            force_conflicts=force_conflicts
        )

        preview_lines = [
            "=== Configuration Preview ===",
            ""
        ]

        if desired_hostname:
            preview_lines.append(f"Current hostname: {self.current_hostname}")
            preview_lines.append(f"Desired hostname: {desired_hostname}")

            if self.current_hostname == desired_hostname:
                preview_lines.append("Hostname result: already compliant")
            else:
                preview_lines.append("Hostname result: will be updated")

            preview_lines.append("")

        if desired_vlans:
            preview_lines.append("VLAN analysis:")

            for vlan_id, desired_name in desired_vlans:
                if vlan_id not in self.current_vlans:
                    preview_lines.append(
                        f"- VLAN {vlan_id}: will be created with name '{desired_name}'"
                    )
                else:
                    current_name = self.current_vlans[vlan_id]
                    if current_name == desired_name:
                        preview_lines.append(
                            f"- VLAN {vlan_id}: already exists with matching name '{desired_name}'"
                        )
                    else:
                        if force_conflicts:
                            preview_lines.append(
                                f"- VLAN {vlan_id}: conflict detected, rename will be included ('{current_name}' -> '{desired_name}')"
                            )
                        else:
                            preview_lines.append(
                                f"- VLAN {vlan_id}: CONFLICT - exists as '{current_name}', desired '{desired_name}'"
                            )

            preview_lines.append("")

        preview_lines.append("Planned configuration:\n")

        if commands:
            for cmd in commands:
                preview_lines.append(cmd)
            preview_lines.append("end")
            preview_lines.append("write memory")
        else:
            preview_lines.append("No configuration changes required")

        self.output_text.insert(tk.END, "\n".join(preview_lines))
    def read_switch_state(self):
            self.output_text.delete("1.0", tk.END)
            ip = self.ip_entry.get()
            username = self.username_entry.get()
            password = self.password_entry.get()
            valid, result = validate_connection_inputs(ip, username, password)
            if not valid:
                self.output_text.insert(tk.END, f"Error: {result}")
                return

            try:
                self.output_text.insert(tk.END, "Connecting to switch...\n")
                self.root.update()
                
                hostname_output, vlan_output = fetch_switch_state(ip, username, password)

                self.output_text.insert(tk.END, "Connection successful.\n")
                self.root.update()

                self.current_hostname = self.parse_hostname(hostname_output)
                self.current_vlans = self.parse_vlan_brief(vlan_output)

                lines = [
                    "=== Switch Current Config ===",
                    "",
                    f"[Hostname] {self.current_hostname if self.current_hostname else 'Not found'}",
                    "",
                    "[VLANs]"
                ]

                if self.current_vlans:
                    for vlan_id, vlan_name in sorted(self.current_vlans.items()):
                        lines.append(f"- VLAN {vlan_id}: {vlan_name}")
                else:
                    lines.append("No VLANs parsed")

                self.output_text.delete("1.0", tk.END)
                self.output_text.insert(tk.END, "\n".join(lines))

            except NetmikoAuthenticationException:
                self.output_text.delete("1.0", tk.END)
                self.output_text.insert(tk.END, "Authentication failed. Please verify username/password.")
            except NetmikoTimeoutException:
                self.output_text.delete("1.0", tk.END)
                self.output_text.insert(tk.END, "Connection timed out. Device unreachable or SSH not available.")
            except Exception as e:
                self.output_text.delete("1.0", tk.END)
                self.output_text.insert(tk.END, f"Unexpected error: {str(e)}")
    def clear_fields(self):
        self.ip_entry.delete(0, tk.END)
        self.username_entry.delete(0, tk.END)
        self.password_entry.delete(0, tk.END)
        self.hostname_entry.delete(0, tk.END)

        for vlan_id_entry, vlan_name_entry in self.vlan_entries:
            vlan_id_entry.delete(0, tk.END)
            vlan_name_entry.delete(0, tk.END)

        self.output_text.delete("1.0", tk.END)
    def parse_hostname(self, hostname_output):
        for line in hostname_output.splitlines():
            line = line.strip()
            if line.startswith("hostname "):
                return line.split("hostname ", 1)[1].strip()
        return None
    def parse_vlan_brief(self, vlan_output):
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
    def get_desired_vlans(self):
        vlan_list = []

        for vlan_id_entry, vlan_name_entry in self.vlan_entries:
            vlan_id = vlan_id_entry.get().strip()
            vlan_name = vlan_name_entry.get().strip()

            if vlan_id and vlan_name:
                vlan_list.append((int(vlan_id), vlan_name))

        return vlan_list
    def get_vlan_conflicts(self, desired_vlans):
        conflicts = []

        for vlan_id, desired_name in desired_vlans:
            if vlan_id in self.current_vlans:
                current_name = self.current_vlans[vlan_id]
                if current_name != desired_name:
                    conflicts.append(
                        f"VLAN {vlan_id}: current='{current_name}', desired='{desired_name}'"
                    )

        return conflicts
    def build_config_commands(self, desired_hostname, desired_vlans, force_conflicts=False):
        commands = []
        detected_conflicts = []

        if desired_hostname and self.current_hostname != desired_hostname:
            commands.append(f"hostname {desired_hostname}")

        for vlan_id, desired_name in desired_vlans:
            if vlan_id not in self.current_vlans:
                commands.append(f"vlan {vlan_id}")
                commands.append(f" name {desired_name}")
            else:
                current_name = self.current_vlans[vlan_id]

                if current_name == desired_name:
                    continue

                detected_conflicts.append(
                    f"VLAN {vlan_id} exists as '{current_name}', desired '{desired_name}'"
                )

                if force_conflicts:
                    commands.append(f"vlan {vlan_id}")
                    commands.append(f" name {desired_name}")

        return commands, detected_conflicts
    def run(self):
        self.root.mainloop()