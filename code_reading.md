## device只有一个in端点，如何接收固件更新数据？

## 测速--test和捕获capture都调用了usb_data_transfer，firmware如何区分两者？
void usb_data_transfer(void)
{
  for (int i = 0; i < TRANSFER_COUNT; i++)
  {
    int rc;

    g_buffers[i]   = os_alloc(TRANSFER_SIZE);
    g_transfers[i] = libusb_alloc_transfer(0);
    os_check(g_transfers[i], "libusb_alloc_transfer()");

    libusb_fill_bulk_transfer(g_transfers[i], g_usb_handle, DATA_ENDPOINT,
        g_buffers[i], TRANSFER_SIZE, usb_capture_callback, NULL, TRANSFER_TIMEOUT);

    rc = libusb_submit_transfer(g_transfers[i]);
    usb_check_error(rc, "libusb_submit_transfer()");
  }

  while (1)
  {
    libusb_handle_events(NULL);
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
外部主控需生成SLCS/SLWR/SLRD控制信号
同步模式下需连接IFCLK时钟源



