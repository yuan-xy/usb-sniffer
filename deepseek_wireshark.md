## 解释wireshark插件的配置：
 --extcap-dlts
dlt {number=288}{name=USB}{display=USB}
--extcap-interfaces
interface {value=usb_sniffer}{display=USB Sniffer}

这段代码是 Wireshark 插件的配置片段，用于定义插件的扩展捕获（extcap）功能。让我逐步解释这些配置的作用：

### 1. `--extcap-dlts` 参数
这个参数用于声明插件支持的链路层类型（Data Link Types, DLTs）。

- `dlt {number=288}{name=USB}{display=USB}`:
  - `number=288`: 指定链路层类型的编号，288 是 USB 的官方 DLT 编号
  - `name=USB`: 内部使用的名称标识
  - `display=USB`: 在 Wireshark 界面中显示的名称

这个声明告诉 Wireshark 该插件可以捕获 USB 流量，并使用 DLT 288 作为链路层类型。

### 2. `--extcap-interfaces` 参数
这个参数用于列出插件提供的捕获接口。

- `interface {value=usb_sniffer}{display=USB Sniffer}`:
  - `value=usb_sniffer`: 接口的内部标识符，用于命令行引用
  - `display=USB Sniffer`: 在 Wireshark 界面中显示的友好名称

这表示插件提供了一个名为 "USB Sniffer" 的捕获接口。

### 整体作用
当 Wireshark 加载这个插件时：
1. 会在捕获接口列表中显示 "USB Sniffer" 选项
2. 选择该接口后，Wireshark 知道将使用 DLT 288 (USB) 来解析捕获的数据包
3. 用户可以像使用其他标准接口一样使用这个插件进行 USB 流量捕获


1. USB 捕获速度 (--speed)
2. 折叠空帧 (--fold)
3. 捕获触发条件 (--trigger)

这段配置是 Wireshark 插件的 **`--extcap-config`** 部分，用于定义插件的**可配置参数**。这些参数会在 Wireshark 的 **"Extcap Options"** 窗口中显示，允许用户调整捕获行为。  

### **`--extcap-config` 的作用**
它定义了插件的**命令行参数**，Wireshark 会将其渲染为 GUI 控件（如下拉菜单、复选框、输入框等），用户可以通过界面配置捕获选项。

---

## **参数详解**
### **1. USB 捕获速度 (`--speed`)**
```text
arg {number=0}{call=--speed}{display=Capture Speed}{tooltip=USB capture speed}{type=selector}
value {arg=0}{value=ls}{display=Low-Speed}{default=false}
value {arg=0}{value=fs}{display=Full-Speed}{default=true}
value {arg=0}{value=hs}{display=High-Speed}{default=false}
```
- **`type=selector`** → 下拉选择框（ComboBox）
- **`call=--speed`** → 传递给插件的命令行参数（如 `--speed fs`）
- **`display=Capture Speed`** → 界面显示的名称
- **`tooltip=USB capture speed`** → 鼠标悬停时的提示信息
- **`value` 条目** → 定义可选值：
  - `ls`（Low-Speed, 1.5 Mbps）
  - `fs`（Full-Speed, 12 Mbps，**默认选中**）
  - `hs`（High-Speed, 480 Mbps）

**效果**：  
在 Wireshark 界面中，用户可以选择 USB 设备的传输速度。

---

### **2. 折叠空帧 (`--fold`)**
```text
arg {number=1}{call=--fold}{display=Fold empty frames}{tooltip=Fold frames that have no data or errors}{type=boolflag}
```
- **`type=boolflag`** → 布尔开关（复选框）
- **`call=--fold`** → 如果勾选，插件会收到 `--fold` 参数
- **`display=Fold empty frames`** → 界面显示名称
- **`tooltip=Fold frames that have no data or errors`** → 提示信息

**效果**：  
如果启用，插件会折叠（不显示）没有数据或错误的 USB 帧，减少捕获噪音。

---

### **3. 捕获触发条件 (`--trigger`)**
```text
arg {number=2}{call=--trigger}{display=Capture Trigger}{tooltip=Condition used to start the capture}{type=selector}
value {arg=2}{value=disabled}{display=Disabled}{default=true}
value {arg=2}{value=low}{display=Low}{default=false}
value {arg=2}{value=high}{display=High}{default=false}
value {arg=2}{value=falling}{display=Falling}{default=false}
value {arg=2}{value=rising}{display=Rising}{default=false}
```
- **`type=selector`** → 下拉选择框
- **`call=--trigger`** → 传递给插件的参数（如 `--trigger rising`）
- **`display=Capture Trigger`** → 界面显示名称
- **`tooltip=Condition used to start the capture`** → 提示信息
- **`value` 条目** → 定义触发条件：
  - `disabled`（不触发，**默认选中**）
  - `low`（低电平时触发）
  - `high`（高电平时触发）
  - `falling`（下降沿触发）
  - `rising`（上升沿触发）

**效果**：  
用户可以选择在特定信号条件（如电平变化）时才开始捕获，适用于硬件调试。

---

### **4. 捕获包数量限制 (`--limit`)**
```text
arg {number=3}{call=--limit}{display=Capture Limit}{tooltip=Limit the number of captured packets (0 for unlimited)}{type=integer}{range=0,10000000}{default=0}
```
- **`type=integer`** → 整数输入框
- **`call=--limit`** → 传递给插件的参数（如 `--limit 1000`）
- **`display=Capture Limit`** → 界面显示名称
- **`tooltip=Limit the number of captured packets...`** → 提示信息
- **`range=0,10000000`** → 允许的数值范围（0 表示无限制）
- **`default=0`** → 默认值（无限制）

**效果**：  
用户可以设置最大捕获包数，防止捕获过多数据导致内存耗尽。

---

### **总结**
| 参数 | 类型 | 作用 | 示例值 |
|------|------|------|------|
| `--speed` | 下拉选择 | 设置 USB 速度 | `ls`, `fs`, `hs` |
| `--fold` | 复选框 | 是否折叠空帧 | `true`/`false` |
| `--trigger` | 下拉选择 | 设置触发条件 | `rising`, `falling` |
| `--limit` | 整数输入 | 限制捕获包数 | `1000`（最多抓 1000 包） |

这些参数会在 Wireshark 的 **"Extcap Options"** 窗口显示，用户调整后，Wireshark 会将其转换为命令行参数传递给插件。