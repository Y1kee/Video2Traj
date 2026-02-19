# GitHub 仓库创建指南

按以下步骤在 GitHub 创建 **video2traj** 私有仓库。

---

## 方法一：通过网页创建（推荐）

### 1. 创建新仓库

1. 打开 [https://github.com/new](https://github.com/new)
2. 填写表单：

| 配置项 | 填写内容 |
|--------|----------|
| **Repository name** | `video2traj` |
| **Description** | `A lightweight tool for robotics researchers to generate stroboscopic trajectory figures from experiment videos.` |
| **Visibility** | **Private**（私有） |
| **Initialize this repository with** | 不勾选 README、.gitignore、license（本地已有） |

3. 点击 **Create repository**

### 2. 添加标签（Topics）

仓库创建后：

1. 进入仓库主页
2. 点击右侧 **About** 旁的齿轮图标
3. 在 **Topics** 中添加（逐个回车确认）：
   - `robotics`
   - `computer-vision`
   - `trajectory`
   - `motion-planning`
   - `visualization`
   - `research-tools`
   - `opencv`
4. 确认 Description 已正确填写
5. 点击 **Save changes**

### 3. 推送本地代码

在项目目录 `g:\Video2Traj` 下执行：

```bash
# 添加远程仓库（将 YOUR_USERNAME 替换为你的 GitHub 用户名）
git remote add origin https://github.com/YOUR_USERNAME/video2traj.git

# 推送（首次推送 master 分支）
git push -u origin master
```

如使用 SSH：

```bash
git remote add origin git@github.com:YOUR_USERNAME/video2traj.git
git push -u origin master
```

---

## 方法二：安装 GitHub CLI 后用命令行创建

```bash
# 安装 gh（Windows 使用 winget）
winget install GitHub.cli

# 安装后重启终端，登录
gh auth login

# 创建私有仓库
gh repo create video2traj --private --source=. --remote=origin --description "A lightweight tool for robotics researchers to generate stroboscopic trajectory figures from experiment videos." --push

# 添加标签（需在网页端完成，或使用 gh api）
```

---

## 配置汇总

| 项目 | 值 |
|------|-----|
| 仓库名称 | video2traj |
| 简介 | A lightweight tool for robotics researchers to generate stroboscopic trajectory figures from experiment videos. |
| 可见性 | Private |
| 标签 | robotics, computer-vision, trajectory, motion-planning, visualization, research-tools, opencv |
| README H1 | Video2TrajectoryFigure: Visual Trajectory Extraction |
