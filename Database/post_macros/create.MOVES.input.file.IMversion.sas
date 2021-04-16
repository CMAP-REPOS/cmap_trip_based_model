/* CREATE.MOVES.INPUT.FILE.IMVERSION.SAS
     Craig Heither, rev. 05-21-2015

    Program reads model output generated by ..\post_macros\punch.moves.data.mac and
    formats it for input into MOVES. Two spreadsheets are created:
      - one containing data for the Vehicle Inspection and Maintenance area in the IL portion of the non-attainment area.
      - one containing data for the non-Vehicle Inspection and Maintenance area in the IL portion of the non-attainment area.


    MOVES Data Conversion Dictionary:


    Road Types:
        MOVES Type & Description                  Model VDF
        -----------------------------             ---------------
         1: Off-Network                     -     N/A
         2: Rural Restricted Access         -     rural 2,3,4,5,7,8
         3: Rural Unrestricted Access       -     rural 1,6
         4: Urban Restricted Access         -     urban 2,3,4,5,7,8
         5: Urban Unrestricted Access       -     urban 1,6

    Source Types:
        MOVES Type & Description                  HPMS Type & Description                 VHT Distribution Source from model
        -----------------------------             -------------------------               ----------------------------------
         11: Motorcycle                     -     10: Motorcycles                    -    (use auto distribution)
         21: Passenger Car                  -     20: Passenger Cars                 -    autos
         31: Passenger Truck                -     30: Other 2 axle-4 tire vehicles   -    b-plate trucks
         32: Light Commercial Truck         -     30: Other 2 axle-4 tire vehicles   -    light duty trucks
         41: Intercity Bus                  -     40: Buses                          -    (use transit bus distribution)
         42: Transit Bus                    -     40: Buses                          -    transit bus
         43: School Bus                     -     40: Buses                          -    (use transit bus distribution)
         51: Refuse Truck                   -     50: Single Unit Trucks             -    (use medium duty trucks under 200 miles distribution)
         52: Single Unit Short-haul Truck   -     50: Single Unit Trucks             -    medium duty trucks under 200 miles
         53: Single Unit Long-haul Truck    -     50: Single Unit Trucks             -    medium duty trucks 200+ miles
         54: Motor Home                     -     50: Single Unit Trucks             -    (use medium duty trucks 200+ miles distribution)
         61: Combination Short-haul Truck   -     60: Combination Trucks             -    heavy duty trucks under 200 miles
         62: Combination Long-haul Truck    -     60: Combination Trucks             -    heavy duty trucks 200+ miles



      Revisions:
        - 06-19-2012: Uses new bus.link file created from GTFS coding.
        - 09-06-2012: Incorporates SU/MU long-haul data from path-based traffic assignment.
        - 09-27-2012: Use surrogate bus & truck shares for speed distribution if necessary: see Note below.
        - 12-21-2012: Surrogate logic also applied to RoadTypeDistribution & hourVMTFraction.
        - 12-19-2014: Creates two spreadsheet per scenario: one for I&M VMT and one for non-I&M vmt.
                         I&M zone ranges were updated 12-2014 by Steve Chau:
                         see the wiki entry: <http://wiki.cmap.local/mediawiki/index.php/Vehicle_Inspection_and_Maintenance_Zones>
        - NRF 02-25-2015: Replace avhov with avh2v and avh3v for 7 vehicle class assignment
        - 04-10-2015: Error check that all eight time periods are included in bus.link file.
        - 07-08-2016: RoadTypeID 1 removed from RoadTypeDistribution tab (it is no longer used in MOVES2014a); code to delete .bak files
        - 3-27-2017 : Read in busveq with other network attributes instead of separate bus link file Bozic
        - 11-15-2018: Read in IM/nonIM areas from network attributes
                      also redefine the nonattainment area zones for the Z17 Bozic
        - NRF 12-18-2018: Read in data\moves_avgSpeedBinID.csv to create template with all speed bins (line 293)
        - SCB 10-15-2020: Edit hourVMTFraction calculation for source types 53 and 54 (start at line 630)

 ----------------------------------------------------------------------------------- */

*** ============================== ***;
%let project=c21q2;
%let run=200_20210324;
%let year=2020;                                   ** scenario year **;
*** ============================== ***;

filename in0 "..\data\moves.longhaul.data";
filename in1 "..\data\moves.data";
***filename in2 "..\data\bus.link"; **==DON'T NEED THIS ANYMORE.  BUS VEHICLES ARE ON THE NETWORK;

options nodate pagesize=156 linesize=135 nocenter nonumber noxwait;

data _null_; command="if exist ..\data\MOVES_&project._scen&run._IM.xlsx (del ..\data\MOVES_&project._scen&run._IM.xlsx /Q)" ;
    call system(command);
data _null_; command="if exist ..\data\MOVES_&project._scen&run._nonIM.xlsx (del ..\data\MOVES_&project._scen&run._nonIM.xlsx /Q)" ;
    call system(command);

 *** -- GET LONG-HAUL DATA -- ***;
data lh; infile in0;
  input @3 flag $1. @;
    select(flag);
     when('i') delete;
     otherwise input @1 i j period m200 h200;
    end;
   proc sort; by period i j;


 *** -- GET LINK DATA -- ***;
 *** -- notice im input here, now stored on the network-;
data a(drop=flag); infile in1;
  input @3 flag $1. @;
    select(flag);
     when('i') delete;
     otherwise input @1 i j period miles lanes vdf zone emcap
                  timau ftime avauv avh2v avh3v avbqv avlqv avmqv avhqv areatype isramp busveq im;
    end;

data a(drop=avh2v avh3v); set a(where=(i>0 & j>0));
 avauv=avauv+avh2v+avh3v;                                      *** combine SOV, HOV2, and HOV3+ into auto category;
 if vdf=3 or vdf=5 or vdf=8 then isramp=1;               *** flag ramps: toll links on ramps already flagged in file;
    proc sort; by period i j;


    data a; merge a(in=hit) lh ; by period i j; if hit;

data a; set a;
 *** -- ISOLATE Z17 NON-ATTAINMENT AREA ZONES -- ***;
  if    1<=zone<=2304
  or 2309<=zone<=2313
  or 2317<=zone<=2319
  or 2326<=zone<=2926
  or zone=2941
  or 2943<=zone<=2944
  or zone= 2949 ;

 *** -- FLAG VEHICLE INSPECTION AND MAINTENANCE AREA (Rev. DEC. 2014) -- ***;
 ** -- now read directly from network export attributes 0=no, 1=yes --;



 *** -- RESET TOTAL M & H VEHICLE EQUIVALENTS TO SHORT-HAUL VEQS -- ***;
  m200=min(m200,avmqv);         *** m200 from scen. x004y cannot exceed the final MSA balanced volau **;
  avmqv=max(avmqv-m200,0);      *** now ony short haul ***;
  h200=min(h200,avhqv);         *** h200 from scen. x004y cannot exceed the final MSA balanced volau **;
  avhqv=max(avhqv-h200,0);      *** now ony short haul ***;


 *** -- CONVERT FROM VEHICLE EQUIVALENTS TO VEHICLES -- ***;
  auveh=max(avauv,0);
  bpveh=max(avbqv,0);
  ldveh=max(avlqv,0);
  mdshveh=max(avmqv/2,0);
  mdlhveh=max(m200/2,0);
  hdshveh=max(avhqv/3,0);
  hdlhveh=max(h200/3,0);
  vubus=max(busveq/3,0);

 *** -- VMT (for verification purposes) -- ***;
  auvehmi=auveh*miles;
  bpvehmi=bpveh*miles;
  ldvehmi=ldveh*miles;
  mdshvehmi=mdshveh*miles;
  mdlhvehmi=mdlhveh*miles;
  hdshvehmi=hdshveh*miles;
  hdlhvehmi=hdlhveh*miles;
  vubusmi=vubus*miles;


  if period=1 then hours=5;
  else if period=2 or period=4 then hours=1;
  else if period=5 then hours=4;
  else hours=2;

  veh=sum(auveh,bpveh,ldveh,mdshveh,mdlhveh,hdshveh,hdlhveh,vubus);   **total vehicles;


 *** -- ADJUST ARTERIAL SPEEDS -- ***;
  v=sum(avauv,avbqv,avlqv,avmqv,m200,avhqv,h200);
  c=emcap*lanes*hours;
  if ftime=0 then fmph=0; else fmph=(miles/(ftime/60));
  if timau=0 then mph=0; else mph=(miles/(timau/60));
  if vdf=1 then mph= fmph*(1/((log(fmph) * 0.249) + 0.153*(v/(c*0.75))**3.98));


 *** -- VHT (the metric MOVES wants) -- ***;
  if mph=0 then do;
    auvehhr=0; bpvehhr=0; ldvehhr=0;
    mdshvehhr=0; mdlhvehhr=0; hdshvehhr=0;
    hdlhvehhr=0; vubushr=0;
  end;
  else do;
    auvehhr=miles/mph*auveh; bpvehhr=miles/mph*bpveh;
    ldvehhr=miles/mph*ldveh; vubushr=miles/mph*vubus;
    mdshvehhr=miles/mph*mdshveh; mdlhvehhr=miles/mph*mdlhveh;
    hdshvehhr=miles/mph*hdshveh; hdlhvehhr=miles/mph*hdlhveh;
  end;

 *** -- PREPARE SPEED BINS -- ***;
  if            mph< 2.5 then avgSpeedBinID=1;
  else if  2.5<=mph< 7.5 then avgSpeedBinID=2;
  else if  7.5<=mph<12.5 then avgSpeedBinID=3;
  else if 12.5<=mph<17.5 then avgSpeedBinID=4;
  else if 17.5<=mph<22.5 then avgSpeedBinID=5;
  else if 22.5<=mph<27.5 then avgSpeedBinID=6;
  else if 27.5<=mph<32.5 then avgSpeedBinID=7;
  else if 32.5<=mph<37.5 then avgSpeedBinID=8;
  else if 37.5<=mph<42.5 then avgSpeedBinID=9;
  else if 42.5<=mph<47.5 then avgSpeedBinID=10;
  else if 47.5<=mph<52.5 then avgSpeedBinID=11;
  else if 52.5<=mph<57.5 then avgSpeedBinID=12;
  else if 57.5<=mph<62.5 then avgSpeedBinID=13;
  else if 62.5<=mph<67.5 then avgSpeedBinID=14;
  else if 67.5<=mph<72.5 then avgSpeedBinID=15;
  else avgSpeedBinID=16;

 *** -- PREPARE FACILITY TYPES -- ***;
  if vdf=1 or vdf=6 then do;
     if areatype<9 then roadTypeID=5;   *** urban arterial;
     else roadTypeID=3;                 *** rural arterial;
  end;
  else do;
    if areatype<9 then roadTypeID=4;    *** urban freeway;
    else roadTypeID=2;                  *** rural freeway;
  end;



data sums; set a;
  allvmt=sum(auvehmi,bpvehmi,ldvehmi,mdshvehmi,mdlhvehmi,hdshvehmi,hdlhvehmi,vubusmi);
  allvht=sum(auvehhr,bpvehhr,ldvehhr,mdshvehhr,mdlhvehhr,hdshvehhr,hdlhvehhr,vubushr);
 proc summary nway data=sums; class im; var allvmt allvht; output out=j1 sum(allvmt)=All_VMT sum(allvht)=All_VHT;
  proc print; format All_VMT All_VHT comma15.2; var im All_VMT All_VHT; sum All_VMT All_VHT; title "VMT and VHT Totals - First Stage";

***;
 proc summary nway data=a; class im roadTypeID period; var vubus; output out=junk sum=;
data junk(drop=_type_ _freq_); set junk(where=(vubus=0));
 proc print; title1 " "; title2 "- +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++ -";
   title3 "Intermediate Bus Data: IM-roadTypeID-Period Categories without Bus Activity - These Will Be Adjusted";
***;


 proc summary nway data=a; var auvehmi bpvehmi ldvehmi mdshvehmi mdlhvehmi hdshvehmi hdlhvehmi vubusmi auvehhr bpvehhr ldvehhr
   mdshvehhr mdlhvehhr hdshvehhr hdlhvehhr vubushr; class im roadTypeID period avgSpeedBinID; id hours; output out=b1 sum=;


  *** VMT Verification ***;
   proc summary nway data=b1; class im; var auvehmi bpvehmi ldvehmi mdshvehmi mdlhvehmi hdshvehmi hdlhvehmi vubusmi auvehhr bpvehhr ldvehhr
     mdshvehhr mdlhvehhr hdshvehhr hdlhvehhr vubushr; output out=junk sum=;
    proc print data=junk; format auvehmi bpvehmi ldvehmi mdshvehmi mdlhvehmi hdshvehmi hdlhvehmi vubusmi auvehhr bpvehhr ldvehhr
       mdshvehhr mdlhvehhr hdshvehhr hdlhvehhr vubushr comma15.2;
       var im auvehmi bpvehmi ldvehmi mdshvehmi mdlhvehmi hdshvehmi hdlhvehmi vubusmi auvehhr bpvehhr ldvehhr
          mdshvehhr mdlhvehhr hdshvehhr hdlhvehhr vubushr;
       sum auvehmi bpvehmi ldvehmi mdshvehmi mdlhvehmi hdshvehmi hdlhvehmi vubusmi auvehhr bpvehhr ldvehhr
          mdshvehhr mdlhvehhr hdshvehhr hdlhvehhr vubushr;
       title1 " "; title2 "- +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++ -"; title3 "&project &run Totals Before";


 *** -- DISAGGREGATE INTO HOURLY DATA -- ***;
data b1(drop=_type_ _freq_); set b1;

  if period=1 then hours=10;  *** set to actual number of temporal hours, other periods OK;

  auvehmi=auvehmi/hours; bpvehmi=bpvehmi/hours; ldvehmi=ldvehmi/hours; mdshvehmi=mdshvehmi/hours; mdlhvehmi=mdlhvehmi/hours;
  hdshvehmi=hdshvehmi/hours; hdlhvehmi=hdlhvehmi/hours; vubusmi=vubusmi/hours;
  auvehhr=auvehhr/hours; bpvehhr=bpvehhr/hours; ldvehhr=ldvehhr/hours; mdshvehhr=mdshvehhr/hours; mdlhvehhr=mdlhvehhr/hours;
  hdshvehhr=hdshvehhr/hours; hdlhvehhr=hdlhvehhr/hours; vubushr=vubushr/hours;

  if period=1 then do;
    do i=1 to 10; hr=i+20; output; end;
  end;
  if period=2 then do; hr=7; output; end;
  if period=3 then do;
    do i=1 to 2; hr=i+7; output; end;
  end;
  if period=4 then do; hr=10; output; end;
  if period=5 then do;
    do i=1 to 4; hr=i+10; output; end;
  end;
  if period=6 then do;
    do i=1 to 2; hr=i+14; output; end;
  end;
  if period=7 then do;
    do i=1 to 2; hr=i+16; output; end;
  end;
  if period=8 then do;
    do i=1 to 2; hr=i+18; output; end;
  end;

data b1; set b1;
  if hr>24 then hr=hr-24;  *** reset first 6 hours of the day;
  hourDayID=hr*10+5;        *** 5 indicates a weekday;

*SEPARATE INTO VEHICLE CLASSES & RECOMBINE;
data b2(keep=roadTypeID period avgSpeedBinID vmt vht hr hourDayID sourceTypeID im); set b1; vmt=auvehmi; vht=auvehhr; sourceTypeID=21;   ** passenger car;
data b3(keep=roadTypeID period avgSpeedBinID vmt vht hr hourDayID sourceTypeID im); set b1; vmt=bpvehmi; vht=bpvehhr; sourceTypeID=31;   ** passenger truck;
data b4(keep=roadTypeID period avgSpeedBinID vmt vht hr hourDayID sourceTypeID im); set b1; vmt=ldvehmi; vht=ldvehhr; sourceTypeID=32;   ** light commercial truck;
data b5(keep=roadTypeID period avgSpeedBinID vmt vht hr hourDayID sourceTypeID im); set b1; vmt=mdshvehmi; vht=mdshvehhr; sourceTypeID=52;  ** SU short haul truck;
data b6(keep=roadTypeID period avgSpeedBinID vmt vht hr hourDayID sourceTypeID im); set b1; vmt=mdlhvehmi; vht=mdlhvehhr; sourceTypeID=53;  ** SU long haul truck;
data b7(keep=roadTypeID period avgSpeedBinID vmt vht hr hourDayID sourceTypeID im); set b1; vmt=hdshvehmi; vht=hdshvehhr; sourceTypeID=61;  ** MU short haul truck;
data b8(keep=roadTypeID period avgSpeedBinID vmt vht hr hourDayID sourceTypeID im); set b1; vmt=hdlhvehmi; vht=hdlhvehhr; sourceTypeID=62;  ** MU long haul truck;
data b9(keep=roadTypeID period avgSpeedBinID vmt vht hr hourDayID sourceTypeID im); set b1; vmt=vubusmi; vht=vubushr; sourceTypeID=42;   ** transit bus;
data b10; set b9; sourceTypeID=41;                 *** apply transit bus distribution to intercity bus **;
data b11; set b9; sourceTypeID=43;                 *** apply transit bus distribution to school bus **;
data b12; set b2; sourceTypeID=11;                 *** apply auto distribution to motorcycles **;
data b13; set b5; sourceTypeID=51;                 *** apply single unit short-haul distribution to refuse trucks **;
data b14; set b6; sourceTypeID=54;                 *** apply single unit long-haul distribution to motor homes **;

data b; set b2-b14; proc sort; by im sourceTypeID roadTypeID hourDayID avgSpeedBinID;


  *** CREATE TEMPLATE WITH ALL COMBINATIONS ***;
  proc summary nway data=b; class sourceTypeID; output out=veh;
  proc summary nway data=b; class roadTypeID; output out=road;
  proc summary nway data=b; class hourDayID; output out=hrday;
  /*proc summary nway data=b; class avgSpeedBinID; output out=speed;*/ proc import datafile="..\data\moves_avgSpeedBinID.csv" out=speed dbms=csv replace; getnames=yes; run;
  proc summary nway data=b; class im; output out=imcat;

proc sql noprint;
  create table template as
    select veh.sourceTypeID,
       road.roadTypeID,
       hrday.hourDayID,
       speed.avgSpeedBinID,
       imcat.im
    from veh,road,hrday,speed,imcat;
  proc sort data=template; by im sourceTypeID roadTypeID hourDayID avgSpeedBinID;


data b; merge template b; by im sourceTypeID roadTypeID hourDayID avgSpeedBinID;
 vmt=max(0,vmt); vht=max(0,vht);
  proc format;
   value ft
     1="Off-Network"
     2="Rural Restricted Access"
     3="Rural Unrestricted Access"
     4="Urban Restricted Access"
     5="Urban Unrestricted Access";
   value cl
     11="Motorcycle"
     21="Passenger Car"
     31="Passenger Truck"
     32="Light Commercial Truck"
     41="Intercity Bus"
     42="Transit Bus"
     43="School Bus"
     51="Refuse Truck"
     52="Single-Unit Short-Haul Truck"
     53="Single-Unit Long-Haul Truck"
     54="Motor Home"
     61="Combination Short-Haul Truck"
     62="Combination Long-Haul Truck";
   value spdbn
     1="speed < 2.5mph"
     2="2.5mph <= speed < 7.5mph"
     3="7.5mph <= speed < 12.5mph"
     4="12.5mph <= speed < 17.5mph"
     5="17.5mph <= speed <22.5mph"
     6="22.5mph <= speed < 27.5mph"
     7="27.5mph <= speed < 32.5mph"
     8="32.5mph <= speed < 37.5mph"
     9="37.5mph <= speed < 42.5mph"
    10="42.5mph <= speed < 47.5mph"
    11="47.5mph <= speed < 52.5mph"
    12="52.5mph <= speed < 57.5mph"
    13="57.5mph <= speed < 62.5mph"
    14="62.5mph <= speed < 67.5mph"
    15="67.5mph <= speed < 72.5mph"
    16="72.5mph <= speed";
   value hr
     1="Hour beginning at 12:00 midnight"
     2="Hour beginning at 1:00 AM"
     3="Hour beginning at 2:00 AM"
     4="Hour beginning at 3:00 AM"
     5="Hour beginning at 4:00 AM"
     6="Hour beginning at 5:00 AM"
     7="Hour beginning at 6:00 AM"
     8="Hour beginning at 7:00 AM"
     9="Hour beginning at 8:00 AM"
    10="Hour beginning at 9:00 AM"
    11="Hour beginning at 10:00 AM"
    12="Hour beginning at 11:00 AM"
    13="Hour beginning at 12:00 Noon"
    14="Hour beginning at 1:00 PM"
    15="Hour beginning at 2:00 PM"
    16="Hour beginning at 3:00 PM"
    17="Hour beginning at 4:00 PM"
    18="Hour beginning at 5:00 PM"
    19="Hour beginning at 6:00 PM"
    20="Hour beginning at 7:00 PM"
    21="Hour beginning at 8:00 PM"
    22="Hour beginning at 9:00 PM"
    23="Hour beginning at 10:00 PM"
    24="Hour beginning at 11:00 PM";


  ****;
   proc summary nway data=b; var vmt vht; class im sourceTypeID; output out=junk sum=;
      proc print data=junk; var im sourceTypeID vmt vht; format vmt vht comma15.2; sum vmt vht;
        title1 " "; title2 "- +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++ -";
        title3 "&project &run Totals After";
  ****;


*~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~*;
  * -- INTERMEDIATE OUTPUT -- *;
*~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~*;
data out; set b(where=(sourceTypeID not in (11,41,43,51,54)));     *** only include actual modeled vehicle types- for QC verification ***;

data outIM(keep=vht vmt sourceTypeID roadTypeID hourDayID avgSpeedBinID);
  retain sourceTypeID roadTypeID hourDayID avgSpeedBinID vht vmt; set out(where=(im=1));
proc export data=outIM file="..\data\MOVES_&project._scen&run._IM.xlsx" dbms=xlsx replace; sheet="initial_model_output";

data outnoIM(keep=vht vmt sourceTypeID roadTypeID hourDayID avgSpeedBinID);
  retain sourceTypeID roadTypeID hourDayID avgSpeedBinID vht vmt; set out(where=(im=0));
proc export data=outnoIM file="..\data\MOVES_&project._scen&run._nonIM.xlsx" dbms=xlsx replace; sheet="initial_model_output";



*~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~*;
  * -- SPEED DISTRIBUTION TAB -- *;
*~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~*;
 *** -- CALCULATE VHT SHARE BY sourceTypeID-roadTypeID-hourDayID -- ***;
proc summary nway data=b; class im sourceTypeID roadTypeID hourDayID; var vht; output out=sumvht sum=allvht;
data share(drop=_type_ _freq_); merge b sumvht; by im sourceTypeID roadTypeID hourDayID;


 * * = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = * *;
  *** -- NOTE: USE SURROGATES TO REPLACE MISSING VALUES, IF NECESSARY -- ***;
    ** ## - Bus part1: use roadTypeID 4 to replace missing values for roadTypeID 2 for sourceTypeID 41,42,43 for IM area ##;
data fb1; set share(where=(sourceTypeID=42 & roadTypeID=4 & im=1));
      roadTypeID=2; output;
      sourceTypeID=41; output;
      sourceTypeID=43; output;

    ** ## - Bus part2: use sourceTypeID 41,42,43 for IM area to replace missing values for non-IM area ##;
data fb2; set fb1 share(where=(sourceTypeID in (41,42,43) & im=1));
      im=0;

    ** ## - SU Long-haul truck part1: use sourceTypeID 52 to replace missing values for sourceTypeID 53,54 for IM area ##;
data fb3; set share(where=(sourceTypeID=52 & im=1));
      sourceTypeID=53; output;
      sourceTypeID=54; output;

    ** ## - SU Long-haul truck part2: use sourceTypeID 52,53,54 for IM area to replace missing values for non-IM area ##;
data fb4; set fb3 share(where=(sourceTypeID=52 & im=1));
      im=0;

    ** ## - MU Long-haul truck part1: use sourceTypeID 61 to replace missing values for sourceTypeID 62 for IM area ##;
data fb5; set share(where=(sourceTypeID=61 & im=1));
      sourceTypeID=62;

    ** ## - MU Long-haul truck part2: use sourceTypeID 61,62 for IM area to replace missing values for non-IM area ##;
data fb6; set fb5 share(where=(sourceTypeID=61 & im=1));
      im=0;

data fallback(drop=period hr vmt); set fb1-fb6;
  rename vht=vht2 allvht=allvht2;
  proc sort nodupkey; by im sourceTypeID roadTypeID hourDayID avgSpeedBinID;
 * * = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = * *;

data share; merge share fallback; by im sourceTypeID roadTypeID hourDayID avgSpeedBinID;
  if allvht=0 & allvht2 then do;             *** -- substitution only occurs if no VHT for entire category -- ***;
     vht=vht2; allvht=allvht2;
  end;
  avgSpeedFraction=round(vht/allvht,0.000001);


data outIM(keep=sourceTypeID roadTypeID hourDayID avgSpeedBinID avgSpeedFraction);
   retain sourceTypeID roadTypeID hourDayID avgSpeedBinID avgSpeedFraction; set share(where=(im=1));
proc export data=outIM outfile="..\data\MOVES_&project._scen&run._IM.xlsx" dbms=xlsx replace; sheet="AvgSpeedDistribution";

data outnoIM(keep=sourceTypeID roadTypeID hourDayID avgSpeedBinID avgSpeedFraction);
   retain sourceTypeID roadTypeID hourDayID avgSpeedBinID avgSpeedFraction; set share(where=(im=0));
proc export data=outnoIM outfile="..\data\MOVES_&project._scen&run._nonIM.xlsx" dbms=xlsx replace; sheet="AvgSpeedDistribution";


*** == Verify Results == ***;
proc summary nway data=share; class im sourceTypeID roadTypeID hourDayID; var avgSpeedFraction; output out=review sum=;
data review(drop=_type_ _freq_); set review(where=(avgSpeedFraction<0.998 or avgSpeedFraction>1.002));
  proc print; title "===================="; title2 "ERROR - IM-sourceTypeID-roadTypeID-hourDayID Shares Do Not Sum To 1.00";
        title3 "====================";


/*
*~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~*;;
  * -- SPEED DISTRIBUTION TAB [WEEKEND] -- *;
*~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~*;
** ## -- for now just use weekday values -- ## **;

data share1; set share;
  hourDayID=hourDayID-3;   *** reset for weekend values ***;

proc export data=share1 outfile="..\data\MOVES_&project._scen&run..xlsx" dbms=xlsx replace; sheet="AvgSpeedDistributionWeekend";
*/


*~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~*;;
  * -- ROAD TYPE DISTRIBUTION TAB -- *;
*~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~*;
proc summary nway data=b; class im sourceTypeID roadTypeID; var vmt; output out=roadtype sum=;
proc summary nway data=b; class im sourceTypeID; var vmt; output out=roadtype2 sum=sourceVMT;

data roadtype; merge roadtype roadtype2; by im sourceTypeID;

 * * = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = * *;
  *** -- NOTE: USE SURROGATES TO REPLACE MISSING VALUES, IF NECESSARY -- ***;
    ** ## - Bus part1: use roadTypeID 4 to replace missing values for roadTypeID 2 for sourceTypeID 41,42,43 for IM area ##;
data fb1; set roadtype(where=(sourceTypeID=42 & roadTypeID=4 & im=1));
      roadTypeID=2; output;
      sourceTypeID=41; output;
      sourceTypeID=43; output;

    ** ## - Bus part2: use sourceTypeID 41,42,43 for IM area to replace missing values for non-IM area ##;
data fb2; set fb1 roadtype(where=(sourceTypeID in (41,42,43) & im=1));
      im=0;

    ** ## - SU Long-haul truck part1: use sourceTypeID 52 to replace missing values for sourceTypeID 53,54 for IM area ##;
data fb3; set roadtype(where=(sourceTypeID=52 & im=1));
      sourceTypeID=53; output;
      sourceTypeID=54; output;

    ** ## - SU Long-haul truck part2: use sourceTypeID 52,53,54 for IM area to replace missing values for non-IM area ##;
data fb4; set fb3 roadtype(where=(sourceTypeID=52 & im=1));
      im=0;

    ** ## - MU Long-haul truck part1: use sourceTypeID 61 to replace missing values for sourceTypeID 62 for IM area ##;
data fb5; set roadtype(where=(sourceTypeID=61 & im=1));
      sourceTypeID=62;

    ** ## - MU Long-haul truck part2: use sourceTypeID 61,62 for IM area to replace missing values for non-IM area ##;
data fb6; set fb5 roadtype(where=(sourceTypeID=61 & im=1));
      im=0;

data fallback(drop=_type_ _freq_); set fb1-fb6;
  rename vmt=vmt2 sourceVMT=sourceVMT2;
  proc sort nodupkey; by im sourceTypeID roadTypeID;
 * * = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = * *;

data roadtype(drop=vmt sourceVMT vmt2 sourceVMT2); merge roadtype fallback; by im sourceTypeID roadTypeID;
  if sourceVMT=0 & sourceVMT2 then do;       *** -- substitution only occurs if no VMT for entire category -- ***;
     vmt=vmt2; sourceVMT=sourceVMT2;
  end;
  sourceVMT=max(sourceVMT,0.000001);                                           *** prevent division by zero ***;
  roadTypeVMTFraction=round(vmt/sourceVMT,0.000001);
  output;
  /* *** === Remove this as of 07-08-2016 == ***
  if roadTypeID=2 then do; roadTypeID=1; roadTypeVMTFraction=0; output; end;   *** add blank observation for Off Network category ***; */
   proc sort; by sourceTypeID roadTypeID;
   /* proc print; title "Fallback Road Type Distribution"; */


data outIM(keep=sourceTypeID roadTypeID roadTypeVMTFraction);
   retain sourceTypeID roadTypeID roadTypeVMTFraction; set roadtype(where=(im=1));
proc export data=outIM outfile="..\data\MOVES_&project._scen&run._IM.xlsx" dbms=xlsx replace; sheet="RoadTypeDistribution";

data outnoIM(keep=sourceTypeID roadTypeID roadTypeVMTFraction);
   retain sourceTypeID roadTypeID roadTypeVMTFraction; set roadtype(where=(im=0));
proc export data=outnoIM outfile="..\data\MOVES_&project._scen&run._nonIM.xlsx" dbms=xlsx replace; sheet="RoadTypeDistribution";


*** == Verify Results == ***;
proc summary nway data=roadtype; class im sourceTypeID; var roadTypeVMTFraction; output out=review sum=;
data review(drop=_type_ _freq_); set review(where=(roadTypeVMTFraction<0.998 or roadTypeVMTFraction>1.002));
  proc print; title "===================="; title2 "ERROR - sourceTypeID roadTypeVMTFraction Shares Do Not Sum To 1.00";
          title3 "====================";


*~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~*;
  * -- RAMP FRACTION TAB -- *;
*~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~*;
 *** -- CALCULATE SHARE OF RAMP VHT DIVIDED BY FREEWAY VMT -- ***;
data rmp; set a(where=(roadTypeID in (2,4)));
   fwyvht=sum(auvehhr,bpvehhr,ldvehhr,mdshvehhr,mdlhvehhr,hdshvehhr,hdlhvehhr,vubushr);
   fwyvmt=sum(auvehmi,bpvehmi,ldvehmi,mdshvehmi,mdlhvehmi,hdshvehmi,hdlhvehmi,vubusmi);
   if isramp then do; rampvht=fwyvht; rampvmt=fwyvmt; end;
   else do; rampvht=0; rampvmt=0; end;

 proc summary nway; class im roadTypeID; var fwyvht rampvht fwyvmt rampvmt; output out=ramp sum=;
data ramp; set ramp;
   rampFraction=round(rampvht/fwyvht,0.000001); vmtFraction=round(rampvmt/fwyvmt,0.000001);
    proc print; title "Ramp Fraction Results";

data outIM(keep=roadTypeID rampFraction); retain roadTypeID rampFraction; set ramp(where=(im=1));
proc export data=outIM outfile="..\data\MOVES_&project._scen&run._IM.xlsx" dbms=xlsx replace; sheet="RampFraction";

data outnoIM(keep=roadTypeID rampFraction); retain roadTypeID rampFraction; set ramp(where=(im=0));
proc export data=outnoIM outfile="..\data\MOVES_&project._scen&run._nonIM.xlsx" dbms=xlsx replace; sheet="RampFraction";


*~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~*;
  * -- HOURLY VMT FRACTION TAB -- *;
*~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~*;
 *** -- CALCULATE HOURLY SHARE OF VMT BY sourceTypeID-roadTypeID-dayID-hourID (may not be needed) -- ***;

  *** CREATE TEMPLATE WITH ALL COMBINATIONS ***;
data road; set road;
  output;
  if roadTypeID=2 then do; roadTypeID=1; output; end;             ** add Off-Network type;
data hrday; set hrday; dayID=5; hourID=(hourDayID-5)/10;

proc sql noprint;
  create table template2 as
    select veh.sourceTypeID,
       road.roadTypeID,
       hrday.dayID, hourID, imcat.im
    from veh,road,hrday,imcat;
  proc sort data=template2; by im sourceTypeID roadTypeID hourID;

data vmt; set b; hourID=(hourDayID-5)/10;
  proc summary nway; class im sourceTypeID roadTypeID hourID; var vmt; output out=hourvmt sum=;
  proc summary nway data=hourvmt; class im sourceTypeID roadTypeID; var vmt; output out=sumvmt sum=allvmt;

data vmtshare; merge hourvmt sumvmt; by im sourceTypeID roadTypeID;
  proc sort; by im sourceTypeID roadTypeID hourID;

 * * = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = * *;
  *** -- NOTE: USE SURROGATES TO REPLACE MISSING VALUES, IF NECESSARY -- ***;
    ** ## - Bus part1: use sourceTypeID 42 to replace missing values for sourceTypeID 41,43 for IM area ##;
data fb1; set vmtshare(where=(sourceTypeID=42 & im=1));
      sourceTypeID=41; output;
      sourceTypeID=43; output;

    ** ## - Bus part2: use sourceTypeID 41,42,43 for IM area to replace missing values for non-IM area ##;
data fb2; set fb1 vmtshare(where=(sourceTypeID in (41,42,43) & im=1 & allvmt>0));
      im=0;

    ** ## - SU Long-haul truck part1: use sourceTypeID 52 to replace missing values for sourceTypeID 53,54 for IM area ##;
data fb3; set vmtshare(where=(sourceTypeID=52 & im=1));
      sourceTypeID=53; output;
      sourceTypeID=54; output;

    ** ## - SU Long-haul truck part2: use sourceTypeID 52,53,54 for IM area to replace missing values for non-IM area ##;
data fb4; set fb3 vmtshare(where=(sourceTypeID in (52,53,54) & im=1 & allvmt>0));
      im=0;

    ** ## - MU Long-haul truck part1: use sourceTypeID 61 to replace missing values for sourceTypeID 62 for IM area ##;
data fb5; set vmtshare(where=(sourceTypeID=61 & im=1));
      sourceTypeID=62;

    ** ## - MU Long-haul truck part2: use sourceTypeID 61,62 for IM area to replace missing values for non-IM area ##;
data fb6; set fb5 vmtshare(where=(sourceTypeID in (61,62) & im=1 & allvmt>0));
      im=0;

data fallback(drop=_type_ _freq_); set fb1-fb6;
  rename vmt=vmt2 allvmt=allvmt2;
  proc sort nodupkey; by im sourceTypeID roadTypeID hourID;
 * * = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = * *;

data vmtshare; merge vmtshare fallback; by im sourceTypeID roadTypeID hourID;

data vmtshare;
        set vmtshare;
        hourVMTFraction1=vmt/max(allvmt,0.000001);      *** calculate hourvmtfraction based on original data ***;
run;

data vmtshare;
        set vmtshare;
        if vmt2 and allvmt2 then hourVMTFraction2=vmt2/allvmt2; ** calculate hourvmtfraction based on fallback data ***;
run;

** for source types 53 and 54, if there is any data ** ;
** then use both the non-zero vmt and the fallback data to arrive at the hourVMTFraction  **;

data truckpart; set vmtshare(where=(sourceTypeID in (53,54) & vmt>0));
run;

** get count of how many vmt values there are for each im/sourcetype/roadtype combo **;
proc summary nway;
        class im sourceTypeID roadtypeID;
        var vmt;
        output out=vmtcount N=vmtcount1;
run;

proc sql;
        create table vmtweight as
        select A.*, B.*
        FROM vmtshare A LEFT JOIN vmtcount B
        on A.im = B.im
        and A.sourceTypeID = B.sourceTypeID
        and A.roadTypeID = B.roadTypeID;
quit;
run;

data vmtweight2;
        set vmtweight;
        if sourceTypeID in (53,54) and allvmt>0 then do;
                if vmt=0 then hourVMTFractionpre=hourVMTFraction2;                               *** use fallback vmtfraction for 0 vmt hours ***;
                else if vmt>0 then hourVMTFractionpre=(((vmtcount1/24)*hourVMTFraction1)+hourVMTFraction2)/((vmtcount1+24)/24);
 *** use average of the original and fallback vmtfraction otherwise ***;
 *** original data is weighted by number of hours with data ***;
        end;
run;

proc summary nway;
        class im sourceTypeID roadtypeID;
        var hourVMTFractionpre;
        output out=vmtpre sum=vmtpresum;
run;

data vmtshare; merge vmtweight2 vmtpre; by im sourceTypeID roadtypeID;
        proc sort; by im sourceTypeID roadTypeID hourID;
run;


data vmtshare;
  set vmtshare;
 if allvmt=0 & allvmt2 then do;             *** -- substitution only occurs if no VMT for entire category -- ***;
     vmt=vmt2; allvmt=allvmt2;
  end;
  allvmt=max(allvmt,0.000001);                                         *** prevent division by zero ***;
  hourVMTFraction=round(vmt/allvmt,0.000001);
  if sourceTypeID in (53,54) and vmtpresum>0 then hourVMTFraction=round(hourVMTFractionpre/vmtpresum, 0.000001);
  drop vmtpresum hourVMTFraction1 hourVMTFraction2 hourVMTFractionpre vmtcount1;
  output;
  if roadTypeID=5 then do; roadTypeID=1; output; end;             ** apply urban arterial distribution to Off-Network type **;
    proc sort; by im sourceTypeID roadTypeID hourID;


proc print; title "Final VMT Fraction";
run;


data vmtshare; merge template2 vmtshare; by im sourceTypeID roadTypeID hourID;

data outIM(keep=sourceTypeID roadTypeID dayID hourID hourVMTFraction);
   retain sourceTypeID roadTypeID dayID hourID hourVMTFraction; set vmtshare(where=(im=1));
proc export data=outIM outfile="..\data\MOVES_&project._scen&run._IM.xlsx" dbms=xlsx replace; sheet="hourVMTFraction";

data outnoIM(keep=sourceTypeID roadTypeID dayID hourID hourVMTFraction);
   retain sourceTypeID roadTypeID dayID hourID hourVMTFraction; set vmtshare(where=(im=0));
proc export data=outnoIM outfile="..\data\MOVES_&project._scen&run._nonIM.xlsx" dbms=xlsx replace; sheet="hourVMTFraction";


*** == Verify Results == ***;
proc summary nway data=vmtshare; class im sourceTypeID roadTypeID dayID; var hourVMTFraction; output out=review sum=;
data review(drop=_type_ _freq_); set review(where=(hourVMTFraction<.998 or hourVMTFraction>1.002));
  proc print; title "===================="; title2 "ERROR - IM-sourceTypeID-roadTypeID-dayID hourVMTFraction Shares Do Not Sum To 1.00";
         title3 "====================";


/*
*~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~*;
  * -- HOURLY VMT FRACTION TAB [WEEKEND] -- *;
*~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~*;
** ## -- for now just use weekday values -- ## **;

data vmtshare; set vmtshare;
  dayID=2;        *** reset for weekend values ***;

proc export data=vmtshare outfile="..\data\MOVES_&project._scen&run..xlsx" dbms=xlsx replace; sheet="hourVMTFractionWeekend";
*/


*~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~*;
  * -- VMT BY ROAD TYPE AND HPMS VEHICLE TYPE TAB -- *;
*~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~*;
 *** -- CALCULATE TOTAL VMT BY HPMS VEHICLE TYPE -- ***;
data hpms; set b(where=(sourceTypeID in (21,31,32,42,52,53,61,62)));        *** modeled vehicle types only ***;
  if sourceTypeID=21 then HPMSVtypeID=20;
  else if 31<=sourceTypeID<=32 then HPMSVtypeID=30;
  else if sourceTypeID<=42 then HPMSVtypeID=40;                    *** transit bus vmt only ***;
  else if 52<=sourceTypeID<=53 then HPMSVtypeID=50;
  else if 61<=sourceTypeID<=62 then HPMSVtypeID=60;

proc summary nway data=hpms; class im roadTypeID HPMSVtypeID; var vmt; output out=hpms1 sum=HPMSDailyVMT;

data outIM(keep=roadTypeID HPMSVtypeID yearID HPMSDailyVMT);
   retain roadTypeID HPMSVtypeID yearID HPMSDailyVMT; set hpms1(where=(im=1)); yearID=&year;
proc export data=outIM outfile="..\data\MOVES_&project._scen&run._IM.xlsx" dbms=xlsx replace; sheet="HPMSDailyVMT";

data outnoIM(keep=roadTypeID HPMSVtypeID yearID HPMSDailyVMT);
   retain roadTypeID HPMSVtypeID yearID HPMSDailyVMT; set hpms1(where=(im=0)); yearID=&year;
proc export data=outnoIM outfile="..\data\MOVES_&project._scen&run._nonIM.xlsx" dbms=xlsx replace; sheet="HPMSDailyVMT";


proc summary nway data=hpms1; class im; var HPMSDailyVMT; output out=hpms2 sum=;
proc print data=hpms2; format HPMSDailyVMT comma15.2; var im HPMSDailyVMT; sum HPMSDailyVMT; title1 " ";
   title2 "- +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++ -";
   title3 "HPMS Daily VMT TOTAL - Final Stage";


*** == Verify Results == ***;
data hpms1; set hpms1;
  if im=0 then HPMSDAILYVMT_NonIM=HPMSDAILYVMT; else HPMSDAILYVMT_NonIM=0;
  if im=1 then HPMSDAILYVMT_IM=HPMSDAILYVMT; else HPMSDAILYVMT_IM=0;
  yearID=&year;
 proc summary nway data=hpms1; class roadTypeID HPMSVtypeID yearID; var HPMSDAILYVMT_IM HPMSDAILYVMT_NonIM; output out=hpms2 sum=;

data hpms2(keep=roadTypeID HPMSVtypeID yearID HPMSDAILYVMT_IM HPMSDAILYVMT_NonIM HPMSDAILYVMT_TOTAL);
   retain roadTypeID HPMSVtypeID yearID HPMSDAILYVMT_IM HPMSDAILYVMT_NonIM HPMSDAILYVMT_TOTAL; set hpms2;
  HPMSDAILYVMT_NonIM=max(HPMSDAILYVMT_NonIM,0);
  HPMSDAILYVMT_IM=max(HPMSDAILYVMT_IM,0);
  HPMSDAILYVMT_TOTAL=HPMSDAILYVMT_NonIM+HPMSDAILYVMT_IM;
proc export data=hpms2 outfile="..\data\MOVES_&project._scen&run._nonIM.xlsx" dbms=xlsx replace; sheet="QC_Values_HPMSDailyVMT";

*** == Clean up .bak files == ***;
data _null_; command="if exist ..\data\*.bak (del ..\data\*.bak /Q)" ;
    call system(command);
run;
