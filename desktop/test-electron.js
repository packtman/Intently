const { app, BrowserWindow } = require('electron');
console.log('app exists:', !!app);
console.log('app.isPackaged:', app?.isPackaged);
app.whenReady().then(() => {
  console.log('App ready!');
  setTimeout(() => app.quit(), 1000);
});
