# 小宇宙播客下载器 · Windows 桌面版

这是基于 https://github.com/daruizi/xiaoyuzhou-downloader 改造的中文图形界面便携版。无需安装 Python，无需命令行。适用于 Windows 10 / 11 的 64 位电脑，已在当前 Windows 11 电脑实际启动。

## 启动和使用

1. 将 ZIP 解压到可以写入的文件夹。不要直接在压缩包内运行。
2. 双击 `PodcastDownloader.exe`。
3. 输入播客名称、小宇宙播客链接或发布者提供的 RSS 地址，点击“获取节目”。名称搜索有多个结果时，从下拉框选择正确播客。
4. 点击节目左侧选择列勾选，或点“只选前 3 期”。选择保存目录，点击“下载勾选节目”。
5. 用“暂停”停止当前下载。再次点击下载即可继续；若服务器不支持续传，自动从头下载。完成的文件会校验并跳过。
6. 点击“打开文件夹”，即可用本机播放器播放已下载的音频。

默认音频保存到 exe 同目录的 `downloads` 文件夹，按播客和年月归档。RSS 没有发布日期时归入 `unknown`。偏好保存在同目录的 `settings.json`。请把程序放在普通可写文件夹。

## 随包测试音频

“测试音频”中包含 LibriVox 的 Short Poetry Collection 001 和 002 两个 RSS 专辑中的 4 段公有领域诗歌朗读：Annabel Lee、Dora、From Lines Composed a Few Miles Above Tintern Abbey、Abou Ben Adhem。它们是以 RSS 发布的朗读音频，不是小宇宙商业播客。

LibriVox 将录音捐赠至公有领域：https://librivox.org/pages/public-domain/ 。原作品作者分别为 Edgar Allan Poe（1849 年去世）、Alfred Tennyson（1892 年去世）、William Wordsworth（1850 年去世）和 Leigh Hunt（1859 年去世），均为已过通常版权期限的古典作品。不要将“公开可下载”理解为所有节目都可以任意转载。

测试记录在 `下载测试报告.json`，包括原始音频地址、大小、SHA-256、MP3 时长和重复下载校验。真实 RSS 获取成功后保存了快照，后续主站间歇返回 522/525，因此测试继续从快照解析原音频链接。可以点击“导入 RSS”选择随包 XML 快照来复现。

## 支持范围

小宇宙链接通过页面中的播客名称寻找 Apple Podcasts 的公开 RSS，搜索结果可能需要人工确认。只有小宇宙独家发布、没有公开 RSS 的节目可能无法获取；程序会提示使用发布者提供的 RSS。没有绕过付费、登录或访问限制。当前下载队列依次执行，界面保持可操作。

## 来源和构建

上游 README 标注 MIT License；本包保留上游源码与 README，不代替作者补写缺失的许可证文件。桌面版修改集中在 `desktop.py` 和 `engine.py`，上游解析器在 `upstream.py`。下载流程使用新的适配器，不调用上游带删除操作的下载实现；本程序没有删除音频功能。

源码包用于后续修改。构建环境：Python 3.12、Tkinter、requests、PyInstaller，使用 `python -m PyInstaller --windowed --onefile --name PodcastDownloader desktop.py`。正常电脑使用标准 Python 的完整 Tk/Tcl 环境即可构建。


## 下载最终 Windows 版本

[GitHub Releases](https://github.com/Anthony20040603/xiaoyuzhou-downloader-windows/releases/latest) 提供 EXE、便携 ZIP 和源码 ZIP。

[网页版](https://anthony20040603.github.io/podcast-downloader-web/) 单独维护。
