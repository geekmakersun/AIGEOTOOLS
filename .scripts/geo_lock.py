#!/usr/bin/env python3
"""生成 requirements.txt：从 pip freeze（运行中容器）+ wheelhouse sha256  → 锁定文件

用法（由 Makefile 调用）:
    docker exec <container> /opt/venv/bin/pip freeze --exclude-editable > /tmp/geo-frozen.txt
    python3 .scripts/geo_lock.py /tmp/geo-frozen.txt requirements.txt wheelhouse/
"""
import re, hashlib, glob, os, sys
from datetime import datetime, timezone

if len(sys.argv) < 4:
    print("用法: geo_lock.py <freeze.txt> <out.txt> <wheelhouse_dir>", file=sys.stderr)
    sys.exit(2)
freeze_file, out_file, wheel_dir = sys.argv[1], sys.argv[2], sys.argv[3]

# 1) freeze → {canonical: (pkg, ver)}
freeze = {}
with open(freeze_file) as f:
    for line in f:
        line = line.strip()
        if '==' in line:
            pkg, ver = line.split('==', 1)
            freeze[re.sub(r'[-_.]+', '-', pkg).lower()] = (pkg, ver)

# 2) wheelhouse → {canonical: [(fname, sha256), ...]}
wheels = {}
for whl in glob.glob(os.path.join(wheel_dir, '*.whl')):
    fname = os.path.basename(whl)
    m = re.match(r'^([^-]+)-(\d[^-]*)', fname)
    if m:
        cname = re.sub(r'[-_.]+', '-', m.group(1)).lower()
        h = hashlib.sha256(open(whl, 'rb').read()).hexdigest()
        wheels.setdefault(cname, []).append((fname, h))

# 3) 生成 requirements.txt
out = [
    "#",
    "# AUTO-GENERATED — DO NOT EDIT MANUALLY",
    "# Source  : requirements.in → pip freeze (verified runtime)",
    "# Hashes  : sha256sum on wheelhouse/*.whl",
    "# Tool    : make lock (regenerate)",
    "# Upgrade : make upgrade PKG=<name>",
    "# Date    : " + datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
    "#",
    f"# {len(freeze)} packages pinned, {sum(len(v) for v in wheels.values())} wheels indexed",
    "",
]
missing = []
for canonical, (pkg, ver) in sorted(freeze.items()):
    hs = wheels.get(canonical, [])
    if hs:
        out.append(f"{pkg}=={ver} \\")
        for _, h in hs:
            out.append(f"    --hash=sha256:{h}")
    else:
        out.append(f"{pkg}=={ver}   # wheelhouse missing")
        missing.append(pkg)
    out.append("")

with open(out_file, 'w') as f:
    f.write('\n'.join(out))

print(f"✅ {out_file} 已写入（{len(freeze)} 包 pin）")
if missing:
    print(f"⚠️  wheelhouse 缺 {len(missing)} 个: {', '.join(missing)}", file=sys.stderr)
    sys.exit(1)
