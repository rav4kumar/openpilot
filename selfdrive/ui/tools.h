/*
https://github.com/arne182/ArnePilot/blob/release4/selfdrive/ui/dashcam.h
https://github.com/dragonpilot-community/dragonpilot/blob/testing/selfdrive/ui/paint_dp.cc
https://github.com/ShaneSmiskol/openpilot/blob/stock_additions/selfdrive/ui/android/ui.cc

*/
#include <time.h>
#include <sys/stat.h>
#include "json11.hpp"
#include <fstream>

#define CAPTURE_STATE_NOT_CAPTURING 0
#define CAPTURE_STATE_CAPTURING 1

#define RECORD_INTERVAL 180 // Time in seconds to rotate recordings; Max for screenrecord is 3 minutes
#define RECORD_FILES 240 // Number of files to create before looping over

bool sa_button_init = false;
//int dfButtonStatus;
//int apButtonStatus;

int captureState = CAPTURE_STATE_NOT_CAPTURING;
int captureNum = 0;
int start_time = 0;
int elapsed_time = 0; // Time of current recording

int click_elapsed_time = 0;
int click_time = 0;
char filenames[RECORD_FILES][50]; // Track the filenames so they can be deleted when rotating
int files_created = 0;

// dp - dynamic follow btn
const int df_btn_h = 180;
const int df_btn_w = 180;
const int df_btn_x = 1650;
const int df_btn_y = 850;
// dp - accel profile btn
const int ap_btn_h = 180;
const int ap_btn_w = 180;
const int ap_btn_x = 1450;
const int ap_btn_y = 850;
const int info_bar_h = 80;
// dp - rec btn
const int rec_btn_h = 130;
const int rec_btn_w = 180;
const int rec_btn_x = 870;
const int rec_btn_y = 900;

int get_time() {
  // Get current time (in seconds)

  int iRet;
  struct timeval tv;
  int seconds = 0;

  iRet = gettimeofday(&tv,NULL);
  if (iRet == 0) {
    seconds = (int)tv.tv_sec;
  }
  return seconds;
}

struct tm get_time_struct() {
  time_t t = time(NULL);
  struct tm tm = *localtime(&t);
  return tm;
}

void remove_file(char *videos_dir, char *filename) {
  if (filename[0] == '\0') {
    // Don't do anything if no filename is passed
    return;
  }

  int status;
  char fullpath[64];
  snprintf(fullpath,sizeof(fullpath),"%s/%s", videos_dir, filename);
  status = remove(fullpath);
  if (status == 0) {
    printf("Removed file: %s\n", fullpath);
  }
  else {
    printf("Unable to remove file: %s\n", fullpath);
    perror("Error message:");
  }
}

void save_file(char *videos_dir, char *filename) {
  if (!strlen(filename)) {
    return;
  }

  // Rename file to save it from being overwritten
  char cmd[128];
  snprintf(cmd,sizeof(cmd), "mv %s/%s %s/saved_%s", videos_dir, filename, videos_dir, filename);
  printf("save: %s\n",cmd);
  system(cmd);
}

void stop_capture() {
  char videos_dir[50] = "/sdcard/dashcam";

  if (captureState == CAPTURE_STATE_CAPTURING) {
    system("killall -SIGINT screenrecord");
    captureState = CAPTURE_STATE_NOT_CAPTURING;
    elapsed_time = get_time() - start_time;
    if (elapsed_time < 3) {
      remove_file(videos_dir, filenames[captureNum]);
    } else {
      captureNum++;
      if (captureNum > RECORD_FILES-1) {
        captureNum = 0;
      }
    }
  }
}

void start_capture() {
  captureState = CAPTURE_STATE_CAPTURING;
  char cmd[128] = "";
  char videos_dir[50] = "/sdcard/dashcam";

  //////////////////////////////////
  // NOTE: make sure videos_dir folder exists on the device!
  //////////////////////////////////
  struct stat st = {0};
  if (stat(videos_dir, &st) == -1) {
    mkdir(videos_dir,0700);
  }

  if (strlen(filenames[captureNum]) && files_created >= RECORD_FILES) {
    remove_file(videos_dir, filenames[captureNum]);
  }

  char filename[64];
  struct tm tm = get_time_struct();
  snprintf(filename,sizeof(filename),"%04d-%02d-%02d_%02d-%02d-%02d.mp4", tm.tm_year + 1900, tm.tm_mon + 1, tm.tm_mday, tm.tm_hour, tm.tm_min, tm.tm_sec);
  //snprintf(cmd,sizeof(cmd),"screenrecord --size 1280x720 --bit-rate 10000000 %s/%s&",videos_dir,filename);
  snprintf(cmd,sizeof(cmd),"./screenrecord.sh %s/%s &",videos_dir,filename);
  strcpy(filenames[captureNum],filename);

  printf("Capturing to file: %s\n",cmd);
  start_time = get_time();
  system(cmd);

  files_created++;
}

void rotate_video() {
  // Overwrite the existing video (if needed)
  elapsed_time = 0;
  stop_capture();
  captureState = CAPTURE_STATE_CAPTURING;
  start_capture();
}

void ui_draw_rec_button(UIState *s) {
  nvgBeginPath(s->vg);
  nvgRoundedRect(s->vg, rec_btn_x, rec_btn_y, rec_btn_w, rec_btn_h, 20);
  nvgStrokeColor(s->vg, COLOR_WHITE_ALPHA(80));
  nvgStrokeWidth(s->vg, 6);
  nvgStroke(s->vg);

  nvgFontSize(s->vg, 70);
  if (captureState == CAPTURE_STATE_CAPTURING) {
    elapsed_time = get_time() - start_time;
    if (elapsed_time >= RECORD_INTERVAL) {
      rotate_video();
    }
    nvgFillColor(s->vg, nvgRGBA(255,0,0,255));
  }
  else {
    nvgFillColor(s->vg, nvgRGBA(255, 255, 255, 255));
  }
  nvgTextAlign(s->vg, NVG_ALIGN_CENTER);
  nvgText(s->vg, rec_btn_x + rec_btn_w / 2, rec_btn_y + (rec_btn_h / 2)+20,"REC",NULL);
}

std::map<int, std::string> AP_TO_IDX = {{0, "OFF"}, {1, "ECO"}, {2, "NORM"}, {3, "SPORT"}};
//std::map<int, std::string> DF_TO_IDX = {{0, "OFF"}, {1, "SHORT"}, {2, "NORM"}, {3, "LONG"}};

void sa_init(UIState *s) {
  s->pm = new PubMaster({"dynamicGasButton", "dynamicFollowButton"});

  // stock additions todo: run opparams first (in main()?) to ensure json values exist
  std::ifstream op_params_file("/data/params_openpilot.json");
  std::string op_params_content((std::istreambuf_iterator<char>(op_params_file)),
                                (std::istreambuf_iterator<char>()));

  std::string err;
  auto json = json11::Json::parse(op_params_content, err);
  if (!json.is_null() && err.empty()) {
    printf("successfully parsed opParams json\n");
    //dfButtonStatus = json["dynamic_follow_mod"].int_value();
    //apButtonStatus = json["dynamic_gas_mod"].int_value();
    //printf("dfButtonStatus: %d\n", dfButtonStatus);
    //printf("apButtonStatus: %d\n", apButtonStatus);
  } else {  // error parsing json
    printf("ERROR PARSING SA OPPARAMS JSON!\n");
    //dfButtonStatus = 0;
    //apButtonStatus = 0;
  }

}

void ui_draw_ap_button(UIState *s) {
  nvgBeginPath(s->vg);
  nvgRoundedRect(s->vg, ap_btn_x, ap_btn_y, ap_btn_w, ap_btn_h, 20);
  nvgStrokeColor(s->vg, COLOR_WHITE_ALPHA(80));
  nvgStrokeWidth(s->vg, 6);
  nvgStroke(s->vg);

  nvgFontFaceId(s->vg,  s->font_sans_regular);
  nvgFillColor(s->vg, COLOR_WHITE_ALPHA(200));
  nvgFontSize(s->vg, 70);
  nvgTextAlign(s->vg, NVG_ALIGN_CENTER);

  //nvgText(s->vg, ap_btn_x + ap_btn_w / 2, ap_btn_y + ap_btn_h / 2, AP_TO_IDX[apButtonStatus].c_str(), NULL);

  nvgFontFaceId(s->vg,  s->font_sans_regular);
  nvgFillColor(s->vg, COLOR_WHITE_ALPHA(200));
  nvgFontSize(s->vg, 37.5);
  nvgTextAlign(s->vg, NVG_ALIGN_CENTER);

  nvgText(s->vg, ap_btn_x + ap_btn_w / 2, ap_btn_y + ap_btn_h - 10, "ACCEL" , NULL);
}



//void send_ap(UIState *s, int status) {
  //MessageBuilder msg;
  //auto apStatus = msg.initEvent().initDynamicGasButton();
  //apStatus.setStatus(status);
  //s->pm->send("dynamicGasButton", msg);
//}

//void send_df(UIState *s, int status) {
  //MessageBuilder msg;
  //auto dfStatus = msg.initEvent().initDynamicFollowButton();
  //dfStatus.setStatus(status);
  //s->pm->send("dynamicFollowButton", msg);
//}


//BB START: functions added for the display of various items
int bb_ui_draw_measure(UIState *s,  const char* bb_value, const char* bb_uom, const char* bb_label,
    int bb_x, int bb_y, int bb_uom_dx,
    NVGcolor bb_valueColor, NVGcolor bb_labelColor, NVGcolor bb_uomColor,
    int bb_valueFontSize, int bb_labelFontSize, int bb_uomFontSize ) {

  nvgTextAlign(s->vg, NVG_ALIGN_CENTER | NVG_ALIGN_BASELINE);
  int dx = 0;
  if (strlen(bb_uom) > 0) {
    dx = (int)(bb_uomFontSize*2.5/2);
  }
  //print value
  nvgFontFaceId(s->vg, s->font_sans_bold);
  nvgFontSize(s->vg, bb_valueFontSize*2.5);
  nvgFillColor(s->vg, bb_valueColor);
  nvgText(s->vg, bb_x-dx/2, bb_y+ (int)(bb_valueFontSize*2.5)+5, bb_value, NULL);
  //print label
  nvgFontFaceId(s->vg, s->font_sans_regular);
  nvgFontSize(s->vg, bb_labelFontSize*2.5);
  nvgFillColor(s->vg, bb_labelColor);
  nvgText(s->vg, bb_x, bb_y + (int)(bb_valueFontSize*2.5)+5 + (int)(bb_labelFontSize*2.5)+5, bb_label, NULL);
  //print uom
  if (strlen(bb_uom) > 0) {
    nvgSave(s->vg);
    int rx =bb_x + bb_uom_dx + bb_valueFontSize -3;
    int ry = bb_y + (int)(bb_valueFontSize*2.5/2)+25;
    nvgTranslate(s->vg,rx,ry);
    nvgRotate(s->vg, -1.5708); //-90deg in radians
    nvgFontFaceId(s->vg, s->font_sans_regular);
    nvgFontSize(s->vg, (int)(bb_uomFontSize*2.5));
    nvgFillColor(s->vg, bb_uomColor);
    nvgText(s->vg, 0, 0, bb_uom, NULL);
    nvgRestore(s->vg);
  }
  return (int)((bb_valueFontSize + bb_labelFontSize)*2.5) + 5;
}

std::string dpLocale="en-US";
void bb_ui_draw_measures_left(UIState *s, int bb_x, int bb_y, int bb_w ) {
  int bb_rx = bb_x + (int)(bb_w/2);
  int bb_ry = bb_y;
  int bb_h = 5;
  NVGcolor lab_color = COLOR_WHITE_ALPHA(200);
  NVGcolor uom_color = COLOR_WHITE_ALPHA(200);
  int value_fontSize=30;
  int label_fontSize=15;
  int uom_fontSize = 15;
  int bb_uom_dx =  (int)(bb_w /2 - uom_fontSize*2.5) ;
  float d_rel = s->scene.lead_data[0].getDRel();
  float v_rel = s->scene.lead_data[0].getVRel();

  //add visual radar relative distance
  if (true) {
    char val_str[16];
    char uom_str[6];
    NVGcolor val_color = COLOR_WHITE_ALPHA(200);
    if (s->scene.lead_data[0].getStatus()) {
      //show RED if less than 5 meters
      //show orange if less than 15 meters
      if((int)(d_rel) < 15) {
        val_color = nvgRGBA(255, 188, 3, 200);
      }
      if((int)(d_rel) < 5) {
        val_color = nvgRGBA(255, 0, 0, 200);
      }
      // lead car relative distance is always in meters
      snprintf(val_str, sizeof(val_str), "%d", (int)d_rel);
    } else {
       snprintf(val_str, sizeof(val_str), "-");
    }
    snprintf(uom_str, sizeof(uom_str), "m   ");
    bb_h +=bb_ui_draw_measure(s,  val_str, uom_str,
       (dpLocale == "zh-TW"? "真實車距" : dpLocale == "zh-CN"? "真实车距" : "REL DIST"),
        bb_rx, bb_ry, bb_uom_dx,
        val_color, lab_color, uom_color,
        value_fontSize, label_fontSize, uom_fontSize );
    bb_ry = bb_y + bb_h;
  }

  //add visual radar relative speed
  if (true) {
    char val_str[16];
    char uom_str[6];
    NVGcolor val_color = COLOR_WHITE_ALPHA(200);
    if (s->scene.lead_data[0].getStatus()) {
      //show Orange if negative speed (approaching)
      //show Orange if negative speed faster than 5mph (approaching fast)
      if((int)(v_rel) < 0) {
        val_color = nvgRGBA(255, 188, 3, 200);
      }
      if((int)(v_rel) < -5) {
        val_color = nvgRGBA(255, 0, 0, 200);
      }
      // lead car relative speed is always in meters
      if (s->is_metric) {
         snprintf(val_str, sizeof(val_str), "%d", (int)(v_rel * 3.6 + 0.5));
      } else {
         snprintf(val_str, sizeof(val_str), "%d", (int)(v_rel * 2.2374144 + 0.5));
      }
    } else {
       snprintf(val_str, sizeof(val_str), "-");
    }
    if (s->is_metric) {
      snprintf(uom_str, sizeof(uom_str), "km/h");;
    } else {
      snprintf(uom_str, sizeof(uom_str), "mph");
    }
    bb_h +=bb_ui_draw_measure(s,  val_str, uom_str,
        (dpLocale == "zh-TW"? "相對速度" : dpLocale == "zh-CN"? "相对速度" : "REAL SPEED"),
        bb_rx, bb_ry, bb_uom_dx,
        val_color, lab_color, uom_color,
        value_fontSize, label_fontSize, uom_fontSize );
    bb_ry = bb_y + bb_h;
  }

  //finally draw the frame
  bb_h += 20;
  nvgBeginPath(s->vg);
    nvgRoundedRect(s->vg, bb_x, bb_y, bb_w, bb_h, 20);
    nvgStrokeColor(s->vg, COLOR_WHITE_ALPHA(80));
    nvgStrokeWidth(s->vg, 6);
    nvgStroke(s->vg);
}

void ui_draw_bbui(UIState *s) {
    //const int bb_dml_w = 184;
    //const int bb_dml_x = s->scene.viz_rect.x + (bdr_s*2);
    //const int bb_dml_y = s->scene.viz_rect.y + (bdr_s*1.5) + 220;
    const int bb_dmr_w = 184;
    const int bb_dmr_x =s->scene.viz_rect.x + s->scene.viz_rect.w - bb_dmr_w - (bdr_s * 2);
    const int bb_dmr_y = s->scene.viz_rect.y + (bdr_s*1.5) + 220;

    //bb_ui_draw_measures_right(s, bb_dml_x, bb_dml_y, bb_dml_w);
    bb_ui_draw_measures_left(s, bb_dmr_x, bb_dmr_y, bb_dmr_w);
}

bool handle_dp_btn_touch(UIState *s, int touch_x, int touch_y) {

  if (s->started && s->active_app != cereal::UiLayoutState::App::SETTINGS) {
    if (touch_x >= rec_btn_x && touch_x <= (rec_btn_x + rec_btn_w) && touch_y >= rec_btn_y && touch_y <= (rec_btn_y + rec_btn_h)) {
      s->scene.uilayout_sidebarcollapsed = true;
      click_elapsed_time = get_time() - click_time;
      if (click_elapsed_time > 0) {
        click_time = get_time() + 1;
        if (captureState == CAPTURE_STATE_CAPTURING) {
          stop_capture();
        }
        else {
          start_capture();
        }
      }
      printf("rec button: %d\n", captureState);
      return true;
    }
  }

  return false;
}

void dashcam( UIState *s) {
  if(!sa_button_init){
      printf("init SA buttons\n");
      sa_init(s);
      sa_button_init = true;
  }

  if (s->vision_connected){
    //ui_draw_df_button(s);
    ui_draw_ap_button(s);
    ui_draw_rec_button(s);
    ui_draw_bbui(s);
  }

  if (!s->started) {
    // Assume car is not in drive so stop recording
    stop_capture();
  }
  //s->scene.recording = (captureState != CAPTURE_STATE_NOT_CAPTURING);

}
