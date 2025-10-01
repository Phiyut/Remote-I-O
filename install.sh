set -e
echo "[1/8] Apt packages..."
sudo apt update
sudo apt install -y curl git nginx build-essential make g++ network-manager avahi-daemon

echo "[2/8] Enable NetworkManager..."
sudo systemctl disable --now dhcpcd 2>/dev/null || true
sudo systemctl enable --now NetworkManager

echo "[3/8] Install Node-RED..."
bash <(curl -sL https://raw.githubusercontent.com/node-red/linux-installers/master/deb/update-nodejs-and-nodered)
sudo systemctl enable --now nodered

echo "[4/8] Patch Node-RED path (/studio) & bind 127.0.0.1 ..."
sed -i 's|// uiHost: .*|uiHost: "127.0.0.1",|' ~/.node-red/settings.js
sed -i 's|// httpAdminRoot: .*|httpAdminRoot: "/studio",|' ~/.node-red/settings.js
sed -i 's|// httpNodeRoot: .*|httpNodeRoot: "/studio/api",|' ~/.node-red/settings.js
node-red-stop && node-red-start
sudo systemctl restart nodered

echo "[5/8] Install API..."
sudo mkdir -p /opt/remoteio/api
sudo cp -f ./api/server.js /opt/remoteio/api/server.js
sudo cp -f ./systemd/remoteio-api.service /etc/systemd/system/remoteio-api.service
cd ./api
npm ci || npm i
cd ..
sudo systemctl daemon-reload
sudo systemctl enable --now remoteio-api

echo "[6/8] Install Modbus TCP Server..."
sudo mkdir -p /opt/remoteio/modbus
sudo cp -f ./modbus/modbus-server.js /opt/remoteio/modbus/modbus-server.js
sudo cp -f ./systemd/modbus-tcp.service /etc/systemd/system/modbus-tcp.service
sudo systemctl daemon-reload
sudo systemctl enable --now modbus-tcp

echo "[7/8] Web files..."
sudo mkdir -p /var/www/remoteio
if [ -d ./web ]; then
  sudo rsync -a --delete ./web/ /var/www/remoteio/
fi

echo "[8/8] Nginx site & Network profiles..."
if [ -f ./nginx/remoteio.conf ]; then
  sudo cp -f ./nginx/remoteio.conf /etc/nginx/sites-available/remoteio
fi
sudo ln -sf /etc/nginx/sites-available/remoteio /etc/nginx/sites-enabled/remoteio
sudo nginx -t && sudo systemctl reload nginx

# Network: eth0 = 192.168.0.5/24 (no gateway), Wi-Fi = default route
nmcli con show | awk -F'  +' '$2=="802-3-ethernet"{print $1}' | xargs -r -I{} nmcli con delete "{}"
sudo nmcli con add type ethernet ifname eth0 con-name eth0-static \
  ipv4.method manual ipv4.addresses "192.168.0.5/24" \
  ipv4.gateway "" ipv4.dns "" ipv4.never-default yes \
  ipv4.route-metric 300 autoconnect yes connection.autoconnect-priority 100
sudo nmcli con up eth0-static
WIFI_CON="$(nmcli -t -f NAME,TYPE con show | awk -F: '$2=="wifi"{print $1;exit}')"
[ -n "$WIFI_CON" ] && sudo nmcli con mod "$WIFI_CON" ipv4.method auto ipv4.never-default no ipv4.route-metric 50 && sudo nmcli con up "$WIFI_CON"

echo "== Verify =="
curl -s http://127.0.0.1/api/status || true
curl -I http://127.0.0.1/studio/ || true
echo "DONE. Open: http://localhost , http://192.168.0.5"
