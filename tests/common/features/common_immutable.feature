@common @bluefin
Feature: Immutable OS integrity
  Verifies Bluefin's immutable OS properties.
  Bluefin is image-based — no RPM packages should be layered
  via rpm-ostree/bootc. Layered packages indicate local mutations
  that break reproducibility and increase upgrade risk.

  Background:
    * Bluefin VM is booted and reachable over SSH

  Scenario: No RPM packages are layered on the base image
    * Run SSH command: "rpm-ostree status --json 2>/dev/null | python3 -c \"import sys,json; d=json.load(sys.stdin); layers=[p for dep in d.get('deployments',[]) for p in dep.get('requested-packages',[])]; print(len(layers)); sys.exit(0 if not layers else 1)\""
    * SSH command return code is "0"

  Scenario: bootc status shows a pinned image
    * Run SSH command: "bootc status --json 2>/dev/null | python3 -c \"import sys,json; d=json.load(sys.stdin); img=d.get('status',{}).get('booted',{}).get('image',{}); print(img.get('image',{}).get('image','none')); sys.exit(0 if img else 1)\""
    * SSH command return code is "0"
    * SSH command output is not empty

  Scenario: /usr filesystem is mounted read-only
    * Run SSH command: "findmnt /usr --output OPTIONS -n 2>/dev/null | grep -q ro && echo read-only || mount | grep 'on /usr ' | grep -q ro && echo read-only"
    * SSH command return code is "0"
    * Last command output contains "read-only"
