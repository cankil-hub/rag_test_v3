* Figure 24: Any-Cap Initial LDO with Device Sizing
* Auto-generated from topology annotation
* Model: 3.3V ideal_3v3 (Level 1)

.title Any-Cap Initial LDO - Figure 24

* Include device models
.include ../models/ideal_3v3.sp

* Supply and reference
VIN VIN 0 DC 3.3
VREF VREF 0 DC 0.6

* Bias Circuit
I3uA VIN n_bias DC 3u
M15 n_bias n_bias VIN VIN pmos_3v3 W=40u L=6u
M16 n1 n_bias VIN VIN pmos_3v3 W=20u L=6u  
M17 n2 n_bias VIN VIN pmos_3v3 W=20u L=6u
M18 n_bias n_bias 0 0 nmos_3v3 W=20u L=10u
M19 n1 FB 0 0 nmos_3v3 W=4u L=12u
M20 n2 n2 0 0 nmos_3v3 W=25u L=2u
M10 n1 n1 0 0 nmos_3v3 W=10u L=6u

* Error Amplifier (Folded-Cascode OTA)
M1 n3 VREF n5 0 nmos_3v3 W=100u L=2u
M2 n4 VFB n5 0 nmos_3v3 W=100u L=2u
M3 n3 n1 VIN VIN pmos_3v3 W=40u L=10u
M4 n4 n1 VIN VIN pmos_3v3 W=40u L=10u
M5 n3 n2 n6 0 nmos_3v3 W=40u L=10u
M6 n4 n2 n7 0 nmos_3v3 W=40u L=10u
M7 n6 n6 0 0 nmos_3v3 W=10u L=5u
M8 n7 n6 0 0 nmos_3v3 W=50u L=2u
M9 n5 n2 0 0 nmos_3v3 W=100u L=5u

* Buffer Stage (Source Follower)
M11 n8 n4 VIN VIN pmos_3v3 W=250u L=2u
M12 n8 n8 n9 0 nmos_3v3 W=100u L=2u
M13 n9 n9 0 0 nmos_3v3 W=100u L=2u
M14 VCTRL n8 VIN VIN pmos_3v3 W=300u L=2u

* Pass Device
MPASS VOUT VCTRL VIN VIN pmos_3v3 W=850000u L=2u

* Feedback Network
R1 VOUT VFB 50k
R2 VFB 0 7.3k
R3 VOUT n10 50k
R4 n10 0 50k

* Load
CLOAD VOUT 0 1u
* RLOAD VOUT 0 {RLOAD_VAL}
ILOAD VOUT 0 DC 50m

* Analysis Commands
.param VIN_VAL=3.3
.param VREF_VAL=0.6
.param CLOAD_VAL=1u
.param ILOAD_VAL=0

* DC Operating Point
.op

* DC Sweep (Load Regulation)
.dc ILOAD 0 100m 1m

* AC Analysis (Loop Gain and Stability)
* .ac dec 100 1 10Meg

* Transient Analysis
* .tran 1n 100u

.control
run
print v(VOUT) v(VFB) v(VCTRL)
plot v(VOUT)
.endc

.end
