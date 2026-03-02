import { Config } from '@remotion/cli/config';

// 1. 关掉 Webpack 带有 eval 的映射模式
Config.overrideWebpackConfig((currentConfiguration) => {
  return {
    ...currentConfiguration,
    devtool: 'source-map',
  };
});

// 2. 强行关闭后台 Chromium 浏览器的 Web 安全策略
Config.setChromiumDisableWebSecurity(true);