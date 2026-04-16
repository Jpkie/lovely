/**
 * Tauri invoke 适配器。
 *
 * 该模块提供与 Tauri `invoke` 兼容的接口，但底层通过 HTTP 请求调用
 * Python FastAPI 后端。
 */

import pythonApi from './python-api.config';

/**
 * 兼容 Tauri `invoke` 的适配函数。
 *
 * @param cmd Tauri 命令名称
 * @param args 命令参数
 * @returns 与原 Tauri invoke 语义一致的结果
 */
export async function invoke(cmd: string, args?: Record<string, any>): Promise<any> {
  const authType = args?.authType ?? args?.auth_type;
  const keyPath = args?.keyPath ?? args?.key_path;
  const keyPassphrase = args?.keyPassphrase ?? args?.key_passphrase;
  const certificatePath = args?.certificatePath ?? args?.certificate_path;
  const encryptedPassword = args?.encryptedPassword ?? args?.encrypted_password;

  // 将 Tauri 命令名映射到 Python API 方法
  const commandMap: Record<string, (...params: any[]) => Promise<any>> = {
    // 窗口控制
    minimize_window: () => pythonApi.minimizeWindow(),
    toggle_maximize: () => pythonApi.toggleMaximize(),
    close_window: () => pythonApi.closeWindow(),
    open_devtools: () => pythonApi.openDevtools(),

    // 主题管理
    get_theme_settings: () => pythonApi.getThemeSettings(),
    set_current_theme: () => pythonApi.setCurrentTheme(args?.theme),

    // 设置管理
    get_app_settings: () => pythonApi.getAppSettings(),
    save_app_settings: () => pythonApi.saveAppSettings(args?.new_settings || args),
    read_settings_file: () => pythonApi.readSettingsFile(),
    write_settings_file: () => pythonApi.writeSettingsFile(args?.content),
    get_system_fonts: () => pythonApi.getSystemFonts(),

    // SSH 连接管理
    load_ssh_connections: () => pythonApi.loadSshConnections(),
    save_ssh_connections: () => pythonApi.saveSshConnections(args?.connections),
    encrypt_password: () => pythonApi.encryptPassword(args?.password),
    decrypt_password: () => pythonApi.decryptPassword(encryptedPassword),

    ssh_connect_with_auth: () => pythonApi.sshConnectWithAuth({
      host: args?.host, port: args?.port, username: args?.username,
      authType, password: args?.password,
      keyPath, keyPassphrase,
      certificatePath,
    }),

    ssh_test_connection: () => pythonApi.sshTestConnection({
      host: args?.host, port: args?.port, username: args?.username,
      authType, password: args?.password,
      keyPath, keyPassphrase,
    }),

    ssh_execute_command: () => pythonApi.sshExecuteCommand(args?.command),
    ssh_disconnect: () => pythonApi.sshDisconnect(),

    // SSH/SFTP 直接命令
    ssh_connect_direct: () => pythonApi.sshConnectDirect(args?.host, args?.port, args?.username, args?.password),
    ssh_disconnect_direct: () => pythonApi.sshDisconnectDirect(),
    ssh_execute_command_direct: () => pythonApi.sshExecuteCommandDirect(args?.command, args?.username),
    ssh_execute_dashboard_command_direct: () => pythonApi.sshExecuteDashboardCommandDirect(args?.command),
    ssh_execute_emergency_command_direct: () => pythonApi.sshExecuteEmergencyCommandDirect(args?.command, args?.username),
    execute_detection_command: () => pythonApi.executeDetectionCommand(args?.command),

    ssh_get_connection_status: () => pythonApi.sshGetConnectionStatus(),
    test_ssh_performance: () => pythonApi.testSshPerformance(),
    diagnose_shell_performance: () => pythonApi.diagnoseShellPerformance(),
    detect_system_type: () => pythonApi.detectSystemType(),

    // SFTP 文件操作
    sftp_list_files: () => pythonApi.sftpListFiles(args?.path),
    sftp_read_file: () => pythonApi.sftpReadFile(args?.path, args?.max_bytes),
    sftp_write_file: () => pythonApi.sftpWriteFile(args?.path, args?.content),
    sftp_upload: () => pythonApi.sftpUpload(args?.local_path ?? args?.localPath, args?.remote_path ?? args?.remotePath),
    sftp_download: () => pythonApi.sftpDownload(args?.remote_path ?? args?.remotePath, args?.local_path ?? args?.localPath),
    sftp_create_directory: () => pythonApi.sftpCreateDirectory(args?.remote_path ?? args?.remotePath),
    sftp_compress: () => pythonApi.sftpCompress(args?.source_path, args?.target_path, args?.format),
    sftp_extract: () => pythonApi.sftpExtract(args?.archive_path, args?.target_dir, args?.overwrite),
    sftp_chmod: () => pythonApi.sftpChmod(args?.path, args?.mode),
    sftp_get_file_details: () => pythonApi.sftpGetFileDetails(args?.path),
    save_temp_file: () => pythonApi.saveTempFile(args?.file_name ?? args?.fileName, args?.data),

    // 文件安全分析
    sftp_file_analysis: () => pythonApi.sftpFileAnalysis(args?.path),
    sftp_file_analysis_independent: () => pythonApi.sftpFileAnalysisIndependent(args?.path),

    // Bash 环境和命令补全
    get_bash_environment_info: () => pythonApi.getBashEnvironmentInfo(),
    get_command_completion: () => pythonApi.getCommandCompletion(args?.input),

    // 安全检测命令
    detect_port_scan: () => pythonApi.detectPortScan(),
    detect_user_audit: () => pythonApi.detectUserAudit(),
    detect_backdoor: () => pythonApi.detectBackdoor(),
    detect_process_analysis: () => pythonApi.detectProcessAnalysis(),
    detect_file_permission: () => pythonApi.detectFilePermission(),
    detect_ssh_audit: () => pythonApi.detectSshAudit(),
    detect_log_analysis: () => pythonApi.detectLogAnalysis(),
    detect_firewall_check: () => pythonApi.detectFirewallCheck(),
    detect_cpu_test: () => pythonApi.detectCpuTest(),
    detect_memory_test: () => pythonApi.detectMemoryTest(),
    detect_disk_test: () => pythonApi.detectDiskTest(),
    detect_network_test: () => pythonApi.detectNetworkTest(),

    // 基线检测
    detect_password_policy: () => pythonApi.detectPasswordPolicy(),
    detect_sudo_config: () => pythonApi.detectSudoConfig(),
    detect_pam_config: () => pythonApi.detectPamConfig(),
    detect_account_lockout: () => pythonApi.detectAccountLockout(),
    detect_selinux_status: () => pythonApi.detectSelinuxStatus(),
    detect_kernel_params: () => pythonApi.detectKernelParams(),
    detect_system_updates: () => pythonApi.detectSystemUpdates(),
    detect_unnecessary_services: () => pythonApi.detectUnnecessaryServices(),
    detect_auto_start_services: () => pythonApi.detectAutoStartServices(),
    detect_audit_config: () => pythonApi.detectAuditConfig(),
    detect_history_audit: () => pythonApi.detectHistoryAudit(),
    detect_ntp_config: () => pythonApi.detectNtpConfig(),
    detect_dns_config: () => pythonApi.detectDnsConfig(),

    // SSH 终端管理
    ssh_create_terminal_session: () => pythonApi.sshCreateTerminalSession(args?.terminal_id, args?.cols, args?.rows),
    ssh_close_terminal_session: () => pythonApi.sshCloseTerminalSession(args?.terminal_id),
    ssh_close_all_terminal_sessions: () => pythonApi.sshCloseAllTerminalSessions(),
    ssh_send_input: () => pythonApi.sshSendInput(args?.terminal_id, args?.data),
    ssh_get_completion: () => pythonApi.sshGetCompletion(args?.input),

    // 日志分析
    read_system_log: () => pythonApi.readSystemLog({
      logPath: args?.log_path ?? args?.logPath,
      page: args?.page,
      pageSize: args?.page_size ?? args?.pageSize,
      filter: args?.filter,
      dateFilter: args?.date_filter ?? args?.dateFilter,
    }),
    read_journalctl_log: () => pythonApi.readJournalctlLog({
      page: args?.page,
      pageSize: args?.page_size ?? args?.pageSize,
      unit: args?.unit ?? args?.journalUnit,
      filter: args?.filter,
      since: args?.since,
      until: args?.until,
    }),
    list_log_files: () => pythonApi.listLogFiles(),
    get_log_file_info: () => pythonApi.getLogFileInfo(args?.log_path),

    // 加密和设备信息
    get_rsa_public_key: () => pythonApi.getRsaPublicKey(),
    get_device_uuid: () => pythonApi.getDeviceUuid(),
  };

  const handler = commandMap[cmd];
  if (handler) {
    return handler();
  }

  console.warn(`[invoke-adapter] 未映射的命令: ${cmd}`);
  throw new Error(`未映射的命令: ${cmd}`);
}

export default invoke;
