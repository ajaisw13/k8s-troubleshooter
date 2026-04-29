import sys
import yaml

c = yaml.safe_load(sys.stdin)
for cl in c.get("clusters", []):
    cl["cluster"].pop("certificate-authority-data", None)
    cl["cluster"]["insecure-skip-tls-verify"] = True
    cl["cluster"]["server"] = cl["cluster"]["server"].replace(
        "127.0.0.1", "host.docker.internal"
    )
print(yaml.dump(c))
