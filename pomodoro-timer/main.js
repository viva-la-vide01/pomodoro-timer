const { app, BrowserWindow, Tray, Menu, Notification, ipcMain, nativeImage } = require('electron');
const path = require('path');
const fs = require('fs');

let mainWindow = null;
let tray = null;
let isQuitting = false;

// Settings file path
const settingsPath = path.join(app.getPath('userData'), 'settings.json');
const historyPath = path.join(app.getPath('userData'), 'history.json');

// Default settings
const defaultSettings = {
  focusDuration: 25,
  shortBreakDuration: 5,
  longBreakDuration: 15,
  longBreakInterval: 4,
  alwaysOnTop: false,
  autoStartBreak: true,
  autoStartFocus: false,
  volume: 0.8
};

// Load settings
function loadSettings() {
  try {
    if (fs.existsSync(settingsPath)) {
      return { ...defaultSettings, ...JSON.parse(fs.readFileSync(settingsPath, 'utf-8')) };
    }
  } catch (e) {
    console.error('Failed to load settings:', e);
  }
  return { ...defaultSettings };
}

// Save settings
function saveSettings(settings) {
  try {
    fs.writeFileSync(settingsPath, JSON.stringify(settings, null, 2), 'utf-8');
  } catch (e) {
    console.error('Failed to save settings:', e);
  }
}

// Load history
function loadHistory() {
  try {
    if (fs.existsSync(historyPath)) {
      return JSON.parse(fs.readFileSync(historyPath, 'utf-8'));
    }
  } catch (e) {
    console.error('Failed to load history:', e);
  }
  return {};
}

// Save history
function saveHistory(history) {
  try {
    fs.writeFileSync(historyPath, JSON.stringify(history, null, 2), 'utf-8');
  } catch (e) {
    console.error('Failed to save history:', e);
  }
}

// Create tray icon
function createTray() {
  // Create a simple 16x16 tray icon programmatically
  const icon = nativeImage.createFromBuffer(createTrayIconBuffer(), { width: 16, height: 16 });
  tray = new Tray(icon);

  const contextMenu = Menu.buildFromTemplate([
    {
      label: '显示番茄钟',
      click: () => {
        if (mainWindow) {
          mainWindow.show();
          mainWindow.focus();
        }
      }
    },
    { type: 'separator' },
    {
      label: '退出',
      click: () => {
        isQuitting = true;
        app.quit();
      }
    }
  ]);

  tray.setToolTip('番茄钟');
  tray.setContextMenu(contextMenu);

  tray.on('double-click', () => {
    if (mainWindow) {
      mainWindow.show();
      mainWindow.focus();
    }
  });
}

// Create a simple tomato-colored tray icon as PNG buffer
function createTrayIconBuffer() {
  // 16x16 RGBA raw pixel data — a simple filled circle (tomato red)
  const size = 16;
  const center = 7.5;
  const radius = 7;
  const buffer = Buffer.alloc(size * size * 4);

  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const idx = (y * size + x) * 4;
      const dist = Math.sqrt((x - center) ** 2 + (y - center) ** 2);

      if (dist <= radius) {
        // Tomato red: #ff6347
        buffer[idx] = 255;     // R
        buffer[idx + 1] = 99;  // G
        buffer[idx + 2] = 71;  // B
        buffer[idx + 3] = 255; // A
      } else {
        buffer[idx] = 0;
        buffer[idx + 1] = 0;
        buffer[idx + 2] = 0;
        buffer[idx + 3] = 0;
      }
    }
  }

  // Create minimal PNG from raw RGBA
  return nativeImage.createFromBuffer(buffer, { width: size, height: size }).toPNG();
}

// Create the main window
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 380,
    height: 560,
    minWidth: 340,
    minHeight: 500,
    frame: false,
    transparent: false,
    backgroundColor: '#1a1a2e',
    resizable: true,
    skipTaskbar: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'));

  // Load settings and send to renderer
  mainWindow.webContents.on('did-finish-load', () => {
    const settings = loadSettings();
    const history = loadHistory();
    mainWindow.webContents.send('init-data', { settings, history });
  });

  // Minimize to tray on close (unless quitting)
  mainWindow.on('close', (event) => {
    if (!isQuitting) {
      event.preventDefault();
      mainWindow.hide();
    }
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// IPC Handlers
function setupIPC() {
  // Save settings
  ipcMain.handle('save-settings', (event, settings) => {
    saveSettings(settings);
    if (mainWindow) {
      mainWindow.webContents.send('settings-updated', settings);
    }
    return true;
  });

  // Load settings
  ipcMain.handle('load-settings', () => {
    return loadSettings();
  });

  // Save history
  ipcMain.handle('save-history', (event, data) => {
    const history = loadHistory();
    const today = new Date().toISOString().split('T')[0];
    if (!history[today]) {
      history[today] = { pomodoros: 0, tasks: [] };
    }
    history[today].pomodoros = data.pomodoros;
    history[today].tasks = data.tasks;
    // Keep only last 90 days
    const keys = Object.keys(history).sort();
    while (keys.length > 90) {
      delete history[keys.shift()];
    }
    saveHistory(history);
    return history;
  });

  // Load history
  ipcMain.handle('load-history', () => {
    return loadHistory();
  });

  // Show notification
  ipcMain.handle('show-notification', (event, { title, body }) => {
    if (Notification.isSupported()) {
      const notification = new Notification({ title, body, silent: false });
      notification.show();
      notification.on('click', () => {
        if (mainWindow) {
          mainWindow.show();
          mainWindow.focus();
        }
      });
    }
    return true;
  });

  // Toggle always on top
  ipcMain.handle('toggle-always-on-top', (event, enabled) => {
    if (mainWindow) {
      mainWindow.setAlwaysOnTop(enabled);
    }
    return enabled;
  });

  // Window controls
  ipcMain.on('minimize-window', () => {
    if (mainWindow) mainWindow.minimize();
  });

  ipcMain.on('maximize-window', () => {
    if (mainWindow) {
      if (mainWindow.isMaximized()) {
        mainWindow.unmaximize();
      } else {
        mainWindow.maximize();
      }
    }
  });

  ipcMain.on('close-window', () => {
    if (mainWindow) mainWindow.hide();
  });

  // Update tray tooltip with timer
  ipcMain.on('update-tray-timer', (event, timeStr) => {
    if (tray) {
      tray.setToolTip(`番茄钟 - ${timeStr}`);
    }
  });
}

// App lifecycle
app.whenReady().then(() => {
  setupIPC();
  createWindow();
  createTray();
});

app.on('window-all-closed', () => {
  // Don't quit on Windows — keep running in tray
});

app.on('before-quit', () => {
  isQuitting = true;
});

app.on('activate', () => {
  if (mainWindow) {
    mainWindow.show();
    mainWindow.focus();
  }
});
