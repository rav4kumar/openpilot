using Cxx = import "./include/c++.capnp";
$Cxx.namespace("cereal");

using Java = import "./include/java.capnp";
$Java.package("ai.comma.openpilot.cereal");
$Java.outerClassname("dp");

@0xbfa7e645486440c7;

# dp.capnp: a home for deprecated structs

# dp
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
  dpAllowGas @13 :Bool;
  dpFollowingProfileCtrl @14 :Bool;
  dpFollowingProfile @15 :UInt8;
  dpAccelProfileCtrl @16 :Bool;
  dpAccelProfile @17 :UInt8;
  dpGearCheck @18 :Bool;
  dpSpeedCheck @19 :Bool;
  dpUiScreenOffReversing @20 :Bool;
  dpUiSpeed @21 :Bool;
  dpUiEvent @22 :Bool;
  dpUiMaxSpeed @23 :Bool;
  dpUiFace @24 :Bool;
  dpUiLane @25 :Bool;
  dpUiLead @26 :Bool;
  dpUiDev @27 :Bool;
  dpUiDevMini @28 :Bool;
  dpUiBlinker @29 :Bool;
  dpAppExtGps @30 :Bool;
  dpAppTomtom @31 :Bool;
  dpAppTomtomAuto @32 :Bool;
  dpAppTomtomManual @33 :Int8;
  dpAppMixplorer @34 :Bool;
  dpAppMixplorerManual @35 :Int8;
  dpCarDetected @36 :Text;
  dpToyotaLdw @37 :Bool;
  dpToyotaSng @38 :Bool;
  dpVwPanda @39 :Bool;
  dpVwTimebombAssist @40 :Bool;
  dpIpAddr @41 :Text;
  dpLocale @42 :Text;
  dpDebug @43 :Bool;
}
