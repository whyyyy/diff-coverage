# diff-coverage
对jacoco覆盖率报告进行修改，添加增量覆盖率

# 结果示例
首页表格最后添加增量覆盖率比例
![pic](https://github.com/whyyyy/diff-coverage/blob/master/pics/chart.png)
代码页面添加增量已覆盖（蓝色钻石）和增量未覆盖（灰色钻石）标记
![pic](https://github.com/whyyyy/diff-coverage/blob/master/pics/code.png)

# 参数详情
-d, -dir 工程根目录
-o, -old_version 指定对比的旧版本号
-n, -new_version 指定对比的新版本号（默认当前版本）
-r, -report_dir jacoco报告路径

# 使用方法
1. 生成jacoco覆盖率报告
2. 设置参数，执行main.py
