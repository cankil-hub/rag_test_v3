* Small-Signal Model Template for LDO
* Uses ideal voltage/current sources to represent gm, ro, etc.

.title Small-Signal LDO Analysis

* Input signal
VIN vin 0 AC 1

* Transconductance stages (VCCS: Voltage-Controlled Current Source)
* Syntax: Gxxx n+ n- nc+ nc- value
* Current from n+ to n- is controlled by voltage across nc+ to nc-

{GM_STAGES}

* Output resistances
{RO_RESISTANCES}

* Capacitances
{CAPACITORS}

* Load
{LOAD}

* AC Analysis
.ac dec 100 1 10Meg

.control
run
* Plot gain and phase
plot vdb(vout) phase(vout)
* Print important frequencies
let gain_db = vdb(vout)
let phase = phase(vout) * 180 / pi
meas ac ugf when gain_db=0
meas ac pm find phase when gain_db=0
print ugf pm
.endc

.end
