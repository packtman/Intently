// Global type declarations for Electron API

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
      showNotification: (title: string, body: string) => Promise<void>
      openExternal: (url: string) => Promise<void>
      downloadGitHubRepo: (githubUrl: string) => Promise<string>
      onPRDLoaded: (callback: (data: { path: string; content: string; filename: string }) => void) => () => void
      onCodebaseSelected: (callback: (data: { path: string }) => void) => () => void
      onNewReview: (callback: () => void) => () => void
      onOpenSettings: (callback: () => void) => () => void
      onExportReport: (callback: () => void) => () => void
      onBackendStatusChanged: (callback: (connected: boolean) => void) => () => void
    }
  }
}

export {}


