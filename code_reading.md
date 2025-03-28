## 启动模式
### cypress默认
把vcc和boot两个测试点短接后，插入电脑，显示设备VID_04B4&PID_8613， 跑的是cypress默认rom里的程序。
此时电脑不认，要用zadig安装winusb驱动。
Vendor ID                : 0x04B4 (Cypress Semiconductor)
Product ID               : 0x8613
Manufacturer String      : ---
Product String           : ---
Serial                   : ---
USB Version              : 2.0

然后执行命令
.\software\usb_sniffer.exe --mcu-sram .\firmware\usb_sniffer.bin
执行成功后会renumerate成下面的设备

### ram启动
Vendor ID                : 0x6666 (Prototype - Non-commercial product (1))
Product ID               : 0x6620
Manufacturer String      : Alex Taradov
Product String           : USB Sniffer
Serial                   : [-----SN-----]
USB Version              : 2.1

执行命令：
.\software\usb_sniffer.exe --mcu-eeprom .\firmware\usb_sniffer.bin

### eeprom启动
EEPROM烧录成功后，断电重启或者短接RESET与GND，设备重新枚举。
Vendor ID                : 0x6666 (Prototype - Non-commercial product (1))
Product ID               : 0x6620
Manufacturer String      : Alex Taradov
Product String           : USB Sniffer
Serial                   : 44342594045a38
USB Version              : 2.1



## device只有一个in端点，如何接收主机out的固件更新数据？
原来是主机直接通过端点0写入，每次64字节。
void fx2lp_sram_upload(u8 *data, int size){
  #define USB_EP0_SIZE   64
  addr = 0;
  usb_fx2lp_reset(true);
  usb_fx2lp_sram_write(addr, data, sz);
}
void usb_fx2lp_reset(bool reset){
  rc = libusb_control_transfer(g_usb_handle,
    LIBUSB_ENDPOINT_OUT | LIBUSB_REQUEST_TYPE_VENDOR | LIBUSB_RECIPIENT_DEVICE,
    CMD_FX2LP_REQUEST, CPUCS_ADDR, 0/*wIndex*/, &reset, sizeof(reset), TIMEOUT);
}
void usb_fx2lp_sram_write(int addr, u8 *data, int size){
  rc = libusb_control_transfer(g_usb_handle,
    LIBUSB_ENDPOINT_OUT | LIBUSB_REQUEST_TYPE_VENDOR | LIBUSB_RECIPIENT_DEVICE,
    CMD_FX2LP_REQUEST, addr, 0/*wIndex*/, data, size, TIMEOUT);
}
software里的定义
enum
{
  CMD_FX2LP_REQUEST    = 0xa0,

  CMD_I2C_READ         = 0xb0,
  CMD_I2C_WRITE        = 0xb1,

  CMD_JTAG_ENABLE      = 0xc0,
  CMD_JTAG_REQUEST     = 0xc1,
  CMD_JTAG_RESPONSE    = 0xc2,

  CMD_CTRL             = 0xd0,
};
firmware里的定义
enum
{
  CMD_I2C_READ         = 0xb0,
  CMD_I2C_WRITE        = 0xb1,

  CMD_JTAG_ENABLE      = 0xc0,
  CMD_JTAG_REQUEST     = 0xc1,
  CMD_JTAG_RESPONSE    = 0xc2,

  CMD_CTRL             = 0xd0,
};
为何不公用一个定义？懂了，可能的原因是firmware里并不支持CMD_FX2LP_REQUEST，这个请求是blank_fx2lp固件支持的。



### 那为何不用端点0接收in数据？端点0应该也是可以收数据的吧？
REG(0xe740, EP0BUF[64]);      //EP0-IN/-OUT 缓冲区
REG(0xe780, EP1OUTBUF[64]);   //EP1-OUT 缓冲区
REG(0xe7c0, EP1INBUF[64]);    //EP1-IN 缓冲区

看来是fx2lp的端口0 IN/OUT共用一个缓冲区，所以主机输出用端口0， 主机接收用端口1。


## 抓包分析
### usb_jtag_enable(bool enable)
Setup Data
    bmRequestType: 0x40
        0... .... = Direction: Host-to-device
        .10. .... = Type: Vendor (0x2)
        ...0 0000 = Recipient: Device (0x00)
    bRequest: 192   //0xc0 CMD_JTAG_ENABLE
    wValue: 0x0001  //enable
    wIndex: 0 (0x0000)
    wLength: 0

对应设备端：
  if (USB_CMD(OUT, DEVICE, VENDOR) == bmRequestType && CMD_JTAG_ENABLE == bRequest){
    if (wValueL)
      jtag_enable();
    else
      jtag_disable();

static inline void jtag_enable(void){
  IFCONFIG = IFCONFIG_IFCLKSRC | IFCONFIG_IFCLKOE | IFCONFIG_IFCFG_PORTS;
  SYNCDELAY;
  JTAG_EN = 1;
}



## 测速--test和捕获capture都调用了usb_data_transfer，firmware如何区分两者？
firmware不区分，是fpga里记录了是否是test模式。

void usb_data_transfer(void)
{
  for (int i = 0; i < TRANSFER_COUNT; i++)
  {
    int rc;

    g_buffers[i]   = os_alloc(TRANSFER_SIZE);
    g_transfers[i] = libusb_alloc_transfer(0);

    libusb_fill_bulk_transfer(g_transfers[i], g_usb_handle, DATA_ENDPOINT(0x82),
        g_buffers[i], TRANSFER_SIZE, usb_capture_callback, NULL, TRANSFER_TIMEOUT);

    发起一个接收请求（主机准备接收 TRANSFER_SIZE 字节的数据），此时 “发送”的字节数为 0，但主机期望从设备接收最多 TRANSFER_SIZE 字节。

    rc = libusb_submit_transfer(g_transfers[i]);
  }

  while (1)
  {
    libusb_handle_events(NULL);  //等待usb_capture_callback
  }
}

在usb_capture_callback回调中，是通过g_speed_test判断是测速还是捕获。



## 三种模式
![ Figure 6.  Signal ](image.png)

Three modes are available in all package versions: Port, GPIF
 master, and Slave FIFO. These modes define the signals on the
 right edge of the diagram. The 8051 selects the interface mode
 using the IFCONFIG[1:0] register bits. Port mode is the power on
 default configuration. 
所有封装版本均支持三种模式：端口（Port）、GPIF主控（GPIF master）和从属FIFO（Slave FIFO）。
这些模式决定了示意图右侧边缘的信号定义。
8051通过IFCONFIG[1:0]寄存器位选择接口模式，其中端口模式为上电默认配置。

### 1. 端口模式（Port Mode）
原理：

默认上电模式，作为USB接口与本地端点FIFO的桥梁
USB数据通过端点缓冲区（EPx）与内部FIFO交互
支持批量/中断/同步传输类型，自动处理USB协议栈

通过EPxCFG寄存器配置端点类型/大小
使用EPxBUF设置缓冲区地址
自动枚举为默认USB设备类（可通过VID/PID自定义）


### 2. GPIF主控模式（GPIF Master Mode）
GPIF: General Programmable Interface  通用可编程接口
原理：

用户可编程状态机生成自定义波形
通过波形描述符（GPIF TCB）控制时序
支持8/16位数据总线，可驱动外部存储器/LCD等

连接USB总线与复杂并行外设

### 3. 从属FIFO模式（Slave FIFO Mode）
原理：

外部主控（FPGA/CPU）直接访问内部FIFO
支持同步（IFCLK）或异步接口
通过外部控制信号（SLWR/SLRD）管理读写指针

关键配置：

通过IFCONFIG选择Slave FIFO模式
配置EPxFIFOCFG设置FIFO行为
同步模式下需连接IFCLK时钟源
外部主控需生成SLCS/SLWR/SLRD控制信号
对应FPGA的下面三个端口
LOCATE COMP "slrd_o" SITE "48";
LOCATE COMP "slwr_o" SITE "49";
LOCATE COMP "sloe_o" SITE "69";

## Table 12.  FX2LP Register Summary
![FX2LP Register Summary](image-1.png)


## CY7C68013A/CY7C68014A  56 引脚 SSOP
![alt text](image-2.png)


## 肖特基二极管BAT54S
为什么IO_IN接到了肖特基二极管BAT54S的中间。
IO_IN也就是PA1/INT1#引脚。

## 如何监听high speed设备的通信，比如U盘
似乎不支持high speed设备？比如一个2.0的高速U盘，抓包如下：
![高速U盘](image-3.png)

原来是我搞错了。监听的时候要设置capture speed为high speed。
bool capture_start(void){
  usb_ctrl(CaptureCtrl_Speed0, g_opt.capture_speed & 1);
  usb_ctrl(CaptureCtrl_Speed1, g_opt.capture_speed & 2); //high speed
}


## 测速代码
修改software/os_common.c
 u16 os_rand16(u16 seed)
 {
-  static u16 state = 0x6c41;
+  static u16 state = 0x6c51;
和fpga/usb_sniffer.v
 always @(posedge ifclk_i) begin
   if (!test_sync_w)
-    rng_r <= rng_next(16'h6c41);
+    rng_r <= rng_next(16'h6c51);

运行下面的代码可以看到效果
make -C .\software
.\software\usb_sniffer.exe --fpga-sram .\fpga\impl\usb_sniffer_impl.bit
.\software\usb_sniffer.exe --test
或者
.\software\usb_sniffer.exe --fpga-flash .\fpga\impl\usb_sniffer_impl.jed


## 五个捕获控制命令
### software层面
enum
{
  CaptureCtrl_Reset  = 0,
  CaptureCtrl_Enable = 1,
  CaptureCtrl_Speed0 = 2,
  CaptureCtrl_Speed1 = 3,
  CaptureCtrl_Test   = 4,
};
只有5个命令。

要执行哪个ctrl命令，就通过vendor特定请求，wValue低四位是命令的index，第5位是启用还是关闭。


void usb_ctrl(int index, int value)
{
  value = index | ((value ? 1 : 0) << CTRL_REG_SIZE);

  rc = libusb_control_transfer(g_usb_handle,
    LIBUSB_ENDPOINT_OUT | LIBUSB_REQUEST_TYPE_VENDOR | LIBUSB_RECIPIENT_DEVICE,
    CMD_CTRL, value/*wValue*/, 0/*wIndex*/, NULL, 0, TIMEOUT);

  usb_check_error(rc, "usb_ctrl()");
}

void usb_speed_test(void)
{
  usb_ctrl_init();
  usb_ctrl(CaptureCtrl_Reset, 1);
  usb_ctrl(CaptureCtrl_Test, 1);
  ......
  usb_data_transfer();
}

### firmware层面
单片机0xE6B8  SET-UPDAT 8个字节的设置数据(只读)
 SET-UPDAT[0] = bmRequestType
 SET-UPDAT[1] = bmRequest
 SET-UPDAT[2:3] = wValue
 SET-UPDAT[4:5] = wIndex
 SET-UPDAT[6:7] = wLength

#define      wValueL        SETUPDAT[2]

通过ctrl_transfer把usb传递过来的value发送给fpga。

static void ctrl_transfer(uint8_t value){
  B = value;

  // Start
  CTRL_DATA = 0;

  CTRL_CLK  = 0;
  CTRL_DATA = B_0_b;
  CTRL_CLK  = 1;

  CTRL_CLK  = 0;
  CTRL_DATA = B_1_b;
  CTRL_CLK  = 1;

  CTRL_CLK  = 0;
  CTRL_DATA = B_2_b;
  CTRL_CLK  = 1;

  CTRL_CLK  = 0;
  CTRL_DATA = B_3_b;
  CTRL_CLK  = 1;

  CTRL_CLK  = 0;
  CTRL_DATA = B_4_b;
  CTRL_CLK  = 1;

  // Stop
  CTRL_DATA = 0;
  CTRL_DATA = 1;
}

### fpga层面
module ctrl (
  input          clk_i,
  input          ctrl_clk_i,
  input          ctrl_data_i,
  output  [15:0] ctrl_o
);

wire clk_i = t_usb_clk_i;

always @(posedge clk_i) begin
  clk_sync_r  <= { ctrl_clk_i, clk_sync_r[2:1] };
  data_sync_r <= { ctrl_data_i, data_sync_r[2:1] };
end

  end else if (done_w) begin
    ctrl_r[data_r[3:0]] <= data_r[4];
  end else begin
      data_r  <= { data_sync_r[1], data_r[4:1] };
    end

assign ctrl_o = ctrl_r;

ctrl.v执行串并转换，最后的结果大概就是wValueL等于几，ctrl_o的第几位置1。


## 如何把抓包数据返回
output [15:0] fd_o,  //这个对应FD0-FD15端口，连接单片机

assign fd_o       = jtagen_i ? 16'hzzzz : (test_sync_w ? rng_r : rd_data_w);

启用jtag时，禁止抓包。
如果测速，返回rng伪随机数；否则返回fifo的数据。

fifo用于时钟同步，wr_clk_i来自usb， ifclk_i来自单片机。

fifo_sync #(
  .W(16)
) fifo_sync_i (
  .reset_i(reset_w),

  .wr_clk_i(clk_i),
  .wr_data_i(wr_data_w),
  .wr_en_i(wr_en_w),
  .wr_ready_o(wr_ready_w),

  .rd_clk_i(ifclk_i),
  .rd_data_o(rd_data_w),
  .rd_en_i(rd_valid_w && if_ready_w),
  .rd_valid_o(rd_valid_w)
);

  input  [W-1:0] wr_data_i,
  output [W-1:0] rd_data_o,

always @(posedge wr_clk_i) begin
  if (wr_en_i && wr_ready_o)
    buf_r[wr_ptr_bin_w[2:0]] <= wr_data_i;
end

assign rd_data_o = buf_r[rd_ptr_bin_w[2:0]];


wire [15:0] wr_data_w = { capture_data_w, buf_r };

## trigger问题
lldb -- .\software\usb_sniffer.exe  -s hs -l -t high -f low.log -c
(lldb) b capture.c:432
* thread #1, stop reason = breakpoint 1.1
  * frame #0: 0x00007ff7a2183fe5 usb_sniffer.exe`status_event(ls=0, vbus=1, trigger=1, speed=1) at capture.c:432:20
    frame #1: 0x00007ff7a2183835 usb_sniffer.exe`capture_sm(byte='p') at capture.c:703:7
    frame #2: 0x00007ff7a2183631 usb_sniffer.exe`capture_callback(data="", size=20992) at capture.c:732:5
    frame #3: 0x00007ff7a2182061 usb_sniffer.exe`usb_capture_callback(transfer=0x00000187bfe98790) at usb.c:314:5
    frame #4: 0x00007ff7a218c915 usb_sniffer.exe`usbi_handle_transfer_completion + 229
    frame #5: 0x00007ff7a21926b6 usb_sniffer.exe`windows_handle_transfer_completion + 182

