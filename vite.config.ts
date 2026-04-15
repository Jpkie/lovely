import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import vitePluginBundleObfuscator from 'vite-plugin-bundle-obfuscator';

// https://vite.dev/config/
export default defineConfig(async () => ({
  plugins: [
    vue(),
    // 仅在生产构建时启用混淆
    process.env.NODE_ENV === 'production' && vitePluginBundleObfuscator({
      enable: true,
      log: true,
      autoExcludeNodeModules: true,
      options: {
        compact: true,
        controlFlowFlattening: false,
        deadCodeInjection: false,
        debugProtection: false,
        debugProtectionInterval: 0,
        disableConsoleOutput: false,
        identifierNamesGenerator: 'hexadecimal',
        log: false,
        numbersToExpressions: false,
        renameGlobals: false,
        selfDefending: false,
        simplify: true,
        splitStrings: false,
        stringArray: true,
        stringArrayCallsTransform: false,
        stringArrayEncoding: ['base64'],
        stringArrayIndexShift: true,
        stringArrayRotate: true,
        stringArrayShuffle: true,
        stringArrayWrappersCount: 1,
        stringArrayWrappersChainedCalls: true,
        stringArrayWrappersParametersMaxCount: 2,
        stringArrayWrappersType: 'variable',
        stringArrayThreshold: 0.75,
        unicodeEscapeSequence: false,
      }
    })
  ],

  // Vite options tailored for Tauri development and only applied in `tauri dev` or `tauri build`
  //
  // 1. prevent vite from obscuring rust errors
  clearScreen: false,
  // 2. tauri expects a fixed port, fail if that port is not available
  server: {
    port: 1420,
    strictPort: true,
    proxy: {
      "/api/v1": {
        target: "http://127.0.0.1:3001",
        changeOrigin: true,
      },
    },
    watch: {
      // 3. tell vite to ignore watching `src-tauri`
      ignored: ["**/src-tauri/**"],
    },
  },

  preview: {
    proxy: {
      "/api/v1": {
        target: "http://127.0.0.1:3001",
        changeOrigin: true,
      },
    },
  },
  
  // 4. force polka to use a different route
  base: './',
  
  // 配置多页面应用
  build: {
    rollupOptions: {
      input: {
        main: 'index.html',
        'ssh-terminal': 'ssh-terminal.html',
        'container-terminal': 'container-terminal.html',
        // 可以在这里添加更多页面
      },
      onwarn(warning: any, warn: any) {
        // 忽略source map相关警告
        if (warning.code === 'SOURCEMAP_ERROR') return;
        if (warning.message && warning.message.includes('source map')) return;
        warn(warning);
      },
      output: {
        // 确保资源路径正确
        assetFileNames: (assetInfo: any) => {
          if (assetInfo.name.endsWith('.woff') || assetInfo.name.endsWith('.woff2')) {
            return 'assets/[name][extname]';
          }
          return 'assets/[name]-[hash][extname]';
        },
        entryFileNames: 'assets/[name]-[hash].js',
        chunkFileNames: 'assets/[name]-[hash].js',
        // 代码分块优化
        manualChunks(id: string) {
          if (id.indexOf('node_modules') !== -1) {
            return 'vendor';
          }
        },
      },
    },
    // 使用相对路径
    outDir: './dist',
    // 确保静态资源也使用相对路径
    assetsDir: 'assets',
    // 减少对外部CDN的依赖
    minify: 'terser',
    cssCodeSplit: false,
    sourcemap: process.env.NODE_ENV === 'development'
  },
  
  // 5. 使入口点可在浏览器中访问
  resolve: {
    alias: [
      { find: '@', replacement: '/src' },
      { find: /^@\//, replacement: '/src/' }
    ]
  },
  
  envPrefix: [
    'VITE_',
  ],
}));
