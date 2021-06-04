#pragma once

#include <atomic>
#include <map>
#include <memory>
#include <sstream>
#include <string>

#include <QObject>
#include <QTimer>

#include "nanovg.h"

#include "cereal/messaging/messaging.h"
#include "cereal/visionipc/visionipc.h"
#include "cereal/visionipc/visionipc_client.h"
#include "common/transformations/orientation.hpp"
#include "selfdrive/camerad/cameras/camera_common.h"
#include "selfdrive/common/glutil.h"
#include "selfdrive/common/mat.h"
#include "selfdrive/common/modeldata.h"
#include "selfdrive/common/params.h"
#include "selfdrive/common/util.h"
#include "selfdrive/common/visionimg.h"

#define COLOR_BLACK nvgRGBA(0, 0, 0, 255)
#define COLOR_BLACK_ALPHA(x) nvgRGBA(0, 0, 0, x)
#define COLOR_WHITE nvgRGBA(255, 255, 255, 255)
#define COLOR_WHITE_ALPHA(x) nvgRGBA(255, 255, 255, x)
#define COLOR_RED_ALPHA(x) nvgRGBA(201, 34, 49, x)
#define COLOR_YELLOW nvgRGBA(218, 202, 37, 255)
#define COLOR_RED nvgRGBA(201, 34, 49, 255)
#define COLOR_RED_ALPHA(x) nvgRGBA(201, 34, 49, x)

typedef struct Rect {
  int x, y, w, h;
  int centerX() const { return x + w / 2; }
  int centerY() const { return y + h / 2; }
  int right() const { return x + w; }
  int bottom() const { return y + h; }
  bool ptInRect(int px, int py) const {
    return px >= x && px < (x + w) && py >= y && py < (y + h);
  }
} Rect;

const int bdr_s = 30;
const int header_h = 420;
const int footer_h = 280;

const int UI_FREQ = 20;   // Hz

// dp - dynamic follow btn
const int df_btn_h = 180;
const int df_btn_w = 180;
const int df_btn_x = 1650;
const int df_btn_y = 750;
// dp - accel profile btn
const int ap_btn_h = 180;
const int ap_btn_w = 180;
const int ap_btn_x = 1450;
const int ap_btn_y = 750;
const int info_bar_h = 80;
// dp - rec btn
const int rec_btn_h = 130;
const int rec_btn_w = 180;
const int rec_btn_x = 870;
const int rec_btn_y = 800;

typedef enum UIStatus {
  STATUS_DISENGAGED,
  STATUS_ENGAGED,
  STATUS_WARNING,
  STATUS_ALERT,
} UIStatus;

static std::map<UIStatus, NVGcolor> bg_colors = {
  {STATUS_DISENGAGED, nvgRGBA(0x0, 0x0, 0x0, 0xff)},
  {STATUS_ENGAGED, nvgRGBA(0x01, 0x50, 0x01, 0x01)},
  {STATUS_WARNING, nvgRGBA(0x80, 0x80, 0x80, 0x0f)},
  {STATUS_ALERT, nvgRGBA(0xC9, 0x22, 0x31, 0xff)},
};

typedef struct {
  float x, y;
} vertex_data;

typedef struct {
  vertex_data v[TRAJECTORY_SIZE * 2];
  int cnt;
} line_vertices_data;

typedef struct UIScene {

  mat3 view_from_calib;
  bool world_objects_visible;

  bool is_rhd;
  bool driver_view;

  cereal::PandaState::PandaType pandaType;

  cereal::DeviceState::Reader deviceState;
  cereal::RadarState::LeadData::Reader lead_data[2];
  cereal::CarState::Reader car_state;
  cereal::ControlsState::Reader controls_state;
  cereal::DriverState::Reader driver_state;
  cereal::DriverMonitoringState::Reader dmonitoring_state;
  cereal::DragonConf::Reader dragon_conf;

  // gps
  int satelliteCount;
  bool gpsOK;

  // modelV2
  float lane_line_probs[4];
  float road_edge_stds[2];
  line_vertices_data track_vertices;
  line_vertices_data lane_line_vertices[4];
  line_vertices_data road_edge_vertices[2];

  // lead
  vertex_data lead_vertices[2];

  float light_sensor, accel_sensor, gyro_sensor;
  bool started, ignition, is_metric, longitudinal_control, end_to_end;
  uint64_t started_frame;

  // dp
  bool dpDashcam;
  bool dpDashcamUi;
  bool dpUiScreenOffReversing;
  bool dpUiSpeed;
  bool dpUiEvent;
  bool dpUiMaxSpeed;
  bool dpUiFace;
  bool dpUiLane;
  bool dpUiLead;
  bool dpUiDev;
  bool dpUiDevMini;
  bool dpUiBlinker;
  int dpUiBrightness;
  int dpUiVolumeBoost;
  std::string dpIpAddr;
  // for minimal UI
  float angleSteersDes;
  float angleSteers;
  // for black screen on reversing
  bool isReversing;
  // for blinker, from kegman
  bool leftBlinker;
  bool rightBlinker;
  bool brakeLights;
  int blinker_blinking_rate;
  // for blind spot
  bool leftBlindspot;
  bool rightBlindspot;
  // for updating icon
//  int dp_alert_rate;
//  int dp_alert_type;
  std::string dpLocale;
  bool dpIsUpdating;
  bool dpAthenad;
  bool dpFollowingProfileCtrl;
  int dpFollowingProfile;
  bool dpAccelProfileCtrl;
  int dpAccelProfile;
  bool dpDebug;
} UIScene;

typedef struct UIState {
  VisionIpcClient * vipc_client;
  VisionIpcClient * vipc_client_front;
  VisionIpcClient * vipc_client_rear;
  VisionBuf * last_frame;

  // framebuffer
  int fb_w, fb_h;

  // NVG
  NVGcontext *vg;

  // images
  std::map<std::string, int> images;

  std::unique_ptr<SubMaster> sm;

  UIStatus status;
  UIScene scene;

  // graphics
  std::unique_ptr<GLShader> gl_shader;
  std::unique_ptr<EGLImageTexture> texture[UI_BUF_COUNT];

  GLuint frame_vao[2], frame_vbo[2], frame_ibo[2];
  mat4 rear_frame_mat, front_frame_mat;

  bool awake;

  Rect video_rect, viz_rect;
  float car_space_transform[6];
  bool wide_camera;
  float zoom;
} UIState;


class QUIState : public QObject {
  Q_OBJECT

public:
  QUIState(QObject* parent = 0);

  // TODO: get rid of this, only use signal
  inline static UIState ui_state = {0};

signals:
  void uiUpdate(const UIState &s);
  void offroadTransition(bool offroad);

private slots:
  void update();

private:
  QTimer *timer;
  bool started_prev = true;
};


// device management class

class Device : public QObject {
  Q_OBJECT

public:
  Device(QObject *parent = 0);

private:
  // auto brightness
  const float accel_samples = 5*UI_FREQ;

  bool awake;
  int awake_timeout = 0;
  float accel_prev = 0;
  float gyro_prev = 0;
  float brightness_b = 0;
  float brightness_m = 0;
  float last_brightness = 0;
  FirstOrderFilter brightness_filter;

  QTimer *timer;

  void updateBrightness(const UIState &s);
  void updateWakefulness(const UIState &s);

signals:
  void displayPowerChanged(bool on);

public slots:
  void setAwake(bool on, bool reset);
  void update(const UIState &s);
};
