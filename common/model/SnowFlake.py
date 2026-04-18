"""
文件名: SnowFlake.py
作者: yangchunhui
创建日期: 2026/2/5
联系方式: chunhuiy20@gmail.com
版本号: 1.0
更改时间: 2026/2/5 17:43
描述:
    基于 Twitter Snowflake 算法的分布式唯一 ID 生成器。通过组合时间戳、数据中心 ID、工作节点 ID 和序列号生成全局唯一的 64 位整数 ID，支持高并发场景下的 ID 生成，具有单调递增、线程安全等特性。

修改历史:
    2026/2/5 17:43 - yangchunhui - 初始版本

依赖:
    - time: 用于获取当前时间戳（毫秒级）
    - threading: 提供线程锁，保证多线程环境下 ID 生成的线程安全性

使用示例:
"""
import time
import threading


# noinspection PyMethodMayBeStatic
class SnowflakeIDGenerator:
    def __init__(self, worker_id=1, datacenter_id=1):
        # 自定义起始时间戳（毫秒）
        self.epoch = 1704067200000  # 2024-01-01

        self.worker_id = worker_id
        self.datacenter_id = datacenter_id
        self.sequence = 0
        self.last_timestamp = -1
        self.lock = threading.Lock()

        self.worker_id_bits = 5
        self.datacenter_id_bits = 5
        self.sequence_bits = 12

        self.max_worker_id = -1 ^ (-1 << self.worker_id_bits)
        self.max_datacenter_id = -1 ^ (-1 << self.datacenter_id_bits)
        self.sequence_mask = -1 ^ (-1 << self.sequence_bits)

        self.worker_id_shift = self.sequence_bits
        self.datacenter_id_shift = self.sequence_bits + self.worker_id_bits
        self.timestamp_shift = self.sequence_bits + self.worker_id_bits + self.datacenter_id_bits

        if self.worker_id > self.max_worker_id or self.datacenter_id > self.max_datacenter_id:
            raise ValueError("worker_id 或 datacenter_id 超出范围")

    def _time_gen(self):
        return int(time.time() * 1000)

    def _wait_for_next_millis(self, last_timestamp):
        timestamp = self._time_gen()
        while timestamp <= last_timestamp:
            timestamp = self._time_gen()
        return timestamp

    def generate(self):
        with self.lock:
            timestamp = self._time_gen()

            if timestamp < self.last_timestamp:
                raise Exception("系统时间回拨，拒绝生成 ID")

            if timestamp == self.last_timestamp:
                self.sequence = (self.sequence + 1) & self.sequence_mask
                if self.sequence == 0:
                    timestamp = self._wait_for_next_millis(self.last_timestamp)
            else:
                self.sequence = 0

            self.last_timestamp = timestamp

            return (
                    ((timestamp - self.epoch) << self.timestamp_shift)
                    | (self.datacenter_id << self.datacenter_id_shift)
                    | (self.worker_id << self.worker_id_shift)
                    | self.sequence
            )
