// SPDX-License-Identifier: GPL-2.0-only
/*
 * DRAFT, NOT HARDWARE TESTED. Sharp and AUO FTE716 1080x2040 video mode DSI
 * panels of the Xiaomi Mi MIX (lithium).
 *
 * The init and off sequences were generated with
 * linux-mdss-dsi-panel-driver-generator --dumb-dcs from the stock lithium
 * device tree (boot.img.dtb-5, qcom,mdss_dsi_{sharp,auo}_fte716_1080p_video):
 *   Copyright (c) 2013, The Linux Foundation. All rights reserved.
 *
 * Power and reset order follows the downstream mdss_dsi / mdss_dsi_panel code
 * paths recorded in research/delegated/display-audit/DISPLAY_EVIDENCE.md §5.
 *
 * Copyright (c) 2026 Xiaomi Mi MIX Linux port contributors
 */

#include <linux/delay.h>
#include <linux/gpio/consumer.h>
#include <linux/mod_devicetable.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/regulator/consumer.h>

#include <video/mipi_display.h>

#include <drm/drm_mipi_dsi.h>
#include <drm/drm_modes.h>
#include <drm/drm_panel.h>
#include <drm/drm_probe_helper.h>

struct fte716;

struct fte716_desc {
	int (*on)(struct fte716 *ctx);
	int (*off)(struct fte716 *ctx);
};

/* Downstream regulator order: vddio, lab, ibb. */
static const struct regulator_bulk_data fte716_supplies[] = {
	{ .supply = "vddio" },
	{ .supply = "lab" },
	{ .supply = "ibb" },
};

struct fte716 {
	struct drm_panel panel;
	struct mipi_dsi_device *dsi;
	const struct fte716_desc *desc;
	struct regulator_bulk_data *supplies;
	struct gpio_desc *reset_gpio;
	struct gpio_desc *enable_gpio;
};

static inline struct fte716 *to_fte716(struct drm_panel *panel)
{
	return container_of_const(panel, struct fte716, panel);
}

/*
 * Downstream qcom,mdss-dsi-reset-sequence = <1 10>, <0 1>, <1 10> on a line
 * that is high when the panel runs, described here as GPIO_ACTIVE_LOW.
 */
static void fte716_reset(struct fte716 *ctx)
{
	gpiod_set_value_cansleep(ctx->reset_gpio, 0);
	usleep_range(10000, 11000);
	gpiod_set_value_cansleep(ctx->reset_gpio, 1);
	usleep_range(1000, 2000);
	gpiod_set_value_cansleep(ctx->reset_gpio, 0);
	usleep_range(10000, 11000);
}

/*
 * Two-byte generic writes below are sent by mainline as short packets (0x23);
 * the stock kernel sent them as long packets (0x29). Whether the panel
 * accepts both is an open hardware question.
 */
static int sharp_fte716_on(struct fte716 *ctx)
{
	struct mipi_dsi_multi_context dsi_ctx = { .dsi = ctx->dsi };

	ctx->dsi->mode_flags |= MIPI_DSI_MODE_LPM;

	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x2a,
					 0x00, 0x00, 0x04, 0x37);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x2b,
					 0x00, 0x00, 0x07, 0xf7);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xff, 0x87, 0x16, 0x01);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x80);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xff, 0x87, 0x16);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x80);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xca,
					 0x80, 0xbf, 0xff, 0x99, 0xff, 0x80,
					 0xff, 0x00, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc6, 0x10);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc7,
					 0x90, 0x9a, 0x9a, 0x9b, 0xc9, 0xa9,
					 0x98, 0x99, 0xaa, 0xa8, 0xbb, 0x88,
					 0x88, 0x68, 0x45, 0x44, 0x44, 0x44);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc6, 0x11);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc7,
					 0x90, 0x9a, 0x8a, 0x9b, 0xc8, 0x99,
					 0x99, 0x99, 0xa9, 0xa8, 0xba, 0x88,
					 0x88, 0x78, 0x56, 0x45, 0x44, 0x44);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc6, 0x12);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc7,
					 0x90, 0x99, 0x9a, 0x8a, 0xb9, 0x9a,
					 0x98, 0x89, 0xb9, 0x98, 0xba, 0x88,
					 0x88, 0x78, 0x56, 0x55, 0x55, 0x44);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc6, 0x13);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc7,
					 0x90, 0x99, 0x8a, 0x8a, 0xb9, 0x99,
					 0x89, 0x89, 0xa9, 0x99, 0xb9, 0x88,
					 0x88, 0x88, 0x56, 0x55, 0x55, 0x55);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc6, 0x14);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc7,
					 0x80, 0x8a, 0x8a, 0x9a, 0xb8, 0x89,
					 0x89, 0x89, 0xa9, 0x98, 0xb9, 0x88,
					 0x88, 0x88, 0x67, 0x56, 0x55, 0x55);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc6, 0x15);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc7,
					 0x80, 0x99, 0x99, 0x99, 0xa8, 0x99,
					 0x89, 0x98, 0xa8, 0x89, 0xa9, 0x88,
					 0x88, 0x88, 0x67, 0x66, 0x66, 0x55);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc6, 0x16);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc7,
					 0x80, 0x99, 0x89, 0x8a, 0xa8, 0x99,
					 0x98, 0x88, 0x99, 0x89, 0xa9, 0x88,
					 0x88, 0x88, 0x67, 0x66, 0x66, 0x66);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc6, 0x17);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc7,
					 0x80, 0x89, 0x99, 0x89, 0x99, 0x99,
					 0x88, 0x89, 0x89, 0x89, 0xa9, 0x88,
					 0x88, 0x88, 0x78, 0x66, 0x66, 0x66);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc6, 0x18);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc7,
					 0x80, 0x89, 0x89, 0x8a, 0x98, 0x89,
					 0x89, 0x88, 0x99, 0x98, 0x98, 0x88,
					 0x88, 0x88, 0x78, 0x77, 0x67, 0x66);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc6, 0x19);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc7,
					 0x80, 0x98, 0x98, 0x89, 0x98, 0x89,
					 0x89, 0x88, 0x99, 0x88, 0x99, 0x88,
					 0x88, 0x88, 0x78, 0x77, 0x77, 0x66);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc6, 0x1a);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc7,
					 0x80, 0x88, 0x99, 0x88, 0x98, 0x89,
					 0x89, 0x88, 0x89, 0x98, 0x98, 0x88,
					 0x88, 0x88, 0x78, 0x77, 0x77, 0x77);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc6, 0x1b);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc7,
					 0x80, 0x88, 0x89, 0x89, 0x88, 0x89,
					 0x89, 0x88, 0x98, 0x88, 0x98, 0x88,
					 0x88, 0x88, 0x88, 0x78, 0x77, 0x77);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc6, 0x1c);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc7,
					 0x80, 0x88, 0x89, 0x88, 0x88, 0x89,
					 0x89, 0x88, 0x98, 0x88, 0x98, 0x88,
					 0x88, 0x88, 0x88, 0x88, 0x77, 0x77);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc6, 0x1d);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc7,
					 0x80, 0x88, 0x88, 0x89, 0x88, 0x98,
					 0x88, 0x88, 0x98, 0x88, 0x88, 0x88,
					 0x88, 0x88, 0x88, 0x88, 0x88, 0x77);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc6, 0x1e);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc7,
					 0x80, 0x88, 0x88, 0x88, 0x98, 0x88,
					 0x88, 0x88, 0x98, 0x87, 0x89, 0x88,
					 0x88, 0x88, 0x88, 0x88, 0x88, 0x78);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc6, 0x1f);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc7,
					 0x80, 0x88, 0x88, 0x88, 0x88, 0x88,
					 0x88, 0x88, 0x88, 0x88, 0x98, 0x88,
					 0x88, 0x88, 0x88, 0x88, 0x88, 0x88);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc6, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x82);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xb3, 0x0c);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xff, 0x00, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x80);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xff, 0x00, 0x00);
	mipi_dsi_dcs_exit_sleep_mode_multi(&dsi_ctx);
	mipi_dsi_msleep(&dsi_ctx, 120);
	mipi_dsi_dcs_write_seq_multi(&dsi_ctx, 0x51, 0xff);
	mipi_dsi_dcs_write_seq_multi(&dsi_ctx, 0x53, 0x24);
	mipi_dsi_dcs_write_seq_multi(&dsi_ctx, 0x55, 0x00);
	mipi_dsi_dcs_write_seq_multi(&dsi_ctx, 0x35, 0x00);
	mipi_dsi_dcs_set_display_on_multi(&dsi_ctx);
	mipi_dsi_msleep(&dsi_ctx, 20);

	return dsi_ctx.accum_err;
}

static int sharp_fte716_off(struct fte716 *ctx)
{
	struct mipi_dsi_multi_context dsi_ctx = { .dsi = ctx->dsi };

	ctx->dsi->mode_flags &= ~MIPI_DSI_MODE_LPM;

	mipi_dsi_dcs_set_display_off_multi(&dsi_ctx);
	mipi_dsi_msleep(&dsi_ctx, 50);
	mipi_dsi_dcs_enter_sleep_mode_multi(&dsi_ctx);
	mipi_dsi_msleep(&dsi_ctx, 120);

	return dsi_ctx.accum_err;
}

static int auo_fte716_on(struct fte716 *ctx)
{
	struct mipi_dsi_multi_context dsi_ctx = { .dsi = ctx->dsi };

	ctx->dsi->mode_flags |= MIPI_DSI_MODE_LPM;

	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x2a,
					 0x00, 0x00, 0x04, 0x37);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x2b,
					 0x00, 0x00, 0x07, 0xf7);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xff, 0x87, 0x16, 0x01);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x80);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xff, 0x87, 0x16);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0xa0);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc0,
					 0x00, 0x02, 0x02, 0x09, 0x01, 0x16,
					 0x07);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0xd0);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc0,
					 0x00, 0x02, 0x02, 0x09, 0x01, 0x16,
					 0x07);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x82);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xa5,
					 0x33, 0x02, 0x0c, 0x00, 0x00, 0x22,
					 0x25, 0x55, 0x77);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0xb0);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc2,
					 0x85, 0x02, 0x01, 0x0b, 0x80, 0x84,
					 0x03, 0x01, 0x0b, 0x80, 0x83, 0x04,
					 0x01, 0x0b, 0x80);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0xc0);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc2,
					 0x82, 0x05, 0x01, 0x0b, 0x80);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0xd0);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc3,
					 0x00, 0x0a, 0x0a, 0x00, 0x00, 0x00,
					 0x00, 0x01, 0x04, 0x00, 0x5a, 0x00,
					 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0xe0);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc3,
					 0x00, 0x0a, 0x0a, 0x00, 0x00, 0x00,
					 0x00, 0x01, 0x04, 0x00, 0x5a, 0x00,
					 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x80);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xce,
					 0x25, 0x00, 0x90, 0x00, 0x78, 0xff);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x8d);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xf5, 0x21);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x90);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc5,
					 0x44, 0x19, 0x23, 0x00, 0x88, 0x01,
					 0x32, 0x52, 0x55, 0x50);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x98);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc3, 0x11, 0x11);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0xd1);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xcf, 0x02);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0xd7);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xcf, 0x02);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x8a);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xa5, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0xa1);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xce,
					 0x00, 0x02, 0x02, 0x08, 0x01, 0x16,
					 0x07);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x90);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xce,
					 0x00, 0x8c, 0x0d, 0x9b, 0x00, 0x5c,
					 0x00, 0x75);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x80);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xcb,
					 0x00, 0x00, 0x00, 0x00, 0x50, 0x00,
					 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x90);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xcb,
					 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
					 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
					 0x00, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0xa0);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xcb,
					 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
					 0x00, 0xc0, 0x00, 0x00, 0x00, 0x00,
					 0x00, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0xc0);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xcb,
					 0x15, 0x00, 0x15, 0x00, 0x15, 0x15,
					 0x15, 0x15, 0x2a, 0x2a, 0x00, 0x00,
					 0x15, 0x15, 0x15);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0xd0);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xcb,
					 0x15, 0x15, 0x15, 0x55, 0x55, 0x00,
					 0x00, 0x2a, 0x00, 0x00, 0x00, 0x00,
					 0x00, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0xf0);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xcb,
					 0x33, 0xff, 0x00, 0x3f, 0xf0, 0x3c,
					 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x81);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xf3,
					 0xff, 0xff, 0xc0, 0xff, 0xfc, 0xc0,
					 0xff, 0xff, 0xc0, 0xff, 0xfc, 0xc0);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x90);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc5, 0x77);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x94);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xcf,
					 0x00, 0x00, 0x10, 0x20);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0xa4);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xcf,
					 0x00, 0x07, 0x01, 0x80);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0xd0);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xcf, 0x08);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x80);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xca,
					 0x80, 0xbf, 0xff, 0x99, 0xff, 0x80,
					 0xff, 0x00, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc6, 0x10);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc7,
					 0x90, 0x9a, 0x9a, 0x9a, 0xc8, 0xba,
					 0x99, 0xaa, 0x8b, 0x98, 0x88, 0x88,
					 0x88, 0x57, 0x55, 0x55, 0x55, 0x55);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc6, 0x11);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc7,
					 0x90, 0x8a, 0x8b, 0x8a, 0xb9, 0xaa,
					 0x99, 0xaa, 0xaa, 0x87, 0x88, 0x88,
					 0x88, 0x67, 0x66, 0x56, 0x55, 0x55);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc6, 0x12);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc7,
					 0x90, 0x99, 0x9a, 0x89, 0xb9, 0xaa,
					 0x89, 0xaa, 0x9a, 0x88, 0x88, 0x88,
					 0x88, 0x67, 0x66, 0x66, 0x56, 0x55);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc6, 0x13);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc7,
					 0x90, 0x99, 0x99, 0x99, 0xb8, 0xa9,
					 0x99, 0xa9, 0xa9, 0x78, 0x88, 0x88,
					 0x88, 0x67, 0x66, 0x66, 0x66, 0x66);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc6, 0x14);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc7,
					 0x80, 0x8a, 0x9a, 0x98, 0xa8, 0xb9,
					 0x98, 0xa8, 0xa9, 0x88, 0x88, 0x88,
					 0x88, 0x78, 0x66, 0x66, 0x66, 0x66);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc6, 0x15);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc7,
					 0x80, 0x99, 0x99, 0x89, 0xa8, 0xa9,
					 0x89, 0xa9, 0x99, 0x79, 0x88, 0x88,
					 0x88, 0x78, 0x77, 0x66, 0x66, 0x66);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc6, 0x16);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc7,
					 0x80, 0x99, 0x99, 0x88, 0x99, 0xa9,
					 0x98, 0x98, 0xa9, 0x79, 0x88, 0x88,
					 0x88, 0x78, 0x77, 0x77, 0x66, 0x66);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc6, 0x17);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc7,
					 0x80, 0x89, 0x99, 0x89, 0x98, 0xa9,
					 0x88, 0x99, 0x99, 0x79, 0x88, 0x88,
					 0x88, 0x78, 0x77, 0x77, 0x77, 0x66);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc6, 0x18);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc7,
					 0x80, 0x98, 0xa8, 0x88, 0x89, 0xa9,
					 0x88, 0x99, 0x89, 0x79, 0x88, 0x88,
					 0x88, 0x78, 0x77, 0x77, 0x77, 0x77);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc6, 0x19);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc7,
					 0x80, 0x98, 0x98, 0x89, 0x88, 0xa9,
					 0x88, 0x98, 0x99, 0x88, 0x88, 0x88,
					 0x88, 0x88, 0x77, 0x77, 0x77, 0x77);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc6, 0x1a);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc7,
					 0x80, 0x98, 0x98, 0x88, 0x98, 0x89,
					 0x89, 0x98, 0x98, 0x89, 0x88, 0x88,
					 0x88, 0x88, 0x78, 0x77, 0x77, 0x77);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc6, 0x1b);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc7,
					 0x80, 0x88, 0x89, 0x88, 0x98, 0xa8,
					 0x88, 0x98, 0x88, 0x89, 0x88, 0x88,
					 0x88, 0x88, 0x88, 0x78, 0x77, 0x77);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc6, 0x1c);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc7,
					 0x80, 0x88, 0x98, 0x88, 0x88, 0x99,
					 0x88, 0x88, 0x89, 0x98, 0x88, 0x88,
					 0x88, 0x88, 0x88, 0x88, 0x77, 0x77);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc6, 0x1d);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc7,
					 0x80, 0x88, 0x98, 0x87, 0x89, 0x98,
					 0x88, 0x88, 0x98, 0x98, 0x88, 0x88,
					 0x88, 0x88, 0x88, 0x88, 0x78, 0x77);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc6, 0x1e);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc7,
					 0x80, 0x88, 0x88, 0x88, 0x88, 0x89,
					 0x88, 0x88, 0x98, 0x97, 0x88, 0x88,
					 0x88, 0x88, 0x88, 0x88, 0x88, 0x78);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc6, 0x1f);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc7,
					 0x80, 0x88, 0x88, 0x88, 0x88, 0x88,
					 0x88, 0x88, 0x88, 0x98, 0x88, 0x88,
					 0x88, 0x88, 0x88, 0x88, 0x88, 0x88);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xc6, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0xb0);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xca, 0x02, 0x0f, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x82);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xb3, 0x0c);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xff, 0x00, 0x00, 0x00);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0x00, 0x80);
	mipi_dsi_generic_write_seq_multi(&dsi_ctx, 0xff, 0x00, 0x00);
	mipi_dsi_dcs_write_seq_multi(&dsi_ctx, 0x51, 0xff);
	mipi_dsi_dcs_write_seq_multi(&dsi_ctx, 0x53, 0x24);
	mipi_dsi_dcs_write_seq_multi(&dsi_ctx, 0x55, 0x00);
	mipi_dsi_dcs_write_seq_multi(&dsi_ctx, 0x35, 0x00);
	mipi_dsi_dcs_exit_sleep_mode_multi(&dsi_ctx);
	mipi_dsi_msleep(&dsi_ctx, 120);
	mipi_dsi_dcs_set_display_on_multi(&dsi_ctx);
	mipi_dsi_msleep(&dsi_ctx, 20);

	return dsi_ctx.accum_err;
}

static int auo_fte716_off(struct fte716 *ctx)
{
	struct mipi_dsi_multi_context dsi_ctx = { .dsi = ctx->dsi };

	ctx->dsi->mode_flags &= ~MIPI_DSI_MODE_LPM;

	mipi_dsi_dcs_enter_sleep_mode_multi(&dsi_ctx);
	mipi_dsi_msleep(&dsi_ctx, 120);
	mipi_dsi_dcs_set_display_off_multi(&dsi_ctx);
	mipi_dsi_msleep(&dsi_ctx, 50);

	return dsi_ctx.accum_err;
}

static int fte716_power_on(struct fte716 *ctx)
{
	int ret;

	ret = regulator_enable(ctx->supplies[0].consumer);
	if (ret < 0)
		return ret;
	usleep_range(1000, 2000);

	ret = regulator_enable(ctx->supplies[1].consumer);
	if (ret < 0)
		goto err_vddio;

	ret = regulator_enable(ctx->supplies[2].consumer);
	if (ret < 0)
		goto err_lab;
	usleep_range(10000, 11000);

	gpiod_set_value_cansleep(ctx->enable_gpio, 1);
	usleep_range(100, 110);

	return 0;

err_lab:
	regulator_disable(ctx->supplies[1].consumer);
err_vddio:
	regulator_disable(ctx->supplies[0].consumer);
	return ret;
}

static void fte716_power_off(struct fte716 *ctx)
{
	gpiod_set_value_cansleep(ctx->enable_gpio, 0);
	usleep_range(100, 110);
	gpiod_set_value_cansleep(ctx->reset_gpio, 1);

	usleep_range(5000, 6000);
	regulator_disable(ctx->supplies[2].consumer);
	regulator_disable(ctx->supplies[1].consumer);
	usleep_range(10000, 11000);
	regulator_disable(ctx->supplies[0].consumer);
}

static int fte716_prepare(struct drm_panel *panel)
{
	struct fte716 *ctx = to_fte716(panel);
	struct device *dev = &ctx->dsi->dev;
	int ret;

	ret = fte716_power_on(ctx);
	if (ret < 0) {
		dev_err(dev, "Failed to power on panel: %d\n", ret);
		return ret;
	}

	fte716_reset(ctx);

	ret = ctx->desc->on(ctx);
	if (ret < 0) {
		dev_err(dev, "Failed to initialize panel: %d\n", ret);
		fte716_power_off(ctx);
		return ret;
	}

	return 0;
}

/*
 * The off commands go out in .disable, while the MDP still streams video: in
 * .unprepare the msm DSI host waits for a video-done that never comes (-110,
 * found on the device).
 */
static int fte716_disable(struct drm_panel *panel)
{
	struct fte716 *ctx = to_fte716(panel);
	struct device *dev = &ctx->dsi->dev;
	int ret;

	ret = ctx->desc->off(ctx);
	if (ret < 0)
		dev_err(dev, "Failed to un-initialize panel: %d\n", ret);

	return 0;
}

static int fte716_unprepare(struct drm_panel *panel)
{
	fte716_power_off(to_fte716(panel));

	return 0;
}

/* Shared by both variants: identical timings in the stock device tree. */
static const struct drm_display_mode fte716_mode = {
	.clock = (1080 + 46 + 4 + 32) * (2040 + 16 + 4 + 16) * 60 / 1000,
	.hdisplay = 1080,
	.hsync_start = 1080 + 46,
	.hsync_end = 1080 + 46 + 4,
	.htotal = 1080 + 46 + 4 + 32,
	.vdisplay = 2040,
	.vsync_start = 2040 + 16,
	.vsync_end = 2040 + 16 + 4,
	.vtotal = 2040 + 16 + 4 + 16,
	.width_mm = 75,
	.height_mm = 143,
	.type = DRM_MODE_TYPE_DRIVER,
};

static int fte716_get_modes(struct drm_panel *panel,
			    struct drm_connector *connector)
{
	return drm_connector_helper_get_modes_fixed(connector, &fte716_mode);
}

static const struct drm_panel_funcs fte716_panel_funcs = {
	.prepare = fte716_prepare,
	.disable = fte716_disable,
	.unprepare = fte716_unprepare,
	.get_modes = fte716_get_modes,
};

static int fte716_probe(struct mipi_dsi_device *dsi)
{
	struct device *dev = &dsi->dev;
	struct fte716 *ctx;
	int ret;

	ctx = devm_drm_panel_alloc(dev, struct fte716, panel,
				   &fte716_panel_funcs,
				   DRM_MODE_CONNECTOR_DSI);
	if (IS_ERR(ctx))
		return PTR_ERR(ctx);

	ctx->desc = of_device_get_match_data(dev);
	if (!ctx->desc)
		return -ENODEV;

	ret = devm_regulator_bulk_get_const(dev, ARRAY_SIZE(fte716_supplies),
					    fte716_supplies, &ctx->supplies);
	if (ret < 0)
		return ret;

	/* Requested high: keep the panel as the bootloader left it until prepare. */
	ctx->reset_gpio = devm_gpiod_get(dev, "reset", GPIOD_OUT_HIGH);
	if (IS_ERR(ctx->reset_gpio))
		return dev_err_probe(dev, PTR_ERR(ctx->reset_gpio),
				     "Failed to get reset-gpios\n");

	/* Downstream disp_en_gpio (TLMM 47); its electrical role is unverified. */
	ctx->enable_gpio = devm_gpiod_get_optional(dev, "enable", GPIOD_OUT_LOW);
	if (IS_ERR(ctx->enable_gpio))
		return dev_err_probe(dev, PTR_ERR(ctx->enable_gpio),
				     "Failed to get enable-gpios\n");

	ctx->dsi = dsi;
	mipi_dsi_set_drvdata(dsi, ctx);

	dsi->lanes = 4;
	dsi->format = MIPI_DSI_FMT_RGB888;
	dsi->mode_flags = MIPI_DSI_MODE_VIDEO | MIPI_DSI_MODE_VIDEO_BURST |
			  MIPI_DSI_MODE_VIDEO_HSE |
			  MIPI_DSI_CLOCK_NON_CONTINUOUS;

	/* Downstream qcom,mdss-dsi-lp11-init: reset with the lanes in LP-11. */
	ctx->panel.prepare_prev_first = true;

	ret = drm_panel_of_backlight(&ctx->panel);
	if (ret)
		return dev_err_probe(dev, ret, "Failed to get backlight\n");

	drm_panel_add(&ctx->panel);

	ret = mipi_dsi_attach(dsi);
	if (ret < 0) {
		dev_err(dev, "Failed to attach to DSI host: %d\n", ret);
		drm_panel_remove(&ctx->panel);
		return ret;
	}

	return 0;
}

static void fte716_remove(struct mipi_dsi_device *dsi)
{
	struct fte716 *ctx = mipi_dsi_get_drvdata(dsi);
	int ret;

	ret = mipi_dsi_detach(dsi);
	if (ret < 0)
		dev_err(&dsi->dev, "Failed to detach from DSI host: %d\n", ret);

	drm_panel_remove(&ctx->panel);
}

static const struct fte716_desc sharp_fte716_desc = {
	.on = sharp_fte716_on,
	.off = sharp_fte716_off,
};

static const struct fte716_desc auo_fte716_desc = {
	.on = auo_fte716_on,
	.off = auo_fte716_off,
};

/* Provisional compatibles; lk2nd selects one from the stock panel name. */
static const struct of_device_id fte716_of_match[] = {
	{ .compatible = "xiaomi,lithium-sharp-fte716", .data = &sharp_fte716_desc },
	{ .compatible = "xiaomi,lithium-auo-fte716", .data = &auo_fte716_desc },
	{ /* sentinel */ }
};
MODULE_DEVICE_TABLE(of, fte716_of_match);

static struct mipi_dsi_driver fte716_driver = {
	.probe = fte716_probe,
	.remove = fte716_remove,
	.driver = {
		.name = "panel-xiaomi-lithium-fte716",
		.of_match_table = fte716_of_match,
	},
};
module_mipi_dsi_driver(fte716_driver);

MODULE_DESCRIPTION("DRM driver for Xiaomi Mi MIX FTE716 video mode DSI panels");
MODULE_LICENSE("GPL");
