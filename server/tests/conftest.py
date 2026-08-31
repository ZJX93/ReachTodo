"""测试全局配置。

**必须在任何 ``app.*`` 模块被导入之前生效** —— ``app.config.Settings`` 在模块
导入时一次性读取环境变量，之后不再重读。pytest 会先加载 conftest，
所以在这里设置环境变量是唯一可靠的时机。

这里只做一件事：把限流的受保护路径收窄到 ``/api/auth/login``。

原因：整个测试套件共享同一个 ASGI app（因而共享同一个进程内滑动窗口计数器），
而每个用例都要 ``POST /api/auth/register`` 注册一个独立用户以保证互不干扰。
用例数量增长后，注册请求总数会超过默认阈值（10 次/60 秒），
导致后加入的用例莫名收到 429 —— 这是测试基础设施的问题，不是被测逻辑的问题。

保留 ``/api/auth/login`` 受限是有意的：``test_api.py::test_rate_limit_on_login``
需要真实触发 429 来验证防爆破仍然生效。
"""

import os

os.environ.setdefault("RATE_LIMIT_PATHS", "/api/auth/login")
