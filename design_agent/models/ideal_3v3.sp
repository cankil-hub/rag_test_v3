* Generic 3.3V MOSFET Model (Level 1)
* For Concept Validation Only

.model nmos_3v3 nmos level=1
+ vto=0.7      gamma=0.45   phi=0.9
+ nsub=9e14    nsd=2e19     tox=7.5n
+ uo=350       lamda=0.01  
+ cj=0.56m     mj=0.45      cjsw=0.35m   mjsw=0.2
+ cgso=0.4n    cgdo=0.4n    cgbo=0.1n
+ rs=10        rd=10

.model pmos_3v3 pmos level=1
+ vto=-0.8     gamma=0.4    phi=0.8
+ nsub=5e14    nsd=2e19     tox=7.5n
+ uo=100       lamda=0.02
+ cj=0.94m     mj=0.5       cjsw=0.32m   mjsw=0.3
+ cgso=0.4n    cgdo=0.4n    cgbo=0.1n
+ rs=20        rd=20
