const ModbusRTU = require("modbus-serial");

const PORT   = parseInt(process.env.MODBUS_PORT || "1502", 10);
const UNITID = parseInt(process.env.MODBUS_UNIT || "1", 10);

async function api(path, body) {
  const res = await fetch(`http://127.0.0.1:8080${path}`, {
    method: body ? "POST" : "GET",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`API ${path} -> HTTP ${res.status}`);
  return res.json();
}
async function readIO(){ try { return await api("/api/io/state"); } catch { return { di: [], do: [] }; } }
async function setDO(index, value){ try { await api("/api/io/set", { index, value: !!value }); return true; } catch { return false; } }
async function readSystem(){ try { return await api("/api/system"); } catch { return { cpu:0, ram:0, disk:0 }; } }

const vector = {
  getDiscreteInput: async (addr, unitID, cb) => {
    try { const st = await readIO(); const di = st.di?.[addr]?.value ? 1 : 0; cb(null, di === 1); } catch (e) { cb(e); }
  },
  getCoil: async (addr, unitID, cb) => {
    try { const st = await readIO(); const dO = st.do?.[addr]?.value ? 1 : 0; cb(null, dO === 1); } catch (e) { cb(e); }
  },
  setCoil: async (addr, value, unitID, cb) => {
    try { const ok = await setDO(addr + 1, !!value); cb(ok ? null : new Error("setDO failed")); } catch (e) { cb(e); }
  },
  getHoldingRegister: async (addr, unitID, cb) => {
    try { const s = await readSystem(); const map = [Math.round(s.cpu||0), Math.round(s.ram||0), Math.round(s.disk||0)]; const v = map[addr] ?? 0; cb(null, v & 0xFFFF); } catch (e) { cb(e); }
  },
  getInputRegister: async (addr, unitID, cb) => { cb(null, 0); },
};

const server = new ModbusRTU.ServerTCP(vector, {
  host: "0.0.0.0",
  port: PORT,
  unitID: UNITID,
  debug: false,
});
server.on("initialized", () => console.log(`[Modbus] TCP Server started on 0.0.0.0:${PORT} (Unit ${UNITID})`));
server.on("socketError", (e) => console.error("[Modbus] socketError:", e.message || e));
