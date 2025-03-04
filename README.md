# Cloud Computing Experiments

## Access your computer in a LAN network

Acquired a server with the public IP address.

- Create a Dedicated User for Regular Operations (Optional).
- Configure Password-less SSH Login (Optional).

Install the **[frp](https://github.com/fatedier/frp)** to access your computer in a LAN network.

> **[frp](https://github.com/fatedier/frp)** is a fast reverse proxy that allows you to expose a local server located behind a NAT or firewall to the Internet. It currently supports TCP and UDP, as well as HTTP and HTTPS protocols, enabling requests to be forwarded to internal services via domain name.

**Install FRP**

Upload the *./lanproxy* folder to your computer, then run the following commands to start the **frp** server.

```bash
cd lanproxy
python3 build_image.py --service frps --image-name lanproxy:frps
docker run -dit -p 7000:7000 -p 2222:2222 -v $(pwd)/conf:/opt/frp/conf --name server lanproxy:frps
docker exec -it server ps -ef | grep frps
```

If you need to start the **frp** client instead, replace `frps` with `frpc`:

```bash
cd lanproxy
python3 build_image.py --service frpc --image-name lanproxy:frpc
docker run -dit -v $(pwd)/conf:/opt/frp/conf --name client lanproxy:frpc
docker exec -it client ps -ef | grep frpc
 ```

By default, when you run *build_image.py* to build the image, it will fetch **frp** from GitHub. If you're offline or unable to access GitHub, you can manually download the frp archive beforehand and use the `--file path/to/frp_xxx.tar.gz` option to specify it for building the image:

```bash
python3 build_image.py --service frps --image-name lanproxy:frps --file path/to/frp_xxx.tar.gz
```