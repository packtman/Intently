import { contextBridge, ipcRenderer } from 'electron'

// Expose protected methods to the renderer process
contextBridge.exposeInMainWorld('electronAPI', {
  // File system operations
  selectDirectory: () => ipcRenderer.invoke('select-directory'),
  selectFile: (filters?: { name: string; extensions: string[] }[]) =>
    ipcRenderer.invoke('select-file', filters),
  readFile: (path: string) => ipcRenderer.invoke('read-file', path),
  saveFile: (defaultPath: string, content: string) =>
    ipcRenderer.invoke('save-file', defaultPath, content),

  // Store operations
  getStore: (key: string) => ipcRenderer.invoke('get-store', key),
  setStore: (key: string, value: unknown) => ipcRenderer.invoke('set-store', key, value),

  // Backend operations
  getBackendUrl: () => ipcRenderer.invoke('get-backend-url'),
  startBackend: () => ipcRenderer.invoke('start-backend'),
  stopBackend: () => ipcRenderer.invoke('stop-backend'),
  checkBackend: () => ipcRenderer.invoke('check-backend'),
  
  // GitHub repo download (bypasses sandbox restrictions)
  downloadGitHubRepo: (githubUrl: string) => ipcRenderer.invoke('download-github-repo', githubUrl),

  // Notifications
  showNotification: (title: string, body: string) =>
    ipcRenderer.invoke('show-notification', title, body),

  // External links
  openExternal: (url: string) => ipcRenderer.invoke('open-external', url),

  // Event listeners
  onPRDLoaded: (callback: (data: { path: string; content: string; filename: string }) => void) => {
    ipcRenderer.on('prd-loaded', (_, data) => callback(data))
    return () => ipcRenderer.removeAllListeners('prd-loaded')
  },
  onCodebaseSelected: (callback: (data: { path: string }) => void) => {
    ipcRenderer.on('codebase-selected', (_, data) => callback(data))
    return () => ipcRenderer.removeAllListeners('codebase-selected')
  },
  onNewReview: (callback: () => void) => {
    ipcRenderer.on('new-review', callback)
    return () => ipcRenderer.removeAllListeners('new-review')
  },
  onOpenSettings: (callback: () => void) => {
    ipcRenderer.on('open-settings', callback)
    return () => ipcRenderer.removeAllListeners('open-settings')
  },
  onExportReport: (callback: () => void) => {
    ipcRenderer.on('export-report', callback)
    return () => ipcRenderer.removeAllListeners('export-report')
  },
  onBackendStatusChanged: (callback: (connected: boolean) => void) => {
    ipcRenderer.on('backend-status-changed', (_, connected) => callback(connected))
    return () => ipcRenderer.removeAllListeners('backend-status-changed')
  },
})

// Type declaration for TypeScript
declare global {
  interface Window {
    electronAPI: {
      selectDirectory: () => Promise<string | null>
      selectFile: (filters?: { name: string; extensions: string[] }[]) => Promise<string | null>
      readFile: (path: string) => Promise<string | null>
      saveFile: (defaultPath: string, content: string) => Promise<string | null>
      getStore: (key: string) => Promise<unknown>
      setStore: (key: string, value: unknown) => Promise<boolean>
      getBackendUrl: () => Promise<string>
      startBackend: () => Promise<boolean>
      stopBackend: () => Promise<boolean>
      checkBackend: () => Promise<boolean>
      downloadGitHubRepo: (githubUrl: string) => Promise<string>
      showNotification: (title: string, body: string) => Promise<void>
      openExternal: (url: string) => Promise<void>
      onPRDLoaded: (callback: (data: { path: string; content: string; filename: string }) => void) => () => void
      onCodebaseSelected: (callback: (data: { path: string }) => void) => () => void
      onNewReview: (callback: () => void) => () => void
      onOpenSettings: (callback: () => void) => () => void
      onExportReport: (callback: () => void) => () => void
      onBackendStatusChanged: (callback: (connected: boolean) => void) => () => void
    }
  }
}
