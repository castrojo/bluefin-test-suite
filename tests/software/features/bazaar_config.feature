@software_suite
Feature: Bazaar app store configuration integrity
  The Bazaar app store reads YAML config files from /etc/bazaar/.
  A syntax error in any config file crashes the app store on launch.

  @software
  Scenario: Bazaar config directory is present
    * Run SSH command: "test -d /etc/bazaar && echo present"
    * SSH command output contains "present"

  @software
  Scenario: Bazaar YAML configuration files are syntactically valid
    * Run SSH command: "python3 -c \"import yaml, glob; files = glob.glob('/etc/bazaar/*.yaml'); [yaml.safe_load(open(f)) for f in files]; print(len(files))\""
    * SSH command return code is "0"

  @software
  Scenario: Bazaar blocklist config is present
    * Run SSH command: "test -f /etc/bazaar/blocklist.yaml && echo present"
    * SSH command output contains "present"

  @software
  Scenario: Bazaar curated config is present
    * Run SSH command: "test -f /etc/bazaar/curated.yaml && echo present"
    * SSH command output contains "present"
