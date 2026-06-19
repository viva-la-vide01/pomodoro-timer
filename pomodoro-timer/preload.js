const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('pomodoroAPI', {
  // Settings
  saveSettings: (settings) => ipcRenderer.invoke('save-settings', settings),
  loadSettings: () => ipcRenderer.invoke('load-settings'),

  // History
  saveHistory: (data) => ipcRenderer.invoke('save-history', data),
  loadHistory: () => ipcRenderer.invoke('load-history'),

  // Notifications
  showNotification: (title, body) => ipcRenderer.invoke('show-notification', { title, body }),

  // Window controls
  toggleAlwaysOnTop: (enabled) => ipcRenderer.invoke('toggle-always-on-top', enabled),
  minimizeWindow: () => ipcRenderer.send('minimize-window'),
  maximizeWindow: () => ipcRenderer.send('maximize-window'),
  closeWindow: () => ipcRenderer.send('close-window'),

  // Tray
  updateTrayTimer: (timeStr) => ipcRenderer.send('update-tray-timer', timeStr),

  // Listen for init data from main process
  onInitData: (callback) => {
    ipcRenderer.on('init-data', (event, data) => callback(data));
  },
  onSettingsUpdated: (callback) => {
    ipcRenderer.on('settings-updated', (event, settings) => callback(settings));
  }
});
