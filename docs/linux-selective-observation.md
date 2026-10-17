# Linux 按需观察

Linux 的 `get_app_state` 可以选择读取 AX 或截图。原生参数 `include_ax` / `include_screenshot` 对应 JS 的 `includeAX` / `includeScreenshot`，均默认 `true`，不能同时设为 `false`。

| 需要什么 | JS 调用 | 实际采集 |
| --- | --- | --- |
| 只读控件和选区 | `await app.getAXState({includeScreenshot: false})` | AX、焦点、选区；不截图、不编码 |
| 只看画面 | `await app.getScreenshot({includeAX: false})` | 截图；不遍历 AX、不查焦点和选区 |
| 两者都要 | `await app.getAXStateAndScreenshot()` | 完整 AX 和截图 |

```js
var app = await cua.getApp("gedit", {initialState: false});
await app.getAXState({includeScreenshot: false});
```

只取截图后，旧元素索引及查询别名会失效，包括应用重启前的索引。坐标操作仍可使用本次观察的窗口位置；元素操作要先重新读取 AX。窗口标题相同不代表旧索引仍然有效。

不传参数的调用保持原行为。这两个采集开关目前只在 Linux 实现，macOS / Windows 尚未实现。

## 和重复截图的关系

macOS / Linux 下的 JS 动作已默认关闭自动回读；`getAXState()` 本身也不向模型输出图片，但默认仍会在 native 层采集图片后丢弃。`includeScreenshot: false` 可以在 Linux 连这部分采集和编码一起省掉。直接使用 native MCP 时，它也会省去返回的 image block。

这里不做截图比较：请求了截图，即使画面相同也照常返回。“画面未变则省略图片”需要单独实现，通常仍要先截图再比较，主要减少传输和模型输入。后续可按会话、应用和窗口保存精确图像指纹，首次观察及状态重置时返回图片，并提供强制返回方式；不能仅凭 AX 没变化就认定画面没变化。

## 测试

```sh
python3 apps/OpenComputerUseLinux/runtime_test.py
(cd apps/OpenComputerUseLinux && go test ./...)
node --test scripts/node-repl/*.test.mjs
```

真实 GTK 测试复用 [私有 D-Bus / Xvfb 环境](linux-action-read-back.md)，另外需要 Node.js：

```sh
(cd apps/OpenComputerUseLinux && go build -o /tmp/ocu-observation-test .)
bash scripts/run-linux-read-back-smoke.sh /tmp/ocu-observation-test --observation-checks
```

脚本包装真实生产采集函数，确认关闭的通道没有被调用；再通过 native MCP 和 Worker JS 检查 PNG、选区、旧索引拒绝、坐标操作及 AX 恢复。GTK 独立导出状态确认动作结果。这是 X11 / GTK / AT-SPI 测试，不代表 Wayland 或完整任务性能测试。
