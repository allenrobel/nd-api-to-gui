# nd_api_to_gui

The intent of this repository is to provide those developing Nexus Dashboard (ND)
applications with an easy way to correlate ND REST API parameters with their
corresponding fields in the ND graphical user interface.

We accomplish this with two scripts and supporting libraries, as described below.

## template_names.py

Return all templates supported by ND.  This takes about 10 seconds to run
so be patient.

```bash
cd $HOME/repos/nd-api-to-gui
source .venv/bin/activate
source env/env
./template_names.py
```

### Example partial output for template_names.py

```text
- AI_Fabric_QOS_100G
- AI_Fabric_QOS_25G
- AI_Fabric_QOS_400G
- AI_Fabric_QOS_800G
- AI_Fabric_QOS_Classification_Custom
- AI_Fabric_QOS_Queuing_Custom
- Default_Network_Extension_Universal

etc...
```

You could redirect the output to a file so that you have the list locally
for offline reference.

```bash
./template_names.py > templates.txt
```

## api_to_gui.py

Passing one of the above template names into api_to_gui.py using the
`--template-name` argument returns information about the parameters
in that template that are most useful for our purposes.

Note, to save your fingers `--template-name` can be shortened to e.g.
`--template`, `--te`, `--t`, etc, and will still work.

```bash
cd $HOME/repos/nd-api-to-gui
source .venv/bin/activate
source env/env
./api_to_gui.py --template-name Default_Network_Extension_Universal
```

### Example partial output for api_to_gui.py

For each API key, the output contains:

- Description: The description that accompanies the field in the Nexus Dashboard GUI
- GUI Section: The tab in the ND GUI that contains the field
- GUI Field Name: The name of the field associated with the API key

```text
API Key: ENABLE_NETFLOW
  Description: Netflow is supported only if it is enabled on fabric. For NX-OS only
  GUI Section: Advanced
  GUI Field Name: Enable Netflow

API Key: MULTISITE_CONN
  Description: L2 Extension Information
  GUI Section: MULTISITE
  GUI Field Name: L2 Extension Information

API Key: SVI_NETFLOW_MONITOR
  Description: Applicable only if 'Layer 2 Only' is not enabled. Provide monitor name defined in fabric setting for Layer 3 Record. For NX-OS only
  GUI Section: Advanced
  GUI Field Name: Interface Vlan Netflow Monitor

API Key: VLAN_NETFLOW_MONITOR
  Description: Provide monitor name defined in fabric setting for Layer 3 Record. For NX-OS only
  GUI Section: Advanced
  GUI Field Name: Vlan Netflow Monitor

etc...
```

You could also search for a specific key with the following.

```bash
./api_to_gui.py --t Easy_Fabric | grep -A4 preInterfaceConfigTor$
API Key: preInterfaceConfigTor
  Description: Additional CLIs, added before interface configurations, for all ToRs as captured from Show Running Configuration
  GUI Section: Freeform
  GUI Field Name: ToR Pre-Interfaces Freeform Config
```

Or display all fields located in a given GUI Section

```bash
./api_to_gui.py --t Easy_Fabric | grep "GUI Section: Freeform" -B3 -A1
```

## Installation and Initial Setup

### Clone the repository

I prefer keeping all my repositories in one place, so will use $HOME/repos in the
examples below.  But you can clone it anywhere you want.

```bash
cd $HOME/repos
git clone https://github.com/allenrobel/nd-api-to-gui.git
```

### Create a Virtual Environment and Install Dependencies

```bash
cd $HOME/repos/nd-api-to-gui
python3 -m .venv --prompt nd-api-to-gui
source .venv/bin/activate
pip install uv
uv sync
```

### Configure Environment Variables

Use whatever editor you're comfortable with to modify the following file.

```bash
$HOME/repos/nd-api-to-gui/env/env
```

- Set ND_IP4 to the address of your ND controller
- Set ND_DOMAIN to the login domain (by default, this is `local`)
- Set ND_USERNAME to the login username (by default, this is `admin`)
- For ND_PASSWORD, I usually set this manually in my terminal session so it's not laying around on disk.
  But you can set it in this file if you're comfortable with that.
- Finally, set ND_API_TO_GUI to point to this repository (in my case, that's
  `$HOME/repos/nd-api-to-gui`)
- Save the file

The file contains the following initially.

```bash
cd $HOME/repos/nd-api-to-gui
cat env/env
# Environment variables for ND-API-to-GUI project
# Modify the following ND_* variables as needed for your Nexus Dashboard environment
export ND_IP4=192.168.1.1
export ND_DOMAIN=local
export ND_USERNAME=admin
#
# Define ND_PASSWORD in a terminal for better security or (not recommended) define here if you're in a secure environment
# export ND_PASSWORD=MyPassword
#
# Path to the nd-api-to-gui repository on your local machine
export ND_API_TO_GUI=$HOME/repos/nd-to-api-gui
#
# No need to modify below this line
#
# Append ND_API_TO_GUI to PYTHONPATH only if not already present
#
if [[ "$PYTHONPATH" != *":$ND_API_TO_GUI"* ]]; then
  export PYTHONPATH=.:$PYTHONPATH:$ND_API_TO_GUI
fi
```

Finally, `source` the file to load these environment variables (which the
scripts read so they have the information they need to connect to ND).

```bash
cd $HOME/repos/nd-api-to-gui
source .venv/bin/activate
source env/env
```

Done!  Now you can run the scripts, per the examples above.

If you didn't set ND_PASSWORD in the env/env file, don't forget to
set it in your terminal session before running the scripts.

```bash
export ND_PASSWORD=MyPassword
```
