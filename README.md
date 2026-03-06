## 系統監視中心 (Python GUI)

一個在 **Windows** 上執行的系統監視工具，使用 **Python + PySide6** 製作圖形介面，提供以下功能：

- **系統資源監控**
  - CPU 使用率
  - 記憶體使用率（已用 / 總量，GB）
  - 各磁碟機使用率（所有本機分割區）
  - 網路上行 / 下行速度（KB/s 或 MB/s）
- **資料夾 / 檔案監控**
  - 監控指定資料夾內的檔案與子資料夾
  - 即時顯示新增、修改、刪除、移動等事件
- **連線 / Port 監控**
  - 顯示目前系統的網路連線狀況
  - 本機位址 / Port、遠端位址 / Port
  - 連線狀態（如 ESTABLISHED、LISTEN）
  - 對應程式的 PID 與程式名稱（若權限允許）

---

## 環境需求

- 作業系統：**Windows 10 / 11**
- Python：建議 **3.10 以上**
- 已安裝 Git（若要從 GitHub 取得原始碼）

---

## 安裝步驟

1. 下載或 clone 專案原始碼：

   ```powershell
   git clone https://github.com/brianshih04/monitor_gui.git
   cd monitor_gui
