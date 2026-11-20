"""48kHz 对白插进 44.1kHz 工程的重采样流水线。

本模块把重采样中容易出错的几个环节抽成纯函数，便于组合与测试：
时间基步长、抗混叠截止、多声道相位、分块重叠、延迟补偿、设备系数、
峰值限幅、抖动幅度、seek 状态重置、多轨一致性、软硬去重、缓存隔离
以及读写线程同步。
"""

def step_ratio(in_rate, out_rate):
    """可变时间基步长：每个输入样本对应的输出样本数。

    不能对可变帧率素材写死 1.0；步长必须由实际输入/输出采样率算出，
    否则对白会一会儿快一会儿慢。
    """
    if in_rate <= 0 or out_rate <= 0:
        raise ValueError("sample rates must be positive")
    return out_rate / in_rate


def anti_alias_cutoff(rate, ratio):
    """抗混叠截止频率。

    截止频率跟随实际转换比例，而不是写死成输入采样率的一半；
    降采样时先低通再抽取，避免高频折返到可听频段。
    """
    return rate * ratio


def phase_drift(channel, base):
    """多声道相位差。

    各声道必须共享同一时间基，这里返回该声道相对基准声道的偏差，
    用于检测/校正声道间的相位漂移。
    """
    return abs(base - channel)


def block_overlap(block, overlap):
    """块重叠：相邻块之间应保留的 hop（新样本数）。

    相邻块重叠 ``overlap`` 个样本，块边界才不会有咔哒声。
    """
    if overlap > block:
        raise ValueError("overlap must not exceed block size")
    return block - overlap


def latency_comp(samples, ratio):
    """重采样延迟补偿。

    滤波器组引入的延迟按比例折算到输出时间基，用于音画对齐。
    """
    if ratio == 0:
        raise ValueError("ratio must be non-zero")
    return samples / ratio


def peak_limit(value, ceiling):
    """峰值限幅：对称地钳制到 +/-ceiling，防止溢出削波。"""
    ceiling = abs(ceiling)
    return max(-ceiling, min(ceiling, value))


def dither_amplitude(bits):
    """抖动幅度：1 LSB 对应 2^-bits。

    抖动应随位深缩放，而不是固定幅度，否则安静段底噪会很明显。
    """
    if bits <= 0:
        raise ValueError("bits must be positive")
    return 2.0 ** (-bits)


def reset_state(seek, state):
    """seek 后重置重采样器状态。

    seek 会打断连续的重采样历史；不清空滤波器/相位状态，前一段的
    尾音就会混进新位置。非 seek 时原样保留状态。
    """
    return None if seek else state


def multitrack_ratio(tracks, ratio):
    """多轨重采样：所有轨道使用同一比例，保证时长一致。

    ``tracks`` 可以是轨道数量或轨道集合；伴奏轨不能漏掉。
    """
    count = len(tracks) if hasattr(tracks, "__len__") else int(tracks)
    return [ratio] * count


def software_hardware_dedupe(software, hardware):
    """软硬去重：硬件重采样可用时不再跑软件重采样。

    返回软件重采样是否应执行，避免同一样本被处理两次造成二次失真。
    """
    return bool(software) and not bool(hardware)


def cache_key(path, rate):
    """缓存隔离键：路径 + 采样率。

    只按文件路径缓存会在切换采样率后复用旧 PCM，必须把采样率纳入键。
    """
    return f"{path}:{rate}"


def thread_sync(read, write):
    """线程同步：读指针不得越过写指针。

    重采样线程与混音线程共享缓冲时，只有 ``read <= write`` 才是安全
    状态；否则说明读指针追上了写指针，缓冲已被掏空。
    """
    return bool(read <= write)


def timebase_ratio(vfr, base):
    """时间基比例：可变帧率时间戳换算到基准时间基。"""
    if base == 0:
        raise ValueError("base timebase must be non-zero")
    return vfr / base


def sample_at(index, ratio):
    """重采样位置：按时间基比例把输出索引映射回输入索引。"""
    return index * ratio


def device_coeff(rate, base):
    """设备系数：设备采样率变化后滤波器系数的重建比例。

    系数按基准采样率设计；切换到 ``rate`` 后，归一化截止频率需乘以
    ``base / rate`` 重新生成，否则声音会变闷。
    """
    if rate <= 0 or base <= 0:
        raise ValueError("sample rates must be positive")
    return base / rate
