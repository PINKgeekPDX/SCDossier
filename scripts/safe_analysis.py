import requests
import json
import time
import sys

url = "http://127.0.0.1:8888"

def get(endpoint, params=None):
    try:
        r = requests.get(f"{url}/{endpoint}", params=params, timeout=10)
        return json.loads(r.text) if r.ok else {"error": r.text}
    except Exception as e:
        return {"error": str(e)}

print("=== SC DOSSIER DEEP DEBUG ANALYSIS ===\n")

# 1. Process state
state = get("IsDebugActive")
debugging = get("Is_Debugging")
print(f"1. STATE: debugging={debugging}, active={state}\n")

# 2. Modules
modules = get("GetModuleList")
if isinstance(modules, list):
    print(f"2. MODULES: {len(modules)} loaded")
    for m in modules:
        name = m.get("name", "?")
        base = m.get("base", "?")
        size = m.get("size", "?")
        print(f"   {name} @ {base} size={size}")
else:
    print(f"2. MODULES: {modules}")
print()

# 3. Threads
tdata = get("GetThreadList")
if isinstance(tdata, dict):
    count = tdata.get("count", 0)
    cur = tdata.get("currentThread", 0)
    threads = tdata.get("threads", [])
    print(f"3. THREADS: {count} total, current_thread_index={cur}")
    for t in threads:
        tid = t.get("threadId", "?")
        name = t.get("threadName", "") or "(unnamed)"
        cycles = t.get("cycles", 0)
        wait = t.get("waitReason", "?")
        susp = t.get("suspendCount", 0)
        err = t.get("lastError", 0)
        last_status = t.get("lastStatus", {})
        status_code = last_status.get("code", 0) if isinstance(last_status, dict) else 0
        cip = t.get("cip", "?")
        flag = ""
        if cycles > 1000000000:
            flag = " *** VERY HIGH CYCLES"
        if name == "Main Thread":
            flag += " *** MAIN"
        if err != 0:
            flag += f" *** ERR={err}"
        if status_code != 0 and status_code != 258:
            flag += f" *** STATUS=0x{status_code:X}"
        print(f"   TID={tid} [{name}] cycles={cycles} cip={cip} wait={wait} susp={susp}{flag}")
else:
    print(f"3. THREADS: {tdata}")
print()

# 4. Call stack
cs = get("GetCallStack")
if isinstance(cs, dict):
    entries = cs.get("entries", [])
    total = cs.get("total", 0)
    print(f"4. CALL STACK: {total} frames")
    for e in entries:
        addr = e.get("addr", "?")
        comment = e.get("comment", "?")
        fr = e.get("from", "?")
        to = e.get("to", "?")
        print(f"   {addr} from={fr} to={to} [{comment}]")
else:
    print(f"4. CALL STACK: {cs}")
print()

# 5. Registers
regs = get("RegisterDump")
if isinstance(regs, dict):
    print("5. REGISTERS:")
    for key in ["cax", "ccx", "cdx", "cbx", "csp", "cbp", "cip", "r8", "r9", "r10", "r11"]:
        val = regs.get(key, "?")
        print(f"   {key} = {val}")
    flags = regs.get("flags", {})
    print(f"   FLAGS: {flags}")
    le = regs.get("lastError", {})
    print(f"   LAST ERROR: {le}")
    ls = regs.get("lastStatus", {})
    print(f"   LAST STATUS: {ls}")
else:
    print(f"5. REGISTERS: {regs}")
print()

# 6. Memory map summary
mm = get("MemoryMap")
if isinstance(mm, dict):
    pages = mm.get("pages", [])
    print(f"6. MEMORY MAP: {len(pages)} pages")
    rwx_count = 0
    rw_count = 0
    total_size = 0
    for p in pages:
        prot = p.get("protect", "")
        size_str = p.get("size", "0x0")
        try:
            sz = int(size_str, 16) if isinstance(size_str, str) else int(size_str)
        except:
            sz = 0
        total_size += sz
        if "EXECUTE" in prot.upper():
            rwx_count += 1
        if "READWRITE" in prot.upper():
            rw_count += 1
    print(f"   Total committed size: 0x{total_size:X} ({total_size // 1024} KB)")
    print(f"   Executable pages: {rwx_count}")
    print(f"   ReadWrite pages: {rw_count}")
elif isinstance(mm, list):
    print(f"6. MEMORY MAP: {len(mm)} entries")
else:
    print(f"6. MEMORY MAP: {str(mm)[:300]}")
print()

# 7. Handles
handles = get("EnumHandles")
if isinstance(handles, list):
    print(f"7. HANDLES: {len(handles)} total")
    types = {}
    for h in handles:
        ht = h.get("type", "unknown")
        types[ht] = types.get(ht, 0) + 1
    for ht, cnt in sorted(types.items(), key=lambda x: -x[1]):
        print(f"   {ht}: {cnt}")
else:
    print(f"7. HANDLES: {str(handles)[:300]}")
print()

# 8. TCP connections
tcp = get("EnumTcpConnections")
if isinstance(tcp, list):
    print(f"8. TCP CONNECTIONS: {len(tcp)}")
    for c in tcp[:10]:
        print(f"   {c}")
else:
    print(f"8. TCP: {str(tcp)[:300]}")
print()

# 9. Patches
patches = get("Patch/List")
if isinstance(patches, list):
    print(f"9. PATCHES: {len(patches)}")
    for p in patches[:10]:
        print(f"   {p}")
else:
    print(f"9. PATCHES: {str(patches)[:300]}")
print()

# 10. Breakpoints
bps = get("Breakpoint/List", {"type": "0"})
print(f"10. BREAKPOINTS: {str(bps)[:300]}")
print()

# 11. Exception info
exc = get("Exception/List")
print(f"11. EXCEPTIONS: {str(exc)[:500]}")
print()

print("=== ANALYSIS COMPLETE ===")
