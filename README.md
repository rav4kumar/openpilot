[![](https://i.imgur.com/xY2gdHv.png)](#)

Welcome to openpilot
======

[openpilot](http://github.com/commaai/openpilot) is an open source driving agent. Currently, it performs the functions of Adaptive Cruise Control (ACC) and Lane Keeping Assist System (LKAS) for selected Honda, Toyota, Acura, Lexus, Chevrolet, Hyundai, Kia. It's about on par with Tesla Autopilot and GM Super Cruise, and better than [all other manufacturers](http://www.thedrive.com/tech/5707/the-war-for-autonomous-driving-part-iii-us-vs-germany-vs-japan).

The openpilot codebase has been written to be concise and to enable rapid prototyping. We look forward to your contributions - improving real vehicle automation has never been easier.

Table of Contents
=======================

* [Community](#community)
* [Hardware](#hardware)
* [Supported Cars](#supported-cars)
* [Community Maintained Cars](#community-maintained-cars)
* [In Progress Cars](#in-progress-cars)
* [How can I add support for my car?](#how-can-i-add-support-for-my-car)
* [Directory structure](#directory-structure)
* [User Data / chffr Account / Crash Reporting](#user-data--chffr-account--crash-reporting)
* [Testing on PC](#testing-on-pc)
* [Contributing](#contributing)
* [Licensing](#licensing)

---

Community
------

openpilot is developed by [comma.ai](https://comma.ai/) and users like you.

We have a [Twitter you should follow](https://twitter.com/comma_ai).

Also, we have a several thousand people community on [Discord](https://discord.comma.ai).

<table>
  <tr>
    <td><a href="https://www.youtube.com/watch?v=ICOIin4p70w" title="YouTube" rel="noopener"><img src="https://i.imgur.com/gBTo7yB.png"></a></td>
    <td><a href="https://www.youtube.com/watch?v=1zCtj3ckGFo" title="YouTube" rel="noopener"><img src="https://i.imgur.com/gNhhcep.png"></a></td>
    <td><a href="https://www.youtube.com/watch?v=Qd2mjkBIRx0" title="YouTube" rel="noopener"><img src="https://i.imgur.com/tFnSexp.png"></a></td>
    <td><a href="https://www.youtube.com/watch?v=ju12vlBm59E" title="YouTube" rel="noopener"><img src="https://i.imgur.com/3BKiJVy.png"></a></td>
  </tr>
  <tr>
    <td><a href="https://www.youtube.com/watch?v=Z5VY5FzgNt4" title="YouTube" rel="noopener"><img src="https://i.imgur.com/3I9XOK2.png"></a></td>
    <td><a href="https://www.youtube.com/watch?v=blnhZC7OmMg" title="YouTube" rel="noopener"><img src="https://i.imgur.com/f9IgX6s.png"></a></td>
    <td><a href="https://www.youtube.com/watch?v=iRkz7FuJsA8" title="YouTube" rel="noopener"><img src="https://i.imgur.com/Vo5Zvmn.png"></a></td>
    <td><a href="https://www.youtube.com/watch?v=IHjEqAKDqjM" title="YouTube" rel="noopener"><img src="https://i.imgur.com/V9Zd81n.png"></a></td>
  </tr>
</table>

Hardware
------

At the moment openpilot supports the [EON Dashcam DevKit](https://comma.ai/shop/products/eon-dashcam-devkit). A [panda](https://shop.comma.ai/products/panda-obd-ii-dongle) and a [giraffe](https://comma.ai/shop/products/giraffe/) are recommended tools to interface the EON with the car. We'd like to support other platforms as well.

Install openpilot on a neo device by entering ``https://openpilot.comma.ai`` during NEOS setup.

Supported Cars
------

| Make                 | Model                    | Supported Package    | Lateral | Longitudinal   | No Accel Below   | No Steer Below | Giraffe           |
| ---------------------| -------------------------| ---------------------| --------| ---------------| -----------------| ---------------|-------------------|
| Acura                | ILX 2016-17              | AcuraWatch Plus      | Yes     | Yes            | 25mph<sup>1</sup>| 25mph          | Nidec             |
| Acura                | RDX 2018                 | AcuraWatch Plus      | Yes     | Yes            | 25mph<sup>1</sup>| 12mph          | Nidec             |
| Buick<sup>3</sup>    | Regal 2018               | Adaptive Cruise      | Yes     | Yes            | 0mph             | 7mph           | Custom<sup>7</sup>|
| Chevrolet<sup>3</sup>| Malibu 2017              | Adaptive Cruise      | Yes     | Yes            | 0mph             | 7mph           | Custom<sup>7</sup>|
| Chevrolet<sup>3</sup>| Volt 2017-18             | Adaptive Cruise      | Yes     | Yes            | 0mph             | 7mph           | Custom<sup>7</sup>|
| Cadillac<sup>3</sup> | ATS 2018                 | Adaptive Cruise      | Yes     | Yes            | 0mph             | 7mph           | Custom<sup>7</sup>|
| Chrysler             | Pacifica 2018            | Adaptive Cruise      | Yes     | Stock          | 0mph             | 9mph           | FCA               |
| Chrysler             | Pacifica Hybrid 2017-18  | Adaptive Cruise      | Yes     | Stock          | 0mph             | 9mph           | FCA               |
| Chrysler             | Pacifica Hybrid 2019     | Adaptive Cruise      | Yes     | Stock          | 0mph             | 39mph          | FCA               |
| GMC<sup>3</sup>      | Acadia Denali 2018       | Adaptive Cruise      | Yes     | Yes            | 0mph             | 7mph           | Custom<sup>7</sup>|
| Holden<sup>3</sup>   | Astra 2017               | Adaptive Cruise      | Yes     | Yes            | 0mph             | 7mph           | Custom<sup>7</sup>|
| Honda                | Accord 2018              | All                  | Yes     | Stock          | 0mph             | 3mph           | Bosch             |
| Honda                | Civic Sedan/Coupe 2016-18| Honda Sensing        | Yes     | Yes            | 0mph             | 12mph          | Nidec             |
| Honda                | Civic Sedan/Coupe 2019   | Honda Sensing        | Yes     | Stock          | 0mph             | 2mph           | Bosch             |
| Honda                | Civic Hatchback 2017-19  | Honda Sensing        | Yes     | Stock          | 0mph             | 12mph          | Bosch             |
| Honda                | CR-V 2015-16             | Touring              | Yes     | Yes            | 25mph<sup>1</sup>| 12mph          | Nidec             |
| Honda                | CR-V 2017-18             | Honda Sensing        | Yes     | Stock          | 0mph             | 12mph          | Bosch             |
| Honda                | CR-V Hybrid 2019         | All                  | Yes     | Stock          | 0mph             | 12mph          | Bosch             |
| Honda                | Odyssey 2017-19          | Honda Sensing        | Yes     | Yes            | 25mph<sup>1</sup>| 0mph           | Inverted Nidec    |
| Honda                | Pilot 2016-18            | Honda Sensing        | Yes     | Yes            | 25mph<sup>1</sup>| 12mph          | Nidec             |
| Honda                | Pilot 2019               | All                  | Yes     | Yes            | 25mph<sup>1</sup>| 12mph          | Inverted Nidec    |
| Honda                | Ridgeline 2017-19        | Honda Sensing        | Yes     | Yes            | 25mph<sup>1</sup>| 12mph          | Nidec             |
| Hyundai              | Santa Fe 2019            | All                  | Yes     | Stock          | 0mph             | 0mph           | Custom<sup>6</sup>|
| Hyundai              | Elantra 2017             | SCC + LKAS           | Yes     | Stock          | 19mph            | 34mph          | Custom<sup>6</sup>|
| Hyundai              | Genesis 2018             | All                  | Yes     | Stock          | 19mph            | 34mph          | Custom<sup>6</sup>|
| Jeep                 | Grand Cherokee 2017-18   | Adaptive Cruise      | Yes     | Stock          | 0mph             | 9mph           | FCA               |
| Jeep                 | Grand Cherokee 2019      | Adaptive Cruise      | Yes     | Stock          | 0mph             | 39mph          | FCA               |
| Kia                  | Optima 2019              | SCC + LKAS           | Yes     | Stock          | 0mph             | 0mph           | Custom<sup>6</sup>|
| Kia                  | Sorento 2018             | All                  | Yes     | Stock          | 0mph             | 0mph           | Custom<sup>6</sup>|
| Kia                  | Stinger 2018             | SCC + LKAS           | Yes     | Stock          | 0mph             | 0mph           | Custom<sup>6</sup>|
| Lexus                | RX Hybrid 2016-18        | All                  | Yes     | Yes<sup>2</sup>| 0mph             | 0mph           | Toyota            |
| Toyota               | Camry 2018<sup>4</sup>   | All                  | Yes     | Stock          | 0mph<sup>5</sup> | 0mph           | Toyota            |
| Toyota               | C-HR 2017-18<sup>4</sup> | All                  | Yes     | Stock          | 0mph             | 0mph           | Toyota            |
| Toyota               | Corolla 2017-18          | All                  | Yes     | Yes<sup>2</sup>| 20mph<sup>1</sup>| 0mph           | Toyota            |
| Toyota               | Highlander 2017-18       | All                  | Yes     | Yes<sup>2</sup>| 0mph             | 0mph           | Toyota            |
| Toyota               | Highlander Hybrid 2018   | All                  | Yes     | Yes<sup>2</sup>| 0mph             | 0mph           | Toyota            |
| Toyota               | Prius 2016               | TSS-P                | Yes     | Yes<sup>2</sup>| 0mph             | 0mph           | Toyota            |
| Toyota               | Prius 2017-18            | All                  | Yes     | Yes<sup>2</sup>| 0mph             | 0mph           | Toyota            |
| Toyota               | Prius Prime 2017-18      | All                  | Yes     | Yes<sup>2</sup>| 0mph             | 0mph           | Toyota            |
| Toyota               | Rav4 2016                | TSS-P                | Yes     | Yes<sup>2</sup>| 20mph<sup>1</sup>| 0mph           | Toyota            |
| Toyota               | Rav4 2017-18             | All                  | Yes     | Yes<sup>2</sup>| 20mph<sup>1</sup>| 0mph           | Toyota            |
| Toyota               | Rav4 Hybrid 2017-18      | All                  | Yes     | Yes<sup>2</sup>| 0mph             | 0mph           | Toyota            |

<sup>1</sup>[Comma Pedal](https://community.comma.ai/wiki/index.php/Comma_Pedal) is used to provide stop-and-go capability to some of the openpilot-supported cars that don't currently support stop-and-go. Here is how to [build a Comma Pedal](https://medium.com/@jfrux/comma-pedal-building-with-macrofab-6328bea791e8). ***NOTE: The Comma Pedal is not officially supported by [comma.ai](https://comma.ai)***  
<sup>2</sup>When disconnecting the Driver Support Unit (DSU), otherwise longitudinal control is stock ACC. For DSU locations, see [Toyota Wiki page](https://community.comma.ai/wiki/index.php/Toyota)  
<sup>3</sup>[GM installation guide](https://zoneos.com/volt/).  
<sup>4</sup>It needs an extra 120Ohm resistor ([pic1](https://i.imgur.com/CmdKtTP.jpg), [pic2](https://i.imgur.com/s2etUo6.jpg)) on bus 3 and giraffe switches set to 01X1 (11X1 for stock LKAS), where X depends on if you have the [comma power](https://comma.ai/shop/products/power/).  
<sup>5</sup>28mph for Camry 4CYL L, 4CYL LE and 4CYL SE which don't have Full-Speed Range Dynamic Radar Cruise Control.  
<sup>6</sup>Open sourced [Hyundai Giraffe](https://github.com/commaai/neo/tree/master/giraffe/hyundai) is designed for the 2019 Sante Fe; pinout may differ for other Hyundais.  
<sup>7</sup>Community built Giraffe, find more information [here](https://zoneos.com/shop/).  

Community Maintained Cars
------

| Make                 | Model                    | Supported Package    | Lateral | Longitudinal   | No Accel Below   | No Steer Below | Giraffe           |
| ---------------------| -------------------------| ---------------------| --------| ---------------| -----------------| ---------------|-------------------|
| Honda                | Fit 2018                 | Honda Sensing        | Yes     | Yes            | 25mph<sup>1</sup>| 12mph          | Inverted Nidec    |
| Tesla                | Model S 2012-13          | All                  | Yes     | Not yet        | Not applicable   | 0mph           | Custom<sup>8</sup>|

[[Honda Fit Pull Request]](https://github.com/commaai/openpilot/pull/266). <br />
[[Tesla Model S Pull Request]](https://github.com/commaai/openpilot/pull/246) <br />
<sup>8</sup>Community built Giraffe, find more information here [Community Tesla Giraffe](https://github.com/jeankalud/neo/tree/tesla_giraffe/giraffe/tesla) <br />

Community Maintained Cars are not confirmed by comma.ai to meet our [safety model](https://github.com/commaai/openpilot/blob/devel/SAFETY.md). Be extra cautious using them.

This goes for all of OpenPilot -- **WARNING: Do NOT depend on OP to stop the car in time if you are approaching an object which is not in motion in the same direction as your car. The radar will NOT detect the stationary object in time to slow your car enough to stop. If you are approaching a stopped vehicle you must disengage and brake as radars ignore objects that are not in motion.**

I drive a 2019 Toyota Prius Prime Advanced. These are my mods.

I'm obsessive about documentation. **READ THE COMMITS** for full details of each change! They are listed below.

**Modifications**:
* Stop and go without Toyota Factory `standstill` mode (may not work on all Toyota models, works on my Prius Prime! Check commit for comments) https://github.com/zorrobyte/openpilot/commit/4b70e41e9b87c6a01f7fff3f018ab1739e0038f2
* TESTING: VSR merge into 0510: https://github.com/zorrobyte/openpilot/commit/901d0b183784d7a5d39a3188d8bad36fab2d363a

Other mods (you have to manually install these):
* Automatic cleanup script to prevent OP from turning off when storage is full & auto shutdown script for battery life after uploads finish:
https://gist.github.com/zorrobyte/a36f6408effda262e626ed87b3e9547a

[![](https://i.imgur.com/xY2gdHv.png)](#)
