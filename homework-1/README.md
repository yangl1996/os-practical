# Homework 1

## Task 1. Datacenter Operating System

Datacenter operating systems are developed to

- support commodity computing devices
- enable multiple parallel programming frameworks coexist on the same cluster
- handle failover
- schedule resources _among_ frameworks
- act as a thing resource sharing layer between programming frameworks and bare metal machines

## Task 2. Containers and VMs

### Containers

Containerization is a concept which became popular only several years ago, but the underlying technology has long been available in the UNIX/Linux world (`chroot` for example). It became widely-known when Docker, the first user-friendly interface to the containerization tools in the Linux kernel, was released. Containerization focus on packaging and isolating the entire runtime environment with the application itself, enabling much easier deployment and migration. Different containers on a single physical machine share a kernel, but the filesystem root, the user id space and the init process are all independent. Application are scheduled directly by the kernel of the host machine, reducing the overhead to barely minimal.

Although the original purpose of containerization is to aid the DevOps's work, nowadays it is also used to run the whole OS, such as LXC (Linux Container) and OpenVZ.

### VMs

Virtual machines have been around for a long time. A "hypervisor" on the host machine schedules hardware resources among multiple virtual machines, acting as a "proxy" to the bare metal. Ancient hypervisors are implemented as userspace applications, which has relatively higher overhead. But recent hypervisors are built right into the kernel of the host OS, enabling much more efficient virtualization.

Typical virtual machine implementations include KVM (kernel-based VM), VMware and Hyper-V.

### Similarity

- Both technology are methods of operating-system-level virtualization.
- Both can improve machine density in a cluster or datacenter.
- As VMs' overhead become lower and containers become more isolated, the boundary between the two is blurring.  

### Difference

- Efficiency: Containers are higher, as they run directly on the kernel of the host machine.
- Isolation: Containers are less isolated, as they share a single kernel.
- Control: VMs offer more control over virtualized machines.
- Density: Containers are higher, as they are simply applications in different FS roots and user namespaces.

## Task 3. Set up Mesos

Steps I took are listed below.

First start two VMs. The hostnames are `mesos0` and `mesos1` at `192.168.1.81` and `192.168.1.80` respectively.

```bash
# get the source code
git clone https://git-wip-us.apache.org/repos/asf/mesos.git
cd mesos
git checkout 1.1.0

# install dependencies
sudo apt install ...

# build
./bootstrap
mkdir build
cd build
../configure
make -j 2
make check -j 2
sudo make install -j 2

# add /usr/local/lib to ld search path
sudo echo '/usr/local/bin' > /etc/ld.so.conf.d/mesos-libs.conf
sudo ldconfig
```

Then start the master and the agents. I started one master and two agents.

On `mesos0`:
```bash
sudo mesos-master --ip=192.168.1.81 --work_dir=/home/yangl1996/mesos-work
sudo mesos-agent --ip=192.168.1.81 --master=192.168.1.81:5050 --work_dir=/home/yangl1996/mesos-work

```

On `mesos1`:
```bash
sudo mesos-agent --ip=192.168.1.80 --master=192.168.1.81:5050 --work_dir=/home/yangl1996/mesos-work
```

## Task 4. Spark on Mesos

### Deployment

To run Spark on the Mesos cluster, I took the following steps.

```bash
# get the spark prebuilt binary
wget 'http://d3kbcqa49mib13.cloudfront.net/spark-2.1.0-bin-hadoop2.7.tgz'
mv spark-2.1.0-bin-hadoop2.7.tgz /home/yangl1996/spark-release/

# on the master machine, untar the package
tar xf spark-2.1.0-bin-hadoop2.7.tgz

# configure
echo 'export MESOS_NATIVE_JAVA_LIBRARY=/usr/local/bin/libmesos.so' >> conf/spark-env.sh
echo 'export SPARK_EXECUTOR_URI=file:///home/yangl1996/spark-release/spark-2.1.0-bin-hadoop2.7.tgz' >> conf/spark-env.sh
echo 'export MASTER=mesos://192.168.1.81:5055' >> conf/spark-env.sh
echo 'spark.executor.uri file:///home/yangl1996/spark-release/spark-2.1.0-bin-hadoop2.7.tgz' >> conf/spark-default.conf
```

Then I managed to generate a big text file.

```bash
wget norvig.com/big.txt

# make it 5x the size
cat big.txt >> huge.txt
cat big.txt >> huge.txt
cat big.txt >> huge.txt
cat big.txt >> huge.txt
cat big.txt >> huge.txt

rm big.txt
```

Good to go.

### Results

I ran the WordCount program with the following command.

```bash
# 2 cores for example
./bin/spark-submit\
  --class org.apache.spark.examples.JavaWordCount\
  --master mesos://192.168.1.81:5050\
  --executor-memory 600M\
  --total-executor-cores 2\
  file:///home/yangl1996/spark-2.1.0-bin-hadoop2.7/examples/jars/spark-examples_2.11-2.1.0.jar\
  file:///home/yangl1996/spark-data/huge.txt
```

I roughly checked the output to make sure that all runs completed without error. Below is the time and resource consumption.

![results](https://github.com/yangl1996/os-practical/blob/master/homework-1/attachments/result-sample.png?raw=true "Outputs")

More screenshots available in the [appendix](https://github.com/yangl1996/os-practical/tree/master/homework-1#screenshots-of-experiment-results).

| # Cores | Memory Usage    | Time  |
| :------------- | :------------- | :------- |
| 1       | 984MB/1000MB      |   6s     |
| 2      | 984MB/1000MB       |     8s     |
| 4       | 984MB/1000MB       |      12s    |

When 1 or 2 cores are allocated, only one machine is used. When 4 cores are allocated, both machines are used.

It is surprising that the time consumption increases as the core number increases. I think that it is because that the input size is too small (30ish-MB) to make multicore execution beneficial. The overhead of data exchange causes the time increase. If more powerful machines are available, redoing the experiment with much bigger input may clarify this question.

## Task 5. Comments

I think the installation process is smooth enough, and it is easy to get started. However, as I dug into the documentation, I found no instructions on a "best practice" deployment. For example, there is no guide on securing the installation.

About the softwares themselves, while the GUI is nice, I think there is huge need for a better command line interface. Also, the softwares are not well integrated into the operating system. I think both aspects need improvements to attract more users.

## Appendix

### Screenshots of Experiment Results

#### 1 Cores

![1core](https://github.com/yangl1996/os-practical/blob/master/homework-1/attachments/1cores-mesos.png?raw=true "Screenshots")

![1core](https://github.com/yangl1996/os-practical/blob/master/homework-1/attachments/1cores-term.png?raw=true "Screenshots")

![1core](https://github.com/yangl1996/os-practical/blob/master/homework-1/attachments/1cores-resource.png?raw=true "Screenshots")

#### 2 Cores

![1core](https://github.com/yangl1996/os-practical/blob/master/homework-1/attachments/2cores-mesos.png?raw=true "Screenshots")

![1core](https://github.com/yangl1996/os-practical/blob/master/homework-1/attachments/2cores-term.png?raw=true "Screenshots")

![1core](https://github.com/yangl1996/os-practical/blob/master/homework-1/attachments/2cores-resource.png?raw=true "Screenshots")

#### 4 Cores

![1core](https://github.com/yangl1996/os-practical/blob/master/homework-1/attachments/4cores-mesos.png?raw=true "Screenshots")

![1core](https://github.com/yangl1996/os-practical/blob/master/homework-1/attachments/4cores-term.png?raw=true "Screenshots")

![1core](https://github.com/yangl1996/os-practical/blob/master/homework-1/attachments/4cores-resource.png?raw=true "Screenshots")
