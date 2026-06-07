// 日观声记 · 首页（录音 + 草稿确认 + 中断保护 + 草稿确认态 + 长录音自动分片）

var logger = require('../../utils/logger.js');
var constants = require('../../utils/constants.js');
var idgen = require('../../utils/idgen.js');
var cryptoUtil = require('../../utils/crypto.js');
var uploader = require('../../utils/uploader.js');

var recorderManager = wx.getRecorderManager();

Page({
  data: {
    recording: false,
    timerDisplay: '00:00',
    seconds: 0,
    // 草稿确认态
    draftPreviewMode: false,
    draftFormat: '',
    draftDuration: 0,
    draftDurationDisplay: '',
    draftOssKeyPreview: '',
    draftFileSize: 0,
    draftChunkCount: 0,
    // 试听状态
    audioPlaying: false,
    audioPaused: false,
    // 保存并上传防重复点击
    saveInProgress: false,
    // 中断恢复提示
    showRecoveryModal: false,
    recoveryDraft: null,
    // 开发者菜单可见性（AC1: 仅非 production 环境可见）
    isProduction: constants.IS_PRODUCTION,
  },

  timerInterval: null,
  _interrupted: false, // 中断标记，防止重复生成草稿
  _currentDraft: null, // 当前草稿确认态中的草稿对象（最后一 chunk）
  _audioContext: null, // 试听音频上下文
  _audioContextSeq: 0, // 试听上下文版本号，用于忽略释放后的异步回调
  _pageHidden: false, // 页面后台态标记，用于区分预期音频权限错误

  // ── 长录音自动分片 ──────────────────────────────────────────────────
  _sessionId: null,       // 当前录音会话 ID（所有 chunk 共享）
  _sessionChunks: [],     // 已收集的 chunk 信息数组
  _chunkSeq: 0,           // 当前 chunk 序号（从 1 递增）
  _userStopped: false,    // true = 用户手动停止，false = 自动分片触发

  onLoad: function () {
    logger.info('[Index] onLoad');
    this._initRecorder();
  },

  onShow: function () {
    logger.info('[Index] onShow');
    this._pageHidden = false;
    // 回到前台时检查是否有被中断的草稿需要恢复
    this._checkInterruptedDraft();
  },

  onHide: function () {
    logger.info('[Index] onHide');
    this._pageHidden = true;
    if (this.data.recording) {
      this._handleInterruption('hide');
    }
    // 切后台时释放试听资源，避免 iOS 后台态 operateAudio 权限错误
    this._releaseAuditionAudio();
  },

  onUnload: function () {
    logger.info('[Index] onUnload');
    this._clearTimer();
    this._releaseAuditionAudio({ resetState: false });
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

      var durationSeconds = Math.round((res.duration || 0) / 1000);

      // 构建 chunk 记录
      var chunk = {
        tempFilePath: tempPath,
        audio: {
          original_format: format,
          size_bytes: res.fileSize || 0,
        },
        duration_seconds: durationSeconds,
      };

      if (that._interrupted) {
        // 中断保存到独立存储，等待用户确认
        that._saveInterruptedDraftForChunk(chunk);
        that._interrupted = false;
        that._clearTimer();
        // 若有已收集的先前 chunk 一并清理（中断时丢弃整个 session）
        that._sessionChunks = [];
        that.setData({
          recording: false,
        });
        return;
      }

      // 记录当前 chunk
      that._sessionChunks.push(chunk);

      if (that._userStopped) {
        // 用户手动停止：所有 chunk 已收集完毕，进入草稿确认态
        that._clearTimer();

        var totalDuration = 0;
        for (var ci = 0; ci < that._sessionChunks.length; ci++) {
          totalDuration += that._sessionChunks[ci].duration_seconds;
        }
        var lastChunk = that._sessionChunks[that._sessionChunks.length - 1];

        that._currentDraft = lastChunk;

        var ossKeyPreview = that._buildOssKeyPreview();

        that.setData({
          recording: false,
          draftPreviewMode: true,
          draftFormat: format,
          draftDuration: totalDuration,
          draftDurationDisplay: that._formatDuration(totalDuration),
          draftOssKeyPreview: ossKeyPreview,
          draftFileSize: lastChunk.audio.size_bytes,
          draftChunkCount: that._sessionChunks.length,
        });

        logger.info('[Index] draft preview mode, session:', that._sessionId,
          'chunks:', that._sessionChunks.length,
          'total_duration:', totalDuration + 's',
          'original_format:', format,
          'oss_key_preview:', ossKeyPreview);
      } else {
        // 自动分片：recorder 达到 600s 上限自动停止
        that._chunkSeq++;
        logger.info('[Index] auto-split: chunk', (that._chunkSeq - 1),
          'done, starting chunk', that._chunkSeq);

        // 立即开始下一片段
        recorderManager.start({
          duration: constants.CHUNK_MAX_DURATION_SECONDS * 1000,
          sampleRate: 16000,
          numberOfChannels: 1,
          encodeBitRate: 48000,
          format: 'mp3',
        });
        // 注意：timer 保持运行，不清零
      }
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

    // 设置中断标记，防止 onStop 回调中走正常/自动分片保存路径
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

  _saveInterruptedDraftForChunk: function (chunk) {
    // 将中断前的所有 chunk 一并保存到中断存储
    try {
      // 把当前 chunk 加入 session 列表
      this._sessionChunks.push(chunk);

      var totalDuration = 0;
      for (var i = 0; i < this._sessionChunks.length; i++) {
        totalDuration += this._sessionChunks[i].duration_seconds;
      }

      var draft = {
        tempFilePath: chunk.tempFilePath,
        audio: {
          original_format: chunk.audio.original_format,
          size_bytes: chunk.audio.size_bytes,
        },
        duration_seconds: totalDuration,
        chunks: this._sessionChunks.length,
        recorded_at: new Date().toISOString(),
        interrupted: true,
        // 保存所有 chunk 的路径信息供恢复时使用
        _chunkPaths: this._sessionChunks.map(function (c) { return c.tempFilePath; }),
      };

      wx.setStorageSync('soniscope_interrupted_draft', draft);
      logger.info('[Index] interrupted draft saved, chunks:', this._sessionChunks.length,
        'total_duration:', totalDuration + 's');
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
    this._userStopped = false;
    // 清理之前的草稿确认态
    this._currentDraft = null;
    // 初始化长录音分片追踪
    this._sessionId = null;
    this._sessionChunks = [];
    this._chunkSeq = 0;
    this.setData({
      recording: true,
      seconds: 0,
      timerDisplay: '00:00',
      draftPreviewMode: false,
      draftFormat: '',
      draftDuration: 0,
      draftDurationDisplay: '',
      draftOssKeyPreview: '',
      draftFileSize: 0,
      draftChunkCount: 0,
      audioPlaying: false,
      audioPaused: false,
      saveInProgress: false,
      showRecoveryModal: false,
      recoveryDraft: null,
    });
    this._startTimer();

    // 分配 session_id（所有 chunk 共享）
    this._sessionId = idgen.generateSessionId();
    this._chunkSeq = 1;
    logger.info('[Index] session started:', this._sessionId, 'chunk 1');

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
    this._userStopped = true;
    recorderManager.stop();
  },

  // ── 草稿确认态：试听 ──────────────────────────────────────────────────────

  onAudition: function () {
    logger.info('[Index] onAudition');
    if (!this._currentDraft || !this._currentDraft.tempFilePath) {
      wx.showToast({ title: '草稿文件不可用', icon: 'none', duration: 1500 });
      return;
    }

    this._prepareAuditionAudio(this._currentDraft.tempFilePath);
  },

  onPause: function () {
    logger.info('[Index] onPause');
    if (this._audioContext) {
      this._audioContext.pause();
      this.setData({ audioPlaying: false, audioPaused: true });
    }
  },

  _prepareAuditionAudio: function (src) {
    this._releaseAuditionAudio();
    this._configureAuditionAudioOptions();

    var that = this;
    var audio = wx.createInnerAudioContext();
    audio.obeyMuteSwitch = false;
    var seq = this._audioContextSeq + 1;
    var playRequested = false;
    this._audioContextSeq = seq;
    this._audioContext = audio;

    audio.onCanplay(function () {
      if (!playRequested) {
        playRequested = true;
        that._startAuditionPlayback(audio, seq);
      }
    });

    audio.onPlay(function () {
      if (that._isCurrentAuditionAudio(audio, seq)) {
        logger.info('[Index] audition onPlay');
        that.setData({ audioPlaying: true, audioPaused: false });
      }
    });

    audio.onEnded(function () {
      if (that._isCurrentAuditionAudio(audio, seq)) {
        that.setData({ audioPlaying: false, audioPaused: false });
      }
    });

    audio.onError(function (err) {
      if (that._isExpectedReleasedAudioError(err, audio, seq)) {
        logger.info('[Index] ignored released/background audio error:', err);
        return;
      }
      that._handleAuditionError(err, audio, seq);
    });

    audio.src = src;
    return audio;
  },

  _configureAuditionAudioOptions: function () {
    if (typeof wx.setInnerAudioOption !== 'function') {
      logger.warn('[Index] wx.setInnerAudioOption unavailable');
      return;
    }
    try {
      wx.setInnerAudioOption({
        obeyMuteSwitch: false,
        fail: function (err) {
          logger.warn('[Index] setInnerAudioOption failed:', err);
        },
      });
    } catch (err) {
      logger.warn('[Index] setInnerAudioOption threw:', err);
    }
  },

  _startAuditionPlayback: function (audio, seq) {
    if (!this._isCurrentAuditionAudio(audio, seq)) {
      return;
    }
    logger.info('[Index] audition canplay, requesting play');
    try {
      audio.play();
      this.setData({ audioPlaying: true, audioPaused: false });
    } catch (err) {
      this._handleAuditionError(err, audio, seq);
    }
  },

  _handleAuditionError: function (err, audio, seq) {
    if (this._isExpectedReleasedAudioError(err, audio, seq)) {
      logger.info('[Index] ignored released/background audio error:', err);
      return;
    }
    logger.error('[Index] audio play error:', err);
    this.setData({ audioPlaying: false, audioPaused: false });
    wx.showToast({ title: '播放失败', icon: 'none', duration: 1500 });
  },

  _isCurrentAuditionAudio: function (audio, seq) {
    return this._audioContext === audio && this._audioContextSeq === seq;
  },

  _isExpectedReleasedAudioError: function (err, audio, seq) {
    if (!this._isCurrentAuditionAudio(audio, seq)) {
      return true;
    }
    var errMsg = err && err.errMsg ? String(err.errMsg) : '';
    return this._pageHidden &&
      errMsg.indexOf('operateAudio:fail jsapi has no permission') !== -1 &&
      errMsg.indexOf('runningState=background') !== -1;
  },

  _releaseAuditionAudio: function (options) {
    var audio = this._audioContext;
    if (audio) {
      this._audioContextSeq += 1;
      this._audioContext = null;
      try {
        audio.stop();
      } catch (e) {
        // ignore release errors
      }
      try {
        audio.destroy();
      } catch (e2) {
        // ignore release errors
      }
    }
    if (!options || options.resetState !== false) {
      this.setData({ audioPlaying: false, audioPaused: false });
    }
  },

  _stopAudition: function () {
    this._releaseAuditionAudio();
  },

  _destroyAudio: function () {
    this._releaseAuditionAudio();
  },

  // ── 草稿确认态：重录 ──────────────────────────────────────────────────────

  onReRecord: function () {
    logger.info('[Index] onReRecord — clearing draft and restarting');
    // 清理当前草稿
    this._clearCurrentDraft();
    // 回到录音初始态
    this._startRecording();
  },

  // ── 草稿确认态：删除 ──────────────────────────────────────────────────────

  onDelete: function () {
    logger.info('[Index] onDelete — clearing draft');
    var that = this;
    wx.showModal({
      title: '删除草稿',
      content: '确定删除当前草稿录音吗？删除后无法恢复。',
      success: function (res) {
        if (res.confirm) {
          that._clearCurrentDraft();
          // 回到录音初始态
          that.setData({
            draftPreviewMode: false,
            draftFormat: '',
            draftDuration: 0,
            draftDurationDisplay: '',
            draftOssKeyPreview: '',
            draftFileSize: 0,
            draftChunkCount: 0,
            audioPlaying: false,
            audioPaused: false,
            saveInProgress: false,
          });
          that._currentDraft = null;
          that._sessionChunks = [];
          wx.showToast({ title: '草稿已删除', icon: 'success', duration: 1500 });
          logger.info('[Index] draft deleted');
        }
      },
    });
  },

  _clearCurrentDraft: function () {
    // 停止并释放试听（如有）
    this._releaseAuditionAudio();
    // 清理草稿对象
    this._currentDraft = null;
  },

  // ── 草稿确认态：保存并上传 ────────────────────────────────────────────────

  onSaveAndUpload: function () {
    var that = this;
    logger.info('[Index] onSaveAndUpload');

    // 防止重复点击
    if (this.data.saveInProgress) {
      logger.info('[Index] save already in progress, skip');
      return;
    }

    if (!this._currentDraft) {
      wx.showToast({ title: '草稿不存在，请重新录音', icon: 'none', duration: 2000 });
      return;
    }

    if (!this._sessionChunks || this._sessionChunks.length === 0) {
      wx.showToast({ title: '没有可保存的录音片段', icon: 'none', duration: 2000 });
      return;
    }

    this.setData({ saveInProgress: true });

    // 获取 device_short_id
    var app = getApp();
    var deviceShortId = (app.globalData && app.globalData.deviceShortId) || idgen.getOrCreateDeviceShortId();

    // 所有 chunk 共享同一个 session_id
    var sessionId = this._sessionId || idgen.generateSessionId();
    var chunkTotal = this._sessionChunks.length;
    var recordedAt = new Date().toISOString();

    logger.info('[Index] processing session:', sessionId,
      'total_chunks:', chunkTotal,
      'device:', deviceShortId);

    // 按顺序处理每个 chunk（SHA-256 计算是异步的，需要串行避免并发问题）
    var chunkEntries = []; // 收集处理后的上传记录
    var idx = 0;

    function processNext() {
      if (idx >= that._sessionChunks.length) {
        // 所有 chunk 处理完毕 → 回填 chunk_total → 批量写入 storage
        _finishSave();
        return;
      }

      var chunk = that._sessionChunks[idx];
      var chunkSeq = idx + 1; // chunk_seq 从 1 递增

      logger.info('[Index] processing chunk', chunkSeq + '/' + chunkTotal);

      // 生成独立 fragment_id
      var fragmentId = idgen.generateFragmentId(deviceShortId);

      cryptoUtil.computeFileSha256(chunk.tempFilePath).then(function (sha256) {
        logger.info('[Index] chunk', chunkSeq, 'sha256 computed');

        // 构建完整 manifest 草案
        var manifest = {
          fragment_id: fragmentId,
          session_id: sessionId,
          chunk_seq: chunkSeq,
          chunk_total: 0,         // 将在此批次完成后回填
          device_id: deviceShortId,
          recorded_at: recordedAt,
          duration_seconds: chunk.duration_seconds,
          audio: {
            original_format: chunk.audio.original_format,
            size_bytes: chunk.audio.size_bytes
          },
          upload: {
            original_sha256: sha256
          }
        };

        // OSS 用户自定义元数据
        var ossMeta = {
          'x-oss-meta-session-id': sessionId,
          'x-oss-meta-chunk-seq': String(chunkSeq),
          'x-oss-meta-chunk-total': '0', // 将在此批次完成后回填
          'x-oss-meta-recorded-at': recordedAt,
          'x-oss-meta-duration': String(chunk.duration_seconds),
          'x-oss-meta-original-format': chunk.audio.original_format,
          'x-oss-meta-sha256': sha256
        };

        // 创建上传记录
        var uploadRecord = {
          fragmentId: fragmentId,
          sessionId: sessionId,
          chunkSeq: chunkSeq,
          chunkTotal: 0, // 等待回填
          tempFilePath: chunk.tempFilePath,
          duration: chunk.duration_seconds,
          format: chunk.audio.original_format,
          size: chunk.audio.size_bytes,
          status: constants.UPLOAD_STATUS.QUEUED,
          recordedAt: recordedAt,
          audio: chunk.audio,
          manifest: manifest,
          ossMeta: ossMeta
        };

        chunkEntries.push(uploadRecord);

        idx++;
        processNext();
      }).catch(function (err) {
        logger.error('[Index] sha256 computation failed for chunk', chunkSeq, ':', err);
        // 单个 chunk 失败不应该阻断整体流程，但需要标记
        // 此处记录错误后继续，用户可手动重试
        idx++;
        processNext();
      });
    }

    // 所有 chunk SHA-256 计算完成后的收尾工作
    function _finishSave() {
      if (chunkEntries.length === 0) {
        // 没有任何 chunk 处理成功
        wx.showToast({ title: 'SHA-256 计算全部失败，请重试', icon: 'none', duration: 2000 });
        that.setData({ saveInProgress: false });
        return;
      }

      // 回填 chunk_total 到所有 chunk 的 manifest 和 ossMeta
      for (var ei = 0; ei < chunkEntries.length; ei++) {
        chunkEntries[ei].manifest.chunk_total = chunkTotal;
        chunkEntries[ei].chunkTotal = chunkTotal;
        chunkEntries[ei].ossMeta['x-oss-meta-chunk-total'] = String(chunkTotal);
      }

      // 批量写入上传列表存储
      try {
        var uploadList = wx.getStorageSync('upload_list') || [];
        for (var uj = 0; uj < chunkEntries.length; uj++) {
          uploadList.push(chunkEntries[uj]);
        }
        wx.setStorageSync('upload_list', uploadList);
        logger.info('[Index] upload records added, chunks:', chunkEntries.length,
          'total in list:', uploadList.length);
      } catch (e) {
        logger.error('[Index] failed to save upload records:', e);
        wx.showToast({ title: '保存失败，请重试', icon: 'none', duration: 2000 });
        that.setData({ saveInProgress: false });
        return;
      }

      // 保存最后 chunk 的草稿信息
      var lastChunk = that._sessionChunks[that._sessionChunks.length - 1];
      var summaryDraft = {
        tempFilePath: lastChunk.tempFilePath,
        audio: lastChunk.audio,
        duration_seconds: lastChunk.duration_seconds,
        session_id: sessionId,
        chunks: chunkTotal,
        recorded_at: recordedAt,
      };
      that._saveDraft(summaryDraft);
      that._releaseAuditionAudio();

      // 退出草稿确认态
      that._currentDraft = null;
      that._sessionChunks = [];
      that.setData({
        draftPreviewMode: false,
        draftFormat: '',
        draftDuration: 0,
        draftDurationDisplay: '',
        draftOssKeyPreview: '',
        draftFileSize: 0,
        draftChunkCount: 0,
        audioPlaying: false,
        audioPaused: false,
        saveInProgress: false,
      });

      var toastMsg = chunkTotal > 1
        ? chunkTotal + ' 段录音已加入上传队列'
        : '已加入上传队列';
      wx.showToast({
        title: toastMsg,
        icon: 'success',
        duration: 1500,
      });

      logger.info('[Index] session saved:', sessionId,
        'chunks:', chunkTotal);

      // Trigger the upload engine to start processing the queue
      uploader.processUploadQueue();
    }

    // 开始处理
    processNext();
  },

  // ── 格式探测 / 工具 ──────────────────────────────────────────────────────

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

  // ── 开发者菜单导航 ──────────────────────────────────────────────────────────

  navigateToDevMenu: function () {
    wx.navigateTo({
      url: '/pages/dev-menu/dev-menu',
    });
  },
});
