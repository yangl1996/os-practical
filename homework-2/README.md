# 第二次作业

## Mesos 的组成结构

### Master

Master 管理整个集群的资源，也是用户使用 Mesos 集群的渠道。在管理资源方面，master 节点维护一个当前全系统可用资源的列表，掌握每个机器上可用资源的详细信息。同时，它不断接收其他机器汇报的当前可用资源量，不断更新这个列表。当框架（Mesos Framework）请求资源时，master 通过不同算法（用户也可自定义）确定将多少资源 lease 给框架。在提供用户接口方面，用户可以通过 Mesos 监控当前集群状态，并控制框架启动、停止。由于它的重要性（一旦宕机则整个系统无法使用），在生产环境中一般使用 Zookeeper 管理多个 master，互相作为备份，并自动选举一个节点作为当前的 master 节点。

Master 代码主要位于 `src/master` 目录下。

### Agent

Agent（之前称为 slave）向 master 间隔报告当前本机资源使用情况，使 master 掌握全集群实时资源量。另外，agent 在 master 的指示下，为框架的 executor 分配计算资源。代码主要位于 `src/slave` 和 `src/sched` 目录下。

### Mesos Framework

Mesos Framework 的 _scheduler_ 部分首先向 master 注册。需要资源时，master 会根据当前可用资源情况，给 scheduler 提供 offer，即当前可提供的最大资源量。Scheduler 选择接受或拒绝。若接受，则将要运行的 task 和每个 task 需要的资源发给 master，master 再通知 agent 分配资源给 framework 的 _executor_ 部分。然后 executor 开始执行 task。Framework 由用户提供。

### 其他部件

Mesos source tree 中还有别的部件辅助 master 和 agent 的运行，如

* Authenticator，用于 agent 向 master 认证，防止恶意 agent 进入系统资源池
* Launcher，负责在 agent 所在机器上执行框架和 task
* HDFS Interface，处理 HDFS 相关操作，如 URI 解析、创建文件、删除文件等
* Authorizer，用于对用户的鉴权，如仅允许部分用户提交框架等

代码分别位于 `src` 目录下同名目录。

### 各部件工作流程

1. Agent 向 master 定期报告可用资源
2. Master 向 framework scheduler 提供资源 offer
3. 若 scheduler 接受 offer，就向 master 报告具体执行的 task 和每个 task 需要的资源量
4. Master 要求 agent 在各自所在机器上分配资源给框架，并分别调用框架的 executor 执行 task

## 框架的运行过程

### Spark on Mesos 的运行过程

当运行在 Mesos 上时，Spark 不再需要实时监控每个节点的资源，这件事情由 Mesos 完成。当 Spark 要运行任务时，它根据 Master 发来的资源情况，决定每个任务在每个节点使用多少资源，然后 master 根据此信息要求 agent 分配资源，并通知在各节点上的 Spark executor 执行任务。之后的执行就和普通 Spark 程序一样，所有通信、同步都由 Spark 完成。相当于，Mesos 只参与资源分配的过程。

### 与传统操作系统的对比

与传统操作系统 __相似__ 的有，

* 都涉及资源的监测、分配和调度
* 都需要处理多个任务共存，资源的合理利用问题

与传统操作系统 __不同__ 的有，

* 传统操作系统，资源分配的协商只有两步：程序请求和系统同意（或拒绝）；而在 Mesos 上有三步，框架请求、系统提供 offer、框架选择使用（或不使用）
* 传统操作系统，内核是唯一的资源调度器；Mesos 上事实上有两层调度：Mesos master 将资源划分粗略给各个框架，各个框架自己的 scheduler 将获得的资源划分给要运行的 task
* 传统操作系统内核不涉及分布式的资源管理；而 Mesos 负责跟踪和分配一个分布式系统中的资源
* Mesos 上注册的“框架”和传统操作系统中提交的进程有本质区别：框架提供类似库的功能，为 task 提供通信、同步等功能，起到运行环境的角色，兼有资源分配的功能；而传统操作系统中提交的程序就是进程，操作系统才是运行环境

## Master 和 Agent 的初始化过程

### Master 的初始化

#### 1 处理命令行参数

`src/master/main.cpp` 的 `main()` 开始先验证并处理传入的选项，从 220 行到 275 行。例如，

```cpp
if (flags.advertise_port.isSome()) {
    os::setenv("LIBPROCESS_ADVERTISE_PORT", flags.advertise_port.get());
  }
```

就是在从命令行参数中获取 `advertise_port` 选项，并以此设置 `LIBPROCESS_ADVERTISE_PORT` 环境变量的值。我猜测使用环境变量是为了方便在子进程之间共享配置参数。

#### 2 输出 Build 号

在 `stdout` 输出 Mesos master 的 build 信息，如编译时间和本 Mesos 实例的版本号、git tag 和 commit SHA 等。

#### 3 初始化 `Libprocess`

`Libprocess` 是负责 message passing 的库。调用

```cpp
process::initialize(
  "master",
  READWRITE_HTTP_AUTHENTICATION_REALM,
  READONLY_HTTP_AUTHENTICATION_REALM);
```

来实现。它理应由 `main()` 初始化，所以若该调用出错，则直接报错退出。

#### 4 初始化日志

调用

```cpp
logging::initialize(argv[0], flags, true);
```

实现。初始化完成后，紧接着输出之前的所有 warning 信息。

#### 5 启动 `VersionProcess`

```cpp
spawn(new VersionProcess(), true);
```

查看 `VersionProcess` 源码（`src/version/version.cpp`）可以发现，该进程专门处理获取 master 版本信息的请求。

#### 6 启动防火墙

防火墙可以禁用特定的 API endpoint。在这里读取命令行参数中防火墙设置，解析并一一设置禁用的 endpoint。

#### 7 加载模块和匿名模块

从这里开始，将会初始化一系列用于扩展 Mesos 的组建。在本阶段，初始化的是模块和匿名模块。读取命令行参数，并调用 `ModuleManager::load` 加载模块，调用 `ModuleManager::create<Anonymous>(name)` 创建匿名模块。

事实上，之后的 Hook，Allocator 等都需要作为模块先被加载，再被设置使用。因此，这里先加载模块。

#### 8 初始化 Hook

Hook 在 Mesos 的一些关键操作的关键节点中被调用，它的返回值将取代正常流程下的值，被直接用于 Hook 插入点之后的流程。这里通过 `HookManager::initialize(flags.hooks.get())` 获得命令行参数并加载 Hook。

#### 9 初始化 Allocator

```cpp
const string allocatorName = flags.allocator;
Try<Allocator*> allocator = Allocator::create(allocatorName);
```

这里首先从 `flags` 中读取要用的 allocator，再进行加载。通过源码 `src/master/constants.hpp` 和 `src/master/flag.cpp` 可以发现，默认的 allocator 是 HierarchicalDRF。

#### 10 初始化注册信息存储空间

Mesos master 需要维护多个状态信息，需要空间存储。这里根据命令行参数的指定，初始化状态存储空间。首先，若要求保存在内存中，则直接 `storage = new InMemoryStorage();` 新建 `InMemoryStorage` 的实例；若要求存储在文件系统，则新建 working directory；若 master 由 zookeeper 选出，则调用 zookeeper 功能初始化这一存储空间。

#### 11 初始化状态

调用 `State` 类构造函数，初始化一个实例。通过阅读 `include/mesos/state/state.hpp` 中对 `State` 类的定义，可以看出它就是维护了一个数据结构，存储收到的状态信息。

#### 12 初始化注册信息进程

改进程负责提供查询当前注册信息的 API Endpoint。这一进程读取上一步刚初始化的 `State`，向 API Caller 提供只读请求。

#### 13 初始化 Zookeeper 竞争和 Leader 监测

两者分别是 contender 和 detector。前者参与 Zookeeper 中的 leader 竞争，与众多冗余的 master node 竞争成为活跃的 master。后者监测当前的活跃 master。

```cpp
Try<MasterContender*> contender_ = MasterContender::create(
      flags.zk, flags.master_contender);
Try<MasterDetector*> detector_ = MasterDetector::create(
      flags.zk, flags.master_detector);

```

分别使用这两个函数生成 contender 和 detector 进程。

#### 14 Authorizer 初始化

Authorizer 用于做用户访问控制，例如控制谁可以提交新框架。目前只支持单个 Authorizer，但从源代码

```cpp
if (authorizerNames.size() > 1) {
    EXIT(EXIT_FAILURE) << "Multiple authorizers not supported";
  }
  string authorizerName = authorizerNames[0];
```

可以明显看出，是预留支持多个 Authorizers 的。

在 Authorizer 初始化后，把它绑定到 `Libprocess` 上，为它提供鉴权服务。

#### 15 限制 agent 下线速率

这里设置一个 `RateLimiter`，用于限制一定时间内 agent 下线数量，防止大量 agent 同时下线。`RateLimiter` 本身用于设置一个进程发送特定消息的速率（详见 `3rdparty/libprocess/include/process/limiter.hpp`）。

#### 16 初始化 `Master` 对象

通过

```cpp
Master* master =
   new Master(
     allocator.get(),
     registrar,
     &files,
     contender,
     detector,
     authorizer_,
     slaveRemovalLimiter,
     flags);
```

将刚才所有阶段生成的对象传入构造函数，获得最终的 `Master` 进程。最后通过 `process::spawn(master);` 开始执行真正的 master 进程。

### Agent 的初始化

Agent 初始化过程与 master 有不少共通之处，其中从第 1 步到第 8 步都是一样的，此处略过。其他初始化过程较 master 更简单，下面按顺序列举。

* Systemd 状态更新：如果监测到当前 Linux 环境由 Shitstemd 管理，则调用相关函数更新该进程在 Systemd 中的状态。
* 初始化 Fetcher 和 Containerizer：Fetcher 用于将框架的运行环境先下载到 agent 所在机器。Containerizer 提供容器化的运行环境，实现隔离。
* 初始化 Master Detector：该进程用于找到 master。
* 初始化 Authorizer：与 master 类似，略过。
* 初始化 GC：agent 直接有框架任务运行，需要 GC 回收泄漏的资源。
* 初始化状态更新进程：该进程不断向 master 汇报当前可用资源等系统状态。
* 初始化系统资源估计进程：本组件和下一个 QoS 控制组建旨在提高资源利用率。本组件估计框架申请的资源中，有多少是事实闲置的，并把改信息提交给 agent 主进程。
* 初始化 QoS：上一个组件允许别的任务借用当前暂时闲置（但已经被分配给某框架）的资源。此时要保证真正拥有该资源的框架可以在需要时立即启用这些资源，这需要 QoS 进程监控，在拥有这些资源的框架性能下降时，及时停止借用资源的任务，把这些资源还回去。
* 创建 Agent 主进程

## Mesos 资源调度算法

在 master 的启动过程的分析中，可以看到默认的调度器是 HierarchicalDRF。继续阅读 `Allocator` 类的定义，可以看到有如下操作

```cpp
if (name == mesos::internal::master::DEFAULT_ALLOCATOR) {
  return HierarchicalDRFAllocator::create();
}
```

即初始化了一个 `HierarchicalDRFAllocator` 类。于是继续阅读该类相关的源代码（`src/master/allocator/mesos/hierarchical.hpp` 和 `src/master/allocator/mesos/hierarchical.cpp`），可以发现

```cpp
template <
  typename RoleSorter,
  typename FrameworkSorter,
  typename QuotaRoleSorter>
class HierarchicalAllocatorProcess;

typedef HierarchicalAllocatorProcess<DRFSorter, DRFSorter, DRFSorter>
HierarchicalDRFAllocatorProcess;
typedef MesosAllocator<HierarchicalDRFAllocatorProcess>
HierarchicalDRFAllocator;
```

该类只是从一个通用的 `MesosAllocator` 模版类定义出来的一个类。显然，核心的算法是在 `HierarchicalDRFAllocatorProcess` 中实现的。该类是由 `HierarchicalAllocatorProcess` 作为模版定义而来，其中 `RoleSorter`、`FrameworkSorter`、`QuotaRoleSorter` 都使用了 `DRFSorter`。事实上，`HierarchicalAllocatorProcess` 继承自 `MesosAllocatorProcess`，查看其构造函数，可以发现 `DRFSorter` 将被用来初始化 `roleSorter`、`quotaRoleSorter` 和 `frameworkSorterFactory`，是调度算法的核心。

`DRFSorter` 的源代码在 `src/master/allocator/sorter/drf/sorter.cpp`。DRF 维护系统总资源列表、当前已分配给各个框架的资源列表、系统已分配资源列表、每个框架主导资源需求比例（框架主导资源量除以系统该项资源总量）。通过 `DRFSorter` 可以维护、读取这个列表。而 `HierarchicalAllocatorProcess` 处理集群的事件，如新 agent 加入、新 framework 加入等，在遇到对应事件是，调用 `DRFSorter` 的相应方法，对 DRF 各个列表进行更新，相当于是 Mesos 集群与 DRF 算法之间通信的代理。DRF 有 paper 进行详解。

_主导资源_ 定义为某框架需求的资源中，量最大的那种。调度算法从主导资源需求最小的框架开始，一一为这些框架分配资源。

1. 找到主导资源最小的框架
2. 若当前系统资源可以满足这个框架，则运行；否则等待
3. 更新各列表
4. 回到第一步

我认为，这一算法保证了系统资源的高效利用。作为集群管理者，一个合理的预期是集群的资源可以尽量全部发挥作用。最好情况下，每一个框架使用的系统资源是平衡的（如占用 CPU 和 内存都是 1/3），这样系统资源可以全部利用。若一个框架大量占用某项系统资源（如内存），则若先运行它，可能导致剩余的内存不足以运行任何一个别的框架。而从主导资源最小的框架开始启动，保证了这种情况不会发生。

## 完成一个简单工作的框架

### Scheduler

使用豆瓣的 `PyMesos` 库。库实现了基本的通信，并以 hook 的形式提供用户编程接口。例如

```python
def on_offers(self, event):
    offers = event.get('offers', [])
    if offers:
        self.sched.resourceOffers(
            self, [self._dict_cls(offer) for offer in offers]
        )

    inverse_offers = event.get('inverse_offers', [])
    if inverse_offers:
        self.sched.inverseOffers(
            self, [self._dict_cls(offer) for offer in inverse_offers]
        )
```

`on_offers` 将在 Mesos 提供 offer 的时候被调用，此时会再调用用户实现的 `resourceOffers` 来决定要如何处理这个 offer。因此，用户只需要实现这部分逻辑即可。

在 scheduler 代码中，首先判断 offer 中的资源是否满足要求，

```python
for offer in offers:
    cpus = self.getResource(offer.resources, 'cpus')
    mem = self.getResource(offer.resources, 'mem')
    if cpus < TASK_CPU or mem < TASK_MEM:
        continue
```

若满足，则准备一个 task 并发送给 Mesos。然后，直接开始执行。

在 scheduler 程序启动时，用刚刚定义的 scheduler 类初始化 `MesosSchedulerDriver` 实例，该实例就是一个 scheduler。调用其 `.run()` 方法即开始工作。

### Executor

使用 `PyMesos` 库，executor 的编程方法也是类似，通过在类中实现 hook 对应的函数，并用它初始化 `MesosExecutorDriver`，得到的实例就是一个可用的 executor。这里实现 `launchTask` 方法，它在收到执行任务要求时调用，功能就是启动任务。它首先报告任务已经开始执行，然后执行任务本身，最后报告任务完成，然后退出。

这次实验，使用 `PyMesos`，实现的功能是在每一台 agent 机器上执行指定的命令。这个功能有实际需求，如大规模集群的运维等。虽然已经有 Ansible、Fabric 等工具实现类似功能，但在 Mesos 上实现也很有趣。之后，还可以给框架提供一个前端，通过网页输入命令并启动执行。

测试时，执行的命令是 `touch /root/done && echo hi >> /root/done`。若成功，应当在 `/root` 下出现 `done` 文件，内容为 `hi`。

代码上传在 [`homework-2/source`](https://github.com/yangl1996/os-practical/tree/master/homework-2/source) 目录。这个 framework 只是参考样例代码使用 `PyMesos` 的实现，且没有做异常处理。若有时间，将直接调用 Mesos 的 HTTP API 从 API 调用和处理开始实现。

### 运行截图

#### 任务运行状况

Scheduler 接收到 executor 更新的状态，并输出在 `stdout`。

![ss](https://github.com/yangl1996/os-practical/blob/master/homework-2/attachments/ss1.png?raw=true)

#### 任务效果

任务共执行 5 次，因此 `/root/done` 中有五行输出。

![ss](https://github.com/yangl1996/os-practical/blob/master/homework-2/attachments/ss2.png?raw=true)

#### Mesos 终端

![ss](https://github.com/yangl1996/os-practical/blob/master/homework-2/attachments/ss3.png?raw=true)

#### 资源消耗

![ss](https://github.com/yangl1996/os-practical/blob/master/homework-2/attachments/ss4.png?raw=true)
