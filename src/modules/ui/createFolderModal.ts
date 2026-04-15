/**
 * 鏂板缓鏂囦欢澶规ā鎬佸璇濇
 */

import { invoke } from '../../shims/@tauri-apps/api/core';

export class CreateFolderModal {
  private modal: HTMLElement | null = null;
  private isVisible: boolean = false;
  private currentParentDir: string = '';

  constructor() {
    this.createModal();
    this.setupEventListeners();
  }

  private createModal(): void {
    // 鍒涘缓妯℃€佸鍣?    this.modal = document.createElement('div');
    this.modal.id = 'create-folder-modal';
    this.modal.innerHTML = `
      <div class="modal-overlay" style="
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 10000;
      ">
        <div class="modal-content" style="
          background: var(--bg-primary);
          border: 1px solid var(--border-color);
          border-radius: var(--border-radius-lg);
          width: 400px;
          max-width: 90vw;
          box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        ">
          <!-- 鏍囬鏍?-->
          <div style="
            padding: var(--spacing-md);
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
          ">
            <h3 style="
              margin: 0;
              color: var(--text-primary);
              font-size: 16px;
              font-weight: 600;
            ">鏂板缓鏂囦欢澶?/h3>
            <button id="create-folder-modal-close" style="
              background: none;
              border: none;
              color: var(--text-secondary);
              font-size: 18px;
              cursor: pointer;
              padding: 4px;
              border-radius: var(--border-radius-sm);
            " onmouseover="this.style.background='var(--bg-tertiary)'" onmouseout="this.style.background='none'">
              鉁?            </button>
          </div>

          <!-- 鍐呭鍖哄煙 -->
          <div style="padding: var(--spacing-md);">
            <!-- 鐖剁洰褰曟樉绀?-->
            <div style="margin-bottom: var(--spacing-md);">
              <label style="
                display: block;
                margin-bottom: var(--spacing-xs);
                color: var(--text-secondary);
                font-size: 12px;
                font-weight: 500;
              ">鍒涘缓浣嶇疆</label>
              <div id="create-folder-parent-dir" style="
                padding: var(--spacing-sm);
                background: var(--bg-secondary);
                border: 1px solid var(--border-color);
                border-radius: var(--border-radius-sm);
                color: var(--text-primary);
                font-family: monospace;
                font-size: 12px;
                word-break: break-all;
              "></div>
            </div>

            <!-- 鏂囦欢澶瑰悕绉拌緭鍏?-->
            <div style="margin-bottom: var(--spacing-md);">
              <label for="create-folder-name" style="
                display: block;
                margin-bottom: var(--spacing-xs);
                color: var(--text-secondary);
                font-size: 12px;
                font-weight: 500;
              ">鏂囦欢澶瑰悕绉?/label>
              <input
                type="text"
                id="create-folder-name"
                placeholder="璇疯緭鍏ユ枃浠跺す鍚嶇О"
                style="
                  width: 100%;
                  padding: var(--spacing-sm);
                  border: 1px solid var(--border-color);
                  border-radius: var(--border-radius-sm);
                  background: var(--bg-secondary);
                  color: var(--text-primary);
                  font-size: 14px;
                  box-sizing: border-box;
                "
              />
              <div id="create-folder-error" style="
                margin-top: var(--spacing-xs);
                color: var(--error-color);
                font-size: 11px;
                display: none;
              "></div>
            </div>

            <!-- 瀹屾暣璺緞棰勮 -->
            <div style="margin-bottom: var(--spacing-lg);">
              <label style="
                display: block;
                margin-bottom: var(--spacing-xs);
                color: var(--text-secondary);
                font-size: 12px;
                font-weight: 500;
              ">瀹屾暣璺緞</label>
              <div id="create-folder-full-path" style="
                padding: var(--spacing-sm);
                background: var(--bg-tertiary);
                border: 1px solid var(--border-color);
                border-radius: var(--border-radius-sm);
                color: var(--text-secondary);
                font-family: monospace;
                font-size: 11px;
                word-break: break-all;
                min-height: 20px;
              "></div>
            </div>

            <!-- 鎿嶄綔鎸夐挳 -->
            <div style="
              display: flex;
              gap: var(--spacing-sm);
              justify-content: flex-end;
            ">
              <button id="create-folder-cancel-btn" class="modern-btn secondary" style="
                padding: var(--spacing-sm) var(--spacing-md);
                font-size: 12px;
              ">
                鍙栨秷
              </button>
              <button id="create-folder-confirm-btn" class="modern-btn" style="
                padding: var(--spacing-sm) var(--spacing-md);
                background: var(--success-color);
                border: 1px solid var(--success-color);
                color: white;
                font-size: 12px;
                opacity: 0.5;
              " disabled>
                鍒涘缓
              </button>
            </div>
          </div>
        </div>
      </div>
    `;

    this.modal.style.display = 'none';
    document.body.appendChild(this.modal);
  }

  private setupEventListeners(): void {
    if (!this.modal) return;

    // 鍏抽棴鎸夐挳
    const closeBtn = document.getElementById('create-folder-modal-close');
    if (closeBtn) {
      closeBtn.onclick = () => this.hide();
    }

    // 鍙栨秷鎸夐挳
    const cancelBtn = document.getElementById('create-folder-cancel-btn');
    if (cancelBtn) {
      cancelBtn.onclick = () => this.hide();
    }

    // 纭鎸夐挳
    const confirmBtn = document.getElementById('create-folder-confirm-btn') as HTMLButtonElement | null;
    if (confirmBtn) {
      confirmBtn.onclick = () => this.createFolder();
    }

    // 鏂囦欢澶瑰悕绉拌緭鍏?    const nameInput = document.getElementById('create-folder-name') as HTMLInputElement;
    if (nameInput) {
      nameInput.oninput = () => this.validateInput();
      nameInput.onkeydown = (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          if (confirmBtn && !confirmBtn.disabled) {
            this.createFolder();
          }
        }
      };
    }

    // ESC閿叧闂?    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.isVisible) {
        this.hide();
      }
    });

    // 鐐瑰嚮閬僵鍏抽棴
    this.modal.onclick = (e) => {
      if (e.target === this.modal) {
        this.hide();
      }
    };
  }

  public show(parentDir: string): void {
    if (!this.modal) return;

    this.currentParentDir = parentDir;
    this.isVisible = true;

    // 鏇存柊鐖剁洰褰曟樉绀?    const parentDirEl = document.getElementById('create-folder-parent-dir');
    if (parentDirEl) {
      parentDirEl.textContent = parentDir;
    }

    // 閲嶇疆杈撳叆妗?    const nameInput = document.getElementById('create-folder-name') as HTMLInputElement;
    if (nameInput) {
      nameInput.value = '';
      nameInput.focus();
    }

    // 閲嶇疆鐘舵€?    this.validateInput();
    this.hideError();

    this.modal.style.display = 'flex';
  }

  public hide(): void {
    if (!this.modal) return;
    
    this.modal.style.display = 'none';
    this.isVisible = false;
    this.currentParentDir = '';
  }

  private validateInput(): void {
    const nameInput = document.getElementById('create-folder-name') as HTMLInputElement;
    const confirmBtn = document.getElementById('create-folder-confirm-btn') as HTMLButtonElement;
    const fullPathEl = document.getElementById('create-folder-full-path');
    
    if (!nameInput || !confirmBtn || !fullPathEl) return;

    const folderName = nameInput.value.trim();
    let isValid = true;
    let errorMessage = '';

    // 妫€鏌ユ槸鍚︿负绌?    if (!folderName) {
      isValid = false;
      fullPathEl.textContent = '';
    } else {
      // 妫€鏌ユ枃浠跺悕鏄惁鍖呭惈闈炴硶瀛楃
      const invalidChars = /[\/\\:*?"<>|]/;
      if (invalidChars.test(folderName)) {
        isValid = false;
        errorMessage = '鏂囦欢澶瑰悕绉颁笉鑳藉寘鍚互涓嬪瓧绗? / \\ : * ? " < > |';
      }
      
      // 妫€鏌ユ槸鍚︿互鐐瑰紑澶存垨缁撳熬
      if (folderName.startsWith('.') || folderName.endsWith('.')) {
        isValid = false;
        errorMessage = '鏂囦欢澶瑰悕绉颁笉鑳戒互鐐瑰紑澶存垨缁撳熬';
      }
      
      // 妫€鏌ラ暱搴?      if (folderName.length > 255) {
        isValid = false;
        errorMessage = '鏂囦欢澶瑰悕绉拌繃闀匡紙鏈€澶?55涓瓧绗︼級';
      }
      
      // 鏇存柊瀹屾暣璺緞棰勮
      if (isValid) {
        const fullPath = this.joinRemotePath(this.currentParentDir, folderName);
        fullPathEl.textContent = fullPath;
      } else {
        fullPathEl.textContent = '';
      }
    }

    // 鏇存柊鎸夐挳鐘舵€?    confirmBtn.disabled = !isValid;
    confirmBtn.style.opacity = isValid ? '1' : '0.5';

    // 鏄剧ず鎴栭殣钘忛敊璇俊鎭?    if (errorMessage) {
      this.showError(errorMessage);
    } else {
      this.hideError();
    }
  }

  private showError(message: string): void {
    const errorEl = document.getElementById('create-folder-error');
    if (errorEl) {
      errorEl.textContent = message;
      errorEl.style.display = 'block';
    }
  }

  private hideError(): void {
    const errorEl = document.getElementById('create-folder-error');
    if (errorEl) {
      errorEl.style.display = 'none';
    }
  }

  private joinRemotePath(dir: string, name: string): string {
    const base = dir.endsWith('/') ? dir.slice(0, -1) : dir;
    if (!base) return `/${name}`;
    return `${base}/${name}`;
  }

  private async createFolder(): Promise<void> {
    const nameInput = document.getElementById('create-folder-name') as HTMLInputElement;
    if (!nameInput) return;

    const folderName = nameInput.value.trim();
    if (!folderName) return;

    const confirmBtn = document.getElementById('create-folder-confirm-btn') as HTMLButtonElement;
    const cancelBtn = document.getElementById('create-folder-cancel-btn') as HTMLButtonElement;
    
    // 绂佺敤鎸夐挳
    confirmBtn.disabled = true;
    cancelBtn.disabled = true;
    confirmBtn.textContent = '鍒涘缓涓?..';

    try {
      // 鏋勫缓瀹屾暣璺緞
      const fullPath = this.joinRemotePath(this.currentParentDir, folderName);
      
      // 璋冪敤鍚庣API鍒涘缓鏂囦欢澶?      await invoke('sftp_create_directory', {
        remotePath: fullPath
      });

      (window as any).showNotification && (window as any).showNotification(`鏂囦欢澶瑰垱寤烘垚鍔? ${folderName}`, 'success');
      
      // 鍒锋柊鏂囦欢鍒楄〃
      if ((window as any).sftpManager && (window as any).sftpManager.refreshCurrentDirectory) {
        (window as any).sftpManager.refreshCurrentDirectory();
      }

      this.hide();

    } catch (error) {
      console.error('鍒涘缓鏂囦欢澶瑰け璐?', error);
      (window as any).showNotification && (window as any).showNotification(`鍒涘缓鏂囦欢澶瑰け璐? ${error}`, 'error');
      this.showError(`鍒涘缓澶辫触: ${error}`);
    } finally {
      // 鎭㈠鎸夐挳鐘舵€?      confirmBtn.disabled = false;
      cancelBtn.disabled = false;
      confirmBtn.textContent = '鍒涘缓';
    }
  }
}


