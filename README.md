**THIS IS A FORK, use at your own risk!**

This goes for all of OpenPilot -- **WARNING: Do NOT depend on OP to stop the car in time if you are approaching an object which is not in motion in the same direction as your car. The radar will NOT detect the stationary object in time to slow your car enough to stop. If you are approaching a stopped vehicle you must disengage and brake as radars ignore objects that are not in motion.**

I drive a 2019 Toyota Prius Prime Advanced. These are my mods.

I'm obsessive about documentation. **READ THE COMMITS** for full details of each change! They are listed below.

**Modifications**:
* Stop and go without Toyota Factory `standstill` mode (may not work on all Toyota models, works on my Prius Prime! Check commit for comments) https://github.com/zorrobyte/openpilot/commit/4b70e41e9b87c6a01f7fff3f018ab1739e0038f2

Other mods (you have to manually install these):
* Automatic cleanup script to prevent OP from turning off when storage is full & auto shutdown script for battery life after uploads finish:
https://gist.github.com/zorrobyte/a36f6408effda262e626ed87b3e9547a

[![](https://i.imgur.com/xY2gdHv.png)](#)
