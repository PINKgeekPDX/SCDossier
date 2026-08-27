import sys, json, os
sys.path.insert(0, os.path.dirname(__file__))
from x64dbg_mcp_server import *

def dump(label, data):
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    print(json.dumps(data, indent=2, default=str))

def section(label):
    print(f"\n{'#'*70}")
    print(f"  {label}")
    print(f"{'#'*70}")

section("PHASE 1: PROCESS HEALTH SNAPSHOT")

# Debug state
print("Debugging:", IsDebugging())

# Registers
regs = GetRegisterDump()
print("\n--- Register Dump ---")
print(json.dumps(regs, indent=2))

# Memory Map Analysis
section("MEMORY MAP ANALYSIS")
mm = GetMemoryMap()
pages = mm.get('pages', [])
print(f"Total pages: {mm.get('count', 0)}")

from collections import Counter
type_counts = Counter(p.get('type', '?') for p in pages)
print("Page types:", dict(type_counts))

protect_counts = Counter(p.get('protect', '?') for p in pages)
print("Protection distribution:", dict(protect_counts))

rwx = [p for p in pages if 'x' in p.get('protect', '').lower() and 'w' in p.get('protect', '').lower()]
print(f"\nRWX (writable+executable) pages: {len(rwx)}")
for p in rwx[:10]:
    print(f"  {p.get('base')} size={p.get('size')} prot={p.get('protect')} info={p.get('info', '')}")

large = [p for p in pages if int(p.get('size', '0x0'), 16) > 0x100000]
print(f"\nLarge allocations (>1MB): {len(large)}")
for p in large[:10]:
    sz = int(p.get('size', '0x0'), 16)
    print(f"  {p.get('base')} size={sz/1024/1024:.1f}MB prot={p.get('protect')} type={p.get('type')} info={p.get('info', '')}")

section("THREAD ANALYSIS")
tl = GetThreadList()
threads = tl.get('threads', [])
print(f"Total threads: {tl.get('count', 0)}")
print(f"Current thread: {tl.get('currentThread', '?')}")

named = [t for t in threads if t.get('threadName')]
print(f"\nNamed threads ({len(named)}):")
for t in named:
    print(f"  [{t.get('threadNumber'):2d}] {t.get('threadName'):30s} TID={t.get('threadId'):6d} pri={t.get('priority'):12s} wait={t.get('waitReason')}")

prios = Counter(t.get('priority') for t in threads)
print(f"\nPriority distribution: {dict(prios)}")
waits = Counter(t.get('waitReason') for t in threads)
print(f"Wait reasons: {dict(waits)}")

errors = [(t.get('threadNumber'), t.get('threadId'), t.get('lastError')) for t in threads if t.get('lastError', 0) != 0]
if errors:
    print(f"\n*** THREADS WITH ERRORS ({len(errors)}) ***")
    for tn, tid, err in errors:
        print(f"  Thread {tn} (TID={tid}): lastError={err}")
else:
    print("\nNo threads with errors.")

section("HANDLE ANALYSIS")
handles = EnumHandles()
h_list = handles.get('handles', [])
print(f"Total handles: {handles.get('count', 0)}")

types = Counter(h.get('typeName', 'Unknown') for h in h_list)
print("\nHandle type distribution:")
for t, count in types.most_common(20):
    print(f"  {t}: {count}")

print("\nNotable named handles:")
seen = set()
for h in h_list:
    name = h.get('name', '')
    if name and name not in seen:
        seen.add(name)
        print(f"  [{h.get('typeName', '?'):10s}] {name}")

section("TCP CONNECTIONS")
tcp = EnumTcpConnections()
conns = tcp.get('connections', [])
print(f"Total connections: {tcp.get('count', 0)}")
for c in conns:
    print(f"  {c.get('localAddress')}:{c.get('localPort')} -> {c.get('remoteAddress')}:{c.get('remotePort')} state={c.get('state')}")

section("PATCHES")
patches = GetPatchList()
print(f"Total patches: {patches.get('count', 0)}")
for p in patches.get('patches', []):
    print(f"  {p.get('module')}+{p.get('address')}: {p.get('oldByte')} -> {p.get('newByte')}")

section("MODULE SECURITY AUDIT")
mods = GetModuleList()
print(f"Total modules: {len(mods)}")

# Full module list
for i, m in enumerate(mods):
    print(f"  [{i:2d}] {m.get('name', '?'):40s} base={m.get('base')} size={m.get('size')}")

section("EXECUTION CONTROL FLOW")
cs = GetCallStack()
print(f"Call stack depth: {cs.get('total', 0)}")
for e in cs.get('entries', []):
    print(f"  {e.get('addr')} from={e.get('from')} to={e.get('to')} {e.get('comment', '')}")

section("BASIC DISASSEMBLY AT CIP")
cip = regs.get('cip', '0x0')
disasm = DisasmGetInstructionRange(cip, 20)
for d in disasm:
    print(f"  {d.get('address')}: {d.get('instruction')}")

section("DETAILED PROCESS INFO")
try:
    pi = ExecCommand("getpiddbg")
    print("PID info:", pi)
except:
    pass

try:
    meminfo = ExecCommand("memmap")
    lines = str(meminfo).split('\\n') if isinstance(meminfo, str) else []
    print(f"Memory map command returned {len(lines)} lines")
except:
    pass

section("DEP/ASLR STATUS")
try:
    dep = ExecCommand("getdep")
    print("DEP:", dep)
except:
    pass

section("HEAP INFO")
try:
    heaps = ExecCommand("heap")
    print("Heap info:", str(heaps)[:2000])
except:
    pass

print("\n\n===== ANALYSIS COMPLETE =====")
