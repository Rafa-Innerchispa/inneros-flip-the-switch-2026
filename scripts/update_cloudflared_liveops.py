from pathlib import Path

path = Path("/home/rlopez/.cloudflared/opportunityops.yml")
content = path.read_text(encoding="utf-8")

liveops_entry = "  - hostname: liveops.pcdoctor.ai\n    service: http://192.168.1.5:8788\n"

if "hostname: liveops.pcdoctor.ai" not in content:
    target = "  - hostname: guardian.pcdoctor.ai"
    content = content.replace(target, liveops_entry + target, 1)

content = content.replace("service: http://192.168.1.5:8793", "service: http://192.168.1.5:8788")

path.write_text(content, encoding="utf-8")
print("opportunityops.yml successfully updated with liveops.pcdoctor.ai -> http://192.168.1.5:8788")
