
QWidget * dp_general(QWidget * parent) {
  QVBoxLayout *dp_list = new QVBoxLayout();

  dp_list->addWidget(new LabelControl("Services", ""));
  dp_list->addWidget(horizontal_line());
  dp_list->addWidget(new ParamControl("dp_updated",
                                            "Enable Updater Service",
                                            "",
                                            "../assets/offroad/icon_empty.png"
                                              ));
  dp_list->addWidget(horizontal_line());
  dp_list->addWidget(new ParamControl("dp_logger",
                                            "Enable Log Services",
                                            "",
                                            "../assets/offroad/icon_empty.png"
                                              ));
  dp_list->addWidget(horizontal_line());
  dp_list->addWidget(new ParamControl("dp_uploader",
                                            "Enable Uploader Services",
                                            "",
                                            "../assets/offroad/icon_empty.png"
                                            ));
  dp_list->addWidget(horizontal_line());
  dp_list->addWidget(new ParamControl("dp_athenad",
                                            "Enable Athenad Service",
                                            "",
                                            "../assets/offroad/icon_empty.png"
                                            ));
/*
  dp_list->addWidget(horizontal_line());
  dp_list->addWidget(new ParamControl("dp_dashcam",
                                            "Enable Dashcam",
                                            "",
                                            "../assets/offroad/icon_empty.png"
                                            ));
*/
  dp_list->addWidget(horizontal_line());
  dp_list->addWidget(new LabelControl("Hardware", ""));
  dp_list->addWidget(horizontal_line());
  dp_list->addWidget(new ParamControl("dp_hotspot_on_boot",
                                            "Enable Hotspot On Boot",
                                            "",
                                            "../assets/offroad/icon_empty.png"
                                              ));
  dp_list->addWidget(horizontal_line());
  dp_list->addWidget(new ParamControl("dp_auto_shutdown",
                                            "Enable Auto Shutdown",
                                            "",
                                            "../assets/offroad/icon_empty.png"
                                              ));
  QWidget *widget = new QWidget;
  widget->setLayout(dp_list);
  return widget;
}

QWidget * dp_controls(QWidget * parent) {
  QVBoxLayout *dp_list = new QVBoxLayout();

  dp_list->addWidget(new LabelControl("Lateral", ""));
  dp_list->addWidget(horizontal_line());
  dp_list->addWidget(new ParamControl("dp_lqr",
                                            "Use LQR Controller",
                                            "",
                                            "../assets/offroad/icon_empty.png"
                                              ));
  dp_list->addWidget(horizontal_line());
  dp_list->addWidget(new ParamControl("dp_sr_learner",
                                            "Enable Steering Ratio Learner",
                                            "",
                                            "../assets/offroad/icon_empty.png"
                                            ));
  dp_list->addWidget(horizontal_line());

  dp_list->addWidget(new ParamControl("dp_auto_lc",
                                            "Enable Auto Lane Change",
                                            "",
                                            "../assets/offroad/icon_empty.png"
                                            ));
  dp_list->addWidget(horizontal_line());
  dp_list->addWidget(new ParamControl("dp_auto_lc_cont",
                                            "Enable Cont. Auto Lane Change",
                                            "",
                                            "../assets/offroad/icon_empty.png"
                                            ));
  dp_list->addWidget(horizontal_line());
  dp_list->addWidget(new LabelControl("Longitudinal", ""));
  dp_list->addWidget(horizontal_line());
//  dp_list->addWidget(new ParamControl("dp_accel_profile_ctrl",
//                                            "Use Acceleration Profile",
//                                            "",
//                                            "../assets/offroad/icon_empty.png"
//                                              ));
//  dp_list->addWidget(new ParamControl("dp_following_profile_ctrl",
//                                            "Use Following Profile",
//                                            "",
//                                            "../assets/offroad/icon_empty.png"
//                                              ));
  dp_list->addWidget(horizontal_line());
  dp_list->addWidget(new ParamControl("dp_allow_gas",
                                            "Allow Gas Pedal Pressed",
                                            "",
                                            "../assets/offroad/icon_empty.png"
                                              ));
//  dp_list->addWidget(horizontal_line());
//  dp_list->addWidget(new ParamControl("dp_lead_car_alert",
//                                            "Enable Lead Car Moving Alert",
//                                            "",
//                                            "../assets/offroad/icon_empty.png"
//                                              ));
  dp_list->addWidget(horizontal_line());
  dp_list->addWidget(new LabelControl("Safety", ""));
  dp_list->addWidget(horizontal_line());
  dp_list->addWidget(new ParamControl("dp_gear_check",
                                            "Enable Gear Safety Check",
                                            "",
                                            "../assets/offroad/icon_empty.png"
                                              ));
  dp_list->addWidget(horizontal_line());
  dp_list->addWidget(new ParamControl("dp_temp_monitor",
                                            "Enable Device Temp Check",
                                            "",
                                            "../assets/offroad/icon_empty.png"
                                              ));
  dp_list->addWidget(horizontal_line());
  dp_list->addWidget(new ParamControl("dp_max_ctrl_speed_check",
                                            "Enable Max Control Speed Check",
                                            "",
                                            "../assets/offroad/icon_empty.png"
                                              ));
  QWidget *widget = new QWidget;
  widget->setLayout(dp_list);
  return widget;
}

QWidget * dp_ui(QWidget * parent) {
  QVBoxLayout *dp_list = new QVBoxLayout();
  /*
  dp_list->addWidget(new ParamControl("dp_ui_screen_off_driving",
                                            "Turn Screen Off While Driving",
                                            "",
                                            "../assets/offroad/icon_empty.png"
                                              ));
  dp_list->addWidget(horizontal_line());
  dp_list->addWidget(new ParamControl("dp_ui_screen_off_reversing",
                                            "Turn Screen Off While Reversing",
                                            "",
                                            "../assets/offroad/icon_empty.png"
                                              ));
  dp_list->addWidget(horizontal_line());
  */
  dp_list->addWidget(new ParamControl("dp_ui_speed",
                                            "Display Speed",
                                            "",
                                            "../assets/offroad/icon_empty.png"
                                            ));
  dp_list->addWidget(horizontal_line());

  dp_list->addWidget(new ParamControl("dp_ui_lane",
                                            "Display Lane Prediction",
                                            "",
                                            "../assets/offroad/icon_empty.png"
                                            ));
  dp_list->addWidget(horizontal_line());
  dp_list->addWidget(new ParamControl("dp_ui_lead",
                                            "Display Lead Car Indicator",
                                            "",
                                            "../assets/offroad/icon_empty.png"
                                            ));
  dp_list->addWidget(horizontal_line());
  dp_list->addWidget(new ParamControl("dp_ui_blinker",
                                            "Display Turning Signal / Blinkers",
                                            "",
                                            "../assets/offroad/icon_empty.png"
                                              ));
  dp_list->addWidget(horizontal_line());
  dp_list->addWidget(new ParamControl("dp_ui_event",
                                            "Display Event / Steer Icon",
                                            "",
                                            "../assets/offroad/icon_empty.png"
                                              ));
  dp_list->addWidget(horizontal_line());
  dp_list->addWidget(new ParamControl("dp_ui_max_speed",
                                            "Display Max Speed",
                                            "",
                                            "../assets/offroad/icon_empty.png"
                                              ));
  dp_list->addWidget(horizontal_line());
  dp_list->addWidget(new ParamControl("dp_ui_face",
                                            "Display Driver Monitor Indicator",
                                            "",
                                            "../assets/offroad/icon_empty.png"
                                              ));
  dp_list->addWidget(horizontal_line());
  dp_list->addWidget(new ParamControl("dp_ui_dev",
                                            "Display Side Info",
                                            "",
                                            "../assets/offroad/icon_empty.png"
                                              ));
  dp_list->addWidget(horizontal_line());
  dp_list->addWidget(new ParamControl("dp_ui_dev_mini",
                                            "Display Bottom Info",
                                            "",
                                            "../assets/offroad/icon_empty.png"
                                              ));
  QWidget *widget = new QWidget;
  widget->setLayout(dp_list);
  return widget;
}
/*
QWidget * dp_apps(QWidget * parent) {
  QVBoxLayout *dp_list = new QVBoxLayout();

  dp_list->addWidget(new ParamControl("dp_app_ext_gps",
                                            "Enable GPS Signal Passthru",
                                            "",
                                            "../assets/offroad/icon_empty.png"
                                              ));
  dp_list->addWidget(horizontal_line());
  dp_list->addWidget(new ParamControl("dp_app_tomtom",
                                            "Enable TomTom Safety Camera",
                                            "",
                                            "../assets/offroad/icon_empty.png"
                                              ));
  dp_list->addWidget(horizontal_line());
  dp_list->addWidget(new ParamControl("dp_app_autonavi",
                                            "Enable Autonavi Map",
                                            "",
                                            "../assets/offroad/icon_empty.png"
                                            ));
  dp_list->addWidget(horizontal_line());

  dp_list->addWidget(new ParamControl("dp_app_aegis",
                                            "Enable Aegis Safety Camera",
                                            "",
                                            "../assets/offroad/icon_empty.png"
                                            ));
  dp_list->addWidget(horizontal_line());
  dp_list->addWidget(new ParamControl("dp_app_mixplorer",
                                            "Enable MiXplorer",
                                            "",
                                            "../assets/offroad/icon_empty.png"
                                            ));
  QWidget *widget = new QWidget;
  widget->setLayout(dp_list);
  return widget;
}
*/
QWidget * dp_cars(QWidget * parent) {
  QVBoxLayout *dp_list = new QVBoxLayout();

  dp_list->addWidget(new LabelControl("Toyota / Lexus", ""));
  dp_list->addWidget(horizontal_line());
  dp_list->addWidget(new ParamControl("dp_toyota_sng",
                                            "Enable SnG Mod",
                                            "",
                                            "../assets/offroad/icon_empty.png"
                                              ));
  dp_list->addWidget(horizontal_line());
  dp_list->addWidget(new ParamControl("dp_toyota_zss",
                                            "Enable ZSS Support",
                                            "",
                                            "../assets/offroad/icon_empty.png"
                                              ));
  dp_list->addWidget(horizontal_line());
  dp_list->addWidget(new LabelControl("Honda", ""));
  dp_list->addWidget(horizontal_line());
  dp_list->addWidget(new ParamControl("dp_honda_eps_mod",
                                            "Enable EPS Mod Support",
                                            "",
                                            "../assets/offroad/icon_empty.png"
                                              ));
  dp_list->addWidget(horizontal_line());
  dp_list->addWidget(new LabelControl("Hyundai / Kia / Genesis", ""));
  dp_list->addWidget(horizontal_line());
  dp_list->addWidget(new ParamControl("dp_hkg_smart_mdps",
                                            "Enable Smart MDPS Support",
                                            "",
                                            "../assets/offroad/icon_empty.png"
                                              ));
  dp_list->addWidget(horizontal_line());
  dp_list->addWidget(new LabelControl("Volkswagen", ""));
  dp_list->addWidget(horizontal_line());
  dp_list->addWidget(new ParamControl("dp_vw_timebomb_assist",
                                            "Enable Timebomb Assist",
                                            "",
                                            "../assets/offroad/icon_empty.png"
                                              ));

  QWidget *widget = new QWidget;
  widget->setLayout(dp_list);
  return widget;
}