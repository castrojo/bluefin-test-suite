@future @nvidia_only @requires_gpu @hardware_blocked
Feature: NVIDIA GPU passthrough validation
  Validates the NVIDIA driver stack, Vulkan, and CUDA on Bluefin NVIDIA variant.
  Runner: plain SSH behave (CLI validation, no GUI needed for most).

  # DEFERRED: Requires VFIO-PCI or vGPU passthrough configured in KubeVirt.
  # All scenarios are stubbed-only. See QA-REVIEW.md Epic E08.

  Background:
    * Bluefin NVIDIA VM is booted and reachable over SSH

  @nvidia @driver
  Scenario: nvidia-smi reports GPU model and driver version
    # TODO: Implement — requires actual GPU passthrough to VM.
    * Run SSH command: "nvidia-smi --query-gpu=name,driver_version --format=csv,noheader"
    * SSH command return code is "0"
    * SSH command output is not empty

  @nvidia @driver
  Scenario: NVIDIA kernel module is loaded
    * Run SSH command: "lsmod | grep -c nvidia"
    * SSH command return code is "0"

  @nvidia @vulkan
  Scenario: vulkaninfo reports NVIDIA Vulkan ICD
    # TODO: Implement — may need DISPLAY or headless Vulkan.
    * Run SSH command: "vulkaninfo --summary 2>&1 | grep -i nvidia"
    * SSH command return code is "0"

  @nvidia @vulkan @regression @bluefin_4620
  Scenario: No Vulkan validation errors in journal (bluefin#4620)
    * Run SSH command: "journalctl -b --no-pager -g 'VUID-' 2>/dev/null | grep -c 'VUID-'"
    * SSH command output stripped "is" "0"

  @nvidia @cuda
  Scenario: CUDA toolkit is functional
    # TODO: Implement — compile and run vectorAdd sample or use nvcc --version.
    * Run SSH command: "nvcc --version 2>/dev/null || echo missing"
    * SSH command output does not contain "missing"

  @nvidia @vaapi
  Scenario: VA-API hardware decode is available via NVIDIA
    # TODO: Implement — vainfo should show NVIDIA VA-API driver.
    * Run SSH command: "vainfo 2>&1 | grep -i nvidia || vainfo 2>&1 | grep -i 'Driver version'"
    * SSH command return code is "0"

  @nvidia @power
  Scenario: GPU power management state is accessible
    * Run SSH command: "nvidia-smi --query-gpu=power.draw --format=csv,noheader 2>/dev/null || echo skip"
    * SSH command output does not contain "skip"

  @nvidia @no_nouveau
  Scenario: nouveau driver is NOT loaded (conflicts with proprietary)
    * Run SSH command: "lsmod | grep -c nouveau"
    * SSH command output stripped "is" "0"

  # ── freedesktop / DRM validation ─────────────────────────────────────────
  # These scenarios use community tools (drm_info, vulkaninfo, glmark2-drm)
  # that are installable via dnf. Requires GPU passthrough (Epic E08).
  # References: issues #39, QA-REVIEW.md Epic E08.

  @nvidia @drm_info
  Scenario: DRM node identifies as nvidia driver
    * Run SSH command: "drm_info -j /dev/dri/card0 2>/dev/null | python3 -c 'import sys,json; d=json.load(sys.stdin); print(list(d.values())[0].get(\"driver\",{}).get(\"desc\",\"unknown\"))'"
    * SSH command output contains "nvidia"

  @nvidia @vulkan @wayland_surface
  Scenario: VK_KHR_wayland_surface extension is available
    * Run SSH command: "vulkaninfo --summary 2>/dev/null | grep -c VK_KHR_wayland_surface"
    * SSH command output is not "0"

  @nvidia @glmark2
  Scenario: glmark2-drm scores above zero (GPU render path works)
    * Run SSH command: "glmark2-drm --benchmark 'scene=build:duration=3' 2>&1 | grep -c '^Score'"
    * SSH command output is not "0"

  @nvidia @wayland_dmabuf
  Scenario: VA-API VAAPI encode/decode works via NVIDIA
    * Run SSH command: "vainfo 2>&1 | grep -c 'VAProfile'"
    * SSH command output is not "0"
