// Karma configuration
// https://karma-runner.github.io/1.0/config/configuration-file.html
//
// ChromeHeadlessCI：Docker / 无 GUI 服务器兼容 launcher（--no-sandbox --disable-gpu --disable-dev-shm-usage）。
// Chrome 二进制由系统安装的 google-chrome-stable 提供（/usr/bin/google-chrome-stable），
// karma-chrome-launcher 的 ChromeHeadless 会自动发现 PATH 中的 chrome。

module.exports = function (config) {
  config.set({
    basePath: '',
    frameworks: ['jasmine'],
    plugins: [
      require('karma-jasmine'),
      require('karma-chrome-launcher'),
    ],
    client: {
      jasmine: {},
      clearContext: false,
    },
    reporters: ['progress'],
    port: 9876,
    colors: true,
    logLevel: config.LOG_INFO,
    autoWatch: false,
    browsers: ['ChromeHeadlessCI'],
    singleRun: true,
    restartOnFileChange: false,
    customLaunchers: {
      ChromeHeadlessCI: {
        base: 'ChromeHeadless',
        flags: [
          '--no-sandbox',
          '--disable-gpu',
          '--headless',
          '--disable-dev-shm-usage',
          '--remote-debugging-port=9222',
        ],
      },
    },
  });
};
