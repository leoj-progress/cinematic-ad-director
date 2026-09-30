# cinematic-ad-director

一个把广告 brief 逐步推进到创意方向、脚本、分镜和视频生成提示词的 Codex skill。

## 包含内容

- `SKILL.md`：skill 的入口说明、阶段门和输出边界。
- `references/`：导演系统、摄影与分镜基础、视频模型交接规范，以及一个可选案例文件。
- `scripts/`：参考视频分析脚本。它们是辅助工具，不会替代创意判断。

这个仓库是社区项目，与 OpenAI 或任何视频模型厂商没有隶属关系。模型能力、案例观察和提示词格式应按具体模型和版本重新核对。

## 安装到 Codex

将仓库目录放到 Codex skills 目录，并保留目录名：

```powershell
git clone https://github.com/leoj-progress/cinematic-ad-director.git "$env:CODEX_HOME\skills\cinematic-ad-director"
```

如果没有设置 `CODEX_HOME`，可直接放到用户 skills 目录，例如：

```text
%USERPROFILE%\.codex\skills\cinematic-ad-director\
```

安装后重新打开 Codex 会话，在需要广告创意、脚本、分镜或视频提示词时调用 `cinematic-ad-director`。

## 使用范围

它会先确认项目阶段和关键事实，再按阶段交付：探索、方向选择、剧本、分镜、提示词和生成反馈。默认一次只推进一个阶段；只有用户明确批准上一阶段，才进入下一阶段。

它不会替用户确认产品功能、品牌资产、版权、模型能力或生成结果。没有真实视频输出时，只能做文字层面的检查。

## 可选的视频分析脚本

脚本需要 Python 3.10+、`numpy`、`Pillow`、`opencv-python`，以及系统中的 `ffmpeg` 和 `ffprobe`。安装 Python 依赖：

```powershell
python -m pip install -r requirements.txt
```

脚本只在用户提供参考视频或明确要求证据分析时使用。示例：

```powershell
python scripts/analyze_videos.py .\videos .\analysis
python scripts/analyze_shots.py .\videos .\shots --ffmpeg C:\path\to\ffmpeg.exe --ffprobe C:\path\to\ffprobe.exe
python scripts/analyze_motion_audio.py .\videos .\shots .\motion --ffmpeg C:\path\to\ffmpeg.exe --ffprobe C:\path\to\ffprobe.exe
python scripts/make_motion_strips.py .\videos .\shots\video-01.json .\strips --ffmpeg C:\path\to\ffmpeg.exe
```

以各脚本的 `--help` 输出为准。视频分析依赖的 `ffmpeg` 由用户自行安装，并受其自身许可证约束。

## 发布前检查

1. 把 README 中的仓库地址、作者身份和联系方式补齐。
2. 审核参考文档中的案例、引用、截图、品牌名称和模型专有内容，确认你有权公开发布。
3. 检查是否包含个人信息、客户 brief、内部提示词或未公开的产品资料。
4. 私有案例只放在本地的 `references/case-studies/` 中；如果案例不能公开，不要把它提交到仓库。
5. 确认许可证适合文档、提示词和 Python 脚本，并在 `LICENSE` 中替换版权持有人。

## 贡献

提交修改时请说明：修改了哪个阶段、解决了什么具体问题、是否改变了既有输出边界，以及如何验证文档或脚本。

## 许可证

本项目使用 MIT License，详见 [`LICENSE`](LICENSE)。版权持有人：leoj 无限进步。



