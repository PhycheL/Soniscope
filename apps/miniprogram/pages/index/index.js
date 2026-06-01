// 日观声记 · 首页（录音 + 草稿确认）

var logger = require('../../utils/logger.js');
var constants = require('../../utils/constants.js');

Page({
  data: {
    recording: false,
    timerDisplay: '00:00',
    seconds: 0,
  },

  timerInterval: null,

  onLoad: function () {
    logger.info('[Index] onLoad');
  },

  onShow: function () {
    logger.info('[Index] onShow');
  },

  onHide: function () {
    logger.info('[Index] onHide');
  },

  onUnload: function () {
    logger.info('[Index] onUnload');
    this._clearTimer();
  },

  onRecordTap: function () {
    if (this.data.recording) {
      this._stopRecording();
    } else {
      this._startRecording();
    }
  },

  _startRecording: function () {
    logger.info('[Index] starting recording');
    this.setData({ recording: true, seconds: 0, timerDisplay: '00:00' });
    this._startTimer();
  },

  _stopRecording: function () {
    logger.info('[Index] stopping recording');
    this.setData({ recording: false });
    this._clearTimer();
  },

  _startTimer: function () {
    var that = this;
    this.timerInterval = setInterval(function () {
      var s = that.data.seconds + 1;
      var m = Math.floor(s / 60);
      var sec = s % 60;
      var display = (m < 10 ? '0' + m : m) + ':' + (sec < 10 ? '0' + sec : sec);
      that.setData({ seconds: s, timerDisplay: display });
    }, 1000);
  },

  _clearTimer: function () {
    if (this.timerInterval) {
      clearInterval(this.timerInterval);
      this.timerInterval = null;
    }
  },
});
