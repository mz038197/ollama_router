# GitHub 發布指南

本文檔提供完整的步驟，幫助你將 `ollama_router` 專案推送到 GitHub。

> **環境**: Windows SSH 遠端連接到 Ubuntu 系統

---

## 目錄

1. [在 GitHub 上建立倉庫](#在-github-上建立倉庫)
2. [設定 SSH Key](#設定-ssh-key)
3. [驗證 SSH 連線](#驗證-ssh-連線)
4. [推送到 GitHub](#推送到-github)
5. [驗證推送結果](#驗證推送結果)
6. [常見問題](#常見問題)

---

## 在 GitHub 上建立倉庫

### 步驟 1.1：登入 GitHub

在瀏覽器訪問 https://github.com，並使用你的帳號登入。

### 步驟 1.2：建立新倉庫

1. 點擊右上角的 **+** 圖標
2. 選擇 **New repository**
3. 填寫倉庫資訊：
   - **Repository name**: `ollama_router`
   - **Description** (可選): 
     ```
     OpenAI-compatible Ollama Router with Clean Architecture
     ```
   - **Public/Private**: 選擇 **Public**（如果要公開分享）或 **Private**（私密倉庫）
   - **Initialize this repository with**: **不要勾選任何選項**
     - ⚠️ 重要：不要勾選「Add a README file」、「Add .gitignore」或「Choose a license」
     - 因為你已有本地倉庫，初始化會造成衝突

4. 點擊 **Create repository**

### 步驟 1.3：記下倉庫 URL

建立完成後，GitHub 會顯示你的倉庫 URL，通常是：
```
https://github.com/YOUR_USERNAME/ollama_router.git
```

或使用 SSH 形式（後續推薦）：
```
git@github.com:YOUR_USERNAME/ollama_router.git
```

---

## 設定 SSH Key

使用 SSH 是更安全且便捷的方式，無需每次輸入密碼。

### 步驟 2.1：在 Ubuntu 伺服器上產生 SSH Key

在 SSH 終端執行：

```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
```

將 `your_email@example.com` 替換為你的 GitHub 帳號郵箱。

**互動提示**：
- `Enter file in which to save the key [/home/mkshaiadmin/.ssh/id_ed25519]:`
  → 直接按 **Enter**（使用預設路徑）

- `Enter passphrase (empty for no passphrase):`
  → 可按 **Enter** 留空，或輸入密碼保護私鑰（推薦輸入密碼）

- `Enter same passphrase again:`
  → 再次輸入相同密碼（如果有的話）

**完成後**會看到：
```
Your identification has been saved in /home/mkshaiadmin/.ssh/id_ed25519
Your public key has been saved in /home/mkshaiadmin/.ssh/id_ed25519.pub
The key fingerprint is:
SHA256:xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx your_email@example.com
```

### 步驟 2.2：查看並複製公鑰

執行以下指令查看公鑰：

```bash
cat ~/.ssh/id_ed25519.pub
```

**輸出範例**：
```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx your_email@example.com
```

📋 **複製整行輸出**（從 `ssh-ed25519` 到 email）。

### 步驟 2.3：在 GitHub 上新增 SSH Key

1. 登入 GitHub，訪問設定頁面：
   ```
   https://github.com/settings/keys
   ```

2. 點擊右上角的 **New SSH key**

3. 填寫表單：
   - **Title**: 填寫識別名稱，例如：
     ```
     Ubuntu Server ollama_router
     ```
   - **Key type**: 保持 **Authentication Key**
   - **Key**: 貼上剛才複製的公鑰（整行）

4. 點擊 **Add SSH key**

5. 如果要求輸入密碼，輸入你的 GitHub 帳號密碼確認

---

## 驗證 SSH 連線

### 步驟 3.1：測試 SSH 連線

在 Ubuntu 終端執行：

```bash
ssh -T git@github.com
```

### 步驟 3.2：確認輸出

**首次連線時會出現**：
```
The authenticity of host 'github.com (20.27.177.113)' can't be established.
ED25519 key fingerprint is SHA256:+DiY3wvvV6TuJJhbpZisF/zLDA0zPMSvHdkr4UvCOqU.
This key is not known by any other names
Are you sure you want to continue connecting (yes/no/[fingerprint])? 
```

📝 **輸入 `yes` 並按 Enter**

### 步驟 3.3：成功信號

連線成功後會看到：
```
Warning: Permanently added 'github.com' (ED25519) to the list of known hosts.
Hi YOUR_USERNAME! You've successfully authenticated, but GitHub does not provide shell access.
```

✅ 如果看到 `Hi YOUR_USERNAME!`，表示 SSH 設定成功！

---

## 推送到 GitHub

### 步驟 4.1：進入專案目錄

```bash
cd /home/mkshaiadmin/Programs/ollama_router
```

### 步驟 4.2：新增遠端倉庫

執行以下指令新增遠端倉庫（將 `YOUR_USERNAME` 替換為你的 GitHub 用戶名）：

```bash
git remote add origin git@github.com:YOUR_USERNAME/ollama_router.git
```

**例如**（使用 mkshaiadmin 作為用戶名）：
```bash
git remote add origin git@github.com:mkshaiadmin/ollama_router.git
```

### 步驟 4.3：驗證遠端倉庫設定

```bash
git remote -v
```

**預期輸出**：
```
origin  git@github.com:YOUR_USERNAME/ollama_router.git (fetch)
origin  git@github.com:YOUR_USERNAME/ollama_router.git (push)
```

### 步驟 4.4：重新命名分支為 main（可選）

GitHub 預設分支是 `main`。檢查目前分支：

```bash
git branch
```

如果當前分支是 `master`，可重新命名為 `main`：

```bash
git branch -M main
```

### 步驟 4.5：推送到 GitHub

執行推送指令：

```bash
git push -u origin main
```

📤 **指令說明**：
- `git push`: 推送提交
- `-u origin main`: 設定上游分支為 `origin/main`（後續可直接用 `git push`）

**預期輸出**（首次推送時）：
```
Enumerating objects: 48, done.
Counting objects: 100% (48/48), done.
Delta compression using up to 8 threads
Compressing objects: 100% (42/42), done.
Writing objects: 100% (48/48), X.XX KiB | X.XX MiB/s, done.
Total 48 (delta 16), reused 0 (delta 0), pack-reused 0
remote: Resolving deltas: 100% (16/16), done.
To github.com:YOUR_USERNAME/ollama_router.git
 * [new branch]      main -> main
Branch 'main' set up to track remote branch 'main' from 'origin'.
```

✅ 看到 `Branch 'main' set up to track remote branch 'main' from 'origin'` 表示推送成功！

---

## 驗證推送結果

### 步驟 5.1：在瀏覽器中查看倉庫

訪問你的 GitHub 倉庫：
```
https://github.com/YOUR_USERNAME/ollama_router
```

### 步驟 5.2：確認內容

頁面應該顯示：
- ✅ 所有專案檔案（src/, tests/, app.py 等）
- ✅ README.md 檔案內容
- ✅ 提交記錄（至少 5 個提交）
- ✅ 分支為 `main`

### 步驟 5.3：查看提交歷史

點擊 **Commits** 按鈕可查看所有提交記錄，應該包括：
```
修復 Bug 1 與 Bug 2：安全審計日誌與 API 契約驗證
Phase 2 完成：Clean Architecture 測試層實作與 REST API 錯誤模型標準化
實作 API 金鑰驗證與日誌系統
完善 .gitignore 設定
初始化 Ollama Router 專案
```

---

## 常見問題

### Q1: 錯誤 `ERROR: Repository not found`

**原因**：GitHub 上還沒建立倉庫。

**解決**：
1. 確認已在 GitHub 上建立 `ollama_router` 倉庫
2. 檢查倉庫名稱拼寫是否正確
3. 執行 `git remote -v` 驗證遠端 URL

### Q2: 錯誤 `Permission denied (publickey)`

**原因**：SSH key 未正確設定或 GitHub 上未新增公鑰。

**解決**：
1. 確認 SSH key 已產生：`ls ~/.ssh/id_ed25519`
2. 確認公鑰已在 GitHub settings 上新增：https://github.com/settings/keys
3. 測試連線：`ssh -T git@github.com`

### Q3: 如何後續推送更新？

**解決**：
```bash
# 進行修改並提交
git add .
git commit -m "描述你的改動"

# 推送到 GitHub
git push
```

由於已設定上游分支 (`-u origin main`)，後續可直接用 `git push`，無需每次指定 origin 和 main。

### Q4: 如何克隆倉庫到另一台電腦？

**使用 SSH**（推薦）：
```bash
git clone git@github.com:YOUR_USERNAME/ollama_router.git
cd ollama_router
```

**使用 HTTPS**（需輸入認證）：
```bash
git clone https://github.com/YOUR_USERNAME/ollama_router.git
cd ollama_router
```

### Q5: 如何查看遠端倉庫的狀態？

```bash
# 查看遠端信息
git remote -v

# 查看與遠端的差異
git status

# 查看本地未推送的提交
git log origin/main..main
```

---

## 快速參考命令

| 操作 | 命令 |
|------|------|
| 產生 SSH Key | `ssh-keygen -t ed25519 -C "email@example.com"` |
| 查看公鑰 | `cat ~/.ssh/id_ed25519.pub` |
| 測試 SSH 連線 | `ssh -T git@github.com` |
| 新增遠端倉庫 | `git remote add origin git@github.com:USERNAME/ollama_router.git` |
| 查看遠端設定 | `git remote -v` |
| 重新命名分支 | `git branch -M main` |
| 推送到 GitHub | `git push -u origin main` |
| 查看狀態 | `git status` |
| 查看提交記錄 | `git log --oneline` |

---

## 下一步

✅ 倉庫推送成功後，你可以：

1. **新增更多說明文件**
   - 在 GitHub 上新增 Issues 和 Discussions
   - 編寫貢獻指南 (CONTRIBUTING.md)
   - 建立 Release 版本

2. **設定 GitHub Actions**
   - 自動化測試 (CI/CD)
   - 自動部署

3. **管理協作者**
   - 邀請他人協作
   - 設定 branch protection rules

4. **發佈到 PyPI**
   - 如果要成為 Python 套件，可發佈到 PyPI
   - 參考 `pyproject.toml` 進行配置

---

## 參考資源

- [GitHub SSH Keys 文檔](https://docs.github.com/en/authentication/connecting-to-github-with-ssh)
- [Git 官方文檔](https://git-scm.com/doc)
- [本專案 GitHub 倉庫](https://github.com/YOUR_USERNAME/ollama_router)

---

**文檔版本**: 1.0  
**最後更新**: 2026-03-13  
**作者**: AI Assistant
