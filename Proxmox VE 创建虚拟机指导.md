# Proxmox VE 创建虚拟机指导
### **一、General 选项卡**
#### **1\. Node（节点）**
* **作用**：选择虚拟机所在的物理服务器（PVE 节点）。
* **你的场景**：单节点环境，默认选择 `pve`（无需修改）。

#### **2\. VM ID（虚拟机 ID）**
* **作用**：虚拟机的唯一标识符（范围 100-999999）。
* **你的场景**：保持默认（如 `100`），或手动输入一个未使用的 ID（如 `101`）。

#### **3\. Name（名称）**
* **作用**：虚拟机的描述性名称（如 `hadoop-master`、`spark-worker1`）。
* **你的场景**：建议按功能命名（如 `hbase-regionserver-01`）。

#### **4\. Resource Pool（资源池）**
* **作用**：将虚拟机分组管理（如集群资源分配）。
* **你的场景**：单节点无需配置，留空即可。

![image](images/zffBKXXtEsFEaWJ-1NJw4pt6M_Yk8GvFxvxhOzVYwiA.png)

* 

---
### **二、OS 选项卡**
#### **1\. ISO 镜像**
* **作用**：选择操作系统安装镜像（如 Ubuntu、CentOS）。
* **你的场景**：
* 点击 **Storage** 选择你上传 ISO 的存储池（如 `local` 或 `ssd-main`）。
* 点击 **ISO Image** 选择对应的镜像文件（如 `ubuntu-22.04.iso`）。

#### **2\. Type（操作系统类型）**
* **作用**：选择操作系统类型（如 Linux、Windows）。
* **你的场景**：选择 `Linux`。

#### **3\. Version（版本）**
* **作用**：选择操作系统子版本（如 5.x - 2.6 Kernel）。
* **你的场景**：根据镜像选择（如 `6.x - 3.x Kernel`）。

![image](images/LGnteVc6lGInHr38BXtZdXb-rWTqRU01xyf7-Y7HmA8.png)



---
### **三、System 选项卡**
#### **1\. BIOS（启动模式）**
* **作用**：选择虚拟机固件类型。
* **选项**：
* **SeaBIOS**：传统 BIOS，适用于大多数 Linux 系统。
* \*\*OVMF (UEFI)\**：现代 UEFI，适用于 Windows 或需要安全启动的场景。* **你的场景**：选择 `SeaBIOS`（默认）。

#### **2\. Machine（机器类型）**
* **作用**：虚拟硬件兼容性。
* **选项**：
* **i440fx**：传统 PC 架构，兼容性好。
* **q35**：现代 PCIe 架构，支持更多高级功能（如 PCIe 直通）。\* **你的场景**：选择 `q35`（若需直通硬件）或默认 `i440fx`。

#### **3\. QEMU Agent（QEMU 代理）**
* **作用**：启用后支持更精细的虚拟机管理（如在线调整磁盘）。
* **你的场景**：勾选 **QEMU Agent**（推荐）。

![image](images/FtLl9DcuhFDCjve6iE5LJq9meN3XWGSsodfLtiJwSAU.png)



---
### **四、Disks 选项卡**
#### **1\. 添加虚拟磁盘**
* **作用**：为虚拟机分配存储空间。
* **你的场景**：
* **Storage**：选择高性能存储池（如 `ssd-main`）。
* **Disk size**：根据组件需求分配（如 Hadoop DataNode 分配 `500GB`）。
* **Format**：选择 `qcow2`（动态分配）或 `raw`（高性能）。
* **Cache**：选择 `Writeback`（高性能，需定期备份）或 `None`（安全）。

#### **2\. 高级选项**
* **Discard**：勾选以支持 TRIM（SSD 优化）。
* **SSD 仿真**：若存储池在 SSD 上，勾选以优化调度。

![image](images/cVGc4cC43I_-UOpgitNho5BXH-qjqXBfwA1j54LLATY.png)



---
### **五、CPU 选项卡**
#### **1\. Cores（核心数）**
* **作用**：分配虚拟 CPU 核心数。
* **你的场景**：
* 大数据组件（如 Spark、Flink）：分配 4-8 核。
* 轻量组件（如 ZooKeeper）：分配 2 核。

#### **2\. Type（CPU 类型）**
* **作用**：模拟的 CPU 型号（兼容性优化）。
* **你的场景**：选择 `host`（最佳性能）或 `kvm64`（兼容性）。

![image](images/JxhY-J4udWyDkXBFj7Kepjcu5Ma3ZvK4kHUph3Jsxcg.png)



---
### **六、Memory 选项卡**
#### **1\. Memory（内存）**
* **作用**：分配虚拟机内存。
* **你的场景**：
* Hadoop/Spark：分配 8-16GB。
* HBase/ClickHouse：分配 16-32GB。
* ZooKeeper：分配 4-8GB。

![image](images/r6XoqbxJHebxASxhJ7IJge9hZ5JGadfeZTt5xR-3Ek8.png)



#### **2\. Ballooning（内存气球）**
* **作用**：允许动态调整内存（需 QEMU Agent）。
* **你的场景**：勾选 **Enable Ballooning**（推荐）。

---
### **七、Network 选项卡**
#### **1\. 网络配置**
* **作用**：设置虚拟机网络连接。
* **你的场景**：
* **Bridge**：选择物理网卡桥接（如 `vmbr0`）。
* **Model**：选择 `VirtIO`（高性能驱动）。
* **VLAN Tag**：按需填写（若有 VLAN 隔离需求）。
* **Firewall**：按需启用（默认禁用）。

![image](images/4NexQhhBZtFi7T8LYolZql1OFuh1Qw1SBTLiT67tV8A.png)



---
### **八、Confirm（确认）**
* **作用**：检查配置并创建虚拟机。
* **你的场景**：

1. 确认所有选项无误。
2. 点击 **Finish** 创建虚拟机。
3. 启动虚拟机并进入操作系统安装流程。

![image](images/1NGFnmhNMmfgst39fH9tblWydvnEiIdeXIzJXzQX1C0.png)



---
### **九、安装后优化**
1. **移除 ISO 镜像**：

* 安装完成后，在虚拟机硬件设置中 **分离 ISO 镜像**，避免下次启动重复进入安装界面。2. **调整高级设置**：
* 如需直通 GPU 或 PCIe 设备，可在硬件设置中添加。
* 若需 EFI 启动，可在 System 选项卡中切换为 `OVMF` 并添加 EFI 磁盘。

---
### **十、示例配置（以 Hadoop DataNode 为例）**
|**选项**|**配置**|
| ----- | ----- |
|**Name**|hadoop-datanode-01|
|**OS**|`Ubuntu 22.04`（ISO 镜像）|
|**Disk**|ssd-main:500GB (qcow2)|
|**CPU**|4 cores, `host` 类型|
|**Memory**|8GB + Ballooning|
|**Network**|`vmbr0`, `VirtIO`|

---
### **总结**
按需调整配置，重点注意：

* **存储池选择**：高性能组件（如 HBase）分配至 `ssd-main`。
* **CPU/内存分配**：根据组件负载动态调整。
* **网络驱动**：优先使用 `VirtIO`。

遇到具体问题时，可随时截图或描述界面细节，我会进一步协助！