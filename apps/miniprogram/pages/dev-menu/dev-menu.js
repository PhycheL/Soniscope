// 日观声记 · 开发者故障注入菜单
//
// AC1: 仅在非 production 环境可见。
// AC2–AC4: 提供 mock-fc-url-broken / mock-network-offline / mock-verify-fail 三个开关。
// AC5: 开关可以运行时切换，不需要修改源码或重新编译。

var devInjector = require('../../utils/dev-injector.js');
var constants = require('../../utils/constants.js');
var logger = require('../../utils/logger.js');

Page({
  data: {
    mockFcUrlBroken: false,
    mockNetworkOffline: false,
    mockVerifyFail: false,
    isProduction: constants.IS_PRODUCTION,
  },

  onLoad: function () {
    this._refreshFlags();
  },

  onShow: function () {
    this._refreshFlags();
  },

  _refreshFlags: function () {
    var flags = devInjector.getAllFlags();
    this.setData({
      mockFcUrlBroken: flags.mockFcUrlBroken,
      mockNetworkOffline: flags.mockNetworkOffline,
      mockVerifyFail: flags.mockVerifyFail,
      isProduction: constants.IS_PRODUCTION,
    });
  },

  onToggleMockFc: function () {
    var newVal = devInjector.toggleFlag('mockFcUrlBroken');
    this.setData({ mockFcUrlBroken: newVal });
    logger.info('[DevMenu] mock-fc-url-broken toggled →', newVal);
  },

  onToggleMockOffline: function () {
    var newVal = devInjector.toggleFlag('mockNetworkOffline');
    this.setData({ mockNetworkOffline: newVal });
    logger.info('[DevMenu] mock-network-offline toggled →', newVal);
  },

  onToggleMockVerify: function () {
    var newVal = devInjector.toggleFlag('mockVerifyFail');
    this.setData({ mockVerifyFail: newVal });
    logger.info('[DevMenu] mock-verify-fail toggled →', newVal);
  },

  onResetAll: function () {
    devInjector.resetAllFlags();
    this._refreshFlags();
    logger.info('[DevMenu] all fault injection flags reset to false');
    wx.showToast({
      title: '已全部关闭',
      icon: 'success',
      duration: 1500,
    });
  },
});
