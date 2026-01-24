import { app, BrowserWindow, ipcMain, dialog, shell, Menu, Notification } from 'electron'
import { spawn, ChildProcess, execSync } from 'child_process'
import path from 'path'
import fs from 'fs'
import https from 'https'
import Store from 'electron-store'

// Initialize store for persistent settings
const store = new Store()

let mainWindow: BrowserWindow | null = null
let pythonProcess: ChildProcess | null = null
let backendPort = 8000
let isBackendStarting = false
let lastBackendStatus = false

// Check if we're in development (lazy evaluation to avoid accessing app before ready)
const isDev = () => process.env.NODE_ENV === 'development' || !app.isPackaged

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1000,
    minHeight: 700,
    titleBarStyle: 'hiddenInset',
    trafficLightPosition: { x: 20, y: 20 },
    backgroundColor: '#07070d',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
    },
    show: false,
  })

  // Show window when ready to prevent visual flash
  mainWindow.once('ready-to-show', () => {
    mainWindow?.show()
  })

  // Load the app
  if (isDev()) {
    mainWindow.loadURL('http://localhost:5173')
    mainWindow.webContents.openDevTools()
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'))
  }

  mainWindow.on('closed', () => {
    mainWindow = null
  })

  // Create application menu
  createMenu()
}

function createMenu() {
  const template: Electron.MenuItemConstructorOptions[] = [
    {
      label: 'Intently',
      submenu: [
        { label: 'About Intently', role: 'about' },
        { type: 'separator' },
        { label: 'Preferences', accelerator: 'CmdOrCtrl+,', click: () => mainWindow?.webContents.send('open-settings') },
        { type: 'separator' },
        { role: 'hide' },
        { role: 'hideOthers' },
        { role: 'unhide' },
        { type: 'separator' },
        { role: 'quit' },
      ],
    },
    {
      label: 'File',
      submenu: [
        { label: 'New Review', accelerator: 'CmdOrCtrl+N', click: () => mainWindow?.webContents.send('new-review') },
        { type: 'separator' },
        { label: 'Open PRD...', accelerator: 'CmdOrCtrl+O', click: () => handleOpenPRD() },
        { label: 'Open Codebase...', accelerator: 'CmdOrCtrl+Shift+O', click: () => handleOpenCodebase() },
        { type: 'separator' },
        { label: 'Export Report', accelerator: 'CmdOrCtrl+E', click: () => mainWindow?.webContents.send('export-report') },
      ],
    },
    {
      label: 'Edit',
      submenu: [
        { role: 'undo' },
        { role: 'redo' },
        { type: 'separator' },
        { role: 'cut' },
        { role: 'copy' },
        { role: 'paste' },
        { role: 'selectAll' },
      ],
    },
    {
      label: 'View',
      submenu: [
        { role: 'reload' },
        { role: 'forceReload' },
        { role: 'toggleDevTools' },
        { type: 'separator' },
        { role: 'resetZoom' },
        { role: 'zoomIn' },
        { role: 'zoomOut' },
        { type: 'separator' },
        { role: 'togglefullscreen' },
      ],
    },
    {
      label: 'Window',
      submenu: [
        { role: 'minimize' },
        { role: 'zoom' },
        { type: 'separator' },
        { role: 'front' },
      ],
    },
    {
      label: 'Help',
      submenu: [
        { label: 'Documentation', click: () => shell.openExternal('https://github.com/context-graph/docs') },
        { label: 'Report Issue', click: () => shell.openExternal('https://github.com/context-graph/issues') },
      ],
    },
  ]

  const menu = Menu.buildFromTemplate(template)
  Menu.setApplicationMenu(menu)
}

async function handleOpenPRD() {
  const result = await dialog.showOpenDialog(mainWindow!, {
    properties: ['openFile'],
    filters: [
      { name: 'Markdown', extensions: ['md', 'markdown'] },
      { name: 'Text', extensions: ['txt'] },
      { name: 'All Files', extensions: ['*'] },
    ],
  })

  if (!result.canceled && result.filePaths.length > 0) {
    const content = fs.readFileSync(result.filePaths[0], 'utf-8')
    mainWindow?.webContents.send('prd-loaded', {
      path: result.filePaths[0],
      content,
      filename: path.basename(result.filePaths[0]),
    })
  }
}

async function handleOpenCodebase() {
  const result = await dialog.showOpenDialog(mainWindow!, {
    properties: ['openDirectory'],
  })

  if (!result.canceled && result.filePaths.length > 0) {
    mainWindow?.webContents.send('codebase-selected', {
      path: result.filePaths[0],
    })
  }
}

// PERFORMANCE OPTIMIZED: Lightweight health check with shorter timeout
// Uses /health endpoint instead of /api/reviews for minimal overhead
async function checkBackendHealth(retries = 1, timeout = 2000): Promise<boolean> {
  for (let i = 0; i < retries; i++) {
    try {
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), timeout)
      
      // Use lightweight /health endpoint instead of /api/reviews
      const response = await fetch(`http://127.0.0.1:${backendPort}/health`, {
        signal: controller.signal,
        method: 'GET',
      })
      
      clearTimeout(timeoutId)
      
      if (response.ok) {
        return true
      }
    } catch (error) {
      // If this isn't the last retry, wait before trying again
      if (i < retries - 1) {
        await new Promise(resolve => setTimeout(resolve, 300))
      }
    }
  }
  return false
}

// Start Python backend server with better error handling
async function startBackend(): Promise<boolean> {
  // Prevent multiple simultaneous start attempts
  if (isBackendStarting) {
    console.log('Backend is already starting...')
    return false
  }
  
  // Check if already running
  const alreadyRunning = await checkBackendHealth(1, 2000)
  if (alreadyRunning) {
    console.log('Backend is already running')
    lastBackendStatus = true
    return true
  }
  
  isBackendStarting = true
  
  return new Promise((resolve) => {
    const contextGraphPath = store.get('contextGraphPath', '') as string

    if (!contextGraphPath) {
      console.log('Intently path not configured')
      isBackendStarting = false
      resolve(false)
      return
    }

    // Check if the path exists
    if (!fs.existsSync(contextGraphPath)) {
      console.log('Intently path does not exist:', contextGraphPath)
      isBackendStarting = false
      resolve(false)
      return
    }

    const scriptPath = path.join(contextGraphPath, 'src', 'context_graph', 'cli.py')
    
    if (!fs.existsSync(scriptPath)) {
      console.log('CLI script not found:', scriptPath)
      isBackendStarting = false
      resolve(false)
      return
    }

    // Kill any existing process first
    if (pythonProcess) {
      pythonProcess.kill()
      pythonProcess = null
    }

    // Use the venv's Python directly for correct dependencies and version
    const venvPythonPath = path.join(contextGraphPath, '.venv', 'bin', 'python')
    const fallbackPythonPath = store.get('pythonPath', 'python3') as string
    
    // Prefer venv Python if it exists, otherwise fall back to configured path
    const pythonPath = fs.existsSync(venvPythonPath) ? venvPythonPath : fallbackPythonPath
    
    console.log('Starting backend with:', pythonPath, scriptPath)

    // Configure storage path for SQLite database
    const storageDir = path.join(app.getPath('userData'), 'data')
    if (!fs.existsSync(storageDir)) {
      fs.mkdirSync(storageDir, { recursive: true })
    }

    pythonProcess = spawn(pythonPath, [scriptPath, 'serve', '--host', '127.0.0.1', '--port', String(backendPort)], {
      cwd: contextGraphPath,
      env: { 
        ...process.env,
        // Pass Electron's userData path to Python for cloning repos
        // This ensures the Python process has write access (macOS sandboxing)
        CONTEXT_GRAPH_CACHE_DIR: path.join(app.getPath('userData'), 'repo-cache'),
        // Enable persistent storage with SQLite
        STORAGE_BACKEND: 'sqlite',
        STORAGE_DB_PATH: path.join(storageDir, 'reviews.db'),
        // Enable PM Tool features (from UNIFIED_PM_TOOL_VISION.md)
        FEATURE_PRD_CHANGES: 'true',
        FEATURE_PRD_QUALITY_SCORING: 'true',
        FEATURE_EFFORT_ESTIMATION: 'true',
        FEATURE_EXPERT_ASSIST: 'true',
        FEATURE_PM_PATTERN_LEARNING: 'true',
        FEATURE_SIDE_BY_SIDE_DIFF: 'true',
        FEATURE_PRD_SAVE_TO_FILE: 'true',
      },
      stdio: ['pipe', 'pipe', 'pipe'],
    })

    let resolved = false

    pythonProcess.stdout?.on('data', (data) => {
      const output = data.toString()
      console.log(`Backend: ${output}`)
      if (!resolved && (output.includes('Uvicorn running') || output.includes('Application startup complete'))) {
        resolved = true
        isBackendStarting = false
        lastBackendStatus = true
        resolve(true)
      }
    })

    pythonProcess.stderr?.on('data', (data) => {
      const output = data.toString()
      console.error(`Backend stderr: ${output}`)
      // Uvicorn sometimes logs to stderr
      if (!resolved && (output.includes('Uvicorn running') || output.includes('Application startup complete'))) {
        resolved = true
        isBackendStarting = false
        lastBackendStatus = true
        resolve(true)
      }
    })

    pythonProcess.on('error', (error) => {
      console.error('Failed to start backend:', error)
      if (!resolved) {
        resolved = true
        isBackendStarting = false
        resolve(false)
      }
    })

    pythonProcess.on('close', (code) => {
      console.log(`Backend process exited with code ${code}`)
      pythonProcess = null
      lastBackendStatus = false
      
      // Notify renderer that backend went offline
      mainWindow?.webContents.send('backend-status-changed', false)
      
      if (!resolved) {
        resolved = true
        isBackendStarting = false
        resolve(false)
      }
    })

    // Timeout after 15 seconds
    setTimeout(() => {
      if (!resolved) {
        resolved = true
        isBackendStarting = false
        // Even if we didn't see the startup message, check if it's responding
        checkBackendHealth(2, 2000).then(isHealthy => {
          if (isHealthy) {
            lastBackendStatus = true
            resolve(true)
          } else {
            resolve(false)
          }
        })
      }
    }, 15000)
  })
}

function stopBackend() {
  if (pythonProcess) {
    console.log('Stopping backend process...')
    pythonProcess.kill('SIGTERM')
    
    // Force kill after 5 seconds if it doesn't stop gracefully
    setTimeout(() => {
      if (pythonProcess) {
        pythonProcess.kill('SIGKILL')
        pythonProcess = null
      }
    }, 5000)
  }
  lastBackendStatus = false
}

// IPC Handlers - wrapped in function to ensure Electron is ready
function registerIpcHandlers() {
  ipcMain.handle('select-directory', async (_, options?: { defaultPath?: string }) => {
  // Default to the cached repos folder on macOS so users can easily select pre-downloaded repos
  let defaultPath = options?.defaultPath
  if (!defaultPath && process.platform === 'darwin') {
    const cacheDir = '/tmp/context-graph-repos'
    // Check if the cache dir exists and has contents
    if (fs.existsSync(cacheDir)) {
      defaultPath = cacheDir
    }
  }
  
  const result = await dialog.showOpenDialog(mainWindow!, {
    properties: ['openDirectory'],
    defaultPath,
  })
  return result.canceled ? null : result.filePaths[0]
})

ipcMain.handle('select-file', async (_, filters?: { name: string; extensions: string[] }[]) => {
  const result = await dialog.showOpenDialog(mainWindow!, {
    properties: ['openFile'],
    filters: filters || [{ name: 'All Files', extensions: ['*'] }],
  })
  return result.canceled ? null : result.filePaths[0]
})

// Download GitHub repo via tarball (bypasses sandbox issues with git clone)
ipcMain.handle('download-github-repo', async (_, githubUrl: string) => {
  const cacheDir = '/tmp/context-graph-repos'
  
  // Parse GitHub URL to get owner/repo
  const match = githubUrl.match(/github\.com[/:]([^/]+)\/([^/.]+)/)
  if (!match) {
    throw new Error('Invalid GitHub URL')
  }
  const [, owner, repo] = match
  const repoName = repo.replace('.git', '')
  
  // Create cache directory
  if (!fs.existsSync(cacheDir)) {
    fs.mkdirSync(cacheDir, { recursive: true })
  }
  
  // Check if already downloaded
  const existingDirs = fs.readdirSync(cacheDir).filter(d => d.startsWith(`${repoName}-`))
  if (existingDirs.length > 0) {
    const existingPath = path.join(cacheDir, existingDirs[0])
    console.log(`Reusing existing download: ${existingPath}`)
    return existingPath
  }
  
  const targetDir = path.join(cacheDir, `${repoName}-cached`)
  const tarballUrl = `https://github.com/${owner}/${repoName}/archive/refs/heads/main.tar.gz`
  const tempTarball = path.join(cacheDir, `${repoName}-download.tar.gz`)
  
  console.log(`Downloading ${tarballUrl}...`)
  
  // Download tarball
  await new Promise<void>((resolve, reject) => {
    const file = fs.createWriteStream(tempTarball)
    
    const request = (url: string) => {
      https.get(url, (response) => {
        // Handle redirects
        if (response.statusCode === 302 || response.statusCode === 301) {
          request(response.headers.location!)
          return
        }
        
        if (response.statusCode === 404) {
          // Try master branch if main doesn't exist
          const masterUrl = `https://github.com/${owner}/${repoName}/archive/refs/heads/master.tar.gz`
          if (!url.includes('master')) {
            console.log('main branch not found, trying master...')
            request(masterUrl)
            return
          }
          reject(new Error('Repository not found (tried main and master branches)'))
          return
        }
        
        if (response.statusCode !== 200) {
          reject(new Error(`HTTP ${response.statusCode}`))
          return
        }
        
        response.pipe(file)
        file.on('finish', () => {
          file.close()
          resolve()
        })
      }).on('error', reject)
    }
    
    request(tarballUrl)
  })
  
  console.log('Extracting tarball...')
  
  // Extract tarball using system tar command
  execSync(`tar -xzf "${tempTarball}" -C "${cacheDir}"`, { stdio: 'inherit' })
  
  // Find extracted directory (GitHub names it repo-branch)
  const extractedDirs = fs.readdirSync(cacheDir).filter(d => 
    d.startsWith(`${repoName}-`) && d !== `${repoName}-download.tar.gz` && d !== `${repoName}-cached`
  )
  
  if (extractedDirs.length > 0) {
    const extractedPath = path.join(cacheDir, extractedDirs[0])
    // Rename to cached name
    if (fs.existsSync(targetDir)) {
      fs.rmSync(targetDir, { recursive: true })
    }
    fs.renameSync(extractedPath, targetDir)
  }
  
  // Create fake .git directory for compatibility
  const gitDir = path.join(targetDir, '.git')
  if (!fs.existsSync(gitDir)) {
    fs.mkdirSync(gitDir)
    fs.writeFileSync(path.join(gitDir, 'HEAD'), 'ref: refs/heads/main\n')
    fs.writeFileSync(path.join(gitDir, 'config'), `[remote "origin"]\n\turl = https://github.com/${owner}/${repoName}.git\n`)
  }
  
  // Cleanup temp tarball
  if (fs.existsSync(tempTarball)) {
    fs.unlinkSync(tempTarball)
  }
  
  console.log(`Downloaded to ${targetDir}`)
  return targetDir
})

ipcMain.handle('read-file', async (_, filePath: string) => {
  try {
    return fs.readFileSync(filePath, 'utf-8')
  } catch {
    return null
  }
})

ipcMain.handle('save-file', async (_, defaultPath: string, content: string) => {
  const result = await dialog.showSaveDialog(mainWindow!, {
    defaultPath,
    filters: [
      { name: 'Markdown', extensions: ['md'] },
      { name: 'JSON', extensions: ['json'] },
      { name: 'All Files', extensions: ['*'] },
    ],
  })

  if (!result.canceled && result.filePath) {
    fs.writeFileSync(result.filePath, content)
    return result.filePath
  }
  return null
})

ipcMain.handle('get-store', (_, key: string) => {
  return store.get(key)
})

ipcMain.handle('set-store', (_, key: string, value: unknown) => {
  store.set(key, value)
  return true
})

ipcMain.handle('get-backend-url', () => {
  return `http://127.0.0.1:${backendPort}`
})

ipcMain.handle('start-backend', async () => {
  return await startBackend()
})

ipcMain.handle('stop-backend', () => {
  stopBackend()
  return true
})

// PERFORMANCE OPTIMIZED: Health check with caching to reduce CPU usage
let lastHealthCheckTime = 0
let cachedHealthResult = false
const HEALTH_CHECK_CACHE_MS = 2000 // Cache result for 2 seconds

ipcMain.handle('check-backend', async () => {
  const now = Date.now()
  
  // Return cached result if recent enough (prevents rapid-fire checks)
  if (now - lastHealthCheckTime < HEALTH_CHECK_CACHE_MS) {
    return cachedHealthResult
  }
  
  const isHealthy = await checkBackendHealth(1, 2000) // Single retry, 2s timeout
  lastHealthCheckTime = now
  cachedHealthResult = isHealthy
  
  // Track status changes to notify frontend
  if (isHealthy !== lastBackendStatus) {
    lastBackendStatus = isHealthy
    mainWindow?.webContents.send('backend-status-changed', isHealthy)
  }
  
  return isHealthy
})

ipcMain.handle('show-notification', (_, title: string, body: string) => {
  if (Notification.isSupported()) {
    new Notification({ title, body }).show()
  }
})

ipcMain.handle('open-external', (_, url: string) => {
    shell.openExternal(url)
  })
}

// App lifecycle
app.whenReady().then(() => {
  registerIpcHandlers()
  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

app.on('window-all-closed', () => {
  stopBackend()
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('before-quit', () => {
  stopBackend()
})
