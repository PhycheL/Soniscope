// 日观声记 · 首页（录音 + 草稿确认）

var logger = require('../../utils/logger.js');
var constants = require('../../utils/constants.js');

var recorderManager = wx.getRecorderManager();

Page({
  data: {
    recording: false,
    timerDisplay: '00:00',
    seconds: 0,
    // 草稿信息
    draftSaved: false,
    draftFormat: '',
    draftDuration: 0,
    draftDurationDisplay: '',
    draftOssKeyPreview: '',
  },

  timerInterval: null,

  onLoad: function () {
    logger.info('[Index] onLoad');
    this._initRecorder();
  },

  onShow: function () {
    logger.info('[Index] onShow');
  },

  onHide: function () {
    logger.info('[Index] onHide');
    if (this.data.recording) {
      this._stopRecording();
    }
  },

  onUnload: function () {
    logger.info('[Index] onUnload');
    this._clearTimer();
  },

  _initRecorder: function () {
    var that = this;

    recorderManager.onStart(function () {
      logger.info('[Index] recorder onStart');
    });

    recorderManager.onStop(function (res) {
      logger.info('[Index] recorder onStop', {
        tempFilePath: res.tempFilePath,
        duration: res.duration,
        fileSize: res.fileSize
      });

      var tempPath = res.tempFilePath || '';
      var format = that._detectFormat(tempPath, res);

      that._clearTimer();

      var durationSeconds = Math.round((res.duration || 0) / 1000);

      // 构建草稿
      var draft = {
        tempFilePath: tempPath,
        audio: {
          original_format: format,
          size_bytes: res.fileSize || 0,
        },
        duration_seconds: durationSeconds,
        recorded_at: new Date().toISOString(),
      };

      that._saveDraft(draft);

      // 生成 OSS key 预览（始终使用 .wav 扩展名，不表示前端已转码）
      var ossKeyPreview = that._buildOssKeyPreview();

      that.setData({
        recording: false,
        draftSaved: true,
        draftFormat: format,
        draftDuration: durationSeconds,
        draftDurationDisplay: that._formatDuration(durationSeconds),
        draftOssKeyPreview: ossKeyPreview,
      });

      logger.info('[Index] draft saved, original_format:', format,
        'duration:', durationSeconds + 's',
        'oss_key_preview:', ossKeyPreview);
    });

    recorderManager.onError(function (err) {
      logger.error('[Index] recorder onError', { errMsg: err.errMsg });
      that.setData({ recording: false });
      that._clearTimer();
      wx.showToast({
        title: '录音失败，请重试',
        icon: 'none',
        duration: 2000,
      });
    });
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
    var that = this;

    wx.authorize({
      scope: 'scope.record',
      success: function () {
        that._doStartRecord();
      },
      fail: function () {
        wx.showModal({
          title: '需要录音权限',
          content: '请在设置中允许使用麦克风',
          success: function (modalRes) {
            if (modalRes.confirm) {
              wx.openSetting();
            }
          },
        });
      },
    });
  },

  _doStartRecord: function () {
    this.setData({
      recording: true,
      seconds: 0,
      timerDisplay: '00:00',
      draftSaved: false,
      draftFormat: '',
      draftDuration: 0,
      draftDurationDisplay: '',
      draftOssKeyPreview: '',
    });
    this._startTimer();

    recorderManager.start({
      duration: constants.CHUNK_MAX_DURATION_SECONDS * 1000,
      sampleRate: 16000,
      numberOfChannels: 1,
      encodeBitRate: 48000,
      format: 'mp3',
    });

    logger.info('[Index] recorder started');
  },

  _stopRecording: function () {
    logger.info('[Index] stopping recording');
    recorderManager.stop();
  },

  _detectFormat: function (tempFilePath, res) {
    // 根据临时文件路径扩展名探测原始格式
    // 当扩展名不可靠时（如无扩展名）使用探测结果
    var path = tempFilePath.toLowerCase();
    var knownExtensions = ['.aac', '.mp3', '.m4a', '.wav', '.amr', '.silk', '.ogg', '.opus'];
    for (var i = 0; i < knownExtensions.length; i++) {
      var ext = knownExtensions[i];
      if (path.indexOf(ext) !== -1 && path.endsWith(ext)) {
        return ext.substring(1);
      }
    }
    // 扩展名不可靠时：微信模拟器通常 mp3，真机通常 aac/m4a
    // 无法可靠探测时记为 unknown，后续由 Worker ffprobe 精确识别
    return 'unknown';
  },

  _formatDuration: function (totalSeconds) {
    var m = Math.floor(totalSeconds / 60);
    var s = totalSeconds % 60;
    return (m < 10 ? '0' + m : m) + ':' + (s < 10 ? '0' + s : s);
  },

  _buildOssKeyPreview: function () {
    // OSS key 预览始终使用 recordings/<YYYY-MM-DD>/<fragment_id>.wav
    // .wav 扩展名表示 Worker 标准化目标，不表示前端已转码
    var now = new Date();
    var yyyy = now.getFullYear();
    var mm = String(now.getMonth() + 1).padStart(2, '0');
    var dd = String(now.getDate()).padStart(2, '0');
    return 'recordings/' + yyyy + '-' + mm + '-' + dd + '/<fragment_id>.wav';
  },

  _saveDraft: function (draft) {
    try {
      var drafts = wx.getStorageSync('soniscope_drafts') || [];
      drafts.push(draft);
      wx.setStorageSync('soniscope_drafts', drafts);
      logger.info('[Index] draft persisted, total drafts:', drafts.length);
    } catch (e) {
      logger.error('[Index] failed to save draft:', e);
    }
  },

  _startTimer: function () {
    var that = this;
    this.timerInterval = setInterval(function () {
      var s = that.data.seconds + 1;
      var display = that._formatDuration(s);
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
