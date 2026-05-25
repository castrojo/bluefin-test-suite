# Deprecated: CDI/PVC v1 Workflow Files

These files used the CDI (Containerized Data Importer) + zot registry approach
for provisioning test VMs. They have been superseded by the **btrfs reflink v2**
approach which is faster (~24ms clone vs ~60-90s CDI pull) and simpler.

## Why deprecated?

- `provision-vm.yaml` — used CDI DataVolume + PVC. Replaced by hostDisk + btrfs reflink.
- `bib-build-and-push.yaml` — pushed disk to zot OCI registry. Now stores golden disk on hostPath.
- `teardown-vm.yaml` — deleted PVC. Now deletes hostDisk file.
- `bluefin-smoke-test.yaml` — inline DAG. Replaced by bluefin-qa-pipeline WorkflowTemplate.

Do not use these files. The canonical v2 files are in `../workflow-templates/`.
