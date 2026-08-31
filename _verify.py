import yaml

raw = open('.github/workflows/sync.yml', 'rb').read().decode('utf-8')
# Replace the YAML 'on:' key with a quoted key so PyYAML keeps it (it coerces on/off to bool)
src = raw.replace('on:\n', '"on":\n', 1)
assert '"on":' in src, 'replace failed; check line endings'
d = yaml.safe_load(src)
on = d['"on"']
assert 'workflow_dispatch' in on, 'NO workflow_dispatch key!'
wd = on['workflow_dispatch']
ins = wd['inputs']
print('workflow_dispatch present:', True)
print('input keys:', list(ins.keys()))
for k, v in ins.items():
    print(f'  {k}: type={v.get("type")} required={v.get("required")} default={v.get("default","<none>")!r} options={v.get("options","<none>")}')
print('YAML DISPATCH BLOCK VALID')
