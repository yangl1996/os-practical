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

与传统操作系统__相似__的有，

* 都涉及资源的监测、分配和调度
* 都需要处理多个任务共存，资源的合理利用问题

与传统操作系统__不同__的有，

* 传统操作系统，资源分配的协商只有两步：程序请求和系统同意（或拒绝）；而在 Mesos 上有三步，框架请求、系统提供 offer、框架选择使用（或不使用）
* 传统操作系统，内核是唯一的资源调度器；Mesos 上事实上有两层调度：Mesos master 将资源划分粗略给各个框架，各个框架自己的 scheduler 将获得的资源划分给要运行的 task
* 传统操作系统内核不涉及分布式的资源管理；而 Mesos 负责跟踪和分配一个分布式系统中的资源
* Mesos 上注册的“框架”和传统操作系统中提交的进程有本质区别：框架提供类似库的功能，为 task 提供通信、同步等功能，起到运行环境的角色，兼有资源分配的功能；而传统操作系统中提交的程序就是进程，操作系统才是运行环境

## Master 和 Agent 的初始化过程



## Mesos 资源调度算法



## 完成一个简单工作的框架
