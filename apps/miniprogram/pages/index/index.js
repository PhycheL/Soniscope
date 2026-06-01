// 日观声记 · 首页（录音 + 草稿确认 + 中断保护）

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
    // 中断恢复提示
    showRecoveryModal: false,
    recoveryDraft: null,
  },

  timerInterval: null,
  _interrupted: false, // 中断标记，防止重复生成草稿

  onLoad: function () {
    logger.info('[Index] onLoad');
    this._initRecorder();
  },

  onShow: function () {
    logger.info('[Index] onShow');
    // 回到前台时检查是否有被中断的草稿需要恢复
    this._checkInterruptedDraft();
  },

  onHide: function () {
    logger.info('[Index] onHide');
    if (this.data.recording) {
      this._handleInterruption('hide');
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
        interrupted: that._interrupted,
      };

      if (that._interrupted) {
        // 中断保存到独立存储，等待用户确认
        that._saveInterruptedDraft(draft);
        that._interrupted = false;
      } else {
        // 正常停止：保存到草稿列表
        that._saveDraft(draft);
      }

      // 生成 OSS key 预览（始终使用 .wav 扩展名，不表示前端已转码）
      var ossKeyPreview = that._buildOssKeyPreview();

      that.setData({
        recording: false,
        draftSaved: !that._interrupted,
        draftFormat: format,
        draftDuration: durationSeconds,
        draftDurationDisplay: that._formatDuration(durationSeconds),
        draftOssKeyPreview: ossKeyPreview,
      });

      logger.info('[Index] draft saved, original_format:', format,
        'duration:', durationSeconds + 's',
        'oss_key_preview:', ossKeyPreview,
        'interrupted:', draft.interrupted);
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

    // 注册录音中断回调：锁屏、来电、其他 App 占用等
    recorderManager.onInterruptionBegin(function () {
      logger.info('[Index] recorder onInterruptionBegin');
      if (that.data.recording && !that._interrupted) {
        that._handleInterruption('interruption');
      }
    });
  },

  // ── 中断处理 ──────────────────────────────────────────────────────────────

  _handleInterruption: function (source) {
    var that = this;
    logger.info('[Index] handling interruption, source:', source);

    // 设置中断标记，防止 onStop 回调中走正常保存路径
    // 也防止重复中断（连续两次中断只保留第一次状态）
    if (this._interrupted) {
      logger.info('[Index] already interrupted, skip duplicate');
      return;
    }
    this._interrupted = true;

    // 自动停止录音（会触发 onStop 回调，其中根据 _interrupted 走中断保存路径）
    try {
      recorderManager.stop();
    } catch (e) {
      logger.error('[Index] stop on interruption failed:', e);
    }
  },

  _saveInterruptedDraft: function (draft) {
    try {
      wx.setStorageSync('soniscope_interrupted_draft', draft);
      logger.info('[Index] interrupted draft saved, duration:', draft.duration_seconds + 's');
    } catch (e) {
      logger.error('[Index] failed to save interrupted draft:', e);
    }
  },

  _checkInterruptedDraft: function () {
    try {
      var draft = wx.getStorageSync('soniscope_interrupted_draft');
      if (draft && draft.interrupted && draft.duration_seconds > 0) {
        logger.info('[Index] found interrupted draft, showing recovery modal');
        this.setData({
          showRecoveryModal: true,
          recoveryDraft: draft,
        });
      }
    } catch (e) {
      logger.error('[Index] checkInterruptedDraft error:', e);
    }
  },

  _clearInterruptedDraft: function () {
    try {
      wx.removeStorageSync('soniscope_interrupted_draft');
    } catch (e) {
      logger.error('[Index] clearInterruptedDraft error:', e);
    }
  },

  // ── 恢复操作按钮 ──────────────────────────────────────────────────────────

  onKeepDraft: function () {
    logger.info('[Index] user chose to keep interrupted draft');
    var draft = this.data.recoveryDraft;
    if (draft) {
      this._saveDraft(draft);
    }
    this._clearInterruptedDraft();
    this.setData({
      showRecoveryModal: false,
      recoveryDraft: null,
    });
    wx.showToast({
      title: '草稿已保留',
      icon: 'success',
      duration: 1500,
    });
  },

  onDiscardDraft: function () {
    logger.info('[Index] user chose to discard interrupted draft');
    this._clearInterruptedDraft();
    this.setData({
      showRecoveryModal: false,
      recoveryDraft: null,
    });
    wx.showToast({
      title: '草稿已丢弃',
      icon: 'none',
      duration: 1500,
    });
  },

  onContinueNew: function () {
    logger.info('[Index] user chose to continue with new recording');
    // 丢弃被中断的草稿
    this._clearInterruptedDraft();
    this.setData({
      showRecoveryModal: false,
      recoveryDraft: null,
    });
    // 开始新的录音
    this._startRecording();
  },

  // ── 录音按钮 ──────────────────────────────────────────────────────────────

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
    this._interrupted = false;
    this.setData({
      recording: true,
      seconds: 0,
      timerDisplay: '00:00',
      draftSaved: false,
      draftFormat: '',
      draftDuration: 0,
      draftDurationDisplay: '',
      draftOssKeyPreview: '',
      showRecoveryModal: false,
      recoveryDraft: null,
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
