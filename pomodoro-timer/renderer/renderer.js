// ===== DOM Elements =====
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const elements = {
  timerText: $('#timer-text'),
  timerStatus: $('#timer-status'),
  ringProgress: $('#ring-progress'),
  sessionDots: $('#session-dots'),
  btnStart: $('#btn-start'),
  btnStartIcon: $('#btn-start-icon'),
  btnReset: $('#btn-reset'),
  btnSkip: $('#btn-skip'),
  btnPin: $('#btn-pin'),
  btnMin: $('#btn-min'),
  btnMax: $('#btn-max'),
  btnClose: $('#btn-close'),
  btnSettings: $('#btn-settings'),
  btnHistory: $('#btn-history'),
  modeTabs: $$('.mode-tab'),
  taskInput: $('#task-input'),
  taskAddBtn: $('#task-add-btn'),
  taskList: $('#task-list'),
  settingsPanel: $('#settings-panel'),
  audioNotify: $('#audio-notify'),
};

// ===== State =====
const CIRCUMFERENCE = 2 * Math.PI * 90; // 565.48

const state = {
  mode: 'focus',           // 'focus' | 'shortBreak' | 'longBreak'
  timerState: 'idle',      // 'idle' | 'running' | 'paused'
  timeLeft: 25 * 60,       // seconds
  totalTime: 25 * 60,      // total seconds for current session
  pomodorosToday: 0,
  pomodoroCycle: 0,        // count within current cycle (0-3 focus, then long break)
  tasks: [],
  settings: {
    focusDuration: 25,
    shortBreakDuration: 5,
    longBreakDuration: 15,
    longBreakInterval: 4,
    alwaysOnTop: false,
    autoStartBreak: true,
    autoStartFocus: false,
    volume: 0.8,
  },
  timerInterval: null,
};

// ===== Audio Generation =====
function generateBeepAudio() {
  // Generate a pleasant double-beep sound using Web Audio API
  const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  const sampleRate = audioCtx.sampleRate;
  const duration = 0.6; // seconds
  const length = Math.ceil(sampleRate * duration);
  const buffer = audioCtx.createBuffer(1, length, sampleRate);
  const data = buffer.getChannelData(0);

  for (let i = 0; i < length; i++) {
    const t = i / sampleRate;
    let sample = 0;

    // Two beeps: one at 0s, one at 0.3s
    const beep1 = t < 0.15 ? Math.sin(2 * Math.PI * 880 * t) * Math.exp(-t * 15) : 0;
    const beep2 = (t >= 0.25 && t < 0.4) ? Math.sin(2 * Math.PI * 1100 * (t - 0.25)) * Math.exp(-(t - 0.25) * 15) : 0;

    sample = (beep1 + beep2) * 0.5;
    data[i] = sample;
  }

  // Convert to WAV and set as audio source
  const wavBuffer = audioBufferToWav(buffer);
  const blob = new Blob([wavBuffer], { type: 'audio/wav' });
  elements.audioNotify.src = URL.createObjectURL(blob);
}

function audioBufferToWav(buffer) {
  const numChannels = buffer.numberOfChannels;
  const sampleRate = buffer.sampleRate;
  const format = 1; // PCM
  const bitsPerSample = 16;
  const data = buffer.getChannelData(0);
  const dataLength = data.length * (bitsPerSample / 8);
  const headerLength = 44;
  const totalLength = headerLength + dataLength;

  const arrayBuffer = new ArrayBuffer(totalLength);
  const view = new DataView(arrayBuffer);

  // RIFF header
  writeString(view, 0, 'RIFF');
  view.setUint32(4, totalLength - 8, true);
  writeString(view, 8, 'WAVE');

  // fmt chunk
  writeString(view, 12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, format, true);
  view.setUint16(22, numChannels, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * numChannels * (bitsPerSample / 8), true);
  view.setUint16(32, numChannels * (bitsPerSample / 8), true);
  view.setUint16(34, bitsPerSample, true);

  // data chunk
  writeString(view, 36, 'data');
  view.setUint32(40, dataLength, true);

  // Write samples
  let offset = 44;
  for (let i = 0; i < data.length; i++) {
    const sample = Math.max(-1, Math.min(1, data[i]));
    const intSample = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;
    view.setInt16(offset, intSample, true);
    offset += 2;
  }

  return arrayBuffer;
}

function writeString(view, offset, str) {
  for (let i = 0; i < str.length; i++) {
    view.setUint8(offset + i, str.charCodeAt(i));
  }
}

function playNotification() {
  elements.audioNotify.volume = state.settings.volume;
  elements.audioNotify.currentTime = 0;
  elements.audioNotify.play().catch(() => {});
}

// ===== Timer Logic =====
function getModeDuration() {
  switch (state.mode) {
    case 'focus': return state.settings.focusDuration * 60;
    case 'shortBreak': return state.settings.shortBreakDuration * 60;
    case 'longBreak': return state.settings.longBreakDuration * 60;
    default: return 25 * 60;
  }
}

function resetTimer() {
  state.totalTime = getModeDuration();
  state.timeLeft = state.totalTime;
  updateTimerDisplay();
  updateRingProgress();
}

function switchMode(mode) {
  state.mode = mode;
  if (state.timerState === 'running') {
    stopTimer();
  }
  state.timerState = 'idle';
  state.totalTime = getModeDuration();
  state.timeLeft = state.totalTime;

  updateModeTabs();
  updateRingColor();
  updateTimerDisplay();
  updateRingProgress();
  updateStartButton();
  updateStatus('准备开始');
  updateTrayTimer();
}

function updateModeTabs() {
  elements.modeTabs.forEach(tab => {
    tab.classList.toggle('active', tab.dataset.mode === state.mode);
  });
}

function updateRingColor() {
  const colors = {
    focus: '#e94560',
    shortBreak: '#4ecca3',
    longBreak: '#3498db',
  };
  elements.ringProgress.style.stroke = colors[state.mode];
}

function updateTimerDisplay() {
  const mins = Math.floor(state.timeLeft / 60);
  const secs = state.timeLeft % 60;
  elements.timerText.textContent = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

function updateRingProgress() {
  const progress = state.timeLeft / state.totalTime;
  const offset = CIRCUMFERENCE * (1 - progress);
  elements.ringProgress.style.strokeDashoffset = offset;
}

function updateStatus(text) {
  elements.timerStatus.textContent = text;
}

function updateStartButton() {
  if (state.timerState === 'running') {
    elements.btnStartIcon.textContent = '⏸';
    elements.btnStart.classList.add('running');
  } else {
    elements.btnStartIcon.textContent = '▶';
    elements.btnStart.classList.remove('running');
  }
}

function updateTrayTimer() {
  const mins = Math.floor(state.timeLeft / 60);
  const secs = state.timeLeft % 60;
  const timeStr = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  const modeLabel = state.mode === 'focus' ? '专注' : state.mode === 'shortBreak' ? '短休息' : '长休息';
  window.pomodoroAPI.updateTrayTimer(`${modeLabel} ${timeStr}`);
}

function startTimer() {
  if (state.timerInterval) return;

  state.timerState = 'running';
  updateStartButton();
  updateStatus('正在专注…');

  state.timerInterval = setInterval(() => {
    state.timeLeft--;

    if (state.timeLeft <= 0) {
      completeSession();
      return;
    }

    updateTimerDisplay();
    updateRingProgress();
    updateTrayTimer();
  }, 1000);
}

function pauseTimer() {
  if (state.timerInterval) {
    clearInterval(state.timerInterval);
    state.timerInterval = null;
  }
  state.timerState = 'paused';
  updateStartButton();
  updateStatus('已暂停');
}

function stopTimer() {
  if (state.timerInterval) {
    clearInterval(state.timerInterval);
    state.timerInterval = null;
  }
  state.timerState = 'idle';
}

function completeSession() {
  stopTimer();
  playNotification();

  if (state.mode === 'focus') {
    // Completed a focus session
    state.pomodorosToday++;
    state.pomodoroCycle++;
    updateSessionDots();
    saveHistory();

    window.pomodoroAPI.showNotification('🍅 专注完成！', `太棒了！已完成 ${state.pomodorosToday} 个番茄。休息一下吧~`);

    // Determine next break type
    if (state.pomodoroCycle % state.settings.longBreakInterval === 0) {
      if (state.settings.autoStartBreak) {
        switchMode('longBreak');
        startTimer();
      } else {
        switchMode('longBreak');
      }
      updateStatus('该长休息了~');
    } else {
      if (state.settings.autoStartBreak) {
        switchMode('shortBreak');
        startTimer();
      } else {
        switchMode('shortBreak');
      }
      updateStatus('休息一下~');
    }
  } else {
    // Completed a break
    const breakType = state.mode === 'longBreak' ? '长休息' : '短休息';
    window.pomodoroAPI.showNotification('⏰ 休息结束', `${breakType}时间到！准备开始新的专注吧~`);

    if (state.settings.autoStartFocus) {
      switchMode('focus');
      startTimer();
    } else {
      switchMode('focus');
      updateStatus('准备开始新的专注');
    }
  }

  updateTrayTimer();
}

function skipSession() {
  stopTimer();

  if (state.mode === 'focus') {
    // Was focusing, skip to break
    state.pomodoroCycle++;
    if (state.pomodoroCycle % state.settings.longBreakInterval === 0) {
      switchMode('longBreak');
    } else {
      switchMode('shortBreak');
    }
  } else {
    // Was on break, skip to focus
    switchMode('focus');
  }
  updateTrayTimer();
}

function resetSession() {
  stopTimer();
  state.timerState = 'idle';
  state.timeLeft = state.totalTime;
  updateTimerDisplay();
  updateRingProgress();
  updateStartButton();
  updateStatus('准备开始');
  updateTrayTimer();
}

// ===== Session Dots =====
function updateSessionDots() {
  const interval = state.settings.longBreakInterval;
  const dotsHtml = [];
  for (let i = 0; i < interval; i++) {
    const completed = i < (state.pomodoroCycle % interval === 0 && state.pomodoroCycle > 0 ? interval : state.pomodoroCycle % interval);
    dotsHtml.push(`<span class="session-dot${completed ? ' completed' : ''}"></span>`);
  }
  elements.sessionDots.innerHTML = dotsHtml.join('');
}

// ===== Task Management =====
function addTask(text) {
  const task = {
    id: Date.now(),
    text: text,
    done: false,
  };
  state.tasks.push(task);
  renderTasks();
}

function toggleTask(id) {
  const task = state.tasks.find(t => t.id === id);
  if (task) {
    task.done = !task.done;
    renderTasks();
  }
}

function deleteTask(id) {
  state.tasks = state.tasks.filter(t => t.id !== id);
  renderTasks();
}

function renderTasks() {
  elements.taskList.innerHTML = state.tasks.map(task => `
    <li class="task-item">
      <div class="task-checkbox${task.done ? ' done' : ''}" data-id="${task.id}" data-action="toggle"></div>
      <span class="task-text${task.done ? ' done' : ''}">${escapeHtml(task.text)}</span>
      <button class="task-delete" data-id="${task.id}" data-action="delete">✕</button>
    </li>
  `).join('');

  // Attach event listeners
  elements.taskList.querySelectorAll('.task-checkbox').forEach(el => {
    el.addEventListener('click', () => toggleTask(Number(el.dataset.id)));
  });
  elements.taskList.querySelectorAll('.task-delete').forEach(el => {
    el.addEventListener('click', () => deleteTask(Number(el.dataset.id)));
  });
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

// ===== Settings =====
function toggleSettings() {
  const panel = elements.settingsPanel;
  const isShowing = panel.classList.toggle('show');
  elements.btnSettings.classList.toggle('active', isShowing);

  if (isShowing) {
    // Populate settings values
    $('#set-focus').value = state.settings.focusDuration;
    $('#set-short-break').value = state.settings.shortBreakDuration;
    $('#set-long-break').value = state.settings.longBreakDuration;
    $('#set-interval').value = state.settings.longBreakInterval;
    $('#set-auto-break').checked = state.settings.autoStartBreak;
    $('#set-auto-focus').checked = state.settings.autoStartFocus;
    $('#set-volume').value = Math.round(state.settings.volume * 100);
  }
}

function saveSettingsFromForm() {
  const newSettings = {
    ...state.settings,
    focusDuration: Math.max(1, Math.min(120, parseInt($('#set-focus').value) || 25)),
    shortBreakDuration: Math.max(1, Math.min(30, parseInt($('#set-short-break').value) || 5)),
    longBreakDuration: Math.max(1, Math.min(60, parseInt($('#set-long-break').value) || 15)),
    longBreakInterval: Math.max(1, Math.min(10, parseInt($('#set-interval').value) || 4)),
    autoStartBreak: $('#set-auto-break').checked,
    autoStartFocus: $('#set-auto-focus').checked,
    volume: Math.max(0, Math.min(1, parseInt($('#set-volume').value) / 100)),
  };

  state.settings = newSettings;
  window.pomodoroAPI.saveSettings(newSettings);

  // Update current timer if idle
  if (state.timerState === 'idle') {
    resetTimer();
  }

  updateSessionDots();
  toggleSettings(); // close panel
}

// ===== History =====
let historyModal = null;

async function showHistory() {
  const history = await window.pomodoroAPI.loadHistory();
  const dates = Object.keys(history).sort().reverse();

  // Remove existing modal if any
  if (historyModal) {
    historyModal.remove();
  }

  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';

  const listItems = dates.length > 0
    ? dates.map(date => `
        <li class="history-item">
          <span class="history-date">${date}</span>
          <span class="history-count">🍅 × ${history[date].pomodoros}</span>
        </li>
      `).join('')
    : '<li class="history-item"><span style="color: var(--text-muted);">暂无记录</span></li>';

  overlay.innerHTML = `
    <div class="modal-content">
      <div class="modal-title">📊 历史记录</div>
      <ul class="history-list">${listItems}</ul>
      <button class="modal-close-btn" id="modal-close-btn">关闭</button>
    </div>
  `;

  document.body.appendChild(overlay);
  historyModal = overlay;

  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) {
      overlay.remove();
      historyModal = null;
    }
  });

  $('#modal-close-btn').addEventListener('click', () => {
    overlay.remove();
    historyModal = null;
  });
}

async function saveHistory() {
  const today = new Date().toISOString().split('T')[0];
  await window.pomodoroAPI.saveHistory({
    date: today,
    pomodoros: state.pomodorosToday,
    tasks: state.tasks,
  });
}

// ===== Event Listeners =====
function setupEventListeners() {
  // Start/Pause button
  elements.btnStart.addEventListener('click', () => {
    if (state.timerState === 'running') {
      pauseTimer();
    } else {
      startTimer();
    }
  });

  // Reset button
  elements.btnReset.addEventListener('click', () => {
    resetSession();
  });

  // Skip button
  elements.btnSkip.addEventListener('click', () => {
    skipSession();
  });

  // Mode tabs
  elements.modeTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      switchMode(tab.dataset.mode);
    });
  });

  // Task input
  elements.taskAddBtn.addEventListener('click', () => {
    const text = elements.taskInput.value.trim();
    if (text) {
      addTask(text);
      elements.taskInput.value = '';
    }
  });

  elements.taskInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      const text = elements.taskInput.value.trim();
      if (text) {
        addTask(text);
        elements.taskInput.value = '';
      }
    }
  });

  // Settings
  elements.btnSettings.addEventListener('click', toggleSettings);
  $('#settings-save-btn').addEventListener('click', saveSettingsFromForm);

  // History
  elements.btnHistory.addEventListener('click', showHistory);

  // Window controls
  elements.btnMin.addEventListener('click', () => window.pomodoroAPI.minimizeWindow());
  elements.btnMax.addEventListener('click', () => window.pomodoroAPI.maximizeWindow());
  elements.btnClose.addEventListener('click', () => window.pomodoroAPI.closeWindow());

  // Pin (always on top)
  elements.btnPin.addEventListener('click', () => {
    state.settings.alwaysOnTop = !state.settings.alwaysOnTop;
    elements.btnPin.classList.toggle('active', state.settings.alwaysOnTop);
    window.pomodoroAPI.toggleAlwaysOnTop(state.settings.alwaysOnTop);
  });

  // Keyboard shortcuts
  document.addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT') return; // Don't capture when typing

    switch (e.code) {
      case 'Space':
        e.preventDefault();
        if (state.timerState === 'running') {
          pauseTimer();
        } else {
          startTimer();
        }
        break;
      case 'KeyR':
        if (e.ctrlKey || e.metaKey) break;
        resetSession();
        break;
      case 'KeyS':
        if (e.ctrlKey || e.metaKey) break;
        skipSession();
        break;
      case 'Digit1':
        switchMode('focus');
        break;
      case 'Digit2':
        switchMode('shortBreak');
        break;
      case 'Digit3':
        switchMode('longBreak');
        break;
    }
  });
}

// ===== Initialization =====
async function init() {
  generateBeepAudio();

  // Load saved data from main process
  window.pomodoroAPI.onInitData(({ settings, history }) => {
    if (settings) {
      state.settings = { ...state.settings, ...settings };
    }
    if (history) {
      const today = new Date().toISOString().split('T')[0];
      if (history[today]) {
        state.pomodorosToday = history[today].pomodoros || 0;
        // Start fresh cycle counting based on today's count
        state.pomodoroCycle = state.pomodorosToday % state.settings.longBreakInterval;
      }
    }

    // Apply settings
    state.totalTime = getModeDuration();
    state.timeLeft = state.totalTime;

    if (state.settings.alwaysOnTop) {
      elements.btnPin.classList.add('active');
      window.pomodoroAPI.toggleAlwaysOnTop(true);
    }

    updateTimerDisplay();
    updateRingProgress();
    updateRingColor();
    updateModeTabs();
    updateSessionDots();
    updateTrayTimer();
  });

  // Listen for settings updates from main process
  window.pomodoroAPI.onSettingsUpdated((settings) => {
    state.settings = { ...state.settings, ...settings };
    if (state.timerState === 'idle') {
      resetTimer();
    }
    updateSessionDots();
  });

  setupEventListeners();
}

// Boot
init();
