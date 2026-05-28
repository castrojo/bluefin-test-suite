@future @nvidia_only @requires_gpu @hardware_blocked
Feature: NVIDIA GPU passthrough validation
  Validates the NVIDIA driver stack, Vulkan, and CUDA on Bluefin NVIDIA variant.
  Runner: plain SSH behave (CLI validation, no GUI needed for most).

  # DEFERRED: Requires VFIO-PCI or vGPU passthrough configured in KubeVirt.
  # ghost has AMD Ryzen AI MAX+ — confirm if discrete NVIDIA GPU is present
  # before activating this suite. All scenarios are stubbed-only.
  # See QA-REVIEW.md Epic E08.

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
    * Run SSH command: "journalctl -b --no-pager -g 'VUID-' 2>/dev/null | grep -c 'VUID-' || echo 0"
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
    * Run SSH command: "lsmod | grep -c nouveau || echo 0"
    * SSH command output stripped "is" "0"
