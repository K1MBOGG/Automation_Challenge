import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

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

        #ttk.Button(button_frame, text="Preview", command=self.preview_config).pack(side="left", padx=5)
        #ttk.Button(button_frame, text="Apply", command=self.apply_config).pack(side="left", padx=5)
        #ttk.Button(button_frame, text="Clear", command=self.clear_fields).pack(side="left", padx=5)
        #tk.Button(button_frame, text="Read Config", command=self.read_switch_state).pack(side="left", padx=5)

        # Output Frame
        output_frame = ttk.LabelFrame(self.root, text="Output")
        output_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.output_text = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD, height=15)
        self.output_text.pack(fill="both", expand=True, padx=5, pady=5)
    def run(self):
        self.root.mainloop()