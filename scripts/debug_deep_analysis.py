import sys, json, os
sys.path.insert(0, os.path.dirname(__file__))
from x64dbg_mcp_server import *

def section(label):
    print(f"\n{'#'*70}")
    print(f"  {label}")
    print(f"{'#'*70}")

section("PHASE 2: MEMORY CORRUPTION & PATTERN SCAN")

# Search for common dangerous patterns in the process memory
print("\n--- Scanning for null pointer dereference patterns ---")

# Search for patterns that might indicate issues
patterns = [
    ("48 89 00 00 00 00 00", "Possible null deref after mov [rax],..."),
    ("FF FF FF FF", "0xFFFFFFFF sentinel value"),
    ("DE AD BE EF", "Dead beef pattern (debug marker)"),
    ("CC CC CC CC", "Int3 padding (uninitialized code)"),
    ("00 00 00 00 00 00 00 00", "Long null run"),
]

for pat, desc in patterns:
    try:
        result = PatternFindMem("0x00000010000", "0x7FFFFFFF0000", pat)
        if result and "error" not in str(result).lower():
            print(f"  [{desc}] Found at: {result}")
        else:
            print(f"  [{desc}] Not found or limited scan")
    except Exception as e:
        print(f"  [{desc}] Scan error: {e}")

section("PHASE 3: ANTI-DEBUG & EXCEPTION HANDLER ANALYSIS")

# Check PEB for debugger flag
print("\n--- PEB Analysis ---")
try:
    peb_cmd = ExecCommand("peb")
    print("PEB:", str(peb_cmd)[:1000])
except:
    pass

# Check SEH chain
print("\n--- SEH Chain ---")
try:
    seh_cmd = ExecCommand("sehchain")
    print("SEH:", str(seh_cmd)[:1000])
except:
    pass

# Check if debugger is being detected
print("\n--- NtGlobalFlag (debug detection) ---")
try:
    # Read PEB.Bitness+0xBC (NtGlobalFlag)
    result = MemoryRead("0x7ffe0000+0xBC", "4")
    print("NtGlobalFlag bytes:", result)
except:
    pass

# Check heap flags
print("\n--- Heap Flags ---")
try:
    result = ExecCommand("heap flags")
    print("Heap flags:", str(result)[:1000])
except:
    pass

section("PHASE 4: THREAD DEADLOCK DETECTION")

tl = GetThreadList()
threads = tl.get('threads', [])

# Find threads that might be stuck (non-suspended, high cycle count, in wait states)
print("\n--- Potentially stuck threads ---")
active_threads = [t for t in threads if t.get('waitReason') != 'Suspended']
for t in active_threads:
    cycles = t.get('cycles', 0)
    print(f"  Thread {t.get('threadNumber'):2d} ({t.get('threadName', 'unnamed'):20s}) "
          f"TID={t.get('threadId'):6d} cycles={cycles:>12,} wait={t.get('waitReason')} pri={t.get('priority')}")

# Check for threads with high cycle counts (potential spin loops)
print("\n--- High cycle threads (>100M cycles) ---")
for t in sorted(threads, key=lambda x: x.get('cycles', 0), reverse=True)[:10]:
    cycles = t.get('cycles', 0)
    if cycles > 100000000:
        print(f"  Thread {t.get('threadNumber'):2d} ({t.get('threadName', 'unnamed'):20s}) "
              f"cycles={cycles:>12,} wait={t.get('waitReason')}")

# Check for TimeCritical and AboveNormal threads
print("\n--- High priority threads ---")
for t in threads:
    if t.get('priority') in ('TimeCritical', 'AboveNormal'):
        print(f"  Thread {t.get('threadNumber'):2d} ({t.get('threadName', 'unnamed'):20s}) "
              f"TID={t.get('threadId'):6d} cycles={t.get('cycles', 0):>12,} wait={t.get('waitReason')}")

section("PHASE 5: HANDLE & RESOURCE LEAK ANALYSIS")

handles = EnumHandles()
h_list = handles.get('handles', [])

from collections import Counter

# Count by type
type_counts = Counter(h.get('typeName', 'Unknown') for h in h_list)
print(f"\nTotal handles: {len(h_list)}")
print("\nHandle type distribution (top 30):")
for t, count in type_counts.most_common(30):
    print(f"  {t:20s}: {count}")

# Check for suspiciously high handle counts
if len(h_list) > 10000:
    print(f"\n*** WARNING: Very high handle count ({len(h_list)}) - potential handle leak ***")

# Count file handles specifically
file_handles = [h for h in h_list if h.get('typeName') == 'File']
print(f"\nFile handles: {len(file_handles)}")

# List unique file paths
file_paths = set()
for h in file_handles:
    name = h.get('name', '')
    if name and len(name) > 5:
        file_paths.add(name)

print(f"Unique file paths: {len(file_paths)}")
print("\nNotable open files:")
for fp in sorted(file_paths)[:30]:
    print(f"  {fp}")

# Check for event handles (potential leak)
event_handles = [h for h in h_list if h.get('typeName') == 'Event']
print(f"\nEvent handles: {len(event_handles)}")
if len(event_handles) > 100:
    print(f"*** WARNING: High event handle count - possible event leak ***")

section("PHASE 6: NETWORK CONNECTION AUDIT")

tcp = EnumTcpConnections()
conns = tcp.get('connections', [])
print(f"TCP connections: {len(conns)}")
for c in conns:
    print(f"  {c.get('localAddress')}:{c.get('localPort')} -> {c.get('remoteAddress')}:{c.get('remotePort')} state={c.get('state')}")

# Search for URLs in memory
print("\n--- Searching for URLs in memory ---")
url_patterns = [
    ("http", "HTTP URLs"),
    ("https", "HTTPS URLs"),
    ("supabase", "Supabase endpoints"),
    ("rsi", "RSI endpoints"),
    ("github", "GitHub URLs"),
    ("api.", "API endpoints"),
]

for pattern, desc in url_patterns:
    try:
        result = ExecCommand(f"findallmem 0x10000,{pattern},100")
        if result and result.get('refView', {}).get('rowCount', 0) > 0:
            print(f"  [{desc}] Found {result['refView']['rowCount']} references")
        else:
            print(f"  [{desc}] Not found in quick scan")
    except:
        pass

section("PHASE 7: CRASH PRONE PATTERNS")

# Scan for patterns that commonly cause crashes
print("\n--- Dangerous API patterns ---")
dangerous_apis = [
    ("strcpy", "Buffer overflow risk"),
    ("strcat", "Buffer overflow risk"),
    ("sprintf", "Buffer overflow risk"),
    ("gets", "Buffer overflow risk"),
    ("scanf", "Buffer overflow risk"),
    ("VirtualAlloc", "Memory allocation"),
    ("VirtualProtect", "Memory protection change"),
    ("CreateRemoteThread", "Code injection indicator"),
    ("WriteProcessMemory", "Process memory write"),
    ("LoadLibrary", "Dynamic loading"),
    ("GetProcAddress", "Dynamic API resolution"),
]

for api, desc in dangerous_apis:
    try:
        result = ExecCommand(f"findallmem 0x10000,{api},100")
        count = result.get('refView', {}).get('rowCount', 0) if isinstance(result, dict) else 0
        if count > 0:
            print(f"  [{api}] ({desc}): {count} references")
    except:
        pass

section("PHASE 8: STRING ANALYSIS")

# Search for interesting strings
interesting_strings = [
    ("password", "Possible credential leak"),
    ("secret", "Possible secret/key"),
    ("api_key", "Possible API key"),
    ("token", "Possible auth token"),
    ("error", "Error messages"),
    ("exception", "Exception handling"),
    ("critical", "Critical messages"),
    ("fatal", "Fatal error messages"),
    ("CRASH", "Crash indicators"),
    ("leak", "Memory leak references"),
    ("overflow", "Overflow references"),
    ("segfault", "Segmentation fault"),
    ("access violation", "Access violation"),
]

for s, desc in interesting_strings:
    try:
        result = ExecCommand(f"findallmem 0x10000,{s},100")
        count = result.get('refView', {}).get('rowCount', 0) if isinstance(result, dict) else 0
        if count > 0:
            print(f"  [{s}] ({desc}): {count} occurrences")
    except:
        pass

section("PHASE 9: PYTHON RUNTIME INSPECTION")

# Look for CPython-specific patterns
print("\n--- CPython Module Analysis ---")
mods = GetModuleList()
python_mods = [m for m in mods if 'python' in m.get('name', '').lower() or m.get('name', '').endswith('.pyd')]
print(f"Python-related modules: {len(python_mods)}")
for m in python_mods:
    print(f"  {m.get('name'):40s} base={m.get('base')} size={m.get('size')}")

# Look for onnxruntime (ML model)
onnx_mods = [m for m in mods if 'onnx' in m.get('name', '').lower()]
print(f"\nONNX Runtime modules: {len(onnx_mods)}")
for m in onnx_mods:
    print(f"  {m.get('name'):40s} base={m.get('base')} size={m.get('size')}")

# Look for Qt modules
qt_mods = [m for m in mods if 'qt' in m.get('name', '').lower()]
print(f"\nQt modules: {len(qt_mods)}")
for m in qt_mods:
    print(f"  {m.get('name'):40s} base={m.get('base')} size={m.get('size')}")

section("PHASE 10: MEMORY PROTECTION ANOMALIES")

mm = GetMemoryMap()
pages = mm.get('pages', [])

# Find pages with unusual protections
print("\n--- Memory protection summary ---")
prot_counts = Counter(p.get('protect', '?') for p in pages)
for prot, count in sorted(prot_counts.items(), key=lambda x: x[1], reverse=True):
    print(f"  {prot:6s}: {count} pages")

# Check for pages with no protection (potential issue)
no_prot = [p for p in pages if p.get('protect') == '---']
print(f"\nNo-protection pages: {len(no_prot)}")

# Check for large committed but unused pages
large_reserved = [p for p in pages if p.get('protect') == '---' and int(p.get('size', '0x0'), 16) > 0x100000]
print(f"Large reserved (>1MB, no protect): {len(large_reserved)}")
total_reserved_bytes = sum(int(p.get('size', '0x0'), 16) for p in large_reserved)
print(f"Total reserved bytes: {total_reserved_bytes / 1024 / 1024:.1f} MB")

section("PHASE 11: CALL STACK DEEP ANALYSIS")

cs = GetCallStack()
print(f"Call stack depth: {cs.get('total', 0)}")
print("\nFull call stack:")
for i, e in enumerate(cs.get('entries', [])):
    print(f"  [{i:2d}] {e.get('addr')} <- {e.get('from')} -> {e.get('to')}")
    print(f"       {e.get('comment', 'N/A')}")

# Disassemble return addresses
print("\n--- Disassembly at return addresses ---")
for e in cs.get('entries', [])[:5]:
    addr = e.get('from')
    if addr:
        try:
            dis = DisasmGetInstructionRange(addr, 3)
            for d in dis:
                print(f"  {d.get('address')}: {d.get('instruction')}")
        except:
            pass
        print()

section("PHASE 12: INPUT VALIDATION - STACK STATE")

print("\n--- Stack pointer analysis ---")
sp = "0x2d59a8f4f8"
stack_data = MemoryRead(sp, "128")
print(f"Stack at {sp}: {stack_data}")

# Read stack values as pointers
print("\n--- Stack values as potential pointers ---")
stack_vals = MemoryRead(sp, "64")
if isinstance(stack_vals, str):
    # Parse hex string into 8-byte chunks
    for i in range(0, min(len(stack_vals), 128), 16):
        chunk = stack_vals[i:i+16]
        if len(chunk) == 16:
            # Reverse byte order (little endian)
            val = "0x" + chunk[14:16] + chunk[12:14] + chunk[10:12] + chunk[8:10] + chunk[6:8] + chunk[4:6] + chunk[2:4] + chunk[0:2]
            # Check if it looks like a valid pointer
            if val.startswith("0x00000") or val.startswith("0x7ff"):
                valid = MemoryIsValidPtr(val)
                print(f"  offset +{i:3d}: {val} valid={valid}")

section("PHASE 13: EXCEPTION HANDLER AUDIT")

print("\n--- Structured Exception Handlers ---")
try:
    result = ExecCommand("sehchain")
    print("SEH chain:", str(result)[:2000])
except:
    pass

print("\n--- Vectored Exception Handlers ---")
try:
    result = ExecCommand("vehchain")
    print("VEH chain:", str(result)[:2000])
except:
    pass

section("PHASE 14: SECURITY POSTURE")

print("\n--- DEP Status ---")
try:
    result = ExecCommand("getdep")
    print("DEP:", result)
except:
    pass

print("\n--- ASLR Status ---")
try:
    result = ExecCommand("getaslr")
    print("ASLR:", result)
except:
    pass

print("\n--- CFG Status ---")
try:
    result = ExecCommand("getcfg")
    print("CFG:", result)
except:
    pass

print("\n--- Module signing status ---")
try:
    result = ExecCommand("sigcheck")
    print("Signature check:", str(result)[:2000])
except:
    pass

print("\n\n===== DEEP ANALYSIS COMPLETE =====")
