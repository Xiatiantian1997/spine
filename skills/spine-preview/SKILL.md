---
name: spine-preview
description: 对用户上传的 Spine ZIP/JSON/atlas/贴图进行批量识别、动画预览与 GIF 导出；优先复用经过验证的渲染程序，不要每次重新手写骨骼播放器。
---

# Spine 动画预览 Skill（实验版）

## 触发条件
用户上传 Spine 压缩包并要求“看看”“拼角色”“多导出几个 GIF”“分析动作”“提取曲线”时使用。先检查是否有完整的 `.json` / `.skel`、`.atlas`、`.png`，优先按角色/动画批量处理；无需重复询问每个角色。

## 标准操作
1. 对 ZIP 做完整性检查与安全路径检查；不直接覆盖原始素材，不运行压缩包内的脚本或可执行文件。遇到 7z / 分卷包先检查分卷完整性、解压工具和空间。
2. 清点资源组、骨骼数据版本、动画名称、贴图页与图层。JSON 与 SKEL 可能为同一角色的两种导出，不应重复计人数。
3. 优先使用**与 Spine 数据版本相匹配、授权合规的官方 runtime / Skeleton Viewer** 还原网格、蒙皮、IK、transform/path constraints、deform、drawOrder、slot attachment 等。官方资料：https://esotericsoftware.com/spine-runtimes 。使用 runtime 时检查 Spine Editor/Runtime 许可证，不把源码误认为无限制开源。
4. 若暂时无法运行官方 runtime，可使用 `scripts/preview.py` 的**实验性 JSON 渲染**作为降级预览；必须标注不支持完整约束、deform 等，不能把它作为原版动作准确性证据。
5. 先出少量 GIF（例如 3 个不同角色，每个 10–16 帧），用户能在消息内直接看到。可再提供 MP4、静态首帧和局部放大；文件存在且已验证才给 sandbox 链接。
6. 同时记录角色编号、动画名、时长、预览质量、渲染限制。不要把“贴图名称包含 breast/touch”误当作确有独立软组织回弹。
7. 需要研究经验函数时，先取得可靠的局部相对运动轨迹，分离身体主运动、相机变化与局部响应，再拟合正弦/缓动/阻尼模型，注明拟合误差、适用条件和非唯一性。

## 对话交付
- 直接给 GIF 和一句人物描述，不要先给一堆骨骼线。
- 批量导出时区分角色编号与动作名称，提供实际完成数量。
- 不声称已完整复现原作，除非与官方 runtime 的播放结果对照通过。
- 游戏原始贴图、受限模型、用户私人素材留在本地，不提交公开仓库。

## 本地实验脚本
仓库的 `scripts/preview.py` 为简化 JSON 网格 GIF 预览器，需要 Python、numpy、Pillow、opencv-python。示例：
```bash
python scripts/preview.py "5.22棕色更新.zip" --character char020601 --animation idle --frames 12 --out char020601.gif
```
该脚本不能替代 Spine runtime；若缺少数据或版本不兼容，明确报告失败，不生成伪造的动画。

## 后续接口
未来输出结构化 manifest（资源 ID、版本、动画名、时长、骨骼曲线、网格/约束支持情况、预览文件），供幻真画室通过本地 API 或文件接口读取；Skill 只是调用说明，实际运行依赖执行环境安装脚本与依赖。
