# Mobile Chat Sticker Packs

新增本地表情包时，在本目录下创建一个英文 `pack_id` 文件夹：

```text
mods/mobile-chat/static/stickers/<pack_id>/
```

例如：

```text
mods/mobile-chat/static/stickers/katishiya/
```

每个表情包目录内放置 `.png` 文件，可选放置 `manifest.json`。后台表情包管理会扫描这些目录，并保存每个表情包自己的 `manifest.json`。

`default/` 是内置 sticker id 协议说明，不作为可编辑图片表情包。
