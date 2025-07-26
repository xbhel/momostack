# Flink

## Watermark

Flink 中，当前事件使用的 watermark 是基于“历史上所有已到达事件中的最大时间戳”计算出的值，而不是当前事件的 timestamp，也不一定是上一条的 timestamp。

当前事件所看到的 watermark，是在它到来之前最后一次生成的 watermark。当前事件到来时的 watermark（ctx.timerService().currentWatermark()）是针对“上一条事件”或“更早事件”的最大时间戳 - 延迟；

当前事件本身的 timestamp 不会影响自己所看到的 watermark，只能影响后续事件的 watermark 值。

watermark 生成策略也影响 watermark 的推进行为:

如果 watermark 生成策略是基于 Periodic 的水印也不会立即推进，而是周期性的推进，如果是 Punctuated(onEvent) 的 watermark 则是 “历史上所有已到达事件中的最大时间戳”