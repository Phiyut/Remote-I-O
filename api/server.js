const express = require("express");
const { exec } = require("child_process");
const os = require("os");

let Gpio;
try { ({ Gpio } = require("pigpio")); console.log("[GPIO] pigpio loaded"); }
catch (e) {
  console.warn("[GPIO] pigpio not available, using stub:", e?.message || e);
  Gpio = class { constructor(){ this._v=0 } digitalWrite(v){ this._v=v?1:0 } digitalRead(){ return this._v } };
}

const app = express();
app.use(express.json());

const DI_GPIO = [26,16,20,21,12,7,8,25];
const DO_GPIO = [4,17,27,22,5,6,13,19];

const outs = DO_GPIO.map(pin => { try { const g = new Gpio(pin, { mode: Gpio.OUTPUT }); g.digitalWrite(0); return g; } catch { return new Gpio(); } });
const ins  = DI_GPIO.map(pin  => { try { return new Gpio(pin, { mode: Gpio.INPUT, pullUpDown: Gpio.PUD_DOWN }); } catch { return new Gpio(); } });

function sh(cmd){ return new Promise((res,rej)=>exec(cmd,{timeout:20000},(e,so,se)=>e?rej(se||e.message):res((so||"").trim()))); }
async function diskRoot(){ try{ const out=await sh(`df -P / | tail -1 | awk '{print $2" " $3}'`); const [b,u]=out.split(/\s+/).map(Number); return Math.round(u*100/b); }catch{return 0;} }

app.get("/api/status",(req,res)=>res.json({locked:false,ts:Date.now()}));
app.get("/api/system", async (req,res)=>{
  try{
    const cpu = Math.min(100, Math.round((os.loadavg()[0]||0)*100/(os.cpus()?.length||4)));
    const ram = Math.round((1-os.freemem()/os.totalmem())*100);
    const disk = await diskRoot();
    res.json({cpu,ram,disk});
  }catch(e){ res.status(500).json({error:String(e)}); }
});
app.get("/api/trend",(req,res)=>{
  const t = new Date().toLocaleTimeString();
  const current = +(Math.random()*10).toFixed(2);
  const voltage = 220 + Math.round(Math.random()*6-3);
  res.json({t,current,voltage});
});
app.get("/api/io/state",(req,res)=>{
  const di = ins.map((g,i)=>({i:i+1,bcm:DI_GPIO[i],value:g.digitalRead()?1:0}));
  const dO = outs.map((g,i)=>({i:i+1,bcm:DO_GPIO[i],value:g.digitalRead? (g.digitalRead()?1:0):0}));
  res.json({di,do:dO});
});
app.post("/api/io/set",(req,res)=>{
  const { index, value } = req.body||{};
  const i = Number(index)-1;
  if (i<0 || i>=outs.length) return res.status(400).json({error:"bad index"});
  outs[i].digitalWrite(value?1:0);
  res.json({ok:true});
});

app.get("/api/wifi/scan", async (req,res)=>{
  try{
    const out = await sh(`nmcli -t -f SSID,SIGNAL dev wifi || true`);
    const networks = (out?out.split("\n"):[]).filter(Boolean).map(l=>{ const [ssid,rssi]=l.split(":"); return {ssid, rssi:rssi?Number(rssi):null}; });
    res.json({networks});
  }catch(e){ res.status(500).json({error:String(e)}); }
});
app.get("/api/wifi/status", async (req,res)=>{
  try{ const out = await sh(`nmcli -t -f GENERAL.CONNECTION device show wlan0 | cut -d: -f2- || true`); res.json({ssid: out||""}); }
  catch{ res.json({ssid:""}); }
});
app.post("/api/ip", async (req,res)=>{
  const { iface="eth0", mode="dhcp", ip, gw, metric } = req.body || {};
  try{
    const conName = await sh(`nmcli -t -f NAME,DEVICE con show --active | awk -F: '$2=="${iface}"{print $1;exit}' || true`);
    const name = conName || (iface==="eth0"?"eth0-static":"");
    if(!name) throw new Error(`cannot find active connection for ${iface}`);

    if (mode === "dhcp") {
      await sh(`nmcli con mod "${name}" ipv4.method auto ipv4.addresses "" ipv4.gateway "" ipv4.never-default no`);
    } else {
      if (!ip) throw new Error("ip required for static");
      await sh(`nmcli con mod "${name}" ipv4.method manual ipv4.addresses "${ip}"`);
      if (gw && gw.trim()) {
        await sh(`nmcli con mod "${name}" ipv4.gateway "${gw}" ipv4.never-default no`);
      } else {
        await sh(`nmcli con mod "${name}" ipv4.gateway "" ipv4.never-default yes`);
      }
    }
    if (metric) await sh(`nmcli con mod "${name}" ipv4.route-metric ${metric} ipv6.route-metric ${metric}`);
    await sh(`nmcli con down "${name}" && nmcli con up "${name}"`);
    res.json({ok:true});
  }catch(e){ res.status(500).json({error:String(e)}); }
});

let modbusCfg = { enabled:false, mode:"tcp", port:502, unitId:1, baud:9600 };
app.get("/api/modbus/status",(req,res)=>res.json(modbusCfg));
app.post("/api/modbus/apply",(req,res)=>{ modbusCfg = { ...modbusCfg, ...req.body }; res.json({ok:true}); });

const PORT = 8080, HOST = "127.0.0.1";
app.listen(PORT, HOST, ()=>console.log(`[RemoteIO] API listening on http://${HOST}:${PORT}`));
