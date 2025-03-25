# USB PHY 模块代码解析
module usb_phy (
  input         ulpi_clk_i,
  inout   [7:0] ulpi_data_io,
  input         ulpi_dir_i,
  input         ulpi_nxt_i,
  output        ulpi_stp_o,

ULPI接口包含以下主要信号：
// ULPI有12根线，4根控制信号：
// CLK - 60MHz时钟(由PHY提供)
// DIR - 方向指示(1=PHY→Link, 0=Link→PHY)
// NXT - 下一个指示(流量控制)
// STP - 停止信号(终止传输)
// 数据总线(8位)：
// DATA[7:0] - 双向数据总线



https://mp.weixin.qq.com/s/DAClQPdsl_Gw62_3PmYpxw
主机驱动dir决定data总线的所有权. 如果PHY有数据需要传输给LINK,则PHY驱动 dir 为高拥有总线. 如果PHY没有数据要传输给LINK则拉低dir,表示LINK拥有data总线,此时PHY监听总线有非0 的数据则表示LINK发过来了数据给PHY. 如果PHY不能接收LINK的数据也可以拉高dir.比如PHY的PLL没有稳定时就会拉高dir,此时LINK不能往PHY发非0数据.


wire [1:0] utmi_xcvrselect_w =
  (speed_w == USB_SPEED_LS) ? 2'b10 :
  (speed_w == USB_SPEED_FS) ? 2'b01 : 2'b00;

wire utmi_termselect_w = (speed_w == USB_SPEED_HS) ? 1'b0 : 1'b1;


reg [1:0] xcvrselect_r = 2'b00;
reg       termselect_r = 1'b0;
reg [1:0] opmode_r     = 2'b11;
reg       dppulldown_r = 1'b1;
reg       dmpulldown_r = 1'b1;


wire func_ctrl_update_w = (opmode_r != utmi_opmode_i || termselect_r != utmi_termselect_i ||
    xcvrselect_r != utmi_xcvrselect_i);

wire otg_ctrl_update_w = (dppulldown_r != utmi_dppulldown_i || dmpulldown_r != utmi_dmpulldown_i);


接收数据：
always @(posedge ulpi_clk_i) begin
  if (!turnaround_w && ulpi_dir_i) begin
    rx_valid_r <= ulpi_nxt_i;
    rx_data_r  <= ulpi_data_io;
  end else begin
    rx_valid_r <= 1'b0;
  end
end


## 三态总线双向通信设计模式
这里设置PHY发送的时候，ulpi_data_io是高阻态。这和前面的rx_data_r  <= ulpi_data_io;是否冲突？

reg [7:0] ulpi_data_r = 8'h00;
reg       ulpi_stp_r  = 1'b0;
assign ulpi_data_io     = (turnaround_w || ulpi_dir_i) ? 8'hzz : ulpi_data_r;
assign ulpi_stp_o       = ulpi_stp_r;


不冲突。assign ulpi_data_io = ... ? 8'hzz : ... 表示的是Link端对总线的驱动控制。
当设为高阻态时，Link端放弃总线驱动权，此时总线值由PHY端驱动。
rx_data_r <= ulpi_data_io 读取的是PHY驱动的值，不是Link端自己驱动的值



## 接口概述
这是一个实现USB物理层(PHY)接口的Verilog代码，用于在UTMI(USB 2.0收发器宏单元接口)和ULPI(UTMI+低引脚接口)之间进行桥接。

### ULPI接口(低引脚数)
- `ulpi_clk_i`: 60 MHz时钟输入
- `ulpi_data_io[7:0]`: 双向数据总线
- `ulpi_dir_i`: 方向信号(1=PHY到Link，0=Link到PHY)
- `ulpi_nxt_i`: 流控制的下一个信号
- `ulpi_stp_o`: 流控制的停止信号

### UTMI接口(高层USB接口)
- 接收路径输出:
  - `utmi_rx_data_o`: 接收到的数据
  - `utmi_rx_active_o`: 接收活动指示
  - `utmi_rx_valid_o`: 有效接收数据
  - `utmi_rx_error_o`: 接收错误指示
- 发送路径输入:
  - `utmi_tx_data_i`: 要发送的数据
  - `utmi_tx_valid_i`: 有效发送数据
  - `utmi_tx_ready_o`: 发送就绪信号
- 控制信号:
  - 各种配置输入和状态输出

## 主要功能

### 状态机
模块实现了以下状态的状态机:
1. `ST_IDLE`: 等待操作
2. `ST_WR_FUNC_CTRL`: 写入功能控制寄存器
3. `ST_WR_OTG_CTRL`: 写入OTG控制寄存器
4. `ST_WR_REG_STOP`: 完成寄存器写入
5. `ST_TX_DATA`: 发送USB数据
6. `ST_CLEAR_STP`: 清除停止条件

### 主要操作
1. **寄存器写入**:
   - 功能控制寄存器(REG_FUNC_CTRL)
   - OTG控制寄存器(REG_OTG_CTRL)
   - 当配置输入改变时触发

2. **数据传输**:
   - 处理来自UTMI接口的USB数据包传输
   - 使用ULPI的流控制(NXT/STP)

3. **数据接收**:
   - 处理传入的USB数据包
   - 提取状态信息(线路状态，VBUS)
   - 生成适当的UTMI接收信号

### 时序控制
- 使用`turnaround_w`信号检测总线方向变化
- 正确处理总线转向时序

## 实现细节

1. **总线方向处理**:
   - 用`dir_r`寄存器跟踪方向变化
   - 在转向期间将数据总线设为三态

2. **配置管理**:
   - 监控UTMI配置输入的变化
   - 需要时更新PHY寄存器

3. **接收路径**:
   - 从ULPI总线提取USB数据和状态
   - 生成UTMI兼容的接收信号
   - 处理错误条件

4. **发送路径**:
   - 接收UTMI发送数据
   - 格式化为ULPI传输
   - 处理流控制

这个模块有效地桥接了引脚数较多的UTMI接口和引脚数较少的ULPI接口，同时保持了正确的USB 2.0 PHY功能。



## 接收数据
always @(posedge ulpi_clk_i) begin
  if (turnaround_w && ulpi_dir_i && ulpi_nxt_i) begin
    rx_active_r <= 1'b1;
  end else if (!turnaround_w && ulpi_dir_i && !ulpi_nxt_i) begin
    linestate_r <= ulpi_data_io[1:0];
    vbus_r <= ulpi_data_io[3:2];

    case (ulpi_data_io[5:4])
      2'b00: begin
        rx_active_r <= 1'b0;
        rx_error_r  <= 1'b0;
      end

      2'b01: begin
        rx_active_r <= 1'b1;
        rx_error_r  <= 1'b0;
      end

      2'b11: begin
        rx_active_r <= 1'b1;
        rx_error_r  <= 1'b1;
      end

      default: begin
        // Host disconnected
      end
    endcase
  end else if (!ulpi_dir_i) begin
    rx_active_r <= 1'b0;
  end
end

#### 条件1：检测接收开始
```verilog
if (turnaround_w && ulpi_dir_i && ulpi_nxt_i) begin
  rx_active_r <= 1'b1;
}
```
**行为**：当同时满足：
- `turnaround_w=1`（总线方向刚发生变化）
- `ulpi_dir_i=1`（当前方向是 PHY→Link）
- `ulpi_nxt_i=1`（PHY 有数据要发送）

**作用**：设置 `rx_active_r=1` 表示开始接收数据

---

#### 条件2：处理状态信息
```verilog
else if (!turnaround_w && ulpi_dir_i && !ulpi_nxt_i) begin
  linestate_r <= ulpi_data_io[1:0];
  vbus_r <= ulpi_data_io[3:2];
  
  case (ulpi_data_io[5:4])
    2'b00: begin  // IDLE状态
      rx_active_r <= 1'b0;
      rx_error_r  <= 1'b0;
    end
    2'b01: begin  // 正常接收
      rx_active_r <= 1'b1;
      rx_error_r  <= 1'b0;
    end
    2'b11: begin  // 错误状态
      rx_active_r <= 1'b1;
      rx_error_r  <= 1'b1;
    end
    default: ;    // 主机断开
  endcase
end
```
**行为**：当：
- 不处于转向周期 (`!turnaround_w`)
- PHY→Link 方向 (`ulpi_dir_i=1`)
- PHY 没有新数据 (`!ulpi_nxt_i`)

**执行操作**：
1. 捕获低4位：
   - `ulpi_data_io[1:0]` → `linestate_r` (USB D+/D- 线状态)
   - `ulpi_data_io[3:2]` → `vbus_r` (VBUS电压状态)
2. 根据 `ulpi_data_io[5:4]` 解码接收状态：
   - `00`：空闲状态，清除活动/错误标志
   - `01`：正常接收中
   - `11`：接收出错
   - `10`：默认情况（主机断开）

---

#### 条件3：方向切换处理
```verilog
else if (!ulpi_dir_i) begin
  rx_active_r <= 1'b0;
end
```
**行为**：当方向变为 Link→PHY 时 (`ulpi_dir_i=0`)

**作用**：立即清除接收活动标志，因为此时PHY不再发送数据


## ULPI数据总线 (ulpi_data_io[7:0]) 的功能定义

#### 1. 当 `ulpi_dir_i=1` (PHY→Link方向，即接收模式)：
| 位域    | 名称          | 功能描述                                                                 |
|---------|---------------|--------------------------------------------------------------------------|
| [1:0]   | LineState     | **USB线路状态**：<br>00 = SE0（单端0，表示复位或断开）<br>01 = J状态<br>10 = K状态<br>11 = SE1（非法状态）|
| [3:2]   | VbusState     | **VBUS电压状态**：<br>00 = 无VBUS或<0.8V<br>01 = 有效VBUS（>4.4V）<br>10 = 有效但电压下降（1.4-4.4V）<br>11 = 保留 |
| [5:4]   | RxStatus      | **接收状态**：<br>00 = 空闲/无数据<br>01 = 正在接收数据<br>11 = 接收错误<br>10 = 主机断开 |
| [7:6]   | 保留          | 通常为00                                                                 |

#### 2. 当 `ulpi_dir_i=0` (Link→PHY方向，即发送模式)：
| 位域    | 功能                                                                 |
|---------|----------------------------------------------------------------------|
| [7:6]   | **命令码**：<br>00 = 无操作<br>01 = 发送数据<br>10 = 寄存器写<br>11 = 寄存器读 |
| [5:0]   | 根据命令类型不同：<br>- 寄存器操作：寄存器地址+数据<br>- 数据发送：有效载荷数据 |

### 代码中的具体应用

在您提供的代码段中：
```verilog
linestate_r <= ulpi_data_io[1:0];  // 捕获D+/D-线路状态
vbus_r <= ulpi_data_io[3:2];       // 捕获VBUS电压状态

case (ulpi_data_io[5:4])           // 解析接收状态
  2'b00: ...  // 空闲状态
  2'b01: ...  // 接收中
  2'b11: ...  // 错误状态
  default: ...// 主机断开
endcase
```

### 规范来源
这些定义来自：
1. **ULPI规范文档**（如ULPI Revision 1.1）
2. **芯片厂商的PHY器件手册**（如SMSC/Microchip的USB3300等）

### 实际应用示例
当PHY检测到USB线路状态变化时：
1. PHY会将状态编码到`ulpi_data_io`的相应位
2. Link层通过读取这些位可以知道：
   - 当前是USB复位(`SE0`)、正常数据(`J/K`)还是错误状态
   - VBUS是否有效（判断设备是否上电）
   - 是否有数据正在接收或发生错误

这种设计使得USB PHY可以用8位总线同时传输状态信息和数据，极大减少了引脚数量。


## 寄存器写操作
  if (!turnaround_w && !ulpi_dir_i) case (state_r)
    ST_IDLE: begin
      if (func_ctrl_update_w) begin
        ulpi_data_r <= { CMD_REG_WRITE, REG_FUNC_CTRL };
        state_r     <= ST_WR_FUNC_CTRL;
      end else if (otg_ctrl_update_w) begin
        ulpi_data_r <= { CMD_REG_WRITE, REG_OTG_CTRL };
        state_r     <= ST_WR_OTG_CTRL;
      end else if (utmi_tx_valid_i) begin
        ulpi_data_r <= { CMD_TX, 2'b00, utmi_tx_data_i[3:0] };
        state_r     <= ST_TX_DATA;
      end
    end

    ST_WR_FUNC_CTRL: begin
      if (ulpi_nxt_i) begin
        ulpi_data_r <= { 3'b010, utmi_opmode_i, utmi_termselect_i, utmi_xcvrselect_i };
        state_r     <= ST_WR_REG_STOP;
      end
    end

    ST_WR_OTG_CTRL: begin
      if (ulpi_nxt_i) begin
        ulpi_data_r <= { 5'b00000, utmi_dmpulldown_i, utmi_dppulldown_i, 1'b0 };
        state_r     <= ST_WR_REG_STOP;
      end
    end

---

### 1. `ST_WR_FUNC_CTRL` 状态（功能控制寄存器写入）
```verilog
ulpi_data_r <= { 3'b010, utmi_opmode_i, utmi_termselect_i, utmi_xcvrselect_i };
```
**字段分解**（从高位到低位）：
| 位域       | 值/信号            | 含义                                                                 |
|------------|--------------------|----------------------------------------------------------------------|
| [7:5]      | `3'b010`           | **ULPI 命令头**：<br>`010` = 寄存器写操作（`CMD_REG_WRITE`）的后续数据阶段 |
| [4:3]      | `utmi_opmode_i`    | **USB 操作模式**：<br>00 = 非驱动模式<br>01 = 主机模式<br>10 = 设备模式<br>11 = 保留 |
| [2]        | `utmi_termselect_i` | **终端电阻选择**：<br>0 = 不启用终端电阻<br>1 = 启用终端电阻（设备模式下通常为1） |
| [1:0]      | `utmi_xcvrselect_i` | **收发器选择**：<br>00 = 高速模式（HS）<br>01 = 全速模式（FS）<br>10 = 低速模式（LS）<br>11 = 保留 |

**对应寄存器**：  
ULPI 的 **Function Control Register**（功能控制寄存器，地址 `0x04`），用于配置 USB 核心的基本操作模式。

---

### 2. `ST_WR_OTG_CTRL` 状态（OTG 控制寄存器写入）
```verilog
ulpi_data_r <= { 5'b00000, utmi_dmpulldown_i, utmi_dppulldown_i, 1'b0 };
```
**字段分解**：
| 位域       | 值/信号            | 含义                                                                 |
|------------|--------------------|----------------------------------------------------------------------|
| [7:3]      | `5'b00000`         | **填充位**：<br>ULPI 寄存器写数据阶段的高5位通常为0（保留位）               |
| [2]        | `utmi_dmpulldown_i`| **DM 下拉电阻控制**：<br>0 = 禁用 DM 下拉电阻<br>1 = 启用 DM 下拉电阻       |
| [1]        | `utmi_dppulldown_i`| **DP 下拉电阻控制**：<br>0 = 禁用 DP 下拉电阻<br>1 = 启用 DP 下拉电阻       |
| [0]        | `1'b0`            | **保留位**：<br>固定为0                                              |

**对应寄存器**：  
ULPI 的 **OTG Control Register**（OTG 控制寄存器，地址 `0x0A`），用于控制 USB OTG 相关的下拉电阻。

---

### 关键背景知识
1. **ULPI 寄存器写入协议**：
   - 分两个阶段发送：
     1. 第一阶段：发送 `{CMD_REG_WRITE, reg_addr}`（在之前的 `ST_IDLE` 状态已发送）
     2. 第二阶段：发送寄存器数据（当前代码段的操作）

2. **字段对齐**：
   - 功能控制寄存器（`0x04`）的字段直接映射到 USB 核心配置参数。
   - OTG 控制寄存器（`0x0A`）的字段主要控制物理层电阻。

3. **信号来源**：
   - 所有配置信号（如 `utmi_opmode_i`）来自上层的 UTMI 接口，ULPI PHY 只是透明传输这些配置。
