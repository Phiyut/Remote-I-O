# RemoteIO Bundle Template
- Copy this folder to /home/pi on a target Pi.
- Run: ./install.sh

After install:
- http://localhost      (UI)
- http://<Pi-IP>/studio (Node-RED)
- Modbus TCP server on port 1502 (unit 1)

Edit api/server.js or modbus/modbus-server.js as needed.


git clone https://github.com/Phiyut/Remote-I-O.git

# 0) เตรียมเครื่อง (ครั้งเดียว)
sudo apt update
sudo apt install -y curl git nginx build-essential make g++ network-manager avahi-daemon

# ใช้ NetworkManager คุมเน็ต (ปิด dhcpcd ถ้ามี)
sudo systemctl disable --now dhcpcd 2>/dev/null || true
sudo systemctl enable --now NetworkManager

# 1) ติดตั้ง Node-RED และย้ายไปเส้นทาง /studio (ฟังเฉพาะเครื่อง)
# ติดตั้งแบบทางการ
bash <(curl -sL https://raw.githubusercontent.com/node-red/linux-installers/master/deb/update-nodejs-and-nodered)
sudo systemctl enable --now nodered

# แก้ settings ให้:
#   - bind 127.0.0.1
#   - httpAdminRoot = /studio
#   - httpNodeRoot  = /studio/api
sed -i 's|// uiHost: .*|uiHost: "127.0.0.1",|' ~/.node-red/settings.js
sed -i 's|// httpAdminRoot: .*|httpAdminRoot: "/studio",|' ~/.node-red/settings.js
sed -i 's|// httpNodeRoot: .*|httpNodeRoot: "/studio/api",|' ~/.node-red/settings.js

node-red-stop && node-red-start
sudo systemctl restart nodered

# 2) ทำ Backend API (Express + pigpio + nmcli)
sudo mkdir -p /opt/remoteio/api
sudo chown -R $USER:$USER /opt/remoteio
cd /opt/remoteio/api
npm init -y
npm i express pigpio

# 2.1 วางไฟล์ /opt/remoteio/api/server.js

โค้ดนี้รองรับ /api/status, /api/system, /api/trend, /api/io/*, /api/wifi/*, /api/ip, /api/modbus/* และ ฟัง 127.0.0.1:8080 (ให้ Nginx proxy)

cat > /opt/remoteio/api/server.js <<'EOF'
const express = require("express");
const { exec } = require("child_process");
const os = require("os");

// pigpio (fallback ถ้าไม่มี)
let Gpio;
try { ({ Gpio } = require("pigpio")); } catch { Gpio = class { constructor(){this._v=0} digitalWrite(v){this._v=v?1:0} digitalRead(){return this._v} }; }

const app = express();
app.use(express.json());

// กำหนดขา BCM สำหรับ DI/DO
const DI_GPIO = [26,16,20,21,12,7,8,25];
const DO_GPIO = [4,17,27,22,5,6,13,19];

const outs = DO_GPIO.map(p=>{ try{ const g=new Gpio(p,{mode:Gpio.OUTPUT}); g.digitalWrite(0); return g; }catch{ return new Gpio(); }});
const ins  = DI_GPIO.map(p=>{ try{ return new Gpio(p,{mode:Gpio.INPUT,pullUpDown:Gpio.PUD_DOWN}); }catch{ return new Gpio(); }});

function sh(cmd){ return new Promise((res,rej)=>exec(cmd,{timeout:20000},(e,so,se)=>e?rej(se||e.message):res((so||"").trim()))); }
async function diskPct(){ try{ const x=await sh(`df -P / | tail -1 | awk '{print $2" " $3}'`); const [b,u]=x.split(/\s+/).map(Number); return Math.round(u*100/b);}catch{return 0;} }

app.get("/api/status",(req,res)=>res.json({locked:false,ts:Date.now()}));
app.get("/api/system", async (req,res)=>{ const cpu=Math.min(100,Math.round((os.loadavg()[0]||0)*100/(os.cpus()?.length||4))), ram=Math.round((1-os.freemem()/os.totalmem())*100), disk=await diskPct(); res.json({cpu,ram,disk}); });
app.get("/api/trend",(req,res)=>{ res.json({ t:new Date().toLocaleTimeString(), current:+(Math.random()*10).toFixed(2), voltage:220+Math.round(Math.random()*6-3) }); });

app.get("/api/io/state",(req,res)=>{ const di=ins.map((g,i)=>({i:i+1,bcm:DI_GPIO[i],value:g.digitalRead()?1:0})); const dO=outs.map((g,i)=>({i:i+1,bcm:DO_GPIO[i],value:g.digitalRead? (g.digitalRead()?1:0):0})); res.json({di,do:dO}); });
app.post("/api/io/set",(req,res)=>{ const i=Number(req.body?.index)-1, v=!!req.body?.value; if(i<0||i>=outs.length) return res.status(400).json({error:"bad index"}); outs[i].digitalWrite(v?1:0); res.json({ok:true}); });

app.get("/api/wifi/scan", async (req,res)=>{ try{ const out=await sh(`nmcli -t -f SSID,SIGNAL dev wifi || true`); const networks=(out?out.split("\n"):[]).filter(Boolean).map(l=>{const[a,b]=l.split(":");return {ssid:a,rssi:b?+b:null};}); res.json({networks}); }catch(e){ res.status(500).json({error:String(e)});} });
app.get("/api/wifi/status", async (req,res)=>{ try{ const s=await sh(`nmcli -t -f GENERAL.CONNECTION device show wlan0 | cut -d: -f2- || true`); res.json({ssid:s||""}); }catch{ res.json({ssid:""});} });

// ตั้ง IP: ถ้า Static แต่ไม่ใส่ Gateway → ทำ LAN only (ไม่แย่ง default route)
app.post("/api/ip", async (req,res)=>{
  const { iface="eth0", mode="dhcp", ip, gw, metric } = req.body || {};
  try{
    const name = (await sh(`nmcli -t -f NAME,DEVICE con show --active | awk -F: '$2=="${iface}"{print $1;exit}' || true`)) || (iface==="eth0"?"eth0-static":"");
    if(!name) throw new Error(`no connection for ${iface}`);
    if(mode==="dhcp"){
      await sh(`nmcli con mod "${name}" ipv4.method auto ipv4.addresses "" ipv4.gateway "" ipv4.never-default no`);
    }else{
      if(!ip) throw new Error("ip required");
      await sh(`nmcli con mod "${name}" ipv4.method manual ipv4.addresses "${ip}"`);
      if(gw && gw.trim()){ await sh(`nmcli con mod "${name}" ipv4.gateway "${gw}" ipv4.never-default no`); }
      else { await sh(`nmcli con mod "${name}" ipv4.gateway "" ipv4.never-default yes`); }
    }
    if(metric) await sh(`nmcli con mod "${name}" ipv4.route-metric ${metric} ipv6.route-metric ${metric}`);
    await sh(`nmcli con down "${name}" && nmcli con up "${name}"`);
    res.json({ok:true});
  }catch(e){ res.status(500).json({error:String(e)}); }
});

// Modbus config (stub สำหรับ UI)
let modbusCfg = { enabled:false, mode:"tcp", port:502, unitId:1, baud:9600 };
app.get("/api/modbus/status",(req,res)=>res.json(modbusCfg));
app.post("/api/modbus/apply",(req,res)=>{ modbusCfg = { ...modbusCfg, ...req.body }; res.json({ok:true}); });

app.listen(8080,"127.0.0.1",()=>console.log(`[RemoteIO] API on http://127.0.0.1:8080`));
EOF

# 3) ทำ Frontend UI (Vite + React + Tailwind v4)
mkdir -p /opt/remoteio && cd /opt/remoteio
npm create vite@latest ui -- --template react   # ตอบ: rolldown = No, install now = No
cd ui && npm i
npm i lucide-react recharts
npm i -D tailwindcss @tailwindcss/postcss postcss autoprefixer

# 3.1 ตั้ง Tailwind v4 + PostCSS
# PostCSS ของ Tailwind v4
cat > postcss.config.js <<'EOF'
export default { plugins: { '@tailwindcss/postcss': {} } };
EOF

# ไฟล์ CSS หลัก
mkdir -p src
cat > src/index.css <<'EOF'
@import "tailwindcss";
EOF

# ให้ main.jsx import CSS
grep -q "import './index.css'" src/main.jsx || sed -i "1i import './index.css'" src/main.jsx

# 3.2 วางหน้าแอป

เปิดแก้ไฟล์: /opt/remoteio/ui/src/App.jsx แล้ววาง โค้ด React dashboard ที่พี่ใช้ (ชุด Network/I/O/Modbus)

(ออปชั่น) ตั้ง title ตามภาษาในแอป: document.title = t("appTitle")

# 3.3 Favicon + Title
mkdir -p public
# วางไฟล์ public/favicon.png , (ออปชั่น) favicon-192.png, favicon-512.png
# ตั้ง title และลิงก์ icon ใน index.html
sed -i 's|<title>.*</title>|<title>Remote I/O – Edge HMI</title>|' index.html
grep -q 'rel="icon"' index.html || \
sed -i 's#</head>#  <link rel="icon" type="image/png" href="/favicon.png?v=2" />\n</head>#' index.html

# 3.4 Build + deploy ไป Nginx
export NODE_OPTIONS=--max-old-space-size=512
npm run build
sudo mkdir -p /var/www/remoteio
sudo rsync -a --delete dist/ /var/www/remoteio/

# 4) ตั้ง Nginx (เสิร์ฟ UI + proxy /api และ /studio)
sudo tee /etc/nginx/sites-available/remoteio >/dev/null <<'NGINX'
server {
  listen 80;
  server_name _;
  root /var/www/remoteio;
  index index.html;

  location / { try_files $uri /index.html; }

  location /api/ {
    proxy_pass http://127.0.0.1:8080;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
  }

  location /studio/ {
    proxy_pass http://127.0.0.1:1880/studio/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
  }
}
NGINX
sudo ln -sf /etc/nginx/sites-available/remoteio /etc/nginx/sites-enabled/remoteio
sudo nginx -t && sudo systemctl reload nginx

# 5) ตั้งค่าเครือข่ายให้ “LAN แยกจาก Wi-Fi”
# ลบโปรไฟล์ ethernet เก่า (กันชน)
nmcli con show | awk -F'  +' '$2=="802-3-ethernet"{print $1}' | xargs -r -I{} nmcli con delete "{}"

# โปรไฟล์ eth0-static (LAN only)
sudo nmcli con add type ethernet ifname eth0 con-name eth0-static \
  ipv4.method manual ipv4.addresses "192.168.0.5/24" \
  ipv4.gateway "" ipv4.dns "" ipv4.never-default yes \
  ipv4.route-metric 300 autoconnect yes connection.autoconnect-priority 100
sudo nmcli con up eth0-static

# ให้ Wi-Fi เป็น default route
WIFI_CON="$(nmcli -t -f NAME,TYPE con show | awk -F: '$2=="wifi"{print $1;exit}')"
[ -n "$WIFI_CON" ] && \
sudo nmcli con mod "$WIFI_CON" ipv4.method auto ipv4.never-default no ipv4.route-metric 50 && \
sudo nmcli con up "$WIFI_CON"

# ตรวจ:
ip -4 addr show eth0
ip -4 addr show wlan0
ip r | sed -n '1,10p'     # ต้องเห็น default via ... dev wlan0

# 6) (ทางเลือก) เปิด Modbus TCP Server บนพอร์ต 1502
sudo mkdir -p /opt/remoteio/modbus && cd /opt/remoteio/modbus
npm init -y
npm i modbus-serial
cat > /opt/remoteio/modbus/modbus-server.js <<'EOF'
const ModbusRTU = require("modbus-serial");
const PORT=parseInt(process.env.MODBUS_PORT||"1502",10), UNIT=parseInt(process.env.MODBUS_UNIT||"1",10);
async function api(p,b){const r=await fetch(`http://127.0.0.1:8080${p}`,{method:b?"POST":"GET",headers:{"Content-Type":"application/json"},body:b?JSON.stringify(b):undefined}); if(!r.ok) throw new Error(p+" "+r.status); return r.json();}
const vec={
  getDiscreteInput:async(a,u,cb)=>{ try{const s=await api("/api/io/state"); cb(null,!!(s.di?.[a]?.value)); }catch(e){cb(e)} },
  getCoil:async(a,u,cb)=>{ try{const s=await api("/api/io/state"); cb(null,!!(s.do?.[a]?.value)); }catch(e){cb(e)} },
  setCoil:async(a,v,u,cb)=>{ try{await api("/api/io/set",{index:a+1,value:!!v}); cb(null); }catch(e){cb(e)} },
  getHoldingRegister:async(a,u,cb)=>{ try{const m=await api("/api/system"); const map=[Math.round(m.cpu||0),Math.round(m.ram||0),Math.round(m.disk||0)]; cb(null,(map[a]??0)&0xFFFF); }catch(e){cb(e)} },
  getInputRegister:async(a,u,cb)=>cb(null,0),
};
new ModbusRTU.ServerTCP(vec,{host:"0.0.0.0",port:PORT,unitID:UNIT});
console.log(`[Modbus] TCP Server 0.0.0.0:${PORT} (Unit ${UNIT})`);
EOF

sudo tee /etc/systemd/system/modbus-tcp.service >/dev/null <<'EOF'
[Unit]
Description=RemoteIO Modbus TCP Server (via API)
After=remoteio-api.service
Requires=remoteio-api.service
[Service]
User=pi
WorkingDirectory=/opt/remoteio/modbus
Environment=MODBUS_PORT=1502
Environment=MODBUS_UNIT=1
ExecStart=/usr/bin/node /opt/remoteio/modbus/modbus-server.js
Restart=on-failure
[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now modbus-tcp
sudo ss -ltnp | grep 1502

# 7) ตรวจเช็คก่อนส่งงาน
# UI + API + Node-RED
curl -I  http://127.0.0.1/
curl -s  http://127.0.0.1/api/status
curl -I  http://127.0.0.1/studio/

# เส้นทางออกเน็ต
ip r | sed -n '1,10p'   # default via ... dev wlan0

# จาก PC (ตั้ง IP เป็น 192.168.0.10/24 ไม่ต้องใส่ gateway)
ping 192.168.0.5
# เปิด http://192.168.0.5/

# 8) อัปเดต UI ครั้งต่อไป (แก้ App.jsx แล้วขึ้น Prod)
cd /opt/remoteio/ui
export NODE_OPTIONS=--max-old-space-size=512
npm run build
sudo rsync -a --delete dist/ /var/www/remoteio/
# (ออปชั่น) sudo systemctl reload nginx

# 9) สรุป “ที่อยู่ไฟล์” ทั้งระบบ
# Backend API
/opt/remoteio/api/server.js
/etc/systemd/system/remoteio-api.service (log: sudo journalctl -u remoteio-api -f)

# Frontend UI (ที่ build แล้ว)
/var/www/remoteio/ (ต้นทางโปรเจกต์อยู่ /opt/remoteio/ui/ → build แล้วคัดลอกมาที่นี่)
index.html, assets/* (หลัง build)

# Vite/React Project
/opt/remoteio/ui/src/App.jsx (หน้า UI หลัก)
/opt/remoteio/ui/src/index.css (Tailwind v4)
/opt/remoteio/ui/postcss.config.js
/opt/remoteio/ui/public/favicon.png (และไฟล์ไอคอนอื่น ๆ)

# Nginx
/etc/nginx/sites-available/remoteio (enabled ที่ sites-enabled/remoteio)
Log: /var/log/nginx/error.log

# Node-RED
~/.node-red/settings.js

# Modbus TCP (ตัวเลือก)
/opt/remoteio/modbus/modbus-server.js
/etc/systemd/system/modbus-tcp.service
