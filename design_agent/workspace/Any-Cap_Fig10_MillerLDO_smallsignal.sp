* Small-Signal Model: Any-Cap_Fig10_MillerLDO
* Source: Any-Cap Low Dropout Voltage Regulator.pdf

.title Block Diagram of Miller-Compensated LDO Regulator (Small-Signal Model)

* Circuit parameters
.param gm_ea=100u
.param ro_ea=1Meg
.param gm_buffer=500u
.param ro_buffer=500k
.param gm_pass=10m
.param ro_pass=100k
.param Cp=5p
.param Cc=5p
.param CL=1u
.param R1=50k
.param R2=50k

* Input signal
VIN vin 0 AC 1

* Transconductance stages (VCCS)
Ggm_ea n_ea_out gnd fb gnd 100u  * gm_ea - Overall transconductance of the Error Amplifier
Ggm_buffer n_buffer_out gnd n_ea_out gnd 500u  * gm_buffer - Buffer stage transconductance
Ggm_pass vout gnd n_buffer_out gnd 10m  * gm_pass - Pass device transconductance

* Resistances
Rro_ea n_ea_out gnd 1Meg  * ro_ea - Output resistance of the Error Amplifier
Rro_buffer n_buffer_out gnd 500k  * ro_buffer - Buffer output resistance
Rro_pass vout gnd 100k  * ro_pass - Pass device output resistance
RR1 vout fb 50k  * R1 - Feedback resistor (upper)
RR2 fb gnd 50k  * R2 - Feedback resistor (lower)

* Capacitances
CCp n_buffer_out gnd 5p  * Cp - Pass device gate capacitance
CCL vout gnd 1u  * CL - Load capacitance
CCc n_ea_out vout 5p  * Cc - Miller compensation capacitor

* AC Analysis
.ac dec 100 1 10Meg

.control
run
plot vdb(vout) phase(vout)
let gain_db = vdb(vout)
let phase_deg = phase(vout) * 180 / pi
meas ac ugf when gain_db=0
meas ac pm find phase_deg when gain_db=0
print ugf pm
.endc

.end