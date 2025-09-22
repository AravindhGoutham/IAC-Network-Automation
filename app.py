#!/usr/bin/env python3

from flask import Flask, render_template, send_from_directory, redirect, url_for, flash, request
from netmiko import ConnectHandler, NetMikoTimeoutException, NetMikoAuthenticationException
from datetime import datetime
from pathlib import Path
import yaml

app = Flask(__name__)
app.secret_key = "aravindh"

CONFIG_DIR = Path("/home/student/Golden-Config")
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

YAML_DIR = Path("/home/student/iac-netman")
YAML_DIR.mkdir(parents=True, exist_ok=True)

DEVICES = {
    "S1": "10.0.0.2",
    "S2": "10.0.0.3",
    "R1": "10.0.0.4",
    "R2": "10.0.0.5",
    "S3": "10.0.0.6",
    "S4": "10.0.0.7",
    "R3": "10.0.0.8",
    "R4": "10.0.0.9",
}

USERNAME = "admin"
PASSWORD = "admin"

def fetch_running_config(hostname: str, ip: str) -> Path:
    device = {
        "device_type": "arista_eos",
        "host": ip,
        "username": USERNAME,
        "password": PASSWORD,
        "timeout": 20,
        "fast_cli": False,
    }

    conn = None
    try:
        conn = ConnectHandler(**device)
        conn.enable()
        output = conn.send_command("show running-config")
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{hostname}_{ts}.cfg"
        file_path = CONFIG_DIR / filename
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(output)
        return file_path
    finally:
        if conn:
            conn.disconnect()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/grafana")
def grafana():
    grafana_url = "http://localhost:3000/d/0ae05200-3ebe-4eeb-bdfc-af533f5e783d/interface-status?orgId=1&from=2025-09-15T02:12:54.877Z&to=2025-09-15T07:32:54.877Z&timezone=browser&var-instance=10.0.0.2&refresh=auto"
    return render_template("grafana.html", grafana_url=grafana_url)

@app.route("/add_device", methods=["GET", "POST"])
def add_device():
    if request.method == "POST":
        data = request.form.to_dict(flat=False)

        device = {
            "hostname": data.get("hostname", [""])[0],
            "device_type": data.get("device_type", [""])[0],
        }

        # VLAN CE
        vlans = []
        vlan_ids = data.get("vlans[][id]", [])
        vlan_names = data.get("vlans[][name]", [])
        for vid, vname in zip(vlan_ids, vlan_names):
            if vid and vname:
                vlans.append({"id": vid, "name": vname})
        if vlans:
            device["vlans"] = vlans

        # Interfaces CE
        interfaces = []
        names = data.get("interfaces[][name]", [])
        ipv4s = data.get("interfaces[][ipv4]", [])
        ipv6s = data.get("interfaces[][ipv6]", [])
        modes = data.get("interfaces[][mode]", [])
        vlan_links = data.get("interfaces[][vlan]", [])
        for n, ip4, ip6, m, vlan in zip(names, ipv4s, ipv6s, modes, vlan_links):
            if not n:
                continue
            iface = {"name": n, "mode": m}
            if ip4:
                iface["ipv4"] = ip4
            if ip6:
                iface["ipv6"] = ip6
            if vlan:
                iface["vlan"] = vlan
            interfaces.append(iface)
        if interfaces:
            device["interfaces"] = interfaces

        # Static IPv4 Routes
        ipv4_routes = []
        prefixes = data.get("ipv4_routes[][prefix]", [])
        next_hops = data.get("ipv4_routes[][next_hop]", [])
        for p, nh in zip(prefixes, next_hops):
            if p and nh:
                ipv4_routes.append({"prefix": p, "next_hop": nh})

        # Static IPv6 Routes
        ipv6_routes = []
        prefixes6 = data.get("ipv6_routes[][prefix]", [])
        next_hops6 = data.get("ipv6_routes[][next_hop]", [])
        for p, nh in zip(prefixes6, next_hops6):
            if p and nh:
                ipv6_routes.append({"prefix": p, "next_hop": nh})

        static_routes = ipv4_routes + ipv6_routes
        if static_routes:
            device["static_routes"] = static_routes

        # Core
        if device["device_type"] == "Core":
            # Core Interfaces
            core_interfaces = []
            c_names = data.get("core_interfaces[][name]", [])
            c_ipv4s = data.get("core_interfaces[][ipv4]", [])
            c_ipv6s = data.get("core_interfaces[][ipv6]", [])
            c_ospfs = data.get("core_interfaces[][ospf]", [])
            c_dhcp_v4s = data.get("core_interfaces[][dhcp_v4]", [])
            c_dhcp_v6s = data.get("core_interfaces[][dhcp_v6]", [])

            for n, ip4, ip6, ospf_flag, d4, d6 in zip(c_names, c_ipv4s, c_ipv6s, c_ospfs, c_dhcp_v4s, c_dhcp_v6s):
                if not n:
                    continue
                iface = {"name": n}
                if ip4:
                    iface["ipv4"] = ip4
                if ip6:
                    iface["ipv6"] = ip6
                if ospf_flag == "yes":
                    iface["ospf"] = {"process_id": 1, "area": "0.0.0.0"}
                if d4:
                    iface["dhcp_server_v4"] = True
                if d6:
                    iface["dhcp_server_v6"] = True
                core_interfaces.append(iface)

            if core_interfaces:
                device["interfaces"] = core_interfaces

            # OSPF Configuration
            ospf_router_id = data.get("ospf_router_id", [""])[0]
            ospf_networks = []
            net_prefixes = data.get("ospf_networks[][prefix]", [])
            net_areas = data.get("ospf_networks[][area]", [])
            for p, a in zip(net_prefixes, net_areas):
                if p and a:
                    ospf_networks.append({"prefix": p, "area": a})

            device["ospf"] = {
                "process_id": 1,
                "router_id": ospf_router_id if ospf_router_id else "0.0.0.0",
                "networks": ospf_networks if ospf_networks else []
            }

            # RIP Configuration
            rip_networks = data.get("rip_networks[]", [])
            device["rip"] = {
                "networks": rip_networks if rip_networks else []
            }

        # DHCP Server
        dhcp_subnets = []
        prefixes = data.get("dhcp_subnets[][prefix]", [])
        ranges = data.get("dhcp_subnets[][range]", [])
        gateways = data.get("dhcp_subnets[][gateway]", [])
        for p, r, g in zip(prefixes, ranges, gateways):
            if p:
                subnet = {"prefix": p}
                if r:
                    if "-" in r:
                        start, end = r.split("-", 1)
                        subnet["range"] = {"start": start.strip(), "end": end.strip()}
                    else:
                        subnet["range"] = {"start": r.strip(), "end": ""}
                if g:
                    subnet["gateway"] = g
                dhcp_subnets.append(subnet)
        if dhcp_subnets:
            device["dhcp"] = {"subnets": dhcp_subnets}

        # PE
        if device["device_type"] == "PE":
            # Interfaces
            pe_interfaces = []
            p_names = data.get("pe_interfaces[][name]", [])
            p_ipv4s = data.get("pe_interfaces[][ipv4]", [])
            p_ipv6s = data.get("pe_interfaces[][ipv6]", [])
            p_ospfs = data.get("pe_interfaces[][ospf]", [])
            for n, ip4, ip6, ospf_flag in zip(p_names, p_ipv4s, p_ipv6s, p_ospfs):
                if not n:
                    continue
                iface = {"name": n}
                if ip4:
                    iface["ipv4"] = ip4
                if ip6:
                    iface["ipv6"] = ip6
                if ospf_flag == "yes":
                    iface["ospf"] = {"process_id": 1, "area": "0.0.0.0"}
                pe_interfaces.append(iface)
            if pe_interfaces:
                device["interfaces"] = pe_interfaces

            # OSPF
            ospf_router_id = data.get("ospf_router_id", [""])[0]
            ospf_networks = []
            net_prefixes = data.get("ospf_networks[][prefix]", [])
            net_areas = data.get("ospf_networks[][area]", [])
            for p, a in zip(net_prefixes, net_areas):
                if p and a:
                    ospf_networks.append({"prefix": p, "area": a})
            device["ospf"] = {
                "process_id": 1,
                "router_id": ospf_router_id if ospf_router_id else "0.0.0.0",
                "networks": ospf_networks if ospf_networks else []
            }

            # BGP
            local_as = data.get("bgp_local_as", [""])[0]
            neighbors = []
            n_ips = data.get("bgp_neighbors[][ip]", [])
            n_asns = data.get("bgp_neighbors[][remote_as]", [])
            n_actives = data.get("bgp_neighbors[][activate_ipv6]", [])
            for ip, ras, act in zip(n_ips, n_asns, n_actives):
                if ip and ras:
                    neighbors.append({
                        "ip": ip,
                        "remote_as": ras,
                        "activate_ipv6": True if act == "1" else False
                    })
            device["bgp"] = {
                "local_as": local_as,
                "neighbors": neighbors
            }

        # Save YAML
        filename = f"{device['hostname']}.yaml"
        file_path = YAML_DIR / filename
        with open(file_path, "w") as f:
            yaml.dump(device, f)

        flash(f"Device {device['hostname']} saved as {filename}")
        return redirect(url_for("index"))

    return render_template("add_device.html")

@app.route("/golden")
def golden():
    return render_template("golden.html", devices=DEVICES)


@app.route("/golden/fetch/<device_name>")
def golden_fetch(device_name):
    device_name = device_name.upper()
    if device_name not in DEVICES:
        flash(f"Unknown device: {device_name}")
        return redirect(url_for("golden"))

    ip = DEVICES[device_name]
    try:
        file_path = fetch_running_config(device_name, ip)
    except NetMikoTimeoutException:
        flash(f"Connection timed out to {device_name} ({ip}).")
        return redirect(url_for("golden"))
    except NetMikoAuthenticationException:
        flash(f"Authentication failed for {device_name} ({ip}).")
        return redirect(url_for("golden"))
    except Exception as e:
        flash(f"Error fetching config from {device_name}: {e}")
        return redirect(url_for("golden"))

    return send_from_directory(str(CONFIG_DIR), file_path.name, as_attachment=True)


@app.route("/configs")
def list_configs():
    files = sorted(CONFIG_DIR.glob("*.cfg"), reverse=True)
    files = [f.name for f in files]
    return render_template("configs.html", files=files)


@app.route("/configs/download/<path:filename>")
def download_config(filename):
    return send_from_directory(str(CONFIG_DIR), filename, as_attachment=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
