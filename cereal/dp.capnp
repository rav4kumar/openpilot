using Cxx = import "./include/c++.capnp";
$Cxx.namespace("cereal");

using Java = import "./include/java.capnp";
$Java.package("ai.comma.openpilot.cereal");
$Java.outerClassname("dp");

@0xbfa7e645486440c7;

# dp.capnp: a home for deprecated structs

struct DragonConf {
  dpThermalStarted @0 :Bool;
  dpThermalOverheat @1 :Bool;
  dpAtl @2 :Bool;
  dpAutoShutdown @3 :Bool;
  dpAthenad @4 :Bool;
  dpUploader @5 :Bool;
  dpSteeringOnSignal @6 :Bool;
  dpSignalOffDelay @7 :UInt8;
  dpAssistedLcMinMph @8 :Float32;
  dpAutoLc @9 :Bool;
  dpAutoLcCont @10 :Bool;
  dpAutoLcMinMph @11 :Float32;
  dpAutoLcDelay @12 :Float32;
  dpSlowOnCurve @13 :Bool;
  dpAllowGas @14 :Bool;
  dpFollowingProfileCtrl @15 :Bool;
  dpFollowingProfile @16 :UInt8;
  dpAccelProfileCtrl @17 :Bool;
  dpAccelProfile @18 :UInt8;
  dpGearCheck @19 :Bool;
  dpSpeedCheck @20 :Bool;
  dpUiScreenOffReversing @21 :Bool;
  dpUiSpeed @22 :Bool;
  dpUiEvent @23 :Bool;
  dpUiMaxSpeed @24 :Bool;
  dpUiFace @25 :Bool;
  dpUiLane @26 :Bool;
  dpUiLead @27 :Bool;
  dpUiDev @28 :Bool;
  dpUiDevMini @29 :Bool;
  dpUiBlinker @30 :Bool;
  dpAppExtGps @31 :Bool;
  dpAppTomtom @32 :Bool;
  dpAppTomtomAuto @33 :Bool;
  dpAppTomtomManual @34 :Int8;
  dpAppMixplorer @35 :Bool;
  dpAppMixplorerManual @36 :Int8;
  dpCarDetected @37 :Text;
  dpToyotaLdw @38 :Bool;
  dpToyotaSng @39 :Bool;
  dpVwPanda @40 :Bool;
  dpVwTimebombAssist @41 :Bool;
  dpIpAddr @42 :Text;
  dpLocale @43 :Text;
  dpDebug @44 :Bool;
}