//#pragma once
#include "ui.h"
#ifndef PAINT_DP_H
#define PAINT_DP_H

void ui_draw_fp_button(UIState *s);
void ui_draw_ap_button(UIState *s);
//void ui_draw_rec_button(UIState *s);
void ui_draw_infobar(UIState *s);
void ui_draw_blindspots(UIState *s, bool hasInfobar);
void ui_draw_bbui(UIState *s);

#endif