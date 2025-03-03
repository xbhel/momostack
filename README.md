# Cloud Computing Experiments

## Access your computer in a LAN network

Acquired a server with the public IP address, and perform the following tasks: 

- :lock: Create a Dedicated User for Regular Operations.
- :lock: Configure Password-less SSH Login.

Install the [frp](https://github.com/fatedier/frp) to access your computer in a LAN network.

> [frp](https://github.com/fatedier/frp) is a fast reverse proxy that allows you to expose a local server located behind a NAT or firewall to the Internet. It currently supports TCP and UDP, as well as HTTP and HTTPS protocols, enabling requests to be forwarded to internal services via domain name.

### Install FRP

Replace the frps to frpc to install FRP client. 

**online**

```bash
cd lanproxy
python3 build.py --service frps 
docker run -dit --name lanproxy-server lanproxy:frps -c conf/frps.toml
```

**offline**

```bash
cd lanproxy
python3 build.py --service frps --archive frp_0.61.1_linux_amd64.tar.gz
docker run -dit --name lanproxy-server lanproxy:frps -c conf/frps.toml
```
