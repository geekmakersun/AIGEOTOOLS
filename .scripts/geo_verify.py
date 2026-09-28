#!/usr/bin/env python3
"""校验 wheelhouse/*.whl 的 sha256 与 requirements.txt 里 --hash=sha256:... 全部一致"""
import re, hashlib, sys, glob, os

if len(sys.argv) < 3:
    print("用法: geo_verify.py <requirements.txt> <wheelhouse_dir>", file=sys.stderr)
    sys.exit(2)
req_file, wheel_dir = sys.argv[1], sys.argv[2]

cur_pkg, expect = None, {}
with open(req_file) as f:
    for line in f:
        m1 = re.match(r'^([a-zA-Z0-9_.\-]+)==([^\s]+)', line)
        if m1:
            cur_pkg = re.sub(r'[-_.]+', '-', m1.group(1)).lower()
            expect[cur_pkg] = []
        m2 = re.search(r'--hash=sha256:([a-f0-9]+)', line)
        if m2 and cur_pkg:
            expect[cur_pkg].append(m2.group(1))

actual = {}
for whl in glob.glob(os.path.join(wheel_dir, '*.whl')):
    fname = os.path.basename(whl)
    m = re.match(r'^([^-]+)-(\d[^-]*)', fname)
    if m:
        cname = re.sub(r'[-_.]+', '-', m.group(1)).lower()
        h = hashlib.sha256(open(whl,'rb').read()).hexdigest()
        actual.setdefault(cname, []).append(h)

errs = 0
for pkg, exp_hashes in expect.items():
    act = actual.get(pkg, [])
    for h in exp_hashes:
        if h not in act:
            print(f'❌ {pkg}: hash 不一致 (期望 {h[:16]}...)')
            errs += 1
for pkg in actual:
    if pkg not in expect:
        print(f'⚠️  wheelhouse 残留 {pkg} 不在 pin 文件里')

print(f'结果: {len(expect)} pin / {len(actual)} wheel / {errs} 错误')
sys.exit(errs)
