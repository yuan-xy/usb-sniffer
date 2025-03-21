import usb.core
import usb.util

# 列出所有设备
# 用winusb默认的驱动，下面的代码找不到任何设备。
# 用zadig替换驱动为libusb-win32, 可以找到设备。但是exe又报错了。
# bin\usb_sniffer_win.exe --test
# Starting speed test
# Error: data error during the speed test on count 6144000
for device in usb.core.find(find_all=True):
    print(f"VID: {device.idVendor:04X}, PID: {device.idProduct:04X}")

dev = usb.core.find(idVendor=0x6666, idProduct=0x6620)

if dev is None:
    raise ValueError("设备未找到")

# 设置配置（通常为第一个配置）
dev.set_configuration()

# dev.ctrl_transfer(bmRequestType, bRequest, wValue, wIndex, data_or_wLength)

# 获取接口和端点
cfg = dev.get_active_configuration()
intf = cfg[(0,0)]  # 假设使用第一个接口

# dev.ctrl_transfer(bmRequestType, bRequest, wValue, wIndex, data_or_wLength)

for ep in intf:
    print(dir(ep))
    print(f"端点地址: {hex(ep.bEndpointAddress)}, 方向: {hex(usb.util.endpoint_direction(ep.bEndpointAddress))}")
    
# 查找端点（OUT端点用于写入，IN端点用于读取）
out_ep = usb.util.find_descriptor(
    intf,
    custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT
)

in_ep = usb.util.find_descriptor(
    intf,
    custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN
)

# breakpoint()
exit(0)

# 写入数据到设备
# data_to_send = b'\x01\x02\x03'
# dev.write(out_ep.bEndpointAddress, data_to_send)

# 从设备读取数据
data_received = dev.read(in_ep.bEndpointAddress, 64)  # 读取64字节
print("收到数据:", data_received)
# *** usb.core.USBError: [Errno None] b'libusb0-dll:err [_usb_reap_async] timeout error\n'



