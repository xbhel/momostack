# Memo Stack

## Access your computer in a LAN network

Acquired a server with the public IP address.

- Create a Dedicated User for Regular Operations (Optional).
- Configure Password-less SSH Login (Optional).

Install the **[frp](https://github.com/fatedier/frp)** to access your computer in a LAN network. 

- [FRP Document.](https://gofrp.org/zh-cn/docs/)
- [FRP README.md](https://github.com/fatedier/frp)
- [FRP Server(frps) Full Configuration](https://github.com/fatedier/frp/blob/dev/conf/frps_full_example.toml)
- [FRP Client(frps) Full Configuration](https://github.com/fatedier/frp/blob/dev/conf/frpc_full_example.toml)

> **[frp](https://github.com/fatedier/frp)** is a fast reverse proxy that allows you to expose a local server located behind a NAT or firewall to the Internet. It currently supports TCP and UDP, as well as HTTP and HTTPS protocols, enabling requests to be forwarded to internal services via domain name.


**Install FRP**

Upload the *./lanproxy* folder to your computer, then run the following commands to start the **frp** server.

```bash
cd lanproxy
python3 build_image.py --service frps --image-name lanproxy:frps

# network mode: bridge 
# docker run --restart=always -dit \
# -p 7000:7000 -p 2222:2222 -p 7500:7500 \
# -v $(pwd)/conf:/opt/frp/conf \
# -e FRP_TOKEN=$FRP_TOKEN \
# -e FRP_DASHBOARD_USER=$FRP_DASHBOARD_USER \
# -e  FRP_DASHBOARD_PASSWD=$FRP_DASHBOARD_PASSWD \
# --name server lanproxy:frps

# network mode: host 
docker run --restart=on-failure \
--network host -dit \
-v $(pwd)/conf:/opt/frp/conf \
-e FRP_TOKEN=$FRP_TOKEN \
-e FRP_DASHBOARD_USER=$FRP_DASHBOARD_USER \
-e FRP_DASHBOARD_PASSWD=$FRP_DASHBOARD_PASSWD \
--name server lanproxy:frps

docker exec -it server ps -ef | grep frps

# By default, frps logs will be output to stdout if you don’t configure a log output file in frps.toml.
# In this case, you can use the following command to view the logs of frps.
docker logs -f server
docker exec 2678cd7a612d tail -f /var/log/frp/frps.log
```

If you need to start the **frp** client instead, replace `frps` with `frpc`:

```bash
cd lanproxy
python3 build_image.py --service frpc --image-name lanproxy:frpc

docker run --restart=on-failure \
--network host -dit \
-v $(pwd)/conf:/opt/frp/conf \
-e FRP_TOKEN=$FRP_TOKEN \
-e FRP_SERVER_ADDR=$FRP_SERVER_ADDR \
--name client lanproxy:frpc

docker exec -it client ps -ef | grep frpc
docker logs -f client
 ```

By default, when you run *build_image.py* to build the image, it will fetch **frp** from GitHub. If you're offline or unable to access GitHub, you can manually download the frp archive beforehand and use the `--file path/to/frp_xxx.tar.gz` option to specify it for building the image:

```bash
python3 build_image.py --service frps --image-name lanproxy:frps --file path/to/frp_xxx.tar.gz
```
